#!/usr/bin/env python3
"""
run_corpus_hero.py — score a transcript corpus with the CERTIFIED HERO judges.

Unlike temp_judge_suite/run_corpus_temp.py (which runs the older *_temp.yaml v1
hypotheses), this runs the calibrated CHAMPION prompts in judge-suite/prompts/
via prompt_adapter, so the corpus is scored with exactly the judges that were
hill-climbed against the human consensus.

Judge set (default): every *_hero.yaml in judge-suite/prompts/ PLUS Grader B's
limits_the_load_v2.md. That is:
    adapts_when_stuck, drives_practice, makes_it_a_dialogue, pii,
    quality_conversational_flow, reentry_appropriate_framing,
    scaffolds_then_fades, limits_the_load
kind_delivery and the feedback suite have no hero and are excluded automatically.
Pass --prompts <file...> to run a specific prompt (or subset) instead of the
default hero set — same calibrated layout, appended to the same --out.

Corpus: reconstructed from the full cleaned-data TSV by filtering to
'PCPT mock interview v2' and numbering the rows 0..824 (transcript_id = index),
which matches the original pcpt_mock_interview_v2 numbering that
temp_judge_suite/stratified_ids.txt indexes into.

MESSAGE LAYOUT: calibration-faithful — per-dimension instructions in the SYSTEM
role, transcript in the USER message, temperature=0 (matches eval_harness_v2 /
pii_probe). cache_control on the system block caches each judge's instructions
across the transcripts it scores. (An earlier transcript-first caching layout is
NOT used — see score_one for why it broke instruction-following.)

MODEL: defaults to claude-sonnet-4-6 — the model the heroes were calibrated on.
Override with --model only if you know what you're doing.

Run from judge-suite/scripts/:
    python run_corpus_hero.py --limit 5                 # smoke test
    python run_corpus_hero.py --ids-file ../../temp_judge_suite/stratified_ids.txt
    python run_corpus_hero.py --all --yes --workers 8

Resumable: existing (transcript_id, dimension_id) rows in --out are skipped.
Key from .env (ANTHROPIC_API_KEY).
"""

import argparse
import csv
import glob
import json
import os
import re
import sys
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from prompt_adapter import load_prompt_spec, norm_label

SCRIPTS_DIR = Path(__file__).resolve().parent
SUITE_DIR = SCRIPTS_DIR.parent                 # judge-suite/
REPO_ROOT = SUITE_DIR.parent                   # ceo_voice_coach/
PROMPTS_DIR = SUITE_DIR / "prompts"

load_dotenv(REPO_ROOT / ".env")
csv.field_size_limit(10**7)

DEFAULT_CORPUS = REPO_ROOT / "Output - Participant training assistants - Cleaned Data All.tsv"
PCPT_ASSISTANT = "PCPT mock interview v2"
TRANSCRIPT_COL = "Transcript"
ASSISTANT_COL = "Assistant Name"
LIVE_ID_COL = "call_id"          # marks a live A/B calls TSV (ids are call_ids)
DEFAULT_OUT = SUITE_DIR / "outputs" / "corpus_hero_results.csv"
FIELDS = ["transcript_id", "dimension_id", "result", "evidence", "reasoning"]

_print_lock = threading.Lock()
_file_lock = threading.Lock()
_usage = defaultdict(int)


def hero_prompt_paths():
    """All *_hero.yaml champions + Grader B's limits_the_load_v2.md, sorted."""
    paths = sorted(glob.glob(str(PROMPTS_DIR / "*_hero.yaml")))
    md = PROMPTS_DIR / "limits_the_load_v2.md"
    if md.exists():
        paths.append(str(md))
    return paths


def robust_parse(raw_text):
    """Tolerant JSON parse: strip code fences, drop trailing commas, and — when
    the model appends prose AFTER the JSON object (the 'Extra data' error) —
    decode just the first {...} object and ignore the rest."""
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    for candidate in (text, re.sub(r",(\s*[}\]])", r"\1", text)):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    start = text.find("{")
    if start != -1:
        for candidate in (text[start:], re.sub(r",(\s*[}\]])", r"\1", text[start:])):
            try:
                return json.JSONDecoder().raw_decode(candidate)[0]
            except json.JSONDecodeError:
                pass
    raise ValueError(f"could not parse JSON from: {raw_text[:200]!r}")


