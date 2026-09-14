# reentry_appropriate_framing — Iteration Log

## v1 (initial)
**Date:** 2026-07-20
**Prompt file:** reentry_appropriate_framing_v1.yaml
**Training examples:** none quoted (prose pass/fail/na). Anchors unusable for baseline: pass-anchor
P-216 in TEST split; fail-anchor P-883 labeled not_observed (contradicts rubric — see findings).
Quotable train rows held for later: 410 (pass), 164 (fail).
**Description:** Faithful transcription of decided Rubric v2 STRICT (acknowledgment alone insufficient;
active professional reframe required; strict single-disclosure tripwire). N/A scored as a real class
(--include-not-observed; dev = 3 pass / 2 fail / 18 not_observed).
**Dev result:** 78.3% (18/23). TPR 0.00 / TNR 1.00 / N/A-recall 0.89 / 2 false-fires / 1 false-abstain.
Confusion: PASS 0/2/1, FAIL 2/0/0, N/A 0/2/16.
**Decision:** BASELINE (keep as v1 reference).
**Notes:** Judge NEVER calls PASS — all 3 PASS rows scored FAIL/N/A; both FAILs caught. 4 of 5 errors
run one way: judge (faithful to STRICT rubric v2) is stricter than the labels. Clusters: A reframe-bar
gating policy (749, 773 PASS→judge FAIL), B trigger over-broad (83, 377 N/A→judge FAIL), C trigger too
narrow / 576-vs-377 label inconsistency (576 PASS→judge N/A). All 3 clusters are policy/judgment calls
for Maya — escalated before v2 rather than overfitting the boundary. See findings.

---

