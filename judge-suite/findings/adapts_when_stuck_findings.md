# adapts_when_stuck — findings

Dimension: **B. Social-emotional awareness — "Adapts when stuck or frustrated."**
Rubric: decided Rubric v2 (Option A: ANY responsive change counts, incl. graceful move-on),
`calibration/rubric.py`. Labels: `master_labels.csv` (Grader B/Maya/Grader C calibration consensus).

## Setup notes (2026-07-20)

- **N/A-heavy dimension.** Of 54 calibration transcripts: **6 pass / 10 fail / 38 not_observed**
  (70% N/A). This is the first dimension where N/A dominates.
- **N/A is scored as a real class** (team decision). The splitter (`--include-not-observed`)
  and `eval_harness_v2.py` were extended so:
  - all 54 rows enter the splits (3-way stratified): train 9 (1P/2F/6NA), dev 23 (3P/4F/16NA),
    test 22 (2P/4F/16NA);
  - the harness no longer skips N/A rows; it reports `na_recall` (correct-abstention rate),
    `false_fire` (calm call, judge scored PASS/FAIL — the worst error here), and
    `false_abstain` (real signal, judge said N/A), plus a 3×3 confusion matrix.
  - tpr/tnr are recall over ALL consensus-PASS/FAIL rows; ppv/npv are precision over ALL
    judge-PASS/FAIL predictions — so both abstention errors count against the judge.

## Flags for team resolution (do NOT tune the judge to these)

1. **Fail-anchor contradicts its own final label.** The rubric's `fail_example` for this
   dimension is ceo **P-365** ("...y'all need to learn how to fucking drive." → coach repeats
   "I'm here to help... let's focus on that"). In the final calibration labels that transcript is
   **not_observed**, not fail. Likely reading: the profanity is a road-rage *story*, not the user
   being frustrated *with the coach*, so raters saw "no stuck moment to adapt to." Either the
   anchor is a poor exemplar or the label is wrong — **team to decide.** v1 does not quote it.

## Quotable (train-split) transcripts, for later prompt iterations
- pass: row 437 (ceo P-433)
- fail: row 205 (ceo P-712), row 749 (ceo P-336)
- (pass-anchor ceo P-430 is in the TEST split — never quote.)

## v1 baseline (2026-07-20, sonnet-4-6, dev n=23)

**47.8% agreement (11/23). TPR 1.00 · TNR 0.00 · N/A-recall 0.50 · 8 false-fires · 0 false-abstains.**
Confusion (rows=consensus): PASS 3/0/0 · FAIL 4/0/0 · N/A 7/1/8. The judge fires PASS on almost
everything — it misses every FAIL (all 4 → PASS) and false-fires on half the calm calls.

Every disagreement runs the same direction: the judge finds a "signal" the humans didn't count, or
credits boilerplate as adaptation. The humans labeled to a **stricter standard than the Option-A
rubric text**, consistently along three axes:

### Cluster 1 — signal bar too low (drives the 8 false-fires) [PROMPT BUG]
Judge treats routine mechanics and minor drift as distress signals: "repeat the question" (594),
"What was that? Sorry" (735), "Hold on" (536), a one-off news tangent (440, 242), "I don't know what
else to say" (313). Humans reserve "stuck/frustrated" for GENUINE distress (profanity-as-frustration,
escalating agitation, real inability to proceed). Fix: raise the signal threshold; enumerate
non-signals (clarification requests, brief pauses, single off-topic remark, terse answers).
Expected flips → N/A: 242, 313, 405, 440, 594, 735 (all consensus N/A).

### Cluster 2 — boilerplate counted as adaptation [PROMPT BUG]
Judge credits the coach's DEFAULT canned lines — "I'm here to help you practice… let's focus on that
for now" and the standard feedback template — as a "responsive change." Humans do not: those are the
template, not an adaptation to THIS user's state. Fix: say the stock redirect / stock feedback opener
does not by itself count; adaptation must be visibly responsive to the specific signal.

### Cluster 3 — call-level aggregation is fail-dominant, judge cherry-picks [PROMPT BUG]
The label is per-CALL: a call FAILS if the coach ignores an explicit signal ANYWHERE, even if other
moments are handled gracefully. Row 536 fails on ignored "Fuck this" despite a later good "Take your
time"; 609 fails on the repeated canned line despite one clean redirect. The judge passes on finding
ONE good moment. Fix: scan for the WORST-handled explicit signal; one ignored explicit signal = FAIL.
Expected flips → FAIL: 536, 577, 609, 164.

