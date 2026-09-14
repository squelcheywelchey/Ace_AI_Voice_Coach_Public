"""Pull REAL production A/B calls from Supabase and pick a labeling set.

Fetches the `ceo_live_calls` table (the Railway eval server's output), keeps
only real participant calls on the live number (same filter as
build_ab_dashboard.py: post live-swap, no 2222 test ID, verified CEO ID, known
arm), and writes:

  live_ab_calls.tsv        every real call — transcript + arm + 9 judge verdicts
  labeling_set_live.tsv    N calls (default 15) roughly balanced pass/fail per dim

Balance is best-effort: it maximizes, per dimension, how close the set gets to
half pass / half fail among *observed* verdicts, bounded by what the corpus has
(e.g. if a dim has 0 fails in production, the set can't contain one). Arm A/B
is kept near-even and duplicate CEO IDs are discouraged. Greedy build + swap
hill-climb with seeded random restarts, deterministic — re-running on the same
data gives the same set.

Short calls (< --min-minutes, default 5) are excluded from the labeling set —
they're mostly dead air / early hangups and not worth labeling capacity
(Grader B, 2026-08-05) — UNLESS a short call carries a scarce dim-side verdict
(e.g. an observed pii) that the longer calls alone can't supply to target.

Judge verdict columns are included FOR TRACKING ONLY — strip them before
seeding a labeling app so human labelers stay blind to the judge.

Run:  python pull_labeling_set.py            # 15 calls
      python pull_labeling_set.py --n 20
"""

import argparse
import csv
from pathlib import Path

from dotenv import load_dotenv

from build_ab_dashboard import (ARM_CODE, JUDGE_TO_DIM, fetch_rows,
                                has_real_ceo_id, is_test_call, norm)

load_dotenv()

ALL_OUT = "live_ab_calls.tsv"
SET_OUT = "labeling_set_live.tsv"

META_FIELDS = ["call_id", "arm", "CEO ID", "started_at", "duration_sec"]
VERDICT_FIELDS = [f"{stem}_verdict" for stem in JUDGE_TO_DIM]
FIELDS = META_FIELDS + VERDICT_FIELDS + ["Transcript"]

ARM_PENALTY = 0.3      # per call of A/B imbalance beyond 1
DUP_CEO_PENALTY = 0.5  # per repeated call from the same participant

# The dims the selection balances on. Default: all 9 judges. Overridden by
# --dims for rounds that relabel a subset (e.g. round 4: qcf + feedback only).
BALANCE_DIMS = list(JUDGE_TO_DIM)


def load_real_calls():
    import os
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_KEY", "")
    if not (url and key):
        raise SystemExit("Set SUPABASE_URL and SUPABASE_KEY in .env")
    rows = fetch_rows(url, key)
    real = [r for r in rows
            if ARM_CODE.get(r.get("assistant_id"))
            and not is_test_call(r) and has_real_ceo_id(r)]
    # newest first so ties in the greedy pick favor recent coach behavior
    real.sort(key=lambda r: r.get("started_at") or "", reverse=True)
    return real


def verdicts(row):
    return {stem: norm(row.get(f"{stem}_verdict")) for stem in BALANCE_DIMS}


def dur_sec(row):
    try:
        return float(row.get("duration_sec") or 0)
    except (TypeError, ValueError):
        return 0.0


def eligible_pool(real, n, min_sec):
    """The calls the labeling set may draw from: everything at least min_sec
    long, plus any short call that carries a scarce dim-side — a pass/fail
    verdict the long calls alone can't supply up to target (e.g. pii, which is
    almost never observed). Everything else short is not worth labeling time."""
    long_calls = [r for r in real if dur_sec(r) >= min_sec]
    short_calls = [r for r in real if dur_sec(r) < min_sec]
    half = n // 2
    scarce = set()
    for stem in BALANCE_DIMS:
        for side in ("pass", "fail"):
            in_long = sum(verdicts(r)[stem] == side for r in long_calls)
            in_all = sum(verdicts(r)[stem] == side for r in real)
            if in_long < min(half, in_all):
                scarce.add((stem, side))
    rescued = [r for r in short_calls
               if any((stem, v) in scarce for stem, v in verdicts(r).items())]
    return long_calls + rescued, rescued


def targets_for(real, n):
    """Per dim+side target counts inside the set: half the set, bounded by
    what exists in the corpus."""
    half = n // 2
    tgt = {}
    for stem in BALANCE_DIMS:
        for side in ("pass", "fail"):
            avail = sum(verdicts(r)[stem] == side for r in real)
            tgt[(stem, side)] = min(half, avail)
    return tgt


def score(subset, tgt):
    """Higher is better: credit each dim-side up to its target (scarce sides
    weighted up so 8-fails-in-corpus dims actually get their fails picked),
    minus arm-imbalance and duplicate-participant penalties."""
    s = 0.0
    counts = {k: 0 for k in tgt}
    arms = {"A": 0, "B": 0}
    ceos = {}
    for r in subset:
        arms[ARM_CODE[r["assistant_id"]]] += 1
        cid = r["ceo_id"]
        ceos[cid] = ceos.get(cid, 0) + 1
        for stem, v in verdicts(r).items():
            if v in ("pass", "fail"):
                counts[(stem, v)] += 1
    for k, t in tgt.items():
        if t:
            s += min(counts[k], t) / t  # each dim-side worth 1.0 when met
    s -= ARM_PENALTY * max(0, abs(arms["A"] - arms["B"]) - 1)
    s -= DUP_CEO_PENALTY * sum(c - 1 for c in ceos.values())
    return s


