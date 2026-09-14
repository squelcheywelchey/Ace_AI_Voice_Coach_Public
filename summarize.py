"""Aggregate coach_eval.jsonl into a rubric report + example buckets.

Produces:
  - overall quality distribution
  - per-criterion mean, n, % scoring <=2
  - weakest-dimensions ranking
  - STRONG examples, EDGE cases, and each failure-mode flag (over-complimentary,
    bad feedback, no practice, coach stuck, PII breach) with example transcripts
  - worst-exemplar transcripts for the weakest dimensions

Usage:
    python summarize.py                          # full report
    python summarize.py drives_practice_uptake   # drill into one criterion
    python summarize.py --flag pii_breach        # list every transcript with a flag
    python summarize.py --file coach_eval.jsonl
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from analyze import (RUBRIC, SECTIONS, FLAGS, GROWTH_DIMS, BASELINE_DIMS,
                     _mean_scores, value_add, is_value_add_candidate)

NAME = {cid: name for _sec, cid, name, *_ in RUBRIC}
SECTION_OF = {cid: sec for sec, cid, *_ in RUBRIC}
CRITERIA = [cid for _sec, cid, *_ in RUBRIC]
FLAG_IDS = [fid for fid, _ in FLAGS]


def load(path: Path) -> list[dict]:
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def avg_score(r: dict) -> float:
    vals = [int(r[c]) for c in CRITERIA if r.get(c) not in (None, "N/A")]
    return sum(vals) / len(vals) if vals else 0.0


def red_quote(r: dict, cid: str) -> str:
    for rf in r.get("red_flags", []):
        if rf.get("criterion") == cid:
            return rf.get("quote", "")
    return ""


def flag_quote(r: dict, fid: str) -> str:
    for fe in r.get("flag_evidence", []):
        if fe.get("flag") == fid:
            return fe.get("quote", "")
    return ""


def stats_for(records, cid):
    dist = Counter(r.get(cid) for r in records)
    scores = [int(r[cid]) for r in records if r.get(cid) not in (None, "N/A")]
    n = len(scores)
    return {
        "n": n,
        "mean": (sum(scores) / n) if n else None,
        "pct_low": (sum(1 for s in scores if s <= 2) / n) if n else None,
        "dist": dist,
    }


def report(records: list[dict]) -> None:
    n = len(records)
    print(f"\n{'=' * 72}\nRUBRIC REPORT — {n} transcripts\n{'=' * 72}")
    print("Overall quality:", dict(Counter(r.get("overall_quality") for r in records)))

    # Failure-mode flags
    print(f"\n{'-' * 72}\nFAILURE-MODE FLAGS (count / % of calls):")
    for fid in FLAG_IDS:
        c = sum(1 for r in records if r.get(fid))
        print(f"   {c:>4}  {100*c/n:4.1f}%  {fid}")

    # Per-criterion table
    st = {cid: stats_for(records, cid) for cid in CRITERIA}
    print(f"\n{'-' * 72}\nPER-CRITERION (mean | %≤2 | n | dist 1/2/3/4/NA):")
    for letter, title in SECTIONS.items():
        print(f"\n  {letter}. {title}")
        for cid in CRITERIA:
            if SECTION_OF[cid] != letter:
                continue
            s = st[cid]
            if not s["n"]:
                print(f"     n/a   {NAME[cid]}")
                continue
            d = s["dist"]
            dstr = "/".join(str(d.get(k, 0)) for k in ("1", "2", "3", "4", "N/A"))
            print(f"     {s['mean']:.2f} | {s['pct_low']*100:4.0f}% | n={s['n']:<4} | {dstr:<12} {NAME[cid]}")

    ranked = sorted((s["mean"], cid) for cid, s in st.items() if s["n"])
    print(f"\n{'-' * 72}\nWEAKEST DIMENSIONS:")
    for mean, cid in ranked[:12]:
        print(f"   {mean:.2f}  [{SECTION_OF[cid]}] {NAME[cid]}  ({cid})")

    # Strong examples
    strong = sorted((r for r in records if r.get("overall_quality") == "strong"),
                    key=avg_score, reverse=True)
    print(f"\n{'-' * 72}\nSTRONG EXAMPLES ({len(strong)}) — highest avg first:")
    for r in strong[:12]:
        print(f"   avg {avg_score(r):.2f} · row {r['row']} · CEO {r['ceo_id']}")
    if not strong:
        print("   (none labeled strong — top transcripts by avg score:)")
        for r in sorted(records, key=avg_score, reverse=True)[:8]:
            print(f"   avg {avg_score(r):.2f} · row {r['row']} · CEO {r['ceo_id']} · {r.get('overall_quality')}")

    # Edge cases
    edges = [r for r in records if r.get("overall_quality") == "edge_case"]
    print(f"\n{'-' * 72}\nEDGE CASES ({len(edges)}):")
    for r in edges[:15]:
        print(f"   row {r['row']} · CEO {r['ceo_id']} — {r.get('summary', '')[:140]}")

    # Examples per failure-mode flag
    print(f"\n{'-' * 72}\nEXAMPLES PER FAILURE-MODE FLAG (up to 5 each):")
    for fid in FLAG_IDS:
        flagged = [r for r in records if r.get(fid)]
        print(f"\n  ▸ {fid} ({len(flagged)})")
        for r in flagged[:5]:
            q = flag_quote(r, fid)
            print(f"     row {r['row']} · CEO {r['ceo_id']}" + (f" — {q}" if q else ""))

    # Worst exemplars for weakest dims
    print(f"\n{'-' * 72}\nWORST-EXEMPLAR TRANSCRIPTS for the 5 weakest dimensions:")
    for mean, cid in ranked[:5]:
        print(f"\n  ▸ {NAME[cid]} (mean {mean:.2f})")
        worst = sorted((r for r in records if r.get(cid) not in (None, "N/A")),
                       key=lambda r: int(r[cid]))[:3]
        for r in worst:
            q = red_quote(r, cid)
            print(f"     score {r[cid]} · row {r['row']} · CEO {r['ceo_id']}" + (f" — {q}" if q else ""))


def drill(records, cid):
    print(f"\n{NAME[cid]} ({cid}) — every transcript, lowest score first:\n")
    rows = sorted((r for r in records if r.get(cid) is not None),
                  key=lambda r: 9 if r[cid] == "N/A" else int(r[cid]))
    for r in rows:
        q = red_quote(r, cid)
        print(f"  {str(r[cid]):>3} · row {r['row']} · CEO {r['ceo_id']}" + (f" — {q}" if q else ""))


def list_flag(records, fid):
    flagged = [r for r in records if r.get(fid)]
    print(f"\n{fid} — {len(flagged)} transcripts:\n")
    for r in flagged:
        q = flag_quote(r, fid)
        print(f"  row {r['row']} · CEO {r['ceo_id']}" + (f" — {q}" if q else ""))


def value_add_report(records: list[dict]) -> None:
    cands = [r for r in records if is_value_add_candidate(r)]
    cands.sort(key=lambda r: value_add(r), reverse=True)
    print(f"\nCOACH VALUE-ADD CANDIDATES — {len(cands)} calls")
    print("(weak participant baseline ≤2.5 AND coach drove practice or named progress ≥3)")
    print("Higher value_add = coach lifted a weaker participant.\n")
    print(f"  {'value':>6} {'growth':>6} {'base':>5}  practice/progress  conf  row/ceo")
    for r in cands:
        print(f"  {value_add(r):>+6.2f} {_mean_scores(r, GROWTH_DIMS):>6.2f} {_mean_scores(r, BASELINE_DIMS):>5.2f}"
              f"   {str(r.get('drives_practice_uptake')):>2}/{str(r.get('frames_progress')):<2}             "
              f"{str(r.get('elicits_confidence')):>2}   row {r['row']} · CEO {r['ceo_id']}")
        print(f"         {r.get('summary','')[:200]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize coach_eval.jsonl.")
    parser.add_argument("criterion", nargs="?", help="A criterion id to drill into.")
    parser.add_argument("--flag", help="List every transcript with this failure-mode flag.")
    parser.add_argument("--value-add", action="store_true", help="List coach value-add candidates (weak participant, coach builds).")
    parser.add_argument("--file", default="coach_eval.jsonl")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"No results file: {path}. Run analyze.py first.")
        return
    records = load(path)
    if not records:
        print("Results file is empty.")
        return

    if args.value_add:
        value_add_report(records)
    elif args.flag:
        if args.flag not in FLAG_IDS:
            print("Unknown flag. Options:", ", ".join(FLAG_IDS))
            return
        list_flag(records, args.flag)
    elif args.criterion:
        if args.criterion not in NAME:
            print("Unknown criterion. Options:")
            for c in CRITERIA:
                print("  ", c)
            return
        drill(records, args.criterion)
    else:
        report(records)


if __name__ == "__main__":
    main()
