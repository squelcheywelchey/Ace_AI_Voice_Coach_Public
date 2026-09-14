# reentry_appropriate_framing — findings

Dimension: **B. Social-emotional awareness — "Reentry-appropriate framing."**
Rubric: decided Rubric v2 (STRICT), `calibration/rubric.py` id `reentry_appropriate_framing`
(2026-07-08 rework: acknowledgment alone is NOT enough — an active professional reframe is required).
Labels: `judge-suite/labels/master_labels.csv` on `main` (Grader B/Maya/Grader C calibration consensus) —
the authoritative source; `consensus_reentry_appropriate_framing.csv` is extracted from it (verified:
adapts_when_stuck consensus matches master 54/54, 0 mismatches).

## Setup notes (2026-07-20)

- **N/A-heavy dimension.** Of 54 calibration transcripts: **8 pass / 4 fail / 42 not_observed**
  (78% N/A) — even more N/A-dominant than adapts_when_stuck (70%). N/A is scored as a real third
  class; split with `--include-not-observed`; harness reports na_recall / false_fire / false_abstain
  + 3×3 confusion (same setup as adapts_when_stuck).
- **Trigger recognition is the design problem.** The behavior only exists when the user discloses
  justice involvement or comparable sensitive history. Most of the judge's job is deciding whether a
  disclosure even occurred (N/A vs not-N/A); the pass/fail question (was it reframed?) only arms once
  a disclosure is present. Define the trigger — "a justice-involvement or comparable sensitive
  disclosure" — as sharply as the pass bar. False-fire (scoring a call with no real disclosure) is
  the worst error.
- **Split (seed 42, 3-way stratified):** train 8 (1P/1F/6NA), dev 23 (3P/2F/18NA), test 23 (4P/1F/18NA).

## Anchor landing (only train-split transcripts are quotable)

The rubric lists TWO pass anchors and TWO fail anchors:

| anchor | ceo | source_row | consensus label | split | quotable? |
|---|---|---|---|---|---|
| pass #1 "probation / better version of myself" | P-216 | 122 | pass | **test** | ✗ (in test) |
| pass #2 "incarcerated / at-risk youth asset" | P-187 | — | — | not in 54-set | ✗ (unverifiable — not a calibration transcript) |
| fail #1 "5 years in prison, glossed over" | P-164 | 164 | fail | **train** | ✓ |
| fail #2 "parole / counselor overshare" | P-883 | 285 | **not_observed** | train | ✗ — see flag |

## Flags for team resolution (do NOT tune the judge to these)

1. **Fail-anchor #2 contradicts its own final label.** The rubric's second `fail_example` (ceo
   **P-883**, row 285 — the "I gotta go parole… go see my counselor…" oversharing example) is
   presented as a canonical FAIL (oversharing validated as-is). In the final calibration labels that
   transcript is **not_observed**, not fail. Likely reading: raters judged the parole/counselor talk
   as everyday-logistics oversharing, not a *justice-involvement disclosure* that arms the reframe
   tripwire — i.e. the trigger didn't fire for them. Either the anchor is a poor exemplar or the label
   is wrong — **team to decide.** v1 does not quote it.

## Quotable (train-split) transcripts, for later prompt iterations
- pass: row 410 (ceo P-589)
- fail: row 164 (ceo P-164) — matches rubric fail-anchor #1
- (pass-anchor P-216 is in the TEST split — never quote.)

## v1 baseline (2026-07-20, sonnet-4-6, dev n=23)

**78.3% agreement (18/23). TPR 0.00 · TNR 1.00 · N/A-recall 0.89 · 2 false-fires · 1 false-abstain.**
Confusion (rows=consensus): PASS 0/2/1 · FAIL 2/0/0 · N/A 0/2/16. The judge **never calls PASS** —
all 3 consensus-PASS rows are scored FAIL or N/A; both FAILs are caught.