### The gating policy question (for Maya) — do NOT tune past this without a ruling
All three clusters tighten the bar in the SAME direction the labels point, but Cluster 1 & 2 in effect
reinterpret the decided Option A ("ANY responsive change counts… redirecting a rant"). The calibration
labels are stricter than Option-A-as-written. Two readings:
  - **(A) Labels are authoritative** — encode the stricter standard (genuine-distress signal bar +
    boilerplate-doesn't-count + fail-dominant aggregation). Aligns with the team's false-pass-averse
    preference. This is a de-facto rubric-wording update to Option A.
  - **(B) Option-A text is authoritative** — then rows like 440/242 are candidate mislabels /
    accepted mismatches, agreement stays capped, and we escalate the labels instead.
Recommendation: (A). Every error in v1 points one way (too lenient), and (A) matches "a FAIL verdict
should almost always be right." But it changes what Option A means, so it's Maya's call before v2.
Also still open: the fail-anchor (ceo P-365) not_observed contradiction above.

**RULING (Maya, 2026-07-20): (A) — tune to the labels.** The calibration labels are authoritative;
encode the stricter standard into the judge. This tightens Option A's wording. Iteration order (one
conceptual change each): v2 = raise signal bar (Cluster 1), v3 = boilerplate ≠ adaptation (Cluster 2),
v4 = fail-dominant aggregation (Cluster 3).

## v2 result + remaining-disagreement classification (2026-07-20)

v2 (raise signal bar) → **78.3% (18/23)**, false-fires 8→1, N/A-recall 0.94, PASS rows all held. KEEP.
TNR still 0.00 — the 4 FAIL rows remain. Reading all 5 disagreements splits them cleanly:

- **PROMPT-FIXABLE (v3): 536, 609.** Judge cherry-picks one handled moment and PASSes, ignoring that
  the call has a genuine signal met with the unchanged/repeated template (536: ignored "Fuck this"
  early; 609: identical "I'm here to help… let's focus" canned line repeated to a can't-answer user).
  Fix = fail-dominant call-level aggregation: scan the WHOLE call; one genuine signal met with the
  template unchanged / same canned line repeated = FAIL, even if another moment was handled.

- **ESCALATE (boundary calls / candidate mislabels — do NOT overfit):**
  - **166** (label N/A, judge FAIL): user says "I can't find the right words" once but answers fluently
    throughout → human saw no genuine stuck moment. "lost for words" as a fleeting filler ≠ genuine
    being-stuck. The judge's FAIL is the defensible-but-stricter read; label N/A is also defensible.
  - **577** (label FAIL, judge N/A): disengaged/deflecting user (terse, "police is a challenge"), coach
    templates throughout, but the one explicit confusion ("Say what?") the coach DID rephrase. The
    "ignored signal" is implicit disengagement, not an explicit distress signal. Reads more like a
    kind_delivery / limits_the_load fail than adapts_when_stuck.
  - **164** (label FAIL, judge N/A): increasingly incoherent/confused speech ("Person.", "We're
    frozen", "Undistributed") + incarceration disclosure; coach templates through. Signal is IMPLICIT
    confusion; the decided rule evaluates EXPLICIT signals, so N/A is defensible.

  Realistic ceiling after v3: 20/23 (~87%) if 536/609 flip clean. 164/577/166 → present to Maya as
  numbered decisions (relabel vs accepted-mismatch); each is judge-defensible under the explicit-signal
  rule, so they may become documented accepted mismatches rather than fixes.

## Maya's rulings (2026-07-20)

- **Row 536 → FAIL (real judge bug, encode in v4).** The "Fuck this" IS a stuck/frustrated signal, and
  the coach didn't catch it — it ran the standard feedback + "try again or move on?" template without
  registering the frustration. Rule: **a genuine frustration/stuck signal met with the stock feedback
  or retry-offer template, with no acknowledgment of the frustration itself, is FAIL** — offering a
  retry is not adapting if the emotional signal is ignored. (This is the Cluster 2 carve-out; the judge
  currently mis-reads the retry-offer as a reframe.)
- **Row 609 → FAIL (real judge bug, encode in v4).** Maya: the coach's response (the repeated "I'm
  here to help… let's focus on that" canned line) doesn't count as an adaptation. So the genuine
  "I don't know what to say" signal went unaddressed → FAIL. Same carve-out as 536: the stock canned
  line, especially repeated, is not a responsive change.
- **Row 577 → FAIL (real judge bug, encode in v4).** Sustained disengagement/deflection (a pattern of
  flippant non-answers — "I just like money", "the police is a challenge" — with the coach robotically
  templating through) IS a signal the coach must adapt to. Broadens the signal bar beyond explicit
  distress to include a disengagement PATTERN. Watch the N/A boundary: simple brevity on a cooperative,
  on-track user is still N/A.

### Accepted mismatches (judge is correct, LABEL is the problem — candidate relabels; labels NOT edited)
- **Row 164 → N/A (judge correct; label FAIL is too strict).** Confusion here is IMPLICIT — inferred
  only from garbled/incoherent STT-ish output ("Person.", "We're frozen", "Undistributed") with no
  explicit stuck/confused statement. Per the explicit-cue rule, N/A. v2 judge already returns N/A →
  keep. Measured agreement counts this as a miss (label FAIL); effective agreement counts it correct.
  KEY DISTINCTION vs 577: 577 = a deliberate disengagement/deflection pattern (a behavioral signal);
  164 = the user is trying but the words come out garbled (not a signal on its own).
- **Row 166 → FAIL (judge correct; label N/A is too lenient).** "I can't find the right words" IS an
  explicit stuck signal; the coach ignored it (stock feedback, no reassurance) → FAIL. v2 judge already
  returns FAIL → keep. So "lost for words / can't find the words" is a GENUINE signal — REMOVE it from
  v2's non-signal list. Measured counts this a miss (label N/A); effective counts it correct.

Report both numbers going forward: **measured** (vs labels as they stand) and **effective** (counting
164 + 166 as correct). Labels 164/166 are candidate relabels flagged for the team; not edited here
(would need to sync master_labels.csv, split_reference, labeling DB). **Maya (2026-07-20): document
only — do NOT relabel.**

## Dimension closed (2026-07-20)

**Champion: `prompts/adapts_when_stuck_v5_hero.yaml`.**
- **Dev: 91.3% measured (21/23) / 100% effective** (only misses are accepted mismatches 164, 166).
- **Test (one-shot, spent): 68.2% (15/22).** TPR 0.50 / TNR 0.75 / PPV 0.17 / **NPV 1.00** / N/A-recall
  0.69.

**Honest characterization.** v5 is a trustworthy **FAIL detector** (NPV 1.00 on test — when it says
FAIL it is right; TNR 0.75) but **over-generous on PASS** (test PPV 0.17): it infers a genuine stuck
signal from a mild pause whenever the coach replies "Take your time", where humans see no signal and
label N/A. The dev→test gap (91%→68%) is entirely this PASS/N/A boundary; dev happened not to contain
"reassurance-on-a-non-signal" cases. This is the thinnest dimension in the suite (16 scoreable of 54;
test PASS class = 2 rows), so the estimate is high-variance and the PASS boundary is under-determined
by the available labels.

**Accepted mismatches (judge correct, labels are candidate relabels — NOT edited):**
- 164 (ceo P-164): label FAIL, judge N/A — confusion is implicit (garbled speech), no explicit cue.
- 166 (ceo P-121): label N/A, judge FAIL — explicit "can't find the words" ignored by the coach.

**Open flags for the team:**
- Fail-anchor ceo P-365 labeled not_observed (contradicts its rubric role).
- Label inconsistencies on the mild-clarification boundary surfaced during tuning (358 PASS vs 594 N/A;
  and the test PASS-boundary rows 71/122/141/246/518 that v5 read as PASS).

**What remains / recommended next:** to raise PASS reliability, add more labeled PASS/N/A cases on the
"mild pause + take-your-time" boundary (the current PASS class is too small to pin it down), then
re-tune against a FRESH holdout (the current test split is spent). As-is, v5 is usable where a
trustworthy FAIL signal is what matters.
