# adapts_when_stuck — Iteration Log

## v1 (initial)
**Date:** 2026-07-20
**Prompt file:** adapts_when_stuck_v1.yaml
**Training examples:** none quoted (prose pass/fail/na; rubric anchors unusable — pass-anchor in
test split, fail-anchor labeled not_observed — see findings).
**Description:** Faithful transcription of decided Rubric v2 (Option A). N/A scored as a real class
(harness + splitter extended; dev = 3 pass / 4 fail / 16 not_observed).
**Dev result:** 47.8% (11/23). TPR 1.00 / TNR 0.00 / N/A-recall 0.50 / 8 false-fires / 0 false-abstains.
**Decision:** BASELINE (keep as v1 reference).
**Notes:** Judge fires PASS on almost everything — misses all 4 FAILs, false-fires on half the calm
calls. Three consistent prompt bugs (signal bar too low; boilerplate counted as adaptation;
cherry-picks instead of fail-dominant call-level aggregation) — see findings. All errors point one way
(too lenient). Gating policy question for Maya before v2: labels are stricter than Option-A-as-written
— tune to labels (rec.) or treat as mislabels? Awaiting ruling.

---

## v1 → v2
**Date:** 2026-07-20
**What changed:** ONE change — raised the SIGNAL bar (Cluster 1). Defined genuine signal (unable to
produce an answer, lost audio, profanity-as-frustration, escalating agitation) vs an explicit
non-signal list (routine clarification, being finished, brief pause, one-off tangent, terseness).
Adaptation wording + aggregation unchanged.
**Predicted:** N/A false-fires 242, 313, 405, 440, 594, 735 → N/A (correct). Collateral watch: PASS
rows 301, 358, 622 must stay PASS. FAIL rows likely still not caught (need v3/v4).
**Result:** 78.3% (18/23), up from 47.8%. TPR 1.00 / TNR 0.00 / N/A-recall 0.94 / false-fires 8→1 /
false-abstains 2. Confusion N/A row: 0/1/15. All 3 PASS rows held; 6 N/A false-fires flipped correct
as predicted.
**Decision:** KEEP. Cluster 1 fix landed cleanly. TNR still 0 — all 4 FAIL rows still missed (536,609
→PASS via cherry-pick/boilerplate; 164,577 →N/A). Next: v3 boilerplate≠adaptation, v4 fail-dominant
aggregation. Two rows to verify for possible mislabel: 166 (judge FAIL, human N/A — "lost for words"
conflicts with 301 PASS principle) and 164/577 (judge finds no genuine signal).

## v2 → v3
**Date:** 2026-07-20
**What changed:** ONE change — fail-dominant CALL-LEVEL aggregation (Clusters 2+3). Scan the whole
call; one genuine signal met with the template continuing unchanged / same canned line repeated =
FAIL, even if other moments were handled. Stock lines ("I'm here to help… let's focus") + standard
feedback template delivered unchanged do NOT count as adapting. Signal bar unchanged from v2.
**Predicted:** 536 → FAIL (ignored "Fuck this"), 609 → FAIL (repeated canned line). Collateral watch:
PASS rows 301/358/622 must hold (358 is long/multi-moment — risk if it has any ignored genuine signal);
15 correct N/A must hold. 164/577 likely stay N/A (implicit signal), 166 likely stays FAIL — all three
are escalation candidates, not v3 targets.
**Result:** 78.3% (18/23) — same headline as v2 but WORSE profile. N/A-recall 1.00 / false-fires 0,
but the judge now abstains instead of ever calling FAIL (judge-FAIL column all zeros; false-abstains
4), and it lost a true PASS (358 → N/A; TPR 1.00→0.67). Fail-dominant framing made the judge more
conservative without gaining any FAIL detection: on 536 it still reads the templated "try again or
move on" retry-offer after "Fuck this" as a reframe (Cluster 2 boilerplate rule did not land).
**Decision:** REVERT. **v2 remains champion (78.3%).**
**Learned:** (1) The unfixed gap is Cluster 2 — the judge credits the standard feedback+retry template
as "adaptation"; the fail rows can't be caught until that's broken, but breaking it risks the mild-
clarification PASS rows. (2) The labels themselves are inconsistent on the mild-clarification boundary:
358 (PASS) hinges on the coach handling "I lost you for a second", while 594 (N/A) is a near-identical
"repeat the question" — so the PASS/N/A line on couldn't-hear moments is not cleanly learnable. (3) The
FAIL class is thin (4 dev rows) and boundary-heavy → escalate to Maya rather than overfit.