**Dominant direction: the judge is STRICTER than the humans labeled (4 of 5 errors).** In every
human-PASS row the coach acknowledged the disclosure's personal weight and gestured at growth
("what you learned," "how it helped you grow"); the humans passed that, the judge (faithfully
applying Rubric v2 STRICT) demanded a fuller employer-ready reframe and called it generic template →
FAIL. This is the mirror image of adapts_when_stuck: there the labels were STRICTER than a lenient
rubric; here the labels are more LENIENT than the STRICT rubric text.

### Cluster A — reframe bar: judge stricter than the labels (PASS→FAIL): 749, 773 [GATING POLICY]
- **749** (label PASS): coach "Thank you for sharing such a personal experience… focus on how you
  overcame the challenge or **what you learned** from the experience." Judge FAIL ("generic template,
  no transferable-skills/'person I am now' reframe").
- **773** (label PASS): coach "That's a very real and challenging situation. It shows maturity…
  **focus on what you learned… how it has helped you grow**." Judge FAIL (same reasoning).
- The humans treat "acknowledge the weight + pivot to growth / overcoming / what-you-learned" as a
  sufficient reframe = PASS. The judge requires explicit employer-ready conversion. The decided
  rubric's **fail-anchor P-164** ("focus on the skills and strengths you've developed") sits right
  next to these PASS cases — the growth-narrative vs generic-skills-gloss line is exactly the strict
  rubric's fail boundary, and the humans drew it more leniently. **NOT prompt-fixable without a
  ruling — this changes what the STRICT bar means.** → gating question below.

### Cluster B — trigger over-broad (N/A→FAIL): 83, 377 [JUDGMENT CALL — trigger scope]
- **83** (label N/A): user "I'm trying to get things in my **criminal background** straightened out"
  — a forward-looking logistics mention in a trucking-career answer. Judge armed the reframe
  requirement and FAILed; humans saw no disclosure to reframe (N/A).
- **377** (label N/A): user "I got **raided by the police** while at my indoor grow" — told as a
  challenge-you-overcame story. Judge FAIL; humans N/A.
- Question: what counts as a justice-involvement disclosure that ARMS the dimension? If a passing
  criminal-background logistics mention and a police-raid anecdote do NOT arm it, both flip to N/A
  (correct). Boundary is Maya's to draw.

### Cluster C — trigger too narrow / candidate label inconsistency: 576 [JUDGMENT CALL — candidate mislabel]
- **576** (label PASS): user "getting **pulled over by law enforcement** is an extreme challenge."
  Judge N/A ("a traffic stop is not incarceration/justice-involvement"); humans PASS (counted it as a
  disclosure AND a good reframe). This makes 576 (PASS on a traffic stop) collide with 377 (N/A on a
  police raid) — a near-contradiction on whether a law-enforcement encounter is a triggering
  disclosure. Flag as candidate label inconsistency; agreement ceiling, not an edit site.

### The gating policy question (for Maya) — do NOT tune past this without a ruling
4 of 5 v1 errors run one way: the judge, faithfully applying the STRICT reframe bar Maya decided on
**2026-07-08**, is stricter than the calibration labels. Note the calibration re-scoring
(`calibration/rubric.py`, loaded **2026-07-07**) may **predate** the strict reentry rework by a day —
so the labels may have been set under a softer bar. Two readings:
  - **(A) Labels authoritative** — relax the reframe bar so that *acknowledge the disclosure's weight
    AND pivot to growth / overcoming / "what you learned"* PASSES, even without explicit
    transferable-skills / "person I am now" language. Flips 749, 773 → PASS. Matches how the humans
    labeled; slightly softens the strict fail line and sits in tension with fail-anchor P-164.
  - **(B) Strict rubric authoritative** — 749, 773 become accepted mismatches (judge correct, labels
    more lenient than the decided rubric); measured agreement stays capped; escalate the labels.
Recommendation: lean **(A)** for the reframe bar IF the labels post-date the strict rework — but this
is Maya's call because she authored the strict rework. Separately she owns the Cluster-B trigger scope
(does criminal-background logistics / a police-raid story arm the dimension?) and the Cluster-C
576-vs-377 label inconsistency. **Escalated before v2.**