def _hill_climb(chosen, rest, tgt):
    """First-improvement swap passes until a local optimum."""
    improved = True
    while improved:
        improved = False
        base = score(chosen, tgt)
        for i, out in enumerate(list(chosen)):
            for j, cand in enumerate(rest):
                trial = chosen[:i] + [cand] + chosen[i + 1:]
                if score(trial, tgt) > base + 1e-9:
                    chosen[i], rest[j] = cand, out
                    base = score(chosen, tgt)
                    improved = True
                    break
    return chosen


def select(real, n, restarts=30):
    import random
    tgt = targets_for(real, n)
    n = min(n, len(real))

    chosen, rest = [], list(real)              # greedy start
    for _ in range(n):
        best = max(rest, key=lambda r: score(chosen + [r], tgt))
        chosen.append(best)
        rest.remove(best)
    best_set = _hill_climb(chosen, rest, tgt)
    best_score = score(best_set, tgt)

    rng = random.Random(0)                     # seeded restarts — deterministic
    for _ in range(restarts):
        cur = rng.sample(real, n)
        cur_rest = [r for r in real if r not in cur]
        cur = _hill_climb(cur, cur_rest, tgt)
        if score(cur, tgt) > best_score + 1e-9:
            best_set, best_score = cur, score(cur, tgt)
    return best_set, tgt


def write_tsv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, delimiter="\t")
        w.writeheader()
        for r in rows:
            w.writerow({
                "call_id": r.get("call_id", ""),
                "arm": ARM_CODE[r["assistant_id"]],
                "CEO ID": r.get("ceo_id", ""),
                "started_at": r.get("started_at", ""),
                "duration_sec": r.get("duration_sec", ""),
                **{f: r.get(f, "") for f in VERDICT_FIELDS},
                "Transcript": r.get("transcript", ""),
            })
    print(f"wrote {path}  ({len(rows)} calls)")


def balance_table(subset, real, tgt):
    print(f"\n{'dimension':<30} {'set P/F/na':>12} {'target P/F':>11} {'pool P/F':>11}")
    for stem in BALANCE_DIMS:
        sp = sum(verdicts(r)[stem] == "pass" for r in subset)
        sf = sum(verdicts(r)[stem] == "fail" for r in subset)
        na = len(subset) - sp - sf
        cp = sum(verdicts(r)[stem] == "pass" for r in real)
        cf = sum(verdicts(r)[stem] == "fail" for r in real)
        print(f"{stem:<30} {f'{sp}/{sf}/{na}':>12} "
              f"{f'{tgt[(stem, 'pass')]}/{tgt[(stem, 'fail')]}':>11} {f'{cp}/{cf}':>11}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=15, help="size of the labeling set")
    ap.add_argument("--min-minutes", type=float, default=5.0,
                    help="exclude calls shorter than this from the set, unless "
                         "they carry a scarce dim-side verdict (0 disables)")
    ap.add_argument("--all-out", default=ALL_OUT)
    ap.add_argument("--set-out", default=SET_OUT)
    ap.add_argument("--dims", default="",
                    help="comma-separated judge stems to balance on "
                         "(default: all 9)")
    ap.add_argument("--exclude-tsv", default="",
                    help="TSV with a call_id column; those calls are excluded "
                         "(e.g. a prior round's labeling set)")
    args = ap.parse_args()

    global BALANCE_DIMS
    if args.dims:
        BALANCE_DIMS = [d.strip() for d in args.dims.split(",") if d.strip()]
        unknown = [d for d in BALANCE_DIMS if d not in JUDGE_TO_DIM]
        if unknown:
            raise SystemExit(f"unknown dims: {unknown}; valid: {list(JUDGE_TO_DIM)}")

    real = load_real_calls()
    if args.exclude_tsv:
        with open(args.exclude_tsv, newline="", encoding="utf-8") as fh:
            seen = {row["call_id"] for row in csv.DictReader(fh, delimiter="\t")}
        before = len(real)
        real = [r for r in real if r.get("call_id") not in seen]
        print(f"excluded {before - len(real)} call(s) already in {args.exclude_tsv}")
    arms = {"A": 0, "B": 0}
    for r in real:
        arms[ARM_CODE[r["assistant_id"]]] += 1
    print(f"real production calls: {len(real)}  (Arm A {arms['A']} / Arm B {arms['B']})")

    write_tsv(args.all_out, real)

    pool, rescued = eligible_pool(real, args.n, args.min_minutes * 60)
    pool.sort(key=lambda r: r.get("started_at") or "", reverse=True)
    print(f"eligible for the set: {len(pool)} of {len(real)} "
          f"(>= {args.min_minutes:g} min, plus {len(rescued)} short call(s) "
          f"rescued for scarce verdicts)")

    chosen, tgt = select(pool, args.n)
    # stable output order: by start time
    chosen.sort(key=lambda r: r.get("started_at") or "")
    write_tsv(args.set_out, chosen)

    sa = sum(ARM_CODE[r["assistant_id"]] == "A" for r in chosen)
    uniq = len({r["ceo_id"] for r in chosen})
    print(f"\nselected {len(chosen)}: Arm A {sa} / Arm B {len(chosen) - sa}, "
          f"{uniq} distinct participants")
    balance_table(chosen, pool, tgt)


if __name__ == "__main__":
    main()
