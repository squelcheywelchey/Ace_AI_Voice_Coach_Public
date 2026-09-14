# quality_conversational_flow — Iteration Log

Consensus: `labels/consensus_quality_conversational_flow.csv` (54 rows: 42 pass / 12 fail).
Split: `splits/quality_conversational_flow/` — train 8 (6P/2F), dev 23 (18P/5F), test 23 (18P/5F), seed 42.
Harness: `scripts/eval_harness_v2.py` (Grader C's — confusion-matrix run log + HTML disagreements report).

## v4 → v5
**Date:** 2026-07-16
**Prompt file:** quality_conversational_flow_v5.yaml (sha 4c590396, git 12a1a54)
**Model:** claude-sonnet-4-6 · **Split:** dev (23 scored)
**What changed:** Sharpened cut-in vs STT-split: a cut-in OPENS a new evaluative reaction mid-answer ("That's a good start…"), a split CONTINUES an unfinished sentence; threshold 3+ → 2+; tie goes to cut-in. (Maya's direction: fixing FPs is the priority; FNs may be the judge catching human misses.)
**Agreement:** 73.9% (17/23) · **TPR:** 0.72 · **TNR:** 0.80 · **PPV:** 0.93 · **NPV:** 0.44
**Confusion:** TP 13 · FN 5 · FP 1 · TN 4
**Decision:** KEEP (ties v4 on agreement but with the error profile Maya wants: FPs 3 → 1)
**Notes:** Targets 166 and 410 both fixed. Remaining FP: 596 only (guardrail at connection checks). FNs (377, 522, 594, 609, 749) are strict-judge calls Maya suspects are human misses — candidates for label re-review rather than prompt relaxation. If those five were relabeled fail, v5 would sit at 95.7%.

---

## v5 → v6
**Date:** 2026-07-16
**Prompt file:** quality_conversational_flow_v6.yaml (sha def9ec69, git b323188)
**Model:** claude-sonnet-4-6 · **Split:** dev (23 scored)
**What changed:** Guardrail firing at connection checks ("Hello?", "Are you there?") declared a misfire (targeting row 596).
**Agreement:** 69.6% (16/23) · **TPR:** 0.67 · **TNR:** 0.80
**Confusion:** TP 12 · FN 6 · FP 1 · TN 4
**Decision:** REVERT (v5 stands)
**Notes:** The target worked — 596 now correctly fails — but the strengthened misfire language pulled 242 and 743 back into false-fails (single recovered misfires) and 166 regressed to pass. Net FP count unchanged (596 → 166), 2 extra FNs. If 596 matters, a narrower version ("repeated redirects at connection checks") could be tried; otherwise accept 596 as v5's one FP.

---

## v3 → v4
**Date:** 2026-07-16
**Prompt file:** quality_conversational_flow_v4.yaml (sha 1a30642e, git 4f24760)
**Model:** claude-sonnet-4-6 · **Split:** dev (23 scored)
**What changed:** Replaced the disruption rule with Maya's row-71 rationale: repeated cut-ins on the user's flow fail even when nothing derails or gets lost. Telltale signature = the user's next turn continues the answer with new content the coach's already-started feedback doesn't account for. STT-split vs cut-in separated by whether the user adds answer content or only backchannels.
**Agreement:** 73.9% (17/23) · **TPR:** 0.83 · **TNR:** 0.40 · **PPV:** 0.83 · **NPV:** 0.40
**Confusion:** TP 15 · FN 3 · FP 3 · TN 2
**Decision:** KEEP (best so far; +4.3 over v3, +13 over v1)
**Notes:** Row 71 now correctly fails; row 242 now correctly passes. Row 749 regressed (judge stacks cut-ins it now sees onto the guardrail complaint). Remaining 6: (a) guardrail cluster unchanged — 609 FN, 596 FP, blocked on the P-646 anchor ruling; (b) cut-in threshold cases — judge counts "one or two" cut-ins in 166/410 (Maya: fail) but "at least two/multiple" in 594/749 (Maya: pass). The count the judge lands on, not the rule, is now the disagreement — these four are candidates for a human side-by-side before more prompt surgery.

---

## v1 → v3 (v2 reverted; v3 builds on v1)
**Date:** 2026-07-16
**Prompt file:** quality_conversational_flow_v3.yaml (sha 23d52d9b, git bd4580d)
**Model:** claude-sonnet-4-6 · **Split:** dev (23 scored)
**What changed:** Replaced the talk-over clause with a disruption-based rule (fail only when the interruption has consequences: user's continuation ignored/lost, or user shows confusion) + explicit "STT mid-sentence splits are transcription noise, not breakdowns" in the pass block.
**Agreement:** 69.6% (16/23) · **TPR:** 0.83 · **TNR:** 0.20 · **PPV:** 0.79 · **NPV:** 0.25
**Confusion:** TP 15 · FN 3 · FP 4 · TN 1
**Decision:** KEEP (best so far; +8.7 over v1)
**Notes:** The transcription-noise language fixed the v2 over-fire AND v1's row 391 (duplication artifact) plus 743/749 (judge stopped stacking weak signals). But the disruption rule did NOT capture Maya's fails — 71, 166, 410 still pass (judge: "no user input is lost"), so TNR stays 0.20; and 594 became a new FN (interruption → "What?" + coach answers own question — judge found consequences where Maya passed). Boundary between 594 (human pass) and 166 (human fail) is now very fine — worth a human consistency check. Remaining 7 disagreements: guardrail misfires 242/609 (FN, blocked on P-646 anchor ruling), guardrail-at-connection-check 596 (FP), talk-over boundary 71/166/410 (FP) + 594 (FN).

---

## v1 → v2
**Date:** 2026-07-16
**Prompt file:** quality_conversational_flow_v2.yaml (sha a4104d2c, git c1e5b4d)
**Model:** claude-sonnet-4-6 · **Split:** dev (23 scored)
**What changed:** Made talk-over countable: coach turn fragments cutting into a user answer on 3+ separate exchanges = FAIL; "completing the script does not redeem repeated talk-over"; pass-side recovery tightened to "isolated (one or two), never a repeated pattern".
**Agreement:** 52.2% (12/23) · **TPR:** 0.50 · **TNR:** 0.60 · **PPV:** 0.82 · **NPV:** 0.25
**Confusion:** TP 9 · FN 9 · FP 2 · TN 3
**Decision:** REVERT
**Notes:** The rule hit its targets — rows 71 and 166 now correctly fail (TNR 0.20 → 0.60) — but STT-split coach turns are ubiquitous in these voice transcripts, so the 3+ fragment count over-fires on human-PASS calls: 377, 522, 594, 619 became new false-fails and TPR collapsed (0.72 → 0.50). Row 410 (human FAIL) counted only 2 fragments, so a count threshold doesn't even capture the real fails. **Learning:** the human separator is not HOW MANY fragments but whether the interruption is DISRUPTIVE — the coach responds to a partial answer and the user's completion is lost / the user shows confusion — vs. benign STT splits where the coach's full reply still addresses the complete answer. v3 candidate: express talk-over in disruption terms, not counts. Guardrail-misfire FNs (242, 609, 743, 749) unchanged, still blocked on the P-646 anchor ruling.

---

## v1 (baseline)
**Date:** 2026-07-15
**Prompt file:** quality_conversational_flow_v1.yaml (sha be8f2c6c, git 853a269)
**Model:** claude-sonnet-4-6 · **Split:** dev (23 scored)
**What changed:** Initial prompt, transcribed straight from rubric v2 (`rubric/dimensions.yaml`): mechanics only, guardrail-misfire fail, "one recovered hiccup ≠ fail". No transcript quotes.
**Agreement:** 60.9% (14/23) · **TPR:** 0.72 · **TNR:** 0.20 · **PPV:** 0.76 · **NPV:** 0.17
**Confusion:** TP 13 · FN 5 · FP 4 · TN 1
**Decision:** KEEP (baseline — nothing to revert to)
**Notes:** Miscalibrated in BOTH directions; the 9 disagreements split into two clean clusters:
- **Judge too harsh on guardrail misfires** (5 FN: rows 242, 391, 609, 743, 749). Judge fails any single misfire ("Provide an example." → redirect); consensus passes these — the humans apparently require repeated/unrecovered misfires (cf. rubric fail anchor: "misfires **twice** before coach corrects"). Fix candidate: a single guardrail misfire that the session recovers from is NOT a fail; repeated misfires or a misfire the coach never corrects is.
- **Judge too lenient on turn fragmentation** (4 FP: rows 71, 166, 410, 596). Judge reads repeated STT-fragmented / stacked / interrupted coach turns as "recovered hiccups"; consensus fails them when the pattern repeats. Fix candidate: define "repeated" concretely (e.g. 3+ fragmented or overlapping exchanges = fail even if the session limps forward), and clarify that "recovery" means the flow problem stops, not that the call merely continues.
- Careful on 596: guardrail firing on "Hello? / Do you anything there?" — consensus FAIL, so humans treat firing the redirect at connection-check utterances as a misfire too. Fold into the misfire definition.

---

## v5_hero — TEST RUN (final, run once)
**Date:** 2026-07-17
**Prompt file:** quality_conversational_flow_v5_hero.yaml (sha 4c590396, git af79a33, clean)
**Model:** claude-sonnet-4-6 · **Split:** test (n=23)
**Agreement:** 65.2% (15/23) · **TPR:** 0.67 · **TNR:** 0.60
**Confusion:** TP 12 · FN 6 · FP 2 · TN 3
**Decision:** FINAL — down from 73.9% dev. Test split is now spent; no further iteration against it.
**Notes:** 8 disagreements, skewed toward over-failing: 6 false-fails (rows 23, 141, 179, 285, 301, 773 — all the same cluster: judge counts 2+ coach cut-ins/restarted evaluative reactions as repeated mechanical breakdown where humans passed the call) and 2 false-passes (358 — judge read fragmentation as STT noise + backchannel; 580 — single recovered guardrail misfire on "Next question", humans failed it). The cut-in threshold ("2+ = repeated") is stricter than the human bar on test; note the errors are mostly on the preferred side (false-fail rather than false-pass) per the team's error-profile preference, but the headline number is well under the 80% target.


<!-- Template for future entries:

## vN → vN+1
**Date:**
**Prompt file:** (sha, git commit)
**Model:** · **Split:**
**What changed:** (ONE change)
**Agreement:** · **TPR:** · **TNR:** · **PPV:** · **NPV:**
**Confusion:** TP · FN · FP · TN
**Decision:** KEEP / REVERT
**Notes:**

-->

---

# LIVE REOPENING (2026-08-11) — new live split, old dev as regression guard

Live split: `labels/live_ids.csv` + `labels/consensus_quality_conversational_flow_live.csv`
(15 round-3 production calls, Maya's blind labels: 13 pass / 2 fail; full
transcripts, not excerpts; consensus CSV local-only/gitignored). Spent test
split untouched. See findings "Live-call reopening" for clusters L1/L2.

## v5_hero — LIVE BASELINE
**Date:** 2026-08-11
**Prompt file:** quality_conversational_flow_v5_hero.yaml (unchanged champion)
**Model:** claude-sonnet-4-6 · **Split:** live (15)
**Expected from round-3 scoring:** ~7/15 (47%), 7 FP-side (judge fail/human pass), 1 FN-side
**Agreement:** 60.0% (9/15) · **TPR:** 0.62 · **TNR:** 0.50 · **PPV:** 0.89 · **NPV:** 0.17
**Confusion:** TP 8 · FN 5 · FP 1 · TN 1
**Notes:** FPs = 019fb5c2, 019fc523, 019fc98e, 019fcdb3, 019fce25 (all cluster L1);
FN = 019fb56f (cluster L2). 019fb437 + 019fb47b, false-fails in the round-3
production scoring, passed this run — the count threshold is unstable on
borderline calls, run-to-run. Judge-correct fail: 019faf19 (ends mid-turn).

## v5_hero → v7 (v6 was reverted; v7 builds on v5)
**Date:** 2026-08-11
**Prompt file:** quality_conversational_flow_v7.yaml
**What changed (ONE concept):** Fail line for cut-ins moved from incident count
("2+ separate exchanges = fail even if nothing is lost") to recovery +
pervasiveness: recovered chop (thought lands once, session progresses) passes
even when repeated on a full call; fail = UNRECOVERED (thought never completes /
call ends mid-turn / answer left unaddressed) or PERVASIVE (dominant texture of
the exchanges, judged relative to transcript length). Also names user/channel-
caused interruptions (keypad, talk-over, connection checks) as not-coach-faults
when handled gracefully. Targets cluster L1 (7 live FPs). Collateral watch:
old-dev fail rows 71/166/410 must stay caught via "pervasive"; live FN 019fb56f
(L2 loop) intentionally NOT addressed this iteration.
**Decision:** (run pending)

## v7 result → REVERT
**Date:** 2026-08-11
**Split live:** 80.0% (12/15) · TPR 0.92 · TNR 0.00 — all 5 L1 FPs fixed, but BOTH human fails now pass (019faf19 "ends mid-turn" read as recovered; 019fb56f loop read as "reminder firing twice... recovered").
**Split dev:** 73.9% (17/23) · TPR 0.89 · TNR 0.20 — headline ties v5 but error profile inverted: fail rows 71/166/410/596 all pass via "coach recovers each time / session progresses"; 609 & 743 regressed to false-fail on guardrail counting.
**Decision:** REVERT. "Recovered" as a blanket allowance is an escape hatch that
overrides every hard fail signal — false-passes (worst error type) exploded on
both splits. Learned: recovery language must be scoped to WHICH incidents count,
not offered as a global pass rationale; v5's fail machinery must stay intact.

## v5 → v8 (v8 builds on v5; v6, v7 reverted)
**Date:** 2026-08-11
**Prompt file:** quality_conversational_flow_v8.yaml
**What changed (ONE concept):** COUNTING RULE for the 2+ cut-in threshold — an
incident counts only when the coach's evaluative reaction interrupts the USER's
in-progress answer. Excluded from the count (named as noise on the pass side
too): user/channel-triggered incidents (keypad entries, talk-over, connection
checks, silence re-prompts) handled gracefully, and the coach's own
chopped/restarted delivery when the thought lands once. Row-71 rationale kept
verbatim: genuine coach-on-user cut-ins count even when recovered. Tie-break
scoped to turns that open over the user's in-progress answer. All other v5 fail
machinery (loops, stacked turns, guardrail misfire, single-recovered-hiccup
allowance) verbatim.
**Prediction:** live L1 FPs (self-restart/user-caused: 019fb5c2, 019fc523,
019fc98e, 019fcdb3, 019fce25) pass; 019faf19 stays fail (v5 failed it on
coach-on-user cut-ins, which still count); 019fb56f stays a known FN (L2, next
iteration). Dev 71/166/410 stay fail (coach-driven), 609/743 stay pass.
**Decision:** (run pending)

## v8 result → KEEP
**Date:** 2026-08-11
**Split live:** 86.7% (13/15) · TPR 0.92 · TNR 0.50 · PPV 0.92 · NPV 0.50 — all 5 L1 FPs fixed AND 019faf19 fails again (predicted: coach-on-user cut-ins still count). FN 019fb56f (L2, deferred by design); FP 019fce25 (judge counts 2 coach-on-user cut-ins; the evidence reads as user interjections chopping the coach — borderline).
**Split dev:** 78.3% (18/23) · TPR 0.83 · TNR 0.60 · PPV 0.88 · NPV 0.50 — best dev yet (v5 was 73.9%). Fixed v5-era FNs 522, 594. Cost: 410 regressed to false-pass (judge now counts only 1 cut-in). Remaining: 377/609/749 (v5-era strict-judge FNs, already on the suspected-human-miss list), 596 (longstanding), 410.
**Decision:** KEEP. Live +26.7 and dev +4.4 over champion; the one new false-pass (410) is offset by two false-fail fixes on dev and the live cleanup.

## v8 → v9
**Date:** 2026-08-11
**Prompt file:** quality_conversational_flow_v9.yaml
**What changed (ONE concept):** Loop rule sharpened (cluster L2): coach
re-delivering the same reminder/feedback from the top, verbatim, at MULTIPLE
SEPARATE points in the session = loop = fail, even when each delivery
completes. Contrast written in: a single chopped delivery that completes once
at one point is noise. Targets live FN 019fb56f (triple name-reminder).
Collateral watch: 019fc98e (keypad-chopped feedback restarting within ONE
exchange, completes, does not recur) must stay pass; dev rows unchanged.
**Decision:** (run pending)

## v9 result → KEEP (with honest attribution note)
**Date:** 2026-08-11
**Split live:** 86.7% (13/15) · TPR 0.92 · TNR 0.50 · PPV 0.92 — same headline as v8, but the FP swapped rows: 019fce25 fixed, 019fb47b regressed (that row has flipped on 3 of 4 runs — borderline count, run-to-run unstable). TARGET MISSED: 019fb56f still passes — its re-deliveries are lightly reworded ("Just a heads up" / "Just a quick reminder"), so the "verbatim" qualifier gave the judge an out; its reasoning never engaged the loop clause.
**Split dev:** 82.6% (19/23) · TPR 0.83 · TNR 0.80 · PPV 0.94 · NPV 0.57 — best dev yet. 410 and 377 fixed; 391 regressed to false-fail (cut-in counting, not the new loop language, per its reasoning). Remaining: 596 (FP, longstanding), 391/609/749 (FN).
**Decision:** KEEP — v9 dominates v8 (dev +4.3, fewer false-passes; live ties). But the gains did NOT come from the targeted loop clause; they came from counting-rule application shifting on borderline rows. Attribution is fuzzy — treat the loop clause as unproven.
**Learned:** "verbatim" is too narrow for re-delivery loops; and 4 of the remaining 6 disagreements across both splits are rows that flip run-to-run or were already on the suspected-mislabel list — this is the escalation point, not more prompt surgery.

## v9 → v10 (encodes ruling R1)
**Date:** 2026-08-11
**Prompt file:** quality_conversational_flow_v10.yaml
**What changed (ONE concept — ruling R1, Maya 2026-08-11):** "Re-treading is a
loop": (a) same reminder/warning/correction re-delivered at several separate
points (verbatim OR reworded, even when each completes, even when user
re-triggers it); (b) habitual restart-from-the-top after interruptions when the
pattern recurs across separate exchanges. Noise contrast kept: restarts within
one exchange cleanly completed (019fc98e), isolated restarts, single chopped
delivery. Replaces v9's too-narrow "verbatim ... from the top" clause.
**Prediction:** flips 019fb56f to fail. Collateral watch: L1 passes must hold
(019fc98e in particular), dev 391 (immediate-duplication artifact row) and the
borderline 019fb47b could move either way.
**Decision:** (run pending)

## v10 result → REVERT
**Date:** 2026-08-11
**Split live:** 86.7% — target 019fb56f STILL passes (reasoning never engages the
loop clause; re-litigates cut-in counts). FP churned back to 019fce25.
**Split dev:** 78.3% (down from v9's 82.6) · TPR 0.78 · TNR 0.80 — clause (b)
(restart-chop recurrence) drew the predicted collateral: 594, 743 regressed and
609's reasoning now cites "repeatedly restarted the same feedback turn".
**Decision:** REVERT. Also a process miss: v10 bundled sub-rules (a)+(b); the
collateral traces to (b), so (a) deserves its own clean attempt.
**Learned:** restart-from-the-top chop cannot be made a fail signal without
re-breaking the excerpt-based dev rows — Maya's chop component of ruling R1 is
not cleanly encodable alongside the v8 counting rule. Also: borderline rows
(019fce25/019fb47b, dev 594/743) flip run-to-run at temperature 0 on long
transcripts — single-run deltas of ±1-2 rows are partly noise.

## v9 → v11 (ruling R1, clause (a) only, structural prominence)
**Date:** 2026-08-11
**Prompt file:** quality_conversational_flow_v11.yaml
**What changed (ONE concept):** The reminder re-delivery rule promoted to its
own NAMED fail signal with an explicit pre-scoring check ("check this
explicitly: same reminder/warning/correction at THREE OR MORE separate
points?"), wording-varies + user-re-triggers + each-completes all named as
non-outs. Threshold 3+ distinct points (fb56f has 4; once-or-twice = pass).
No restart-chop clause (learned from v10). Hypothesis: prior failures were
attentional — the clause was an aside inside a list; prominence + a checklist
step should force engagement.
**Prediction:** fb56f fails. Collateral watch: any call with a legitimately
repeated consent/ID reminder; dev unchanged (no dev row has a 3+ reminder).
**Decision:** (run pending)

## v11 result → KEEP (new champion candidate)
**Date:** 2026-08-11
**Split live:** 93.3% (14/15) · TPR 1.00 · TNR 0.50 · PPV 0.93 · NPV 1.00 —
zero false-fails; sole miss is 019fb56f.
**Split dev:** 87.0% (20/23) · TPR 0.89 · TNR 0.80 · PPV 0.94 · NPV 0.67 —
best dev ever. Remaining: 377, 749 (both on the July suspected-human-miss
list), 596 (longstanding). (Some borderline churn in this run's favor — 391,
594, 743, 609 all landed right; ±1-2 row instability documented at v10.)
**Decision:** KEEP — dominates v9 on both splits.
**On 019fb56f — the checklist clause ENGAGED and revealed a miscount:** the
judge counted the reminder at TWO distinct points, not 3+ — and it's right:
the call has two reminder POINTS, each chopped-and-re-delivered (my "4
deliveries" counted the restart pairs). Encoding options are exhausted
honestly: threshold 2 would over-fire on legitimate re-reminding of a repeat
offender; the chop component broke dev in v10. RECORDED AS KNOWN MISS: ruled
FAIL by Maya (ruling R1), judge passes it, prompt-encoding attempts
v9/v10/v11 documented. Effective live agreement counting the ruled miss:
14/15 with the miss on the non-preferred side (false-pass) — flag for any
future compound-signal work.
