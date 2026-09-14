# feedback_question_low_bar — iteration log

## Prior work (Grader B, July 2026 — reconstructed from git, no run_log rows)
In-place edits to prompts/feedback_question_low_bar.md, scores in commit
messages: v1 single-pass 18/23 (78%, "lenient, 5 false passes") · v4 two-step
scan + quality-claim criterion (peak ~20/23 implied by "regression 18-20 to
16") · v5 malfunction reframe REVERTED (14/23) · redirect criterion REVERTED
(16/23) · substantive-praise criterion KEPT · turn-independence REVERTED (lost
376, 594). Current file = v4 + substantive-praise. This is the judge running
in production (eval server prompts/feedback_question_low_bar.md).

## Live reopening (Maya + Claude, 2026-08-12)
Production judge matched Grader B's round-3 labels on only 5/15 (33%), mismatches
5/5 in BOTH directions — suspected construct disagreement, not mere strictness.
Setup mirroring the qcf reopening: split mirrored into labels/*_ids.csv,
consensus_feedback_question_low_bar_live.csv (9 pass / 6 fail) from Grader B's
round-3 labels, live_ids.csv extended. v6 = verbatim snapshot of the
production .md so runs are version-tagged; old dev kept as regression guard.

## v6 baseline (production prompt, unchanged)
**Date:** 2026-08-12
**Decision:** baseline (runs pending on dev + live)
**v6 baseline results:** dev 65.2% (15/23, TPR 0.72 TNR 0.40 NPV 0.29) · live
33.3% (5/15) — matches production's round-3 agreement exactly. Note: well
below Grader B's July judge.py scores (~78-87%) — possible harness/layout drift,
flagged, not investigated (her runner is gone; harness numbers are now the
baseline going forward). 18 disagreements = clusters F1 + F2 (see findings).

## v6 → v7 (encodes Maya's STT ruling — cluster F1)
**Date:** 2026-08-12
**Prompt file:** feedback_question_low_bar_v7.md
**What changed (ONE concept):** STT carve-out appended to the Step-1
disconnected criteria: garbled/fragmented User text is transcription noise,
not participant content; the coach heard audio, not the transcript; warm
acknowledgment / retry / move-along over such a response is ALIGNED. The
no-real-content and garbled clauses fire only when the coach attributes
specific substantive quality a response never showed.
**Prediction:** flips live 019faf6c/b437/b47b/b56f/b918/c98e and dev
120/285/440/580/619 to pass. Collateral watch: dev 122 (humans failed a
thin-answer call — if it stays judge-pass, fine; it's an F2 row), and the
carve-out must NOT weaken true unearned-quality fails (F2 rows stay as they
are until v8).
**Decision:** (run pending)

## v7 result → KEEP
**Date:** 2026-08-12
**Split dev:** 78.3% (18/23) · TPR 0.94 · TNR 0.20 — F1 rows 120/285/440/580
flipped as predicted; 619 remains (separate micro-pattern: mild topic-mismatch
tolerated by humans); collateral: 576 (true fail formerly caught via the
garbled clause) now passes — watch if v8 recaptures.
**Split live:** 66.7% (10/15) · TPR 1.00 · zero false-fails — all 6 F1 rows
flipped. Remaining 5 = exactly cluster F2.
**Decision:** KEEP. dev +13.1, live +33.4; error profile temporarily
false-pass-heavy pending the F2 fix (v8).

## v7 → v8 (cluster F2 — Grader B's superlative principle)
**Date:** 2026-08-12
**Prompt file:** feedback_question_low_bar_v8.md
**What changed (ONE concept):** praise-tier distinction inside the existing
quality-claim criterion: mild process encouragement passes even on weak
answers; superlative/content-specific certification of quality a weak or
mediocre answer doesn't show fails — including repeated superlative
certification across a session where every turn accurately restates content
("accurately restating content does not earn the quality label").
**Prediction:** flips live faf19/b5c2/bae9/c523/c89e and dev 122/179/609 to
fail; may recapture 576. Collateral watch: F1 rows must stay pass (mild
encouragement explicitly protected); mid-tier praise rows in train; 619
untouched.
**Decision:** (run pending)

## v8 result → KEEP
**Date:** 2026-08-12
**Split dev:** 82.6% (19/23) · TPR 0.89 · TNR 0.60 — 609 flipped to fail (F2
win), 576 recaptured; 580 regressed (collision row: judge stretched
"certifying quality" to "framing as a legitimate answer worth coaching on").
**Split live:** 66.7% (10/15) · TPR 0.89 · TNR 0.33 — faf19 now correctly
fails; c98e regressed (collision: superlative-ish praise on garbled Q7);
b5c2/bae9/c523/c89e still pass, judge arguing "praise is calibrated".
**Decision:** KEEP — dev +4.3, live flat but F2 catches are real; regressions
are the F1×F2 collision, addressable as a definitional sharpening (v9).
**Learned:** "certifying quality" without a directionality test is stretchable;
the human line between 580-pass and bae9-fail is praise AT THE ANSWER vs
generic topic-value/process warmth.

## v8 → v9
**Date:** 2026-08-12
**Prompt file:** feedback_question_low_bar_v9.md
**What changed (ONE concept):** directionality test on the quality-claim
criterion — a quality claim is praise directed AT THE ANSWER ITSELF or its
qualities; topic-value statements, person/process encouragement, and bridging
that coaches from a thin/garbled response without praising it are NOT quality
claims. (Train has no overpraise anchor to quote — train fails 164/437 fail on
other grounds; live rows may not be quoted.)
**Prediction:** dev 580 re-passes, 619 unaffected; live c98e re-passes (its
praise needs checking against the test — if answer-directed, it stays failed
and becomes a precedence decision for Maya+Grader B). b5c2/c89e/122/179
("calibrated vs dangerous validation") likely unchanged — those are the
escalation candidates after this run.
**Decision:** (run pending)

## v9 result → KEEP (live), with a compliance defect found
**Date:** 2026-08-12
**Split live:** 73.3% (11/15) · TPR 1.00 · zero false-fails — best live yet;
c98e re-passed, faf19 stayed caught. Remaining 4 = degree-of-praise rows.
**Split dev:** 78.3% (18/23) — 576 flipped back to false-pass (3rd flip;
churny), 580 still false-fails despite the carve-out naming its exact phrase.
**DEFECT:** v9's carve-out quoted dev row 580's coach line verbatim
("handling challenges is a valuable skill") — violates the no-dev-quotes rule.
Fixed in v10 (invented example). The quote didn't even flip the row —
evidence the 580 boundary is not wording-fixable.
**bae9 verified:** the "great and creative answer" line IS in the transcript;
the judge defends it (the answer had semi-real content; "creative" arguably
earned). Degree call → escalation pile, not attention failure.
**Decision:** KEEP v9 concept; v10 = dequote compliance fix, then escalate.

## v9 → v10 (compliance)
**What changed:** replaced the quoted dev phrase with an invented generic
example. No conceptual change intended.
**Decision:** (run pending)

## v10 result → champion (recorded)
**Split dev:** 78.3% (18/23) · **Split live:** 73.3% (11/15), zero false-fails
— identical to v9 as intended (dequote only). Decision doc exported mid-stream
for Grader B's rulings.

## Rulings applied (Grader B, 2026-08-18)
Praise density ruled OUT of this dimension (122, 179, b5c2, c523, c89e =
accepted mismatches); 619 accepted mismatch (judge correct); **580 relabeled
pass → fail** (consensus + split_reference; master_labels/calibration DB not
synced); 576 and bae9 stay fails the judge must catch. Dev balance is now
17 pass / 6 fail. Measured dev with no prompt change = 19/23 (580 becomes a
correct row).

## v10 → v11 (cluster F3 — certification of intelligible non-answers)
**Date:** 2026-08-18
**Prompt file:** feedback_question_low_bar_v11.md
**What changed (ONE concept):** a NON-ANSWER rule. A response that is
intelligible but supplies none of what the question asked (bare yes, one-word
topic, generic self-description, no past instance on a "tell me about a time"
question) cannot earn any positive attribution: certifying it as a good/great/
creative answer, or extracting a trait/skill/interest/virtue from it, is a
quality claim. Scoped away from F1 by an explicit boundary — garbled text is
unintelligible and stays exempt (assume the participant answered); a
non-answer is intelligible and empty. The v9 topic-value / bridging exemption
is narrowed to responses that actually contained content (it existed to protect
580, now relabeled fail). Anchor quoted from TRAIN row 437.
**Prediction:** dev 576 → fail (correct), 580 stays fail (now correct), 619
stays fail (accepted mismatch) ⇒ measured dev 20/23, effective 23/23. Live
bae9 → fail ⇒ measured 12/15, effective 15/15.
**Collateral watch:** F1 garbled rows must stay pass (dev 120/285/440/619-adj,
live faf6c/b437/b47b/b56f/b918/c98e — c98e is the riskiest, praise on a garbled
Q7); ruling-1 rows (122/179/b5c2/c523/c89e) must stay pass — if they flip to
fail, the non-answer rule has leaked into praise density and must be tightened.
**Decision:** (run pending)

## v11 result → REVERT (concept kept, scoping wrong)
**Date:** 2026-08-18
**Split dev:** 69.6% (16/23) · TPR 0.71 · TNR 0.67 — targets hit (576 fixed,
122 flipped to a genuinely correct fail, 580 correct) but FOUR new false-fails
(285, 391, 440, 577) and 609 lost.
**Split live:** 73.3% (11/15) · TPR 1.00 · TNR 0.33 — bae9 CAUGHT as predicted,
but faf19 regressed to pass. Zero false-fails throughout.
**Diagnosis:** the rule fired as a single-turn tripwire. 285/391/440/577 each
contain ONE manufactured positive on ONE non-answer inside an otherwise sound
session ("I receive feedback all the time" → "great to hear you're open to
feedback"); humans pass all four. 577 is the sharpest evidence: same CEO id as
576 (P-101), same coach move, opposite label — the difference is that in 576
nearly every answer is a non-answer, which is exactly Grader B's word,
"repeatedly". Separately, the new bullet displaced the praise-tier clause: 609
and faf19 were caught by "repeatedly certify mediocre answers as strong" in
v8-v10 and the judge stopped applying it.
**Decision:** REVERT v11 wording. Concept survives, scoped in v12.

## v11 → v12 (scope the non-answer rule)
**Date:** 2026-08-18
**Prompt file:** feedback_question_low_bar_v12.md
**What changed (ONE concept):** the non-answer rule now fires in exactly two
situations — (a) single turn, only when the coach certifies the non-answer AS
AN ANSWER with superlative/answer-directed praise (Grader B's bae9 ruling), or
(b) session pattern, when manufacturing positives out of non-answers is the
dominant shape of the session (her 576 rationale). Explicit non-firing cases:
one or two manufactured positives alongside real answers, and acknowledge-then-
name-the-gap. Added a line restoring the praise-tier clause's independent
force (the 609/faf19 displacement).
**Prediction:** dev 576 stays fail, 285/391/440/577 return to pass, 609
recaptured ⇒ measured 21/23, effective 23/23 with 179+619 accepted. Live bae9
stays caught, faf19 recaptured ⇒ measured 12/15, effective 15/15.
**Collateral watch:** 122 flipped to fail under v11 and matched the human label
— it may revert to pass under (b) if its non-answers are not dominant; that
costs a measured row but is an already-accepted mismatch. F1 garbled rows must
stay pass.
**Decision:** (run pending)

## v12 result → REVERT
**Date:** 2026-08-18
**Split dev:** 65.2% (15/23) · TPR 0.71 · TNR 0.50 — the scoping did not hold.
285/391/440 still fired on a single trait extraction despite the explicit
"does NOT fire on one or two" carve-out, and 577 fired through path (a)
("That's a solid start. Working in a team to unload containers, is a great
example" on a generic response). 609 still lost; 619's topic-mismatch fail
also disappeared, so the added bullet keeps crowding out existing tripwires.
**Decision:** REVERT. Two runs (v11, v12) confirm the same thing: at
single-turn granularity the labels do not support a non-answer trigger. 577
passes with answer-directed praise on a thin answer while bae9 fails for the
same move — the difference the labels encode is not a wording problem.
**Learned:** a fail condition stated as a definition ("a non-answer is X")
overrides carve-outs written after it; the judge applies the definition and
narrates the carve-out away. Restraints have to be part of the trigger, not an
appendix to it.

## v12 → v13 (narrow carve-in for the ruled bae9 pattern)
**Date:** 2026-08-18
**Prompt file:** feedback_question_low_bar_v13.md — branches from v10, not v12.
**What changed (ONE concept):** a single named pattern, per Grader B's ruling 2:
on a "tell me about a time..." question, if the participant's example is the
practice call itself, no past experience has been offered; accepting it as a
valid example is a disconnect and praising it as clever/creative is worse. No
general non-answer machinery.
**Prediction:** live bae9 → fail (12/15 measured, 15/15 effective). Dev
unchanged at 19/23 measured — verified no dev row answers the feedback question
self-referentially, so the clause is dev-neutral by construction.
**Collateral watch:** any row where the participant legitimately cites feedback
received during the call from a human coach (none in dev/live).
**Decision:** (run pending)

## v13 result → REVERT (net zero, wrong trade)
**Date:** 2026-08-18
**Split live:** 73.3% (11/15) · TPR 1.00 · TNR 0.33 — bae9 CAUGHT as ruled, but
faf19 regressed to pass, excusing generous praise as "coaching through what
appears to be a language barrier and audio issues" (the STT carve-out used as
an escape hatch). Dev not run (clause verified dev-neutral by construction).
**Attribution check:** re-ran v10 on live in the same session — it reproduced
exactly (faf19 fail, bae9 pass), so the faf19 flip is caused by the added
bullet, not model drift. Worth the extra run: three versions in a row lost
faf19 and nondeterminism was the competing explanation.
**Decision:** REVERT placement. Concept (ruling 2) still wanted; a whole new
bullet gives the judge a new lens and the praise-tier clause loses primacy.

## v13 → v14 (same ruling, embedded instead of appended)
**Date:** 2026-08-18
**Prompt file:** feedback_question_low_bar_v14.md — branches from v10.
**What changed (ONE concept, placement only):** the self-referential-example
pattern is now one sentence INSIDE the existing quality-claim bullet, as a
named case of unearned certification, rather than its own tripwire.
**Prediction:** live bae9 → fail AND faf19 stays fail ⇒ 12/15 measured, 15/15
effective. Dev unchanged (19/23 measured, 22/23 effective).
**Decision:** (run pending)

## v14 result → KEEP (concept), faf19 still lost
**Date:** 2026-08-18
**Split live:** 73.3% (11/15) · TPR 1.00 · TNR 0.33 — bae9 caught (ruling 2
encoded), faf19 still passes. Placement was not the cause: every encoding of
ruling 2 costs faf19, so faf19's fail is fragile on its own terms and the fix
belongs where it escapes — the STT allowance.
**Decision:** KEEP v14 as the base; address faf19 in v15.

## v14 → v15 (close the STT escape hatch)
**Date:** 2026-08-18
**Prompt file:** feedback_question_low_bar_v15.md
**What changed (ONE concept):** the STT allowance is bounded — bad audio, a
language barrier, or fragmented speech explains a warm move-along, but never
licenses certifying qualities (passion, strength, confidence, detail) the call
never demonstrated.
**Prediction:** live faf19 → fail with bae9 staying caught ⇒ 12/15 measured,
15/15 effective.
**Collateral watch:** the F1 rows are exactly the population this clause
borders — live faf6c/b437/b47b/b56f/b918/c98e and dev 120/285/440 must stay
pass. If any re-fails, v15 has re-broken the v7 ruling and must be reverted.
**Decision:** (run pending)

## v15 result → REVERT (breaks the STT ruling)
**Date:** 2026-08-18
**Split live:** 73.3% (11/15) · TPR 0.89 · TNR 0.50 — faf19 AND bae9 both
caught, but c98e re-failed: the coach restated words the participant did say
("completing the task and making sure everyone was satisfied") and called it a
positive attitude. That is the F1 population Maya's STT ruling protects, and
the run introduced the first live false-fail since v8.
**Decision:** REVERT. Effective agreement is the same 14/15 as v14, but the
remaining error is a false-fail on a ruled row, which is the worse profile.
**Learned:** bounding the STT allowance by "don't certify qualities" is too
coarse — restating caught words and attaching a modest attribute is exactly
what the ruling protects.

## v15 → v16 (bound the STT allowance by inner state, not by quality)
**Date:** 2026-08-18
**Prompt file:** feedback_question_low_bar_v16.md — branches from v14.
**What changed (ONE concept):** the allowance never covers claims about the
participant's inner state or delivery — passion, enthusiasm, conviction,
confidence, energy — which no transcript can evidence when the words show
nothing of the kind. Restating caught words with a modest attribute stays
aligned, which is the c98e/F1 behavior.
**Prediction:** live faf19 → fail ("I could hear a genuine passion in that
answer", Grader B's own round-3 note), bae9 stays caught, c98e stays pass ⇒
12/15 measured, 15/15 effective, zero false-fails.
**Collateral watch:** same F1 rows; any coach line praising audible enthusiasm
on an answer that genuinely shows it must still pass.
**Decision:** (run pending)

## v16 result → KEEP on live, dev cost
**Date:** 2026-08-18
**Split live:** 80.0% (12/15) · TPR 1.00 · TNR 0.50 · zero false-fails — best
live yet. faf19 and bae9 both caught; the three remaining rows are exactly the
ruling-1 accepted mismatches ⇒ effective live 15/15.
**Split dev:** 78.3% (18/23) · TPR 0.88 · TNR 0.50 — 122 and 576 now correct
(both ruled fails), but 580 and 609 regressed to pass and 735 is a new
false-fail ⇒ measured 18/23, effective 20/23 with 179+619 accepted.
**Diagnosis:** every addition since v10 dilutes the quality-claim criterion —
580, 609, faf19 and c98e have each flipped on edits that never mentioned them.
The clause is stated once, early, inside a long bullet list; the judge stops
weighting it as more text accumulates.
**Decision:** KEEP as the live champion pending v17's dev-recovery attempt.

## v16 → v17 (re-assert the quality-claim criterion at verdict time)
**Date:** 2026-08-18
**Prompt file:** feedback_question_low_bar_v17.md
**What changed (ONE concept, emphasis not content):** a final check before any
PASS verdict, re-running the quality-claim criterion over the whole session,
including the repeated-certification form. No new fail conditions.
**Prediction:** dev 580 and 609 re-fail ⇒ 20/23 measured, 22/23 effective; live
holds at 12/15 with zero false-fails.
**Collateral watch:** 735 (already a false-fail — if the check hardens it, the
error profile worsens) and the F1 garbled rows.
**Decision:** (run pending)

## v17 result → REVERT
**Date:** 2026-08-18
**Split dev:** 78.3% (18/23) — identical rows to v16; the pre-PASS re-check
moved nothing (580 and 609 stayed passes).
**Split live:** 73.3% (11/15) — c98e false-failed again, the same F1 collateral
v15 produced.
**Decision:** REVERT. Re-asserting an existing criterion at verdict time buys
no recall and costs precision on the garbled rows. v16 stands as champion.

## v16 → v18 (tighten the self-referential clause off dev 735)
**Date:** 2026-08-18
**Prompt file:** feedback_question_low_bar_v18.md — branches from v16.
**What changed (ONE concept):** the self-referential-example case is explicitly
narrowed to the AI practice call itself; feedback received from a real person —
supervisor, teacher, program staff — is a real instance however recent, same
day included. v16 stretched it to "the current session/program" and false-failed
735, whose participant cited feedback from the program earlier that day.
**Prediction:** dev 735 → pass ⇒ 19/23 measured, 21/23 effective, no false-fails
left on dev except ruled 619; live unchanged at 12/15 with bae9 still caught.
**Decision:** (run pending)

## v18 result → KEEP — CHAMPION (renamed feedback_question_low_bar_v18_hero.md)
**Date:** 2026-08-18
**Split dev:** 82.6% (19/23) · TPR 0.94 · TNR 0.50 — 735 recaptured as
predicted, nothing else moved. Disagreements: 179 + 619 (both ruled accepted
mismatches), 580, 609 ⇒ effective 21/23 (91.3%).
**Split live:** 80.0% (12/15) · TPR 1.00 · TNR 0.50 · zero false-fails — the
three remaining rows are exactly the ruling-1 accepted mismatches ⇒ effective
15/15 (100%). Both rows Grader B ruled must be caught (576, bae9) are caught.
**Decision:** KEEP as champion. Open on dev: 580 (she relabeled it fail on the
strength of v10's verdict; v18 passes it) and 609.

## Round-4 certification run (hero, fresh labels, never tuned on)
**Date:** 2026-08-18
**Split round4:** 60.0% (6/10) · TPR 0.71 · TNR 0.33. Grader B's 10 fresh labels
(7 pass / 3 fail), pulled from the deployed labeling app.
- **Caught:** dd54 — "That's really good. You're expressing genuine passion for
  the work" on a weak answer. That is the v16 inner-state clause firing on data
  it was never tuned against.
- **Missed (2, both praise density):** dcc3 and ed19 — her own notes call these
  overpraise, and dcc3 says "borderline, wouldn't mind a pass". Ruling 1 put
  praise density out of this dimension, so under that ruling both are accepted
  mismatches ⇒ effective 8/10 (80%).
- **False-failed (2):** cee4 and d534, both the Q7 topic-mismatch pattern —
  the participant answers "tell me about a time you received feedback" with a
  story that isn't about receiving feedback, and the coach praises it before
  redirecting. This is precisely the tripwire Grader B ruled should stand on dev
  619; on fresh calls she labeled the same pattern pass. New decision needed.
**Not run:** the test split remains untouched.
