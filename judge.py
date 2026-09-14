"""LLM judge that grades a coach call the way the HUMAN graders do.

This judge scores against the *round-2 calibration* rubric (calibration/rubric.py,
v2 DECIDED) — the same 13 dimensions (incl. the 4 feedback brackets), the same
PASS / FAIL / NOT_OBSERVED vocabulary, and the same "would you recommend this
coach?" overall verdict that labelers fill in the calibration web app. Output is
therefore drop-in comparable to a human `assignment` row, which is exactly what
the Phase-2 calibration needs (target 80%+ agreement).

Design:
  - The rubric is IMPORTED from calibration/rubric.py — single source of truth,
    no re-transcription. Edit the rubric there and this judge follows automatically.
  - One judge = one PROMPT (JUDGE_VERSION below). The prompt is the thing you
    tune to match the humans; bump JUDGE_VERSION when you change it so old and
    new gradings stay distinguishable in the output file.
  - Output appends to judge_eval.jsonl, one JSON per line, keyed by
    (row, judge) so several prompt variants can coexist. Resumable + parallel,
    same as analyze.py.

Each line mirrors a human grade:
  scores       {dim_id: "pass"|"fail"|"not_observed"}      <- assignment.scores_json
  notes        {dim_id: "<why>"}                            <- assignment.notes_json
  evidence     {dim_id: {"good":[...], "bad":[...]}}        <- assignment.evidence_json
  overall_quality  "pass"|"fail"   (would you recommend this coach?)
  overall_notes    "<summary>"

Usage:
    python judge.py                       # sample (default 5) of the PCPT file
    python judge.py --limit 50
    python judge.py --all --yes --workers 8
    python judge.py --file sim_calls.tsv
    python judge.py --judge strict_v2     # tag a prompt variant (after you edit the prompt)

Key from .env (ANTHROPIC_API_KEY).
"""

import argparse
import csv
import json
import sys
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Literal

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, Field, create_model

# Import the human rubric directly so the judge and the graders score the same thing.
sys.path.insert(0, str(Path(__file__).parent / "calibration"))
import rubric as R  # noqa: E402

load_dotenv()
csv.field_size_limit(10**7)

MODEL = "claude-opus-4-8"
JUDGE_VERSION = "v2"          # bump when you change the prompt; recorded on every line
DEFAULT_FILE = "pcpt_mock_interview_v2.tsv"
TRANSCRIPT_COL = "Transcript"
OUTPUT_FILE = "judge_eval.jsonl"

SECTION_NAMES = dict(R.SECTIONS)
DIM_IDS = [d["id"] for d in R.DIMENSIONS]

_print_lock = threading.Lock()
_file_lock = threading.Lock()

Verdict = Literal["pass", "fail", "not_observed"]


def build_rubric_text() -> str:
    """Render the rubric the way a grader sees it: definition, watch-for, and the
    real pass/fail example anchors. Calibration parity — the judge reads what the
    humans read."""
    lines = []
    for sec_key, sec_name in R.SECTIONS:
        lines.append(f"\n### {sec_name}")
        for d in R.DIMENSIONS:
            if d["section"] != sec_key:
                continue
            lines.append(f"\n[{d['id']}] {d['name']}")
            lines.append(f"  PASS means: {d['definition']}")
            lines.append(f"  FAIL / watch for: {d['watch_for']}")
            if d.get("not_observed"):
                lines.append(f"  NOT_OBSERVED when: {d['not_observed']}")
            if d.get("pass_example"):
                lines.append(f"  Pass example:\n    {d['pass_example'].strip()}")
            if d.get("fail_example"):
                lines.append(f"  Fail example:\n    {d['fail_example'].strip()}")
    return "\n".join(lines)


