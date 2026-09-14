# scaffolds_then_fades — Iteration Log

## v1 (initial)
**Date:** 2026-07-16
**Prompt file:** scaffolds_then_fades_v1.yaml
**Training examples:** none quoted (rubric v2 anchors P-240 / P-646 landed in test / dev — not quotable; P-982 is in train and available for later versions)
**Description:** Initial prompt, straight transcription of the decided rubric v2: pass = ≥1 successful scaffold built from the user's OWN material (templates count, fades dropped); fail = model answer EVER / invented content EVER / no scaffolding at all; N/A never correct.
**Split:** splits/scaffolds_then_fades/ (seed default) — train 8 (2P/6F), dev 23 (6P/17F), test 23 (6P/17F); mirrored into labels/{train,dev,test}_ids.csv
**Dev result:** 69.6% (16/23), TPR 0.17, TNR 0.88 — judge far too strict on PASS (1 of 6 caught)
**Notes:** Two false-fail clusters (see findings): judge requires a formal template and won't credit successful elicitation (377, 735, 758); MODEL/INVENTED tripwire misfires on suggestions that point back at the user's own stated material (120, 376). The 2 false-passes (155, 205) confirm the humans require the scaffold to LAND — offers declined every time never pass.

---

## v1 → v2
**Date:** 2026-07-16
**What changed:** Scaffolding redefined as successful ELICITATION, not template delivery — one conceptual change with three clauses: (a) a plain drawing-out prompt counts when the user then produces better answer content from their own life, template not required; (b) pointing back at material the user already stated is scaffolding, NOT a model answer / invention (invention = no basis in anything the user said); (c) the outcome requirement made explicit — offers always declined, or retries filled with the coach's own suggested content, do not pass.
**Agreement before:** 69.6% (TPR 0.17, TNR 0.88)
**Agreement after:** 78.3% (18/23), TPR 0.67, TNR 0.82
**Decision:** KEEP
**Notes:** All 5 remaining disagreements sit on one boundary — the QUALITY bar for the elicited answer. Humans PASS 376/758, where full specific stories arrive after coach prompting, but FAIL 155/205/213, where the "improvement" is a thin one-line addition or an echo of the coach's own suggested list. The judge currently credits any marginal elaboration (155/205/213 false-pass) while demanding it on a same-question retry (376/758 false-fail).

---

## v2 → v3
**Date:** 2026-07-16
**What changed:** Set the SUCCESS BAR for an elicited answer — a scaffold succeeds only when the user produces a SUBSTANTIVE answer from their own material (a concrete example or story with real specifics: what happened, what they did). A one-line addition, a marginally longer restatement, or a retry that repeats the coach's own suggested content does not clear the bar; and the substantive answer may arrive on ANY later question after coach prompting, not only a same-question retry.
**Agreement before:** 78.3% (TPR 0.67, TNR 0.82)
**Agreement after:** 82.6% (19/23), TPR 0.50, TNR 0.94
**Decision:** KEEP — first version at/above the 80% target on dev; fixed 155 and 213, only 1 false-pass left.
**Notes:** The 4 remaining disagreements are judgment calls needing Maya's ruling, not prompt bugs — see "Open judge calls" in findings/scaffolds_then_fades_findings.md: (1) model-answer stem anchored in the user's real background (120), (2) how thin is too thin (205, likely-correct judge / possible relabel), (3) crediting stories elicited by plain "go ahead and share" invitations (376, 758).

---

## v3 → v4
**Date:** 2026-07-16
**What changed:** Maya's ruling on judge call #1 — a short recitable STEM anchored in the user's real background is scaffolding (paraphrasing the user's own material back to them), NOT a model answer. The model-answer tripwire now requires a COMPLETE answer or content the user never said. (Example in prompt is generic — the motivating dev row 120 can't be quoted.)
**Agreement before:** 82.6% (TPR 0.50, TNR 0.94)
**Agreement after:** 87.0% (20/23), TPR 0.83, TNR 0.88
**Decision:** KEEP — best so far. 120 → PASS as targeted; 758 also flipped to PASS (stem allowance relaxed the coach-contribution read). 155 regressed to false-PASS (borderline flip-flopper: its retry echoes the coach's suggested list, consensus FAIL). Remaining: 155, 205 (judge PASS / consensus FAIL), 376 (judge FAIL / consensus PASS).

---

## v4 → v5
**Date:** 2026-07-16
**What changed:** Maya's ruling on judge call #2 — a genuine attempt built from the user's OWN real material counts as a successful scaffold even when minimal/thin. Echoes of the coach's suggested content still do not count. Removed the "thin one-line addition / marginally longer restatement" fail language.
**Agreement before:** 87.0% (TPR 0.83, TNR 0.88)
**Agreement after:** 78.3% (18/23), TPR 1.00, TNR 0.71
**Decision:** REVERT — v4 stays champion.
**Notes:** The explicit thin-attempt allowance over-generalized: the judge began crediting ANY concrete user content as a landed scaffold, including content that wasn't a response to coaching at all. 594: the user's strong stories are FIRST-TAKE answers to the interview questions; every actual coaching prompt is declined — humans fail it because no scaffold ever landed. 329: the "retry" repeats the flagging license already stated in Q1 (nothing new was drawn out). It did fix 376 (+ kept 205 per Maya's ruling), but 213/329/594 flipped wrong: net 20→18. Maya's ruling #2 survives WITHOUT this language: v4 already passes 205 — so 205 (and 155) stand as accepted mismatches / relabel candidates rather than prompt work. The durable insight for any future edit: elicited content must arrive AFTER and BECAUSE OF a coach prompt — uptake, not user forthcomingness.

---

## v4_hero — TEST RUN (final, run once)
**Date:** 2026-07-17
**Prompt file:** scaffolds_then_fades_v4_hero.yaml (sha 1addac50, git af79a33, clean)
**Model:** claude-sonnet-4-6 · **Split:** test (n=23)
**Agreement:** 87.0% (20/23) · **TPR:** 0.83 · **TNR:** 0.88 · **PPV:** 0.71 · **NPV:** 0.94
**Confusion:** TP 5 · FN 1 · FP 2 · TN 15
**Decision:** FINAL — identical to dev (87.0%), no generalization gap.
**Notes:** 3 disagreements: rows 27 & 284 (consensus FAIL, judge PASS — both are coach-prompt-elicits-concrete-story-from-user's-own-history, i.e. the same pattern as Maya's ruling #2 accepted mismatches; candidates for the same accepted-mismatch treatment, Maya to confirm) and row 522 (consensus PASS, judge FAIL — judge says retries never produced substantive content from the user's own material). Test split is now spent; no further iteration against it.


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
