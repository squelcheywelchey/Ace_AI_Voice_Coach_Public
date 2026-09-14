# limits_the_load — Iteration Log

> **CLOSED FOR HANDOVER 2026-08-27.** Production keeps `limits_the_load.md` (v1).
> **Corrected 2026-08-29: this judge is certified, not uncertified.** The build and its
> numbers live in Grader B's run history, not in this log — see the correction entry at the
> bottom, which supersedes the "never measured" language that stood here until 2026-08-29.

## v1 (initial)
**Date:** 2026-07-17 (prompt file mtime; predates the run_log)
**Prompt file:** `limits_the_load.md` — a `.md` scan-then-judge prompt, not the
`limits_the_load_v1.yaml` this template originally guessed at. It is the prompt in
production today.
**Training examples:** none in this log. The judge *was* hill-climbed — ten runs, by Grader B,
recorded in `Judge Calls to Be Made + Takeaways.docx` at the repo root (see the correction
entry at the bottom for the run history and the numbers).
**Description:** Scan every mid-session feedback turn, classify focused (≤1 suggestion) vs
overloaded (≥3), exempt the end-of-session summary, then judge holistically with one hard
gate (a 3+-point lecture block more than twice = automatic fail).
**Dev set agreement:** 19/23 (82.6%) — TPR 0.94, TNR 0.57, PPV 0.83, NPV 0.80.
**Test set (one shot):** 21/23 (91.3%) — TPR 0.94, TNR 0.86, PPV 0.94, NPV 0.86.
**Notes:** There are no rows in `iteration_log/run_log.csv` for this dimension on any split,
because the runs were made outside `eval_harness_v2.py`. That is a **provenance** gap, not an
absence of measurement — the earlier note here, which dismissed the 82.6% as "a best-observed
number from Grader B's exploratory work", was wrong: it is the recorded dev score of Run 10,
and it is accompanied by a held-out test reveal with a full confusion matrix.

---

<!-- Template for future entries:

## vN → vN+1
**Date:**
**What changed:**
**Alpha before:**
**Alpha after:**
**Precision (pass):**
**Recall (fail):**
**Decision:** KEEP / REVERT
**Notes:**

-->

---

## Closing decision — 2026-08-27 (Maya)

**Decision: hold at v1 and ship it, documented. `limits_the_load_v2.md` is
NOT promoted.** This closes the last open item on the handover judge freeze.

**Why it is safe to close without a hill-climb:** v2 was never a behavioural revision. It is
byte-for-byte the same prompt as v1 apart from two cosmetic edits:

1. line 12 moves a markdown bold — v1 `**overloaded: three or more…**` (whole clause bold),
   v2 `**overloaded:** three or more…` (label only);
2. two trailing blank lines after the criteria block.

Same criteria, same thresholds, same summary exemption, same hard gate. So there is no
pending improvement being left on the table by staying on v1, and nothing a promotion would
buy. Diff it yourself before reopening this:

    diff ceo-eval-server/prompts/limits_the_load.md prompts/limits_the_load_v2.md

**What this decision does NOT mean.** v1 == v2 settles *which* prompt ships. It says nothing
about quality — for which see the correction below.

---

## Correction — 2026-08-29 (Maya)

**This judge was measured. The "never measured" language above was wrong** and has been
struck from this log, `JUDGE_PLAYBOOK.md` §1, `HANDOVER_PLAN.md`, and handover Docs 1 and 6.

The build is Grader B's, recorded in `Judge Calls to Be Made + Takeaways.docx` (repo root),
headed *"Labels: Maya | Judge: Grader B"*. Ten runs, one change at a time, with the reasoning
for each kept:

| Run | Change | Score |
|---|---|---|
| 1 | original two-step prompt, pre-temperature-fix | 15/23 (13–20, non-deterministic) |
| 2–5 | removed checkout + changed the overloaded definition | 7/23 — `{transcript}` placeholder had been dropped; the judge was scoring blind |
| 6 | placeholder restored, two changes from baseline | 10/23 — two changes at once, undiagnosable |
| 7 | restored baseline at temperature 0 | 15/23, stable |
| 8 | overloaded redefined format-based → suggestion-count | 18/23 — biggest single gain |
| 9 | dropped the two-step scan | 7/23 — reverted; the scan is load-bearing |
| 10 | pass criteria decoupled from the coach's format | **19/23, stable over two runs** |

**Certification numbers.** Dev 19/23 (82.6%) — TPR 0.94, TNR 0.57, PPV 0.83, NPV 0.80.
Held-out test 21/23 (91.3%) — TPR 0.94, TNR 0.86, PPV 0.94, NPV 0.86. That test figure is
the highest in the suite, and unlike most dimensions here the test split came in *above* dev.

**What is actually still open** — narrower than "uncertified", and worth keeping:

1. **No provenance row.** The runs did not go through `eval_harness_v2.py`, so no
   `run_log.csv` row ties a prompt hash and git commit to those numbers, and the standing
   health check reports "no baseline, cannot certify" for this dimension. The deployed
   prompt was hand-checked on 2026-08-29 and does carry Run 10's suggestion-count wording
   (`focused: one or fewer distinct improvement suggestions`), so the measured prompt and
   the shipped prompt agree. Closing the gap properly is **one harness run per split** —
   not a rebuild.
2. **Dev TNR 0.57.** Three false alarms on dev, recovering to 0.86 on test. Small-n, but
   this is the side to watch.
3. **Four decisions left unmade** in the takeaways doc: whether the hard gate should
   auto-fail at 3+ overloaded turns or 4+ (rows 285 and 372 hit exactly 3 and humans passed
   them); whether a two-suggestion turn is focused or overloaded (currently unclassified);
   whether scaffolded sub-points unpacking one suggestion should count as 3+; and three
   possible mislabels (rows 120, 440, 596).

**To reopen properly:** Recipe A from Stage 6 in `JUDGE_PLAYBOOK.md`. The labels already
exist (`labels/consensus_limits_the_load.csv`, `splits/limits_the_load/`), so it starts from
a scored dev run, not from scratch.