SYSTEM_PROMPT = f"""\
You are an expert evaluator standing in for a trained human grader, scoring an AI
job-interview coach against a call-evaluation rubric. Grade EXACTLY as the human
graders are instructed to.

Context: "CEO" is the Center for Employment Opportunities, a reentry-employment
nonprofit. Participants (often returning from incarceration) call an AI Voice
Coach by phone to practice mock interviews. In the transcript, "AI:" is the
COACH and "User:" is the participant. You are grading the COACH — the "AI:"
turns. These are auto-transcribed phone calls, so some lines contain
transcription errors; use your best judgment and don't penalize the coach for an
obvious ASR glitch.

How to grade, for EACH dimension below, give one holistic verdict from your read
of the WHOLE transcript (not a tally of snippets):
  - "pass"          = the coach demonstrated this behavior well.
  - "fail"          = the coach had a clear chance to show this behavior and did
                      it poorly or not at all.
  - "not_observed"  = there was NO opportunity for this behavior to show up at
                      all in this call. (Not the same as fail.)

Be a calibrated, skeptical grader. Do NOT inflate to be nice and do NOT inflate
to "balance things out" — this coach has real weaknesses, and there is no target
pass rate. Judge each dimension on its own merits against the rubric. This is a
voice-only transcript: judge only what is audible/textual, never anything visual.

For every dimension also provide:
  - why:   one sentence justifying the verdict (what the coach did or failed to do).
  - quote: a short verbatim quote from the transcript (keep the AI:/User: label)
           that supports the verdict. For a "fail", quote the missed/poor moment;
           for a "pass", quote the moment it did well. Use "" for not_observed.

Finally give an overall verdict — "Would you recommend this coach to a
participant?":
  - would_recommend: "pass" or "fail" (your holistic read of the whole call).
  - summary: 2-3 sentences on the coach's overall performance.

RUBRIC ({len(R.DIMENSIONS)} dimensions):
{build_rubric_text()}"""


class DimResult(BaseModel):
    dimension: str = Field(description="The dimension id being graded.")
    verdict: Verdict = Field(description="pass, fail, or not_observed.")
    why: str = Field(description="One sentence justifying the verdict.")
    quote: str = Field(description="Short supporting quote (keep AI:/User: label); '' if not_observed.")


# Output model: an explicit verdict field per dimension (so the schema forces the
# model to grade ALL of them), plus a parallel list carrying the why+quote, plus
# the overall recommend verdict.
_fields = {
    "would_recommend": (Literal["pass", "fail"],
                        Field(description="Would you recommend this coach? Holistic pass/fail.")),
    "summary": (str, Field(description="2-3 sentences on overall coach performance.")),
}
for _d in R.DIMENSIONS:
    _fields[_d["id"]] = (Verdict, Field(description=_d["name"]))
_fields["details"] = (list[DimResult],
                      Field(description="One entry per dimension with its verdict, why, and a quote."))
CoachGrade = create_model("CoachGrade", **_fields)


def reshape(grade) -> dict:
    """Turn the flat model output into the human-grader shape (scores/notes/evidence)."""
    data = grade.model_dump()
    detail = {d["dimension"]: d for d in data.get("details", [])}
    scores, notes, evidence = {}, {}, {}
    for cid in DIM_IDS:
        verdict = data.get(cid)
        if verdict is None:
            continue
        scores[cid] = verdict
        d = detail.get(cid, {})
        why = (d.get("why") or "").strip()
        if why:
            notes[cid] = why
        quote = (d.get("quote") or "").strip()
        if quote:
            # mirror assignment.evidence_json's good/bad buckets
            bucket = "good" if verdict == "pass" else "bad"
            evidence[cid] = {"good": [], "bad": []}
            evidence[cid][bucket] = [quote]
    return {
        "scores": scores,
        "notes": notes,
        "evidence": evidence,
        "overall_quality": data["would_recommend"],
        "overall_notes": data["summary"],
    }


def load_rows(tsv_path: Path):
    with open(tsv_path, newline="", encoding="utf-8") as fh:
        for i, row in enumerate(csv.DictReader(fh, delimiter="\t")):
            transcript = (row.get(TRANSCRIPT_COL) or "").strip()
            if transcript:
                yield i, row, transcript


def already_done(path: Path, judge: str, source_file: str) -> set:
    """Rows of THIS source file already graded BY THIS JUDGE (a different prompt
    variant, or a different source file, re-runs). Keying on source_file matters
    because row indices restart at 0 for every file and would otherwise collide."""
    done = set()
    if path.exists():
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    if rec.get("judge") == judge and rec.get("source_file") == source_file:
                        done.add(rec["row"])
                except Exception:
                    pass
    return done


