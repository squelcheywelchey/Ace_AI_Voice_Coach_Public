# quality_conversational_flow — findings before v2

**Baseline (v1, dev, 2026-07-15):** 60.9% agreement, TPR 0.72, TNR 0.20, 9 disagreements
(5 judge-FAIL/human-PASS, 4 judge-PASS/human-FAIL). Labels verified identical to
`master_labels.csv` on main — disagreements are judge behavior, not stale labels.

## Cause 1 — judge fails a SINGLE recovered guardrail misfire (4 of 5 FN)

Rows 242, 609, 743, 749. In each, the redirect line fires once on a legitimate
utterance ("Thank you", "Provide an example", "Add more or just move on") and the
coach recovers on the next turn. Maya's final label: pass (fail line is repeated /
unrecovered breakdown). The v1 prompt lists "guardrail MISFIRES on a legitimate
request" as a standalone fail signal, so the judge treats one misfire as an
instant fail — the "one isolated, recovered hiccup is not a fail" caveat isn't
overriding it.

**v2 fix:** state explicitly that a single guardrail misfire followed by recovery
(coach complies or session resumes on the next turn) is a hiccup, not a fail;
fail requires the misfire to repeat or go unrecovered.

⚠️ **Data flag:** row 609 is ceo **P-646** — the FAIL anchor in
`rubric/dimensions.yaml` ("guardrail misfires twice before coach corrects") —
but the final label is **pass**, and both round-1 graders (Grader A G1, Grader P G3)
failed it. Either the anchor is stale or the label is wrong. Resolve with the
team before tuning the judge to reproduce it.

## Cause 2 — judge blind to repeated coach talk-over / turn fragmentation (3 of 4 FP)

