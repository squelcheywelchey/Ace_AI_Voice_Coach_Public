# makes_it_a_dialogue — Iteration Log

## v1 (initial)
**Date:** 2026-07-21
**Prompt file:** makes_it_a_dialogue_v1.yaml (sha 668e72a0)
**Model:** claude-sonnet-4-6
**Data:** consensus_makes_it_a_dialogue.csv — 18 SYNTHETIC seeds (no real coach meets
the pass bar). 4 clean pass (reflective Q + specifics, 9001–9004) + 5 TRICKY pass
(9005–9009) + 4 MATCHED near-miss fails (9101–9104) + 5 TRICKY fails (9105–9109).
Tricky positives stress: buried/disfluent-STT reflective Q (9005), one reflective Q
amid an otherwise templated coach (9006), non-canonical reflective phrasing (9007),
reflective Q only at the closing wrap-up (9008), participant deflects the reflective Q
(9009). Tricky negatives stress the FAIL line with surface features that resemble
dialogue: comprehension check "does that make sense?" (9105), disfluent-STT CONTENT
follow-up (9106), reflective questions PRESENT but zero engagement with specifics
(9107 — the mirror of 9006, tests that BOTH conditions are enforced), content-add
question "what else could you add?" (9108, sits next to 9007's "what would you
tighten?"), factual clarifier "was that at your last job?" (9109). Split: dev 8p/8f
(balanced), test 1p/1f (tricky rows all in dev).
**Description:** Faithful transcription of Rubric v2 DECIDED. Bright line built
around the reflective-question-vs-content-follow-up distinction (the corpus's
nearest miss): only a question that turns attention back on the participant's OWN
answer/experience ("how did that feel?") satisfies (a); content follow-ups
("say more about why you enjoy that?") do not.
**Dev agreement:** 16/16 (100%), TPR 1.00 / TNR 1.00 — includes all 5 tricky positives
AND all 5 tricky negatives.
**Test holdout:** 2/2 (100%), TPR 1.00 / TNR 1.00.
**Real-corpus TNR spot-check:** 12/12 real transcripts correctly FAIL (0 false-fires),
including P-755 — the rubric's named nearest-miss content follow-up.
**Right-reason check (positives):** on all 5 tricky positives the judge cited the actual
reflective question as evidence (incl. non-canonical "if you played that back, what would
you tighten?" and "how do you feel you did today?") — passing by category recognition,
not keyword match.
**Right-reason check (negatives):** all 5 tricky negatives fail for the correct reason —
notably 9107, where the judge explicitly notes reflective questions ARE present but
"the feedback never engages the specifics… generic numbered advice," confirming BOTH
conditions are enforced. It also distinguishes comprehension checks (9105), content
follow-ups incl. under STT noise (9106), content-add questions (9108), and factual
clarifiers (9109) from genuine reflective questions.
**Status:** v1 holds at 100% across an 18-row synthetic set spanning easy + adversarial
cases in both directions. No iteration needed. Remaining risk is entirely upstream: the
PASS class is author-generated (zero human-labeled positives) — needs Grader B/Grader C sign-off
before it's treated as calibration ground truth.
**Notes:** Synthetic contrastive pairs are easy by construction; the meaningful
signal is the clean FAIL line on real corpus rows. Before treating these as
calibration ground truth, get Grader B/Grader C to sign off on the synthetic PASS seeds
(this dimension has zero human-labeled positives). Next stress test: real transcripts
that combine strong content engagement + a genuine reflective question — none exist in
the corpus, so the pass class stays synthetic until the coach is improved.

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
