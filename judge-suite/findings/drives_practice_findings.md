# Drives Practice & Uptake — Findings

Dimension key: `drives_practice_uptake`.
Labels/Judge: consensus in `labels/consensus_drives_practice.csv` (built from
`splits/drives_practice/split_reference.csv`; no `master_labels.csv` exists for this dim, so
split_reference IS the canonical source). Judge model = claude-sonnet-4-6 via `eval_harness_v2`.

Split (Grader C, 2026-07-12): train 8 (4/4) · dev 23 (11 pass / 12 fail) · test 23 (11/12).
The v1 prompt quotes NO transcript text, so there is no dev/test leakage.

## v1 baseline
**Date:** 2026-07-17 · **Split:** dev · **Prompt:** drives_practice_v1.yaml (faithful transcription of Grader C's low-bar definition — unchanged from her draft, never previously run)

**Result: 22/23 (95.7%).** TPR 1.00 · TNR 0.92 · PPV 0.92 · NPV 1.00.
Confusion: 11 TP / 11 TN / 1 FP / 0 FN. The single error is a **false-pass** (the error type the team weights most heavily).

### The one disagreement — row 596 (ceo P-506)
Consensus = FAIL (single rater: Grader B). Judge = PASS.

What actually happened in the transcript:
- The coach offered "would you like to try responding again?" after **essentially every one of the 8 questions**.
- The participant **declined every coach offer** ("Next question", "Next").
- The ONE retry in the whole call was **user-self-initiated**: on the responsibility question the user said *"I want to repeat that,"* the coach said *"Of course, please go ahead,"* and the user gave a second attempt ("Buying my own business and planning my own crews…").

v1's definition is **participant-centric** — "Did the participant attempt at least one retry or expansion?" By that literal bar the judge is correct: a retry attempt exists. The humans read the *dimension* (drives practice **and uptake**) as coach-centric: the coach drove practice all call but secured **zero uptake of any coach-offered retry**; the lone retry was user forthcomingness, not coach-driven uptake.

### Classification: JUDGMENT CALL — escalate, do not silently tune
Two **decided** sources contradict each other on exactly this row:
- **Coach-centric read** (CLAUDE.md "evaluate the coach, not the participant" + this skill's durable rule "elicited content must arrive because of a coach prompt — uptake, not user forthcomingness") ⇒ **596 = FAIL**, and v1's participant-centric definition is the bug to fix.
- **Rubric v2, DECIDED** (CLAUDE.md: "uptake is outcome-based but relaxed — *any retry attempt passes*") ⇒ **596 = PASS**, the judge is correct, and the label is an **accepted mismatch**.

This is not a prompt bug with an obvious fix; the fix *direction* is itself the open policy lever. Escalated to Maya as decision #1 (below). Not tuning the judge to reproduce a single-rater label that contradicts the decided rubric until ruled.

## Decision #1 — RULED (2026-07-17)
**Does a user-self-initiated retry count as uptake?** (row 596)
**Maya's ruling: A — "any retry attempt passes" (rubric v2 as written).** Judge is correct on 596; recorded as an accepted mismatch; v1 shipped as champion (`drives_practice_v1_hero.yaml`). Dimension moved to close-out → ran the test split once.

## Test run — Ruling A does NOT survive the holdout
**Date:** 2026-07-17 · **Split:** test · **Prompt:** drives_practice_v1_hero.yaml
**Result: 17/23 (73.9%).** TPR 1.00 · TNR **0.50** · PPV 0.65 · NPV 1.00. (11 TP / 6 TN / 6 FP / 0 FN)

**All 6 test errors are false-passes with the identical shape as row 596** — a retry/expansion literally happened, judge = PASS, humans = FAIL:

| row | ceo | how the retry arose | src / raters |
|-----|-----|---------------------|--------------|
| 155 | P-430 | user reluctantly complies, gives prioritization detail | Grader B solo |
| 179 | P-176 | **coach-prompted** ("AI: Let's try again"), user gives 2nd answer | Grader B solo |
| 205 | P-712 | user-initiated ("Add more detail") | Grader B solo |
| 536 | P-801 | user "More"; coach hands a model answer | Grader B solo |
| 580 | P-982 | user-initiated ("Try to answer the question again"); coach gives an example | Grader B solo |
| 617 | P-646 | **coach-prompted** ("Would you like to try again? / Yes") | tiebreak: Grader B PASS, **Grader C FAIL** |

### What this means
- The lone dev disagreement (596) was **not** a one-off. On held-out data the humans systematically FAIL retry-happened calls at **26% (6/23)**. The holdout did exactly its job: it caught that Ruling A overfit to the single dev example.
- **The stricter bar is not "user-initiated vs coach-driven."** 179 and 617 are coach-*prompted* retries and were still failed. So Ruling B (coach-driven carve-out) would fix at most 3–4 of the 6, not the pattern.
- The bar the humans actually applied looks **holistic / session-level**: did a genuine *practice loop* occur (coach drives, participant substantively re-attempts, answer improves) — not "was there ≥1 retry anywhere." This matches the original corpus finding ("the coach lectures instead of running a practice loop; no practice uptake ~60%").
- **Data-quality caveat:** 5 of the 6 are **single-rater (Grader B)** labels; 617 is Grader B-PASS overridden by Grader C. This strict bar is largely one labeler's, applied consistently. Whether it *is* the team's intended bar (vs. rubric v2's relaxed "any retry passes") is now the open question.

### Methodological cost (must flag)
The test split is now **informative** — running it under Ruling A was the correct close-out step, but it revealed the definition is wrong, so if we iterate to a stricter v2 the 73.9% is no longer a clean unbiased holdout for the *new* judge. Any real v2 will need either a fresh holdout (re-split) or an explicit "no clean test number" caveat.

## Closer look (2026-07-17) — the 6 test FAILs are TWO problems, not one
Read all 6 test FAIL transcripts in full + PASS calls (164, 166, 285) for contrast.

**Genuine PASS calls** (mostly 2-rater "agreement"): the participant takes up the coach's offer **multiple times**, each producing a fuller answer **in their own words** — 164 "Let's say I'm in Anthony again" → expanded forklift/postal answer; 166 "I like to do that response again" → UPS/Caltrans detail; 285 "Answer it again" → real culinary answer. Real uptake, as a session-level pattern.

**Pattern 1 — no genuine user re-attempt exists (536, 580, 617): CLEAN JUDGE BUG.**
- 580: user says "Say it again / Repeat that / Try to answer the question again" = asking the *coach* to repeat its model answer. The judge read this as the user re-attempting. It isn't.
- 536: user says "More"; the coach responds with a *model answer*; the user never re-attempts.
- 617: coach offers, user says "Yes" then immediately "No… move on."
- Fix: require that **the participant produces a second attempt in their OWN words** — not a request for the coach to repeat, not the coach reading a model answer, not an offer the user declines/reverses. This is fully consistent with Ruling A and rubric v2; it does NOT touch the 596 policy. Should flip all 3 to FAIL.

**Pattern 2 — exactly one real retry in a mostly-declining session (155, 179, 205): THE 596 POLICY.**
- 155 even has a *substantive* coach-driven retry (organization Q), but the participant is combative and declines the rest → Grader B FAIL.
- 179: one brief coach-driven retry, rest declined → FAIL. 205: declined all 8, minor expansions only in the bonus round → FAIL.
- These are the same question as 596: does ONE genuine retry pass, or does PASS require a real practice *loop* (typically 2+ substantive uptakes)? Grader B fails them; Maya's Ruling A (per 596) passes them.

**Provenance skew worth flagging:** every Pattern-2 FAIL (155/179/205) and 596 is **single-rater Grader B** (617 too, overridden by Grader C); the PASS set is mostly 2-rater "agreement." So the strict "one retry isn't enough" bar is essentially one rater's, and it contradicts the decided rubric v2. Candidate for a second-rater reconciliation pass regardless of the ruling.

## Decision #2 — needs Maya (reopens the definition)
The v1 low-bar definition ("≥1 retry attempt = PASS") disagrees with the human labels on 26% of held-out data, all in the lenient direction. Two ways forward:
- **2A — Tighten the judge to the humans' holistic bar.** Redefine PASS as a genuine coach-driven practice loop with a substantive re-attempt (not one stray retry). Iterate v2 against dev — but dev only contains ONE example of this pattern (596), so dev can't validate a fix; we'd re-split or lean on the (now-spent) test rows as diagnostic. Expect measured agreement to move a lot.
- **2B — Treat Grader B's strict FAILs as candidate mislabels.** Rubric v2 as decided says "any retry attempt passes," which makes the *judge* correct on all 6. Then the labels (mostly single-rater) need a second-rater / reconciliation pass before this dimension can be scored honestly. Judge stays as-is.