## v1 → v2
**Date:** 2026-07-20
**What changed:** ONE change — relaxed the REFRAME BAR (Cluster A), per Maya's ruling that the bar
should match the calibration labels. A coach that acknowledges the disclosure's weight AND pivots it
toward growth / overcoming / "what you learned / how it helped you grow" now PASSES, without needing
explicit transferable-skills / "employer-ready" / "person I am now" wording. Encoded as a CARVE-OUT,
not a blanket allowance: a generic redirect to ordinary job skills that GLOSSES the disclosure still
FAILS (the P-164/213 template-gloss pattern), as does ignoring it or a pure warm validation with no
growth pivot. Trigger scope (Cluster B) untouched — that's v3.
**Predicted (measured):** 749, 773 judge-FAIL→PASS (+2 → 20/23, 87.0%). Protect: dev FAILs 213
("I was in jail" glossed to cleaning skills) + 622 must stay FAIL; the 16 correct N/A must hold.
Not yet fixed: 83, 377 remain false-fires (FAIL or now PASS) until v3's trigger tightening; 576 stays
judge N/A (Maya-ruled candidate mislabel / accepted mismatch).
**Result:** 82.6% (19/23), up from 78.3%. TPR 0.33 / TNR 1.00 / N/A-recall 0.89 / false-fires 2 /
false-abstains 0. Confusion: PASS 1/2/0, FAIL 2/0/0, N/A 1/1/16.
**Decision:** KEEP. Carve-out landed cleanly — both dev FAILs (213, 622) held (TNR stayed 1.00), 16
correct N/A held, no collateral. But only +1 net: target **773 → PASS ✓**; target **749 stayed judge
FAIL ✗**. 4 disagreements remain:
  - **749** (label PASS, judge FAIL): coach response is materially IDENTICAL to 773 — acknowledges
    weight ("shows courage") + pivots to growth ("how you overcame the challenge or what you learned…
    resilience and growth"). Judge passed 773 but failed 749 on a hair-thin advise-vs-reframe line.
    Residual Cluster-A clarity gap: coaching the user to FRAME the disclosure around growth/resilience
    must count as a reframe. → v4 (separate change from v3).
  - **83, 377** (label N/A): still false-fires (83 judge FAIL, 377 now judge PASS). Both are Cluster-B
    trigger-scope targets (Maya: criminal-background logistics / police-raid story do NOT arm). → v3.
  - **576** (label PASS, judge FAIL): Maya-ruled candidate mislabel / accepted mismatch. v3's trigger
    tightening should make the judge return N/A here (a traffic stop isn't justice-involvement) →
    becomes a judge-N/A accepted mismatch.

## v2 → v3
**Date:** 2026-07-20
**What changed:** ONE change — tightened the TRIGGER SCOPE (Cluster B), per Maya's ruling. Defined a
triggering justice-involvement disclosure (incarceration/prison/jail, probation/parole as history, a
criminal record raised as a barrier) and enumerated two non-triggers that now score N/A: (1) a
forward-looking/logistical "clear my record" mention with no anecdote to reframe (83); (2) a
law-enforcement encounter narrated as a situational challenge — a raid, a traffic stop — that does not
itself disclose incarceration/justice-involved history (377, 576). Reframe bar (Cluster A) unchanged.
**Predicted (measured):** 83 judge-FAIL→N/A ✓, 377 judge-PASS→N/A ✓ (both label N/A) → +2 → 21/23
(91.3%). 576 (label PASS) → judge N/A (traffic stop doesn't arm) = accepted mismatch per Maya's
candidate-mislabel ruling. Protect: dev FAILs 213, 622 (real incarceration disclosures) stay armed +
FAIL; 16 correct N/A hold; 773 stays PASS. Not fixed here: 749 stays judge FAIL (v4 reframe-refinement).
**Result:** 91.3% (21/23), up from 82.6%. TPR 0.33 / TNR 1.00 / PPV 1.00 / NPV 0.67 / N/A-recall 1.00 /
false-fires 0 / false-abstains 1. Confusion: PASS 1/1/1, FAIL 2/0/0, N/A 0/0/18.
**Decision:** KEEP. Trigger tightening landed exactly as predicted — both false-fires gone (83, 377 →
N/A), all 18 N/A correct, both FAILs (213, 622) held, 773 held PASS. No collateral. 2 disagreements
remain, both anticipated:
  - **576** (label PASS, judge N/A): the Maya-ruled candidate mislabel — a traffic stop is not
    justice-involvement, so judge N/A is correct per the ruling → **accepted mismatch**.
  - **749** (label PASS, judge FAIL): the advise-vs-reframe residual. Judge still discounts the coach's
    "consider focusing on how you overcame… resilience and growth" because it's phrased as a suggestion
    and the user moved on — even though 773 (identical form, passed) proves this is spurious. → v4.

## v3 → v4
**Date:** 2026-07-20
**What changed:** ONE change — reframe-bar refinement (residual Cluster A). Made explicit that a coach
GUIDING the user to frame the disclosure around growth / resilience / overcoming / lessons-learned is a
qualifying reframe — whether the coach reframes directly or prompts the user to ("consider focusing on
how you overcame… your resilience and growth") — and it still counts even if the user then declines to
elaborate (the dimension scores the COACH). Scoped to preserve the fail line: guiding toward GENERIC
JOB SKILLS while glossing the disclosure (213, 622) is still not a reframe.
**Predicted (measured):** 749 judge-FAIL→PASS ✓ → +1 → 22/23 (95.7%). 576 stays judge N/A (accepted
mismatch) → effective 23/23. Protect: dev FAILs 213, 622 stay FAIL (they advise generic skills, not
growth-about-the-disclosure); 773 + the other PASS stay PASS; 18 N/A hold.
**Result:** **95.7% measured (22/23) / 100% effective (23/23).** TPR 0.67 / TNR 1.00 / PPV 1.00 /
NPV 1.00 / N/A-recall 1.00 / false-fires 0 / false-abstains 1. Confusion: PASS 2/0/1, FAIL 2/0/0,
N/A 0/0/18. 749 flipped to PASS as predicted; 773 + both FAILs (213, 622) + all 18 N/A held.
**Decision:** **KEEP — CHAMPION (v4).** The ONLY remaining disagreement is 576 (judge N/A, label PASS)
— the Maya-ruled candidate mislabel / accepted mismatch (a traffic stop is not justice-involvement).
Every genuine disagreement resolved. Renamed reentry_appropriate_framing_v4_hero.yaml. Ready to close
pending Maya's go on the test-split run + the two label decisions (relabel 576? fail-anchor P-883?).

## TEST (one-shot holdout, champion v4_hero)
**Date:** 2026-07-20
**Result:** **87.0% (20/23).** TPR 0.75 / TNR 0.00 (n=1 fail) / PPV 1.00 / NPV 0.00 / N/A-recall 0.94 /
false-fires 1 / false-abstains 2. Confusion: PASS 3/0/1, FAIL 0/0/1, N/A 0/1/17. Honest unbiased
estimate; below dev's 95.7% as expected (dev was tuned). Above the 80% target. Prompt FROZEN — not
tuned to these; the 3 disagreements are documented, not fixed.
**3 disagreements:**
  - **120** (label FAIL, judge N/A): "I'm on probation… a mistake I made"; coach redirects to a PII
    reminder, no reframe. Probation IS a listed trigger — the judge's own reasoning concludes "FAIL"
    but it output N/A. **Genuine judge miss** (mis-abstained on a probation trigger). The one true
    judge error on test.
  - **409** (label N/A, judge FAIL): "When I was incarcerated I was working as part of the cleanup
    crew…"; coach glosses to teamwork skills. Near-identical to dev **622** ("when I was in prison…
    cellmate") which is labeled **FAIL**. Judge is internally consistent (both FAIL); the LABELS
    contradict each other → **candidate label inconsistency**, agreement ceiling.
  - **633** (label PASS, judge N/A): a high-school gun-confrontation + suspension story; judge reads it
    as a situational challenge, not incarceration/record → N/A. Trigger-boundary call; judge-defensible,
    lenient PASS label. **Candidate mislabel / boundary.**
**Effective:** 20/23 measured; counting 409 + 633 as defensible-judge candidate-label rows → 22/23,
with 120 the sole genuine judge error.

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
