# Drives Practice & Uptake — Iteration Log

## v1 (initial)
**Date:** 2026-07-12
**Prompt file:** drives_practice_v1.yaml
**Training examples:** CEO_249401 (PASS), CEO_182444 (FAIL)
**Description:** Initial prompt with low-bar, participant-centric definition. PASS = at least one retry or expansion. FAIL = never attempts a single retry.
**Dev run (2026-07-17):** 22/23 = 95.7%. TPR 1.00 · TNR 0.92 · PPV 0.92 · NPV 1.00. (11 TP / 11 TN / 1 FP / 0 FN)
**Decision:** HOLD — baseline is strong; the lone error (row 596, a false-pass) is a policy question, not a prompt bug. Escalated to Maya (findings decision #1) before any v2 edit.
**Notes:** Single disagreement = row 596: coach offered a retry after every question, participant declined all; the only retry was user-self-initiated. v1's participant-centric wording calls it PASS; consensus (single rater) = FAIL. Rubric v2 ("any retry attempt passes") vs. the coach-centric "uptake not forthcomingness" rule disagree on this exact row — Maya to rule.

## v1_hero — test run (Ruling A close-out)
**Date:** 2026-07-17 · **Prompt:** drives_practice_v1_hero.yaml (identical content to v1; sha 370ae431)
**Maya ruling on 596:** A — "any retry attempt passes." Shipped v1 as champion, ran test once.
**Test:** 17/23 = 73.9%. TPR 1.00 · TNR 0.50 · PPV 0.65 · NPV 1.00. (11 TP / 6 TN / 6 FP / 0 FN)
**Outcome:** Holdout FALSIFIED Ruling A. All 6 errors are the same false-pass shape as 596 (retry happened → judge PASS → human FAIL). 5/6 are Grader B single-rater FAILs; 617 is Grader B-PASS/Grader C-FAIL. Two of the six (179, 617) are coach-*prompted* retries, so a simple coach-driven carve-out won't explain the labels — the human bar is holistic ("was there a real practice loop"), not "≥1 retry."
**Decision:** DIMENSION NOT CLOSED. Definition reopened → Maya decision #2 (tighten judge to holistic bar vs. treat strict FAILs as candidate mislabels needing a 2nd rater). Test holdout now spent/informative — flagged in findings.

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