## v2 → v4 (encode Maya's rulings; built on v2, not v3)
**Date:** 2026-07-20
**What changed:** Encoded the 3 confirmed judge-bug rulings as carve-outs: (a) stock feedback template /
retry-offer / repeated canned line is NOT an adaptation (536, 609); (b) fail-dominant aggregation so one
ignored genuine signal = FAIL even with a good moment elsewhere (536); (c) sustained disengagement/
deflection pattern is a genuine signal (577); (d) "can't find words / lost for words" IS a signal —
removed from non-signals (166); garbled-speech-alone stays N/A (164). v2 signal recognition otherwise
inherited (protect 358 PASS; avoid v3 over-conservatism — no heavy "high threshold" framing).
**Predicted (measured, vs labels):** 536 PASS→FAIL ✓, 609 PASS→FAIL ✓, 577 N/A→FAIL ✓ (+3 → ~21/23).
164 stays N/A (judge-correct, label FAIL → measured-miss/accepted), 166 stays FAIL (judge-correct, label
N/A → measured-miss/accepted). Effective ≈ 23/23. **Collateral watch:** the 3 PASS rows (esp. 358) must
hold; the 15 correct N/A must not flip to FAIL from the new disengagement-signal rule (terse-but-fine =
still N/A).
**Result:** 73.9% measured (17/23) / 82.6% effective (19/23, counting 164+166 accepted). TNR 0.00→0.75
(3/4 fails CAUGHT: 536/609/577 flipped to FAIL as predicted), NPV 0.50. But false-fires 1→4: the
disengagement rule overshot onto 242 ("Hello?/what's in the special?") and 440 (Lil Nas X tangent) →
false FAIL; and v4 dropped two v2 recognitions → 313 (lost "nothing-more-to-add = finished" → false
PASS) and 358 (lost "couldn't hear/lost you" → false N/A, PASS collateral).
**Decision:** PARTIAL — core rulings encode correctly (fails caught) but 4 collateral errors. Do NOT
keep as champion yet; v5 tightens. 164 (judge N/A) + 166 (judge FAIL) confirmed as accepted mismatches.

## v4 → v5
**Date:** 2026-07-20
**What changed:** Tighten v4's over-reach, restore v2 precision (all corrections to the ruling
encoding, not new direction): (1) disengagement signal must be the DOMINANT pattern of the session
(user deflects/won't genuinely answer across most questions), explicitly excluding a single tangent/
story (440) or stray interjection (242); (2) restore "nothing more to add AFTER answering" = finished
= N/A (313), distinct from "can't produce any answer when asked" = signal (609); (3) restore "couldn't
hear / I lost you" as a mild genuine signal handled by re-summarizing = adapts (358), while a plain
"repeat the question" re-ask stays routine N/A (594).
**Predicted (measured):** 242→N/A, 440→N/A, 313→N/A, 358→PASS restored; 536/609/577 stay FAIL. →
21/23 (91%); only misses 164+166 (accepted) → effective 23/23. Risk: 358's "couldn't hear" carve-out
may flip 594 to a false PASS (358-vs-594 is a known label inconsistency).
**Result:** **91.3% measured (21/23) / 100% effective (23/23).** TPR 1.00 / TNR 0.75 / PPV 1.00 /
NPV 0.75 / N/A-recall 0.94 / false-fires 1 / false-abstains 1. Confusion: PASS 3/0/0, FAIL 0/3/1,
N/A 0/1/15. All predicted flips landed: 242/440/313 back to N/A, 358 restored to PASS, 536/609/577
stay FAIL; 594 stayed N/A (feared collateral did NOT occur). The ONLY 2 remaining disagreements are
the accepted mismatches 164 (judge N/A, label FAIL) and 166 (judge FAIL, label N/A) — judge correct
on both per Maya.
**Decision:** **KEEP — CHAMPION (v5).** Every genuine dev disagreement resolved; residual = 2 candidate
relabels. Ready to close pending Maya's go on the test-split run + whether to relabel 164/166.

## TEST SPLIT (one-shot, v5, 2026-07-20) — final unbiased estimate
**68.2% (15/22).** TPR 0.50 / TNR 0.75 / PPV 0.17 / NPV 1.00 / N/A-recall 0.69 / false-fires 5 /
false-abstains 2. Confusion: PASS 1/0/1, FAIL 0/3/1, N/A 5/0/11.
**Dev→test gap (91.3%→68.2%) = PASS over-fire.** 5 of 7 misses are N/A→PASS: the judge infers a genuine
stuck signal from a mild pause ("Let's see." 246, "I can't think right now" 141, "Hello?" 71, "This is
a challenge by itself" 122, "I already have it. I mean," 518) *because the coach said "Take your time"*,
and passes — humans call these N/A. Dev lacked these reassurance-on-a-non-signal cases, so v5 overfit
that boundary. Also 633 PASS→N/A (isolated interjections dismissed) and 758 FAIL→N/A (missed fail).
**What generalized:** FAIL detection — NPV 1.00 (every judge-FAIL correct on test), TNR 0.75. The judge
is trustworthy when it says FAIL; it is over-generous when it says PASS.
**Honest read:** this was the lowest-N dimension (16 scoreable; test = 2 pass/4 fail/16 N/A), so the
PASS class is tiny and the estimate is high-variance. The test split is now SPENT — no further tuning
against it. Improving the PASS/N/A boundary needs more labeled PASS cases or a fresh holdout.

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