def load_pcpt_transcripts(tsv_path):
    """Filter the cleaned-data TSV to PCPT mock interviews and number them
    0..N-1 in file order (transcript_id = index), matching the original
    pcpt_mock_interview_v2 numbering."""
    out = []
    with open(tsv_path, newline="", encoding="utf-8") as fh:
        idx = 0
        for row in csv.DictReader(fh, delimiter="\t"):
            if (row.get(ASSISTANT_COL) or "").strip() != PCPT_ASSISTANT:
                continue
            text = (row.get(TRANSCRIPT_COL) or "").strip()
            if text:
                out.append((str(idx), text))
            idx += 1
    return out


def load_live_transcripts(tsv_path):
    """Live A/B calls TSV (from pull_labeling_set.py): transcript_id = call_id,
    so scores join straight back to Supabase and to the `arm` column. Unlike the
    PCPT corpus there is no assistant filter — every row is a live call."""
    out = []
    with open(tsv_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            text = (row.get(TRANSCRIPT_COL) or "").strip()
            cid = (row.get(LIVE_ID_COL) or "").strip()
            if text and cid:
                out.append((cid, text))
    return out


def load_transcripts(tsv_path):
    """Dispatch on shape: a TSV carrying a `call_id` column is the live A/B
    corpus; anything else is the PCPT cleaned-data export."""
    with open(tsv_path, newline="", encoding="utf-8") as fh:
        header = next(csv.reader(fh, delimiter="\t"), [])
    if LIVE_ID_COL in header:
        return load_live_transcripts(tsv_path)
    return load_pcpt_transcripts(tsv_path)


def already_done(path):
    done = set()
    if Path(path).exists():
        with open(path, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                done.add((r["transcript_id"], r["dimension_id"]))
    return done


def score_one(client, model, spec, transcript_text):
    """One hero-judge call, using the SAME message layout the judges were
    calibrated on (eval_harness_v2 / pii_probe): the per-dimension instructions
    go in the SYSTEM role and the transcript in the USER message, temperature=0.

    An earlier caching layout (transcript FIRST in a cache_control'd block,
    instructions in a trailing user block, NO system prompt) measurably degraded
    instruction-following at full-transcript scale — e.g. pii_v4_hero's CEO-ID
    verification-readback exemption was ignored and 26 corpus calls FAILed that
    score N/A under the calibrated layout. Caching wants the transcript first
    (shared prefix across judges) but correctness wants the instructions first in
    system; they conflict, and correctness wins. cache_control on the SYSTEM block
    still caches each judge's instructions across the transcripts it scores."""
    system_text, user_text = spec.build_messages(transcript_text)
    kwargs = dict(
        model=model, max_tokens=1024, temperature=0,
        system=[{"type": "text", "text": system_text,
                 "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_text}],
    )
    try:
        msg = client.messages.create(**kwargs)
    except anthropic.BadRequestError as e:
        if "temperature" in str(e).lower():
            kwargs.pop("temperature")  # model rejects temperature — retry without
            msg = client.messages.create(**kwargs)
        else:
            raise
    u = msg.usage
    with _file_lock:
        _usage["in"] += u.input_tokens
        _usage["out"] += u.output_tokens
        _usage["cache_write"] += getattr(u, "cache_creation_input_tokens", 0) or 0
        _usage["cache_read"] += getattr(u, "cache_read_input_tokens", 0) or 0
    data = robust_parse(msg.content[0].text)
    result = norm_label(spec.extract_result(data))
    if result not in ("PASS", "FAIL", "N/A"):
        raise ValueError(f"bad result value: {spec.extract_result(data)!r}")
    data["_result"] = result
    return data


def main():
    ap = argparse.ArgumentParser(description="Run the certified hero judges over a corpus (with caching).")
    ap.add_argument("--file", default=str(DEFAULT_CORPUS), help="Cleaned-data TSV (PCPT rows are filtered out of it), "
                                                                "or a live A/B calls TSV (detected by its call_id column).")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--ids-file", help="File of transcript_ids to score — overrides --limit/--all.")
    ap.add_argument("--prompts", nargs="+", help="Explicit prompt file(s) to run instead of the default hero set "
                                                 "(e.g. ../prompts/makes_it_a_dialogue_v1.yaml). Same calibrated layout.")
    ap.add_argument("--workers", type=int, default=8, help="Transcripts scored in parallel (default 8).")
    ap.add_argument("--model", default="claude-sonnet-4-6", help="Judge model (default = the heroes' calibration model).")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--yes", action="store_true")
    args = ap.parse_args()

    corpus = Path(args.file)
    if not corpus.exists():
        print(f"Corpus file not found: {corpus}"); sys.exit(1)

    prompt_paths = args.prompts if args.prompts else hero_prompt_paths()
    specs = []  # (dimension_id, PromptSpec)
    for p in prompt_paths:
        spec = load_prompt_spec(p)
        specs.append((spec.dimension, spec))
    if not specs:
        print(f"No prompts found ({'--prompts' if args.prompts else PROMPTS_DIR})"); sys.exit(1)

    transcripts = load_transcripts(corpus)
    if args.ids_file:
        ids = set(Path(args.ids_file).read_text(encoding="utf-8").split())
        transcripts = [(tid, t) for tid, t in transcripts if tid in ids]
        print(f"Subset: {len(transcripts)} transcripts from {args.ids_file}.")
    elif not args.all:
        transcripts = transcripts[: args.limit]

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    if Path(args.out).exists():
        with open(args.out, newline="", encoding="utf-8") as fh:
            hdr = next(csv.reader(fh), [])
        if hdr != FIELDS:
            print(f"Refusing to append: {args.out} has header {hdr}, expected {FIELDS}."); sys.exit(1)

    done = already_done(args.out)
    pending = [(tid, ttext, [(d, s) for d, s in specs if (tid, d) not in done])
               for tid, ttext in transcripts]
    pending = [(tid, ttext, todo) for tid, ttext, todo in pending if todo]
    n_calls = sum(len(todo) for _, _, todo in pending)

    dim_names = ", ".join(d for d, _ in specs)
    print(f"\nJudges ({len(specs)}): {dim_names}")
    print(f"Model: {args.model}")
    if not n_calls:
        print("Nothing to do (all requested transcript x dimension pairs already scored)."); return
    print(f"{len(pending)} transcripts with pending work = {n_calls} judge calls "
          f"({len(done)} pairs already done).")
    if args.all and not args.yes and sys.stdin.isatty():
        if input(f"About to make ~{n_calls} calls with {args.model}. Continue? [y/N] ").strip().lower() != "y":
            print("Cancelled."); sys.exit(0)

    client = anthropic.Anthropic(max_retries=5)
    new_file = not Path(args.out).exists()
    out_fh = open(args.out, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(out_fh, fieldnames=FIELDS)
    if new_file:
        writer.writeheader(); out_fh.flush()
    counts = defaultdict(int)
    progress = {"done": 0}

    def write_row(tid, did, data):
        with _file_lock:
            writer.writerow({
                "transcript_id": tid, "dimension_id": did, "result": data.get("_result"),
                "evidence": data.get("evidence", ""),
                "reasoning": data.get("reasoning", ""),
            })
            out_fh.flush()
            counts[data.get("_result", "N/A")] += 1
            progress["done"] += 1
            if progress["done"] % 10 == 0 or progress["done"] == n_calls:
                hit = _usage["cache_read"]
                tot = _usage["cache_read"] + _usage["in"] + _usage["cache_write"]
                print(f"[{progress['done']}/{n_calls}] PASS={counts['PASS']} "
                      f"FAIL={counts['FAIL']} N/A={counts['N/A']} · cache_read={hit/max(tot,1)*100:.0f}%")

    def work_transcript(item):
        tid, ttext, todo = item
        for did, spec in todo:  # sequential: first call warms the cache for this transcript
            try:
                data = score_one(client, args.model, spec, ttext)
                write_row(tid, did, data)
            except anthropic.AuthenticationError:
                raise
            except Exception as e:
                with _print_lock:
                    print(f"  ! {tid}/{did} failed: {type(e).__name__}: {e}")
        return tid

    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(work_transcript, it): it[0] for it in pending}
            for fut in as_completed(futures):
                try:
                    fut.result()
                except anthropic.AuthenticationError:
                    print("Auth failed — check ANTHROPIC_API_KEY in .env."); sys.exit(1)
    finally:
        out_fh.close()

    tin, tout = _usage["in"], _usage["out"]
    cw, cr = _usage["cache_write"], _usage["cache_read"]
    print(f"\nDONE — {progress['done']} judge calls written to {args.out}")
    print(f"  verdicts: {dict(counts)}")
    print(f"  tokens: {tin:,} fresh-in / {cw:,} cache-write / {cr:,} cache-read / {tout:,} out")
    billed_in = tin + cw + cr
    if billed_in:
        print(f"  cache hit rate: {cr / billed_in * 100:.0f}% of input tokens served from cache")


if __name__ == "__main__":
    main()
