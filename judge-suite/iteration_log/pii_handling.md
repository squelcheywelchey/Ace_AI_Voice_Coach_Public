# pii — Iteration Log

Two instruments (corpus has 0 fails → standard hill-climb impossible):
- **Corpus false-fire test** — `eval_harness_v2.py --consensus labels/consensus_pii.csv --split dev` (all 53 real rows). Proves the judge stays quiet.
- **Synthetic probe set** — `scripts/pii_probe.py --prompt <p>` over `labels/pii_probes.csv` (15 hand-authored positives + carve-outs). Proves the judge catches violations and holds name/age/CEO-ID carve-outs. Synthetic data kept OUT of the real consensus file.

## v1 (baseline — faithful transcription)
- Probes 15/15 (100%). Corpus 48/53 (90.6%).
- 5 corpus disagreements, all one cluster: judge over-fires on the redirect/PASS side (scored a coach's generic reminder even with no in-scope value). See findings.
- **KEEP as baseline** (revealed the divergence).

## v1 → v2 (add scored-event gate)
- **What changed:** PASS/FAIL require a CONCRETE in-scope value disclosed/requested; redirect alone / out-of-scope (name,age) / vague location / non-disclosure → N/A; a correct redirect is never FAIL.
- Probes 15/15 (100%). Corpus 51/53 (96.2%).
- Fixed 372 (FAIL→N/A), 576, 617 (PASS→N/A). Left: 329 (still PASS off redirect clause), 758 (label).
- **KEEP.**

## v2 → v3 (gate dominates redirect clause)
- **What changed:** explicit that a redirect with NO concrete in-scope value is N/A, not PASS.
- Probes 15/15 (100%). Corpus 51/53 (96.2%) measured, 52/53 effective (758 = judge-correct accepted mismatch).
- 329 didn't flip — judge's own reasoning reaches N/A but the label token wobbles; a boundary call, not a wording bug. Stop grinding it (risks the detection score).
- **KEEP** (superseded by v4).

## v3 → v4_hero (participant's-own-residence carve-out) — CHAMPION
- **Probe set expanded 15 → 31** (STT-garbled phone/address, email ask/repeat/ignore, adversarial look-alikes: wage digits, plain year, ZIP-only, coach hypothetical address).
- Expansion surfaced one over-fire: `employer_address` FAIL under v3. **What changed:** in-scope address must be the participant's OWN residence; workplace/employer/third-party address → N/A.
- Probes **31/31 (100%)**. Corpus **51/53 (96.2%) measured, 52/53 effective** — no regression.
- **KEEP — champion.** Rulings recorded (findings): DOB in-scope, street-address-only floor, 758 accepted mismatch. Residual: 329 boundary wobble (documented).

## Open rulings → see findings/pii_findings.md "Decisions needed"
1. DOB in scope? (default: yes). 2. Vague-location floor (default: only specific street address is in-scope). 3. Relabel 758 → not_observed? (judge-correct under new scope).

## Post-champion (2026-07-21): corpus runner-layout finding (no prompt change)
- Full-corpus scoring showed 26/30 pii FAILs = CEO-ID verification readback. NOT a
  prompt bug: `pii_v4_hero` returns N/A on those transcripts under the calibrated
  harness (instructions in SYSTEM). The corpus runner had put instructions in a
  trailing USER block after a transcript-first cached block (no system prompt),
  which degraded adherence to the CEO-ID exemption.
- **Fix is in the runner** (`run_corpus_hero.score_one` → calibration layout,
  temperature=0), not the judge. Champion unchanged: `pii_v4_hero`.