def evaluate(client: anthropic.Anthropic, transcript: str):
    response = client.messages.parse(
        model=MODEL,
        max_tokens=6000,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Grade the coach in this call:\n\n<transcript>\n{transcript}\n</transcript>",
        }],
        output_format=CoachGrade,
    )
    return response.parsed_output


def main() -> None:
    parser = argparse.ArgumentParser(description="Grade the AI Voice Coach like a human grader.")
    parser.add_argument("--file", default=DEFAULT_FILE)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--all", action="store_true", help="Grade every row (confirms first unless --yes).")
    parser.add_argument("--workers", type=int, default=8, help="Parallel judge calls (default 8).")
    parser.add_argument("--judge", default=JUDGE_VERSION,
                        help="Judge/prompt label recorded on each line (default JUDGE_VERSION).")
    parser.add_argument("--yes", action="store_true", help="Skip the cost confirmation.")
    args = parser.parse_args()

    tsv_path = Path(args.file)
    if not tsv_path.exists():
        print(f"File not found: {tsv_path}")
        sys.exit(1)

    out_path = Path(OUTPUT_FILE)
    done = already_done(out_path, args.judge, tsv_path.name)
    rows = [r for r in load_rows(tsv_path) if r[0] not in done]
    if not args.all:
        rows = rows[: args.limit]

    if not rows:
        print(f"Nothing to do (all selected rows already graded by judge '{args.judge}').")
        return

    if args.all and not args.yes and sys.stdin.isatty():
        ans = input(f"About to grade {len(rows)} transcripts (~${len(rows) * 0.05:.0f}). Continue? [y/N] ")
        if ans.strip().lower() != "y":
            print("Cancelled.")
            sys.exit(0)

    if done:
        print(f"Resuming judge '{args.judge}' — {len(done)} already graded, {len(rows)} to go.")
    print(f"Grading {len(rows)} transcripts as judge '{args.judge}' with {args.workers} workers...")

    client = anthropic.Anthropic(max_retries=5)
    recommend_counts: Counter = Counter()
    fail_counts: Counter = Counter()   # per-dimension FAIL tally, for a quick weakest-dims read
    obs_counts: Counter = Counter()    # times each dim was observed (pass+fail)
    completed = 0
    total = len(rows)

    def work(item):
        idx, row, transcript = item
        grade = evaluate(client, transcript)
        return idx, row.get("CEO ID", "?"), reshape(grade)

    with open(out_path, "a", encoding="utf-8") as out, \
            ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(work, item): item[0] for item in rows}
        for fut in as_completed(futures):
            idx = futures[fut]
            try:
                idx, ceo_id, data = fut.result()
            except anthropic.AuthenticationError:
                print("Auth failed — check ANTHROPIC_API_KEY in .env.")
                sys.exit(1)
            except Exception as e:
                with _print_lock:
                    print(f"  ! row {idx} failed: {type(e).__name__}: {e}")
                continue

            with _file_lock:
                out.write(json.dumps({
                    "row": idx, "ceo_id": ceo_id, "judge": args.judge,
                    "model": MODEL, "source_file": tsv_path.name, **data,
                }) + "\n")
                out.flush()

            recommend_counts[data["overall_quality"]] += 1
            for cid, verdict in data["scores"].items():
                if verdict in ("pass", "fail"):
                    obs_counts[cid] += 1
                if verdict == "fail":
                    fail_counts[cid] += 1

            completed += 1
            with _print_lock:
                nfail = sum(1 for v in data["scores"].values() if v == "fail")
                print(f"[{completed}/{total}] row {idx} CEO {ceo_id} · "
                      f"recommend={data['overall_quality']:<4} fails={nfail}/{len(data['scores'])}")

    print(f"\n{'=' * 72}\nDONE — {completed} graded by judge '{args.judge}'")
    print("  would_recommend:", dict(recommend_counts))
    rates = sorted(
        ((fail_counts[c] / obs_counts[c], c, obs_counts[c]) for c in obs_counts),
        key=lambda x: -x[0],
    )
    print("\n  weakest dimensions (FAIL rate among calls where observed):")
    for rate, cid, n in rates[:10]:
        print(f"      {rate * 100:5.0f}%  {cid}  (n={n})")
    print(f"\n  appended to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
