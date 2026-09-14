#!/usr/bin/env python3
"""
ab_report.py — arm A vs arm B comparison for a locally-scored live-call run.

Joins a run_corpus_hero.py results CSV (transcript_id = call_id) back to the
`arm` column in the live A/B calls TSV, then reports per-dimension pass rates
per arm with an exact two-sided significance test.

    python ab_report.py                                   # default paths
    python ab_report.py --results ../outputs/live_ab_hero_results.csv

N/A verdicts are excluded from a dimension's denominator (same convention as
the dashboard). The derived overall mirrors build_dashboard_data.derive_overall:
a call fails if PII tripped or it passes <60% of its observed dimensions.
"""

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
SUITE_DIR = SCRIPTS_DIR.parent
REPO_ROOT = SUITE_DIR.parent

csv.field_size_limit(10**7)

DEFAULT_RESULTS = SUITE_DIR / "outputs" / "live_ab_hero_results.csv"
DEFAULT_CALLS = REPO_ROOT / "live_ab_calls.tsv"


def fisher_exact_two_sided(a, b, c, d):
    """Two-sided Fisher exact p for [[a,b],[c,d]] — no scipy needed."""
    n = a + b + c + d
    if n == 0:
        return 1.0
    row1, row2, col1 = a + b, c + d, a + c

    def p_table(x):
        y, z, w = row1 - x, col1 - x, row2 - (col1 - x)
        if min(y, z, w) < 0:
            return 0.0
        return (math.comb(row1, x) * math.comb(row2, z)) / math.comb(n, col1)

    observed = p_table(a)
    lo, hi = max(0, col1 - row2), min(row1, col1)
    tol = observed * (1 + 1e-9)
    total = 0.0
    for x in range(lo, hi + 1):
        px = p_table(x)
        if px <= tol:
            total += px
    return min(1.0, total)


def pct(passed, total):
    return f"{passed / total * 100:5.1f}%" if total else "    — "


def main():
    ap = argparse.ArgumentParser(description="Arm A vs B report for locally-scored live calls.")
    ap.add_argument("--results", default=str(DEFAULT_RESULTS))
    ap.add_argument("--calls", default=str(DEFAULT_CALLS))
    args = ap.parse_args()

    arm = {}
    with open(args.calls, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            cid = (row.get("call_id") or "").strip()
            if cid:
                arm[cid] = (row.get("arm") or "?").strip()

    # per_call[call_id][dimension] = PASS/FAIL/N/A
    per_call = defaultdict(dict)
    with open(args.results, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            per_call[r["transcript_id"]][r["dimension_id"]] = r["result"]

    scored = {cid: dims for cid, dims in per_call.items() if cid in arm}
    orphans = len(per_call) - len(scored)
    n_by_arm = defaultdict(int)
    for cid in scored:
        n_by_arm[arm[cid]] += 1

    dims = sorted({d for v in scored.values() for d in v})

    print(f"\nLocal A/B — {len(scored)} live calls  (A={n_by_arm['A']}, B={n_by_arm['B']})"
          + (f"  [{orphans} scored rows with no arm, skipped]" if orphans else ""))
    print("Judges: newest hero of each dimension.  N/A excluded from denominators.\n")

    hdr = f"{'dimension':32s} {'arm A':>14s} {'arm B':>14s} {'B-A':>8s} {'p':>8s}"
    print(hdr)
    print("-" * len(hdr))

    rows = []
    for d in dims:
        cnt = {"A": [0, 0], "B": [0, 0]}  # [pass, observed]
        for cid, v in scored.items():
            res = v.get(d)
            if res in ("PASS", "FAIL"):
                cnt[arm[cid]][1] += 1
                if res == "PASS":
                    cnt[arm[cid]][0] += 1
        pa, na = cnt["A"]
        pb, nb = cnt["B"]
        if not na or not nb:
            print(f"{d:32s} {pct(pa,na)} ({na:3d}) {pct(pb,nb)} ({nb:3d}) {'—':>8s} {'—':>8s}")
            continue
        delta = pb / nb - pa / na
        p = fisher_exact_two_sided(pa, na - pa, pb, nb - pb)
        star = " *" if p < 0.05 else ""
        print(f"{d:32s} {pct(pa,na)} ({na:3d}) {pct(pb,nb)} ({nb:3d}) "
              f"{delta*100:+7.1f} {p:8.3f}{star}")
        rows.append((d, delta, p))

    # derived overall (mirrors build_dashboard_data.derive_overall)
    ov = {"A": [0, 0], "B": [0, 0]}
    for cid, v in scored.items():
        if v.get("pii") == "FAIL":
            ok = False
        else:
            obs = [x for k, x in v.items() if x in ("PASS", "FAIL")]
            ok = bool(obs) and sum(x == "PASS" for x in obs) / len(obs) >= 0.6
        ov[arm[cid]][1] += 1
        ov[arm[cid]][0] += ok
    pa, na = ov["A"]
    pb, nb = ov["B"]
    print("-" * len(hdr))
    if na and nb:
        p = fisher_exact_two_sided(pa, na - pa, pb, nb - pb)
        print(f"{'DERIVED OVERALL':32s} {pct(pa,na)} ({na:3d}) {pct(pb,nb)} ({nb:3d}) "
              f"{(pb/nb - pa/na)*100:+7.1f} {p:8.3f}{' *' if p < 0.05 else ''}")

    sig = [r for r in rows if r[2] < 0.05]
    print(f"\n* = p < 0.05 (Fisher exact, two-sided).  "
          f"{len(sig)} of {len(rows)} dimensions significant at 0.05.")
    if not sig:
        print("No dimension separates the arms at this sample size.")


if __name__ == "__main__":
    main()