**RULINGS (Maya, 2026-07-20):**
- **Cluster A (reframe bar) → (A) relax to match labels.** Acknowledge the disclosure's weight AND
  pivot to growth / overcoming / "what you learned" PASSES, without explicit transferable-skills
  wording. (v2 + v4 encode this.)
- **Cluster B (trigger scope) → only a justice-involvement disclosure/anecdote arms it.** A
  forward-looking "clear my record" logistics mention (83) and a police-encounter-as-challenge story
  (377) do NOT arm → N/A. (v3 encodes this.)
- **Cluster C (576) → candidate mislabel / agreement ceiling.** A traffic stop is not
  justice-involvement; the judge's N/A is correct. Documented as an accepted mismatch, not tuned to.

## Iteration summary
| v | change | measured | key |
|---|---|---|---|
| v1 | faithful STRICT baseline | 78.3% | judge never PASSes; 4/5 errors = judge stricter than labels |
| v2 | relax reframe bar (Cluster A) | 82.6% | 773→PASS; 749 stubborn; FAILs held |
| v3 | tighten trigger scope (Cluster B) | 91.3% | 83, 377→N/A; false-fires 0 |
| v4 | reframe-bar refinement (coaching-to-reframe counts) | **95.7% / 100% eff.** | 749→PASS; sole residual 576 |

## Dimension closed (2026-07-20) — champion v4_hero
- **Final dev: 95.7% measured (22/23) / 100% effective (23/23).** TPR 0.67 · TNR 1.00 · PPV 1.00 ·
  NPV 1.00 · N/A-recall 1.00 · false-fires 0 · false-abstains 1.
- **Operative rule:** N/A unless the user discloses justice-involved history (incarceration/jail/
  prison, probation/parole, a record raised as a barrier); a law-enforcement encounter or logistical
  record mention does NOT arm it. Once armed, PASS iff the coach acknowledges the disclosure without
  judgment AND pivots it toward growth / overcoming / lessons-learned / resilience — directly or by
  guiding the user to (counts even if the user moves on). FAIL if the disclosure is glossed to generic
  job skills, ignored, or oversharing is left to stand. Single-disclosure strict tripwire.
- **Accepted mismatch (1):** row 576 (ceo P-101) — judge N/A, label PASS. A traffic stop is not a
  justice-involvement disclosure; judge correct per Maya's ruling. Label NOT edited (would need to sync
  master_labels.csv on main, split_reference, calibration DB). Candidate relabel flagged for the team.
- **Open label flag:** fail-anchor P-883 (row 285) still labeled not_observed while the rubric
  presents it as a canonical FAIL (see Flags above) — for team resolution; did not affect the champion.
- **TEST (one-shot, 2026-07-20): 87.0% (20/23)** — the final unbiased estimate (dev was 95.7%; drop is
  expected). Above the 80% target. Prompt frozen; the 3 disagreements are documented, not tuned to:
  - **120** (label FAIL, judge N/A) — the ONE genuine judge miss: probation ("a mistake I made") is a
    listed trigger, coach glossed it with a PII redirect; the judge's reasoning concluded FAIL but it
    output N/A (mis-abstention). A known judge-reliability gap on bare probation mentions.
  - **409** (label N/A, judge FAIL) vs dev **622** (label FAIL) — near-identical "incarcerated →
    generic teamwork skills gloss"; the two labels contradict each other. **Candidate label
    inconsistency** (arm-or-not on incarceration-as-work-backdrop) — for team resolution; judge is
    internally consistent.
  - **633** (label PASS, judge N/A) — a high-school gun-incident/suspension story; judge-defensible
    N/A (not incarceration/record). **Candidate mislabel / trigger boundary.**
  Effective (counting 409 + 633 as defensible-judge candidate-label rows): 22/23, leaving 120 as the
  sole genuine judge error.
- **Candidate label flags for the team** (do NOT edit without a ruling; would need to sync
  master_labels.csv on main + split_reference + calibration DB): 576 (PASS→N/A), 409-vs-622 (resolve
  the incarceration-backdrop arm/no-arm rule), 633 (PASS→N/A?), and the standing fail-anchor P-883
  (not_observed vs FAIL).
