"""Focused re-judge: did the coach genuinely BUILD a struggling participant?

Targets the value-add candidates (weak participant baseline + coach drove
practice/progress) from coach_eval.jsonl and re-judges each transcript with a
prompt focused on ONE question: did the coach measurably move a struggling
participant (more confident / specific / clear by the end), or just run redos
and praise? Separates real skill-building from going-through-the-motions.

Output → value_add_eval.jsonl, plus a printed ranking.

Usage:
    python value_add_eval.py            # judge all candidates
    python value_add_eval.py --limit 5  # quick test
"""

import argparse
import csv
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Literal

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from analyze import is_value_add_candidate, DEFAULT_FILE, TRANSCRIPT_COL

load_dotenv()
csv.field_size_limit(10**7)

MODEL = "claude-opus-4-8"
SCORES_FILE = "coach_eval.jsonl"
OUTPUT_FILE = "value_add_eval.jsonl"

SYSTEM_PROMPT = """\
You are evaluating an AI job-interview coach at the Center for Employment
Opportunities (a reentry-employment nonprofit). In the transcript "AI:" is the
coach and "User:" is the participant. These calls were pre-selected because the
participant STARTED WEAK (fragmented, vague, hesitant, or low-confidence answers)
and the coach attempted to drive practice.

Answer ONE focused question: did the coach GENUINELY build this struggling
participant's skill and confidence within the call — so that their answers were
measurably more specific, fuller, clearer, or more confident by the end — or did
it just run the motions (offer redos, praise) without real improvement?

Be skeptical and evidence-based. A second attempt that is no better than the
first is NOT improvement, even if the coach called it 'great.' Praising a weak
or incoherent answer is NOT skill-building. Require concrete before/after
evidence from the participant's own words."""


class ValueAddEval(BaseModel):
    genuine_skill_building: Literal["clear", "partial", "none"] = Field(
        description="clear = measurable improvement with evidence; partial = some real improvement on at least one answer; none = redos/praise but no real improvement.")
    participant_start: str = Field(description="1 sentence: how weak/where the participant started.")
    participant_end: str = Field(description="1 sentence: where they ended — better or not.")
    improvement_evidence: list[str] = Field(description="Before→after quotes from the PARTICIPANT showing change (or showing none).")
    coach_moves_that_helped: list[str] = Field(description="Specific coach actions that actually built skill/confidence (scaffolding, modeling, a real redo, naming genuine progress, easing nerves). Empty if none.")
    hollow_praise: bool = Field(description="True if the coach praised 'improvement' that did not actually occur.")
    verdict: str = Field(description="2-3 sentences: did the coach add real value to a struggling participant?")


def load_candidates() -> dict:
    cands = {}
    with open(SCORES_FILE, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                r = json.loads(line)
                if is_value_add_candidate(r):
                    cands[r["row"]] = r
    return cands


def load_transcripts(path: Path) -> dict:
    by_row = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for i, row in enumerate(csv.DictReader(fh, delimiter="\t")):
            by_row[i] = (row.get("CEO ID", "?"), (row.get(TRANSCRIPT_COL) or "").strip())
    return by_row


def evaluate(client, transcript):
    resp = client.messages.parse(
        model=MODEL, max_tokens=3000, system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"<transcript>\n{transcript}\n</transcript>"}],
        output_format=ValueAddEval,
    )
    return resp.parsed_output


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=0, help="0 = all candidates")
    p.add_argument("--tsv", default=DEFAULT_FILE)
    p.add_argument("--workers", type=int, default=6)
    args = p.parse_args()

    cands = load_candidates()
    transcripts = load_transcripts(Path(args.tsv))
    rows = sorted(cands)
    if args.limit:
        rows = rows[: args.limit]
    print(f"Re-judging {len(rows)} value-add candidates with {args.workers} workers...")

    client = anthropic.Anthropic(max_retries=5)
    results = []

    def work(row_idx):
        ceo_id, transcript = transcripts[row_idx]
        return row_idx, ceo_id, evaluate(client, transcript).model_dump()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out, \
            ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(work, r): r for r in rows}
        for fut in as_completed(futures):
            try:
                row_idx, ceo_id, data = fut.result()
            except Exception as e:
                print(f"  ! row {futures[fut]} failed: {e}")
                continue
            rec = {"row": row_idx, "ceo_id": ceo_id, **data}
            results.append(rec)
            out.write(json.dumps(rec) + "\n")
            out.flush()
            print(f"  [{data['genuine_skill_building']:>7}] row {row_idx} · CEO {ceo_id}")

    counts = Counter(r["genuine_skill_building"] for r in results)
    order = {"clear": 0, "partial": 1, "none": 2}
    print(f"\n{'=' * 72}\nRESULT — {len(results)} candidates re-judged")
    print("  ", dict(counts))

    for label in ("clear", "partial"):
        group = [r for r in results if r["genuine_skill_building"] == label]
        print(f"\n{'-' * 72}\n{label.upper()} skill-building ({len(group)}):")
        for r in sorted(group, key=lambda r: r["row"]):
            print(f"\n  ▸ row {r['row']} · CEO {r['ceo_id']}{'  [hollow praise too]' if r['hollow_praise'] else ''}")
            print(f"    start: {r['participant_start']}")
            print(f"    end:   {r['participant_end']}")
            for q in r["improvement_evidence"][:3]:
                print(f"      • {q}")
            print(f"    verdict: {r['verdict']}")
    print(f"\nSaved {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
