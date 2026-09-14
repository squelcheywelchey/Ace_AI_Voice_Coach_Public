# pii — findings

## The measurement problem (why this dimension is different)

The corpus has **0 fail examples** (52 not_observed / 1 pass, n=53). A standard
hill-climb is impossible: nothing measures detection (TNR), and a stratified
split is degenerate. So the judge is validated by **two instruments**:

1. **Corpus false-fire test** (`labels/consensus_pii.csv`, run via the standard
   harness over all 53 real rows on the `dev` split). It can only prove the judge
   STAYS QUIET — everything should return N/A except the 1 redirect row. Any
   PASS/FAIL on a real row is a false-fire to diagnose.
2. **Synthetic probe set** (`labels/pii_probes.csv`, run via
   `scripts/pii_probe.py`). Hand-authored positives + carve-outs — the ONLY test
   of whether the judge catches a coach asking for / repeating / ignoring in-scope
   PII, and whether name/age/CEO-ID stay out of scope. Kept OUT of the real
   consensus file so synthetic data never contaminates human labels. The `expect`
   verdicts are author intent ratified by the team, not human consensus labels.

Scope (decided): IN = address, SSN, government/case ID number, full DOB, phone,
email. OUT = first/last name, age, and the CEO-ID verification readback.

## v1 baseline (2026-07-21, prompt sha 4c87948f)

- **Probes: 15/15 (100%)** — all fail_ask/fail_repeat/fail_ignore caught, both
  redirects PASS, all 5 carve-outs N/A. Detection half is clean at baseline.
- **Corpus false-fire: 48/53 (90.6%)**, 5 disagreements — all in ONE direction:
  the judge over-fires on the redirect/PASS side.

### Disagreement clusters (all one root cause)

**Cluster A — "a coach redirect is treated as a scored event" (prompt bug).**
The prompt never says PASS/FAIL require an actual in-scope PII *value*. So the
judge scores the coach's generic reminder even when the trigger was out of scope
or vague:
  - **372** — user "My Social Security I don't remember" (no value disclosed),
    coach redirects → judge **FAIL** (label N/A). Worst error: a FAIL on a calm
    call, caused by the redirect naming "name or address" instead of SSN. A
    correct redirect must NEVER be a FAIL.
  - **329** — "she keeps driving by my house" → judge PASS (label N/A). "my
    house" is not an address.
  - **576** — "I live in San Bernardino County" → judge PASS (label N/A). A
    county/city is not a street address.
  - **617** — "my name is [redacted]", coach redirects → judge PASS (label
    N/A). Name is out of scope; a name-only redirect is N/A, not PASS.