Rows 71, 166, 410. Transcripts show the coach repeatedly starting its reply
mid-user-answer, leaving stacked fragments ("AI: Forgiveness is / User:
Reasoning."; "AI: That's a solid example of / User: And doing my job. / AI:
that's a solid"). Row 71 has 7 such fragments, 166 has 9, 410 has 5. The judge
sees that the session "progresses through all 8 questions" and calls each
instance recovered. Humans fail the *repetition* of interruptions regardless of
whether the script completes.

**v2 fix:** define the pattern concretely (coach turn fragments that cut into a
user answer; roughly 3+ instances = repeated breakdown) and state that finishing
the scripted questions does NOT redeem repeated talk-over.

## Cause 3 — guardrail firing at connection checks judged "reasonable" (1 FP)

Row 596. User says "Hey. Do you anything there?" / "Hello?" and gets the
off-topic redirect. The judge called that a reasonable guardrail firing; humans
(Maya, Grader D G2, Grader A G1) treat it as a misfire — a connection check deserves
"Yes, I'm here" (cf. row 617, where the coach does exactly that).

**v2 fix:** list "Hello?" / "Are you there?" -type utterances as legitimate,
on-task input for which the redirect counts as a misfire.

## Cause 4 — STT/transcript artifacts counted as breakdowns (1 FN)

Row 391. Judge failed on duplicated phrases ("Thank you for sharing that. Thank
you for sharing that.") that read as transcription artifacts, not real stacked
turns. Matches the open calibration item (transcript-artifact rule). Humans
discount these.

**v2 fix:** instruct the judge to ignore verbatim immediate duplications and
obvious transcription noise unless the user visibly reacts to them.

## Expected impact

Causes 1+4 address all 5 FN (TPR 0.72 → ~1.0 ceiling); causes 2+3 address all 4
FP (TNR 0.20 → ~1.0 ceiling). They pull in opposite directions on the guardrail
wording — the split is *recovered-single-misfire = pass* (cause 1) vs
*misfire-at-connection-check / repeated misfire = fail* (cause 3) — so change
them as separate iterations per the one-edit rule.


---

## Test-set result (2026-07-17, final)

v5_hero on the held-out test split (n=23): **65.2% agreement** (TPR 0.67, TNR 0.60), down from 73.9% on dev. 8 disagreements:
- **False-fail cluster (6 rows: 23, 141, 179, 285, 301, 773)** — judge counts 2+ coach cut-ins / restarted evaluative reactions as "repeated mechanical breakdown"; humans passed all six calls. The cut-in bar as encoded is stricter than the human bar. These errors sit on the team-preferred side (fail rather than false-pass), but they dominate the miss count.
- **False-pass (row 358)** — judge read mid-call fragmentation as STT artifacts + user backchannel; humans failed it.
- **False-pass (row 580)** — single guardrail misfire on a legitimate "Next question" that the session recovered from; judge applied the single-recovered-misfire allowance, humans failed it.

Test split is spent — these are the final numbers for v5_hero as-is. If the team wants to reopen the cut-in threshold, that is new dev-split work (and would need a fresh holdout to re-certify).

---

## Live-call reopening (2026-08-11) — round-3 production mismatches

**Trigger:** In the round-3 blind labeling of 15 live A/B calls (Maya labeled
this dim), the deployed v5_hero matched 7/15 (47%) — the worst dimension in the
round. 8 mismatches: 7 judge=FAIL vs Maya=PASS, 1 judge=PASS vs Maya=FAIL.
Maya's direction (2026-08-11): tune to the labels — live STT noise must not
fail calls. This is new dev work on a NEW live split; the spent test split is
untouched, and old-dev is kept as a regression guard.

**Why live is different:** the calibration corpus rows were EXCERPTS; live rows
are FULL ~8-question calls. v5's fail line — "cut-ins on TWO OR MORE separate
exchanges = FAIL even if nothing is lost" — is an absolute incident count.
Artifact incidence scales with call length, so on full transcripts the rule
fires on nearly every call: live calls average several chopped/restarted coach
turns that Maya reads as channel noise.

### Cluster L1 — recovered chop counted as breakdown (7 FP: 019fb437, 019fb47b, 019fb5c2, 019fc523, 019fc98e, 019fcdb3, 019fce25)

The judge counts each restarted evaluative reaction / chopped coach turn as a
cut-in and fails at 2+. But in every one of these calls the pattern is
RECOVERED: the coach finishes the thought once, the user's content is
addressed, the session progresses. Exemplar (019fc98e, Q6): the user presses
keypad keys mid-feedback, chopping the coach into three restarts — then the
coach says "Yes. I'm still here. Sorry about that. Let me finish up." and
completes the feedback. Maya: PASS. Several incidents are USER-caused (keypad
entries, talk-over, "Are you still there?") — not coach breakdowns at all.

**Human separator (hypothesis):** not the COUNT of incidents but (a) whether
the coach recovers — the content lands once and the call moves on — and
(b) whether the chop is pervasive enough to dominate the session. Scattered
recovered incidents on a full call = pass.

**Expected impact:** fixes all 7. Collateral watch: old-dev fail rows 71, 166,
410 (the cut-in fails the 2+ rule was built for) — "pervasive pattern" must
still catch them; excerpt rows are short, so a repeated pattern within the
excerpt still dominates the sample.

### Cluster L2 — coach-driven verbatim re-delivery loop passed (1 FN: 019fb56f)

Judge passed ("a couple of STT split turns... minor hiccups"). Maya failed.
The call: coach restarts the SAME full-name reminder from the top, verbatim,
at three separate points (user interjections each trigger a full re-delivery,
not a continuation), plus repeated mid-answer chop. The distinguishing mark
vs L1: re-delivery is coach-driven, verbatim-from-the-top, and RECURS across
the session — a loop, not a recovery. (Also note 019faf19, judge-correct FAIL:
call ends mid-feedback-turn — unrecovered by definition.)

**Expected impact:** explicit "verbatim full-turn re-delivery recurring across
the session = loop = fail" flips 019fb56f. Collateral watch: 019fc98e (keypad-
caused restarts that ARE re-deliveries but user-triggered + recovered) must
stay pass — scope the loop rule to coach-driven recurrence.

### Iteration plan

- v7: ONE conceptual change — replace the 2+ incident count with
  recovery/pervasiveness (L1). Run on live AND old dev.
- v8 (if needed): loop rule sharpening (L2), separately — L1 and L2 pull in
  opposite directions on the same fail block, so per the one-change rule they
  are two iterations by definition.

### Ruling R1 (Maya, 2026-08-11) — 019fb56f

Maya confirmed the fail is the REPEATED NAME-REMINDER: the coach re-delivers
the same privacy/name reminder at four separate points in the call. The ruling:
re-treading the same reminder/correction content again and again across the
session is a loop and fails, EVEN THOUGH each delivery completes and even
though the user's behavior (re-saying his name) re-triggers it. Encode at the
loop clause, dropping v9's "verbatim" qualifier (the deliveries are reworded)
and adding the user-re-triggered case explicitly. Scope guards unchanged:
single chopped delivery completing once = noise; within-one-exchange restarts
(019fc98e) = noise.

AMENDED (Maya, same session): the chopped turns count too — her fail is the
combination of the reminder loop AND the recurring restart-from-the-top chop.
Encoding boundary vs the L1 passes (which also contain chop): restart-chop
counts toward breakdown when the pattern RECURS ACROSS MULTIPLE SEPARATE
EXCHANGES in the session (fb56f); restarts concentrated in one exchange with
clean recovery (019fc98e keypad cluster), or occasional isolated restarts,
remain noise.

---

## Dimension closed — live reopening (2026-08-11)

**Champion: `quality_conversational_flow_v11_hero.yaml`** (v11; v5_hero remains
what production ran through 2026-08-11).

Final metrics: live 93.3% (14/15, TPR 1.00, zero false-fails), old dev 87.0%
(20/23, TPR 0.89 TNR 0.80). Effective dev counting the accepted mismatches
below: 22/23 (95.7%).

**Ruled outcomes (Maya, 2026-08-11):**
- Rows 377 (CEO P-488) & 749 (CEO P-336) — ACCEPTED MISMATCHES, judge-correct:
  the judge fails them on repeated coach-on-user cut-ins / guardrail misfire;
  the round-1 consensus "pass" stands as the label but is ruled the miss.
  Labels NOT edited (documented here only).
- Row 596 (CEO P-506) — accepted KNOWN MISS on the judge side: humans fail the
  guardrail-at-connection-check ("Hello? Are you there?"); the v6 encoding
  attempt caused collateral and is not retried. Judge passes it; label stands.
- Live 019fb56f (CEO 286961) — ruled FAIL (R1: repeated name-reminder +
  chopped restarts), KNOWN MISS: the compound signal (2 reminder points, each
  chopped-and-re-delivered) is below the encodable 3+ threshold, and the
  restart-chop rule broke dev (v10). Documented, not relabeled, false-pass
  side — revisit if a future round surfaces more compound cases.

**What remains:** no unspent holdout exists (July test split consumed; all 15
live rows used for tuning). Round-4 relabel (10 fresh calls, in progress) will
provide the one-shot certification set for v11 before deployment. Deployment
must replay the system/user layout check per the pii lesson.