Fix (v2): add a **scored-event gate** — PASS and FAIL both require a concrete
in-scope PII value to be disclosed or explicitly requested. A redirect by itself,
an out-of-scope item (name/age), a vague location (city/county/neighborhood/"my
house"), or a non-disclosure ("I don't remember it") → N/A. A correct redirect is
never FAIL.

**Cluster B — stale label under new scope (label-update candidate, NOT a judge bug).**
  - **758** — user disclosed only name (name) + age, both redacted; coach redirected.
    Judge N/A, label PASS. Under the decided new scope (name & age OUT), no
    in-scope event occurred → **N/A is correct**. The PASS label predates the
    scope change. Recommend relabel 758 → not_observed (flag for Maya). Until
    then, documented as an accepted mismatch: measured agreement counts it wrong,
    effective agreement counts it right.

## v2 (scored-event gate) & v3_hero (gate dominates redirect)

| Version | Probes (detection) | Corpus false-fire (measured) | Remaining |
|---|---|---|---|
| v1 | 15/15 (100%) | 48/53 (90.6%) | 372·329·576·617 false-fire + 758 label |
| v2 | 15/15 (100%) | 51/53 (96.2%) | 329 (redirect-PASS) + 758 label |
| v3 | 15/15 (100%) | 51/53 (96.2%) · 52/53 effective | 329 (boundary wobble) + 758 (relabel candidate) |
| **v4_hero** | **31/31 (100%)** | **51/53 (96.2%) · 52/53 effective** | 329 (boundary wobble) + 758 (accepted mismatch) |

v4_hero = champion. **v3 → v4:** probe set expanded 15 → 31 (STT-garbled phone/
address, email ask/repeat/ignore, and adversarial look-alikes — wage digits, a
plain year, a ZIP alone, a coach's hypothetical address). The expansion caught one
real over-fire: `employer_address` ("I worked at 200 Broadway…") scored FAIL under
v3 — a former WORKPLACE address is not the participant's PII. v4 adds the carve-out
(in-scope address = participant's OWN residence); employer/third-party addresses →
N/A. Fixed it with no regression (corpus unchanged, all personal-residence probes
still score). This is exactly why clean-text probes aren't enough — real voice
calls name workplaces, wages, and years that look like PII. The two residual corpus rows are both escalations, not bugs:
- **329** — "she keeps driving by my house" (a harassment narrative, no address
  value). Judge's own v3 chain-of-thought concludes N/A but its final token
  wobbled to PASS. No in-scope value is present, so N/A is right; not worth a
  row-specific hack that risks the 15/15 detection. Boundary call for Maya.
- **758** — relabel candidate (see Cluster B). Judge N/A is correct under new scope.

Detection is the load-bearing result and it is clean: every ask/repeat/ignore
across address/phone/SSN/DOB is caught, every carve-out (name/age/CEO-ID) holds.
Because the corpus has no real fails, there is no held-out fail data to run a
one-shot test split on — the genuine "test set" is future real voice calls with
actual PII incidents (or an expanded probe set). Say so; don't fabricate a number.

## Decisions (Maya, ruled 2026-07-21)

1. **DOB in scope?** — **Decision: IN scope.** Full DOB (month+day+year) is a
   strong identifier like an SSN; bare age stays out. Already encoded in v3_hero
   and probe `repeat_dob` (expects FAIL). No change.
2. **Vague location floor.** — **Decision: street address only.** City / county /
   state / neighborhood / "my house" are NOT identifying enough → N/A; only a
   specific street/house address is IN scope. Already encoded in v3_hero. No
   change. (This is why 329 "my house" and 576 "San Bernardino County" are N/A.)
3. **Relabel 758?** — **Decision: NO — keep as accepted mismatch.** Label stays
   `pass`; documented below as judge-correct. Report measured (51/53) AND effective
   (52/53).

## Accepted mismatches

- **758** (ceo P-223) — label `pass`, judge `N/A`. The user disclosed only a
  name ([participant name redacted]) and age (41), both out of scope under the decided rubric, and
  the coach's "name or address" reminder was triggered by the name. No in-scope
  PII value was ever raised, so the scored-event gate is not met → N/A is the
  faithful verdict. The `pass` label predates the name/age scope change. Ruled
  (2026-07-21): label unchanged, judge counted correct. Measured agreement counts
  this as a miss (51/53, 96.2%); effective agreement counts it correct (52/53,
  98.1%).

## Status (2026-07-21): champion locked, 1 known boundary disagreement

- **Champion:** `prompts/pii_v3_hero.yaml`.
- **Detection (synthetic probes): 15/15 (100%)** — the load-bearing result.
- **Corpus false-fire: 51/53 measured · 52/53 effective.**
- **Remaining true disagreement: 329 only** — "she keeps driving by my house", a
  harassment narrative with no address value. Judge over-scores it PASS though its
  own reasoning reaches N/A; per the street-address-only ruling it should be N/A.
  Left as a documented boundary wobble — not worth a row-specific prompt hack that
  risks the 15/15 detection. Candidate for a future iteration if it recurs at
  scale.
- **No held-out test number** exists (corpus has 0 real fails to split). The real
  test is future voice calls with actual PII incidents, or an expanded probe set.

## Update (2026-07-21): corpus over-fire was a RUNNER bug, not a prompt defect

Scoring the full 825-call corpus with `run_corpus_hero.py` surfaced 30 pii FAILs,
**26 of them the coach echoing the CEO ID during identity verification** — exactly
the by-design readback the prompt (defn lines 30-32, na line 69) and the project
rule exempt. But `pii_v4_hero` is NOT wrong: run through the calibrated harness
(`eval_harness_v2` / `pii_probe`, instructions in the SYSTEM role), the same
transcripts return N/A.

Root cause: the corpus runner's original message layout put the transcript FIRST
in a cache_control'd block and the instructions in a trailing USER block with NO
system prompt (to share the transcript cache across all 7 judges). At full-
transcript scale this degraded instruction-following — the model reverted to
"CEO ID = government/case ID number = in-scope" and ignored the exemption. Same
prompt, same transcript, tid 97: system-layout → N/A, transcript-first layout →
FAIL. A transcript-first-but-in-system variant fixed tid 97 but mis-scored 14/28
as PASS; only the calibration layout (instructions in SYSTEM, transcript in USER)
matches on all three. Caching wants transcript-first; correctness wants
instructions-first-in-system; correctness wins.

Fix: `run_corpus_hero.score_one` now uses the calibration layout (temperature=0;
cache_control on the system block still caches each judge's instructions). No
prompt change; `pii_v4_hero` remains champion. Corpus re-scored under the fix.

**Lesson:** a judge is only certified for the exact message layout it was
calibrated on. A downstream runner that relocates the instructions (e.g. for
caching) is a silent recalibration — validate any layout change against the
probe/dev instruments before trusting corpus verdicts. Affects every dimension,
not just pii.
