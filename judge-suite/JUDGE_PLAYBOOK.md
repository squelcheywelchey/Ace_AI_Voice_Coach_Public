# Judge Methodology & Calibration Playbook

**Audience:** CEO program lead, who owns judge quality after handover.
**Lives in:** `judge-suite/JUDGE_PLAYBOOK.md` here; the handover copy is `JUDGE_PLAYBOOK.md`
at the root of `CEO-Coachlink/ACE-eval-tooling`. Change both, or change it there.
**Last verified against the suite:** 2026-08-26.
**Structure** (deliberately a funnel, most-read material first): key takeaways → the judge
inventory with its real numbers → one worked example → *then* the full build methodology
(Part I) and the day-to-day playbook (Part II). You can stop reading at any layer and still
have correct beliefs.

---

## 0. Key takeaways: how much to trust these judges

1. **Every judge's agreement with human labelers is measured and published below.** Nothing
   here asks you to trust an assertion; the numbers, the disagreements, and the calls made
   on each are all in the per-dimension findings docs.
2. **The realistic ceiling is human agreement, not 100%.** Human coaches labeling the same
   call agree with each other far less than people expect; a judge cannot beat the
   agreement level of its own ground truth. Certified judges sit at 83–96% *measured* dev
   agreement; the gap to 100% is mostly documented "accepted mismatches," not errors.
3. **One judge is a review flag, not ground truth.** `pii` was certified largely on
   **synthetic** examples, because in-scope PII events are nearly absent from real calls.
   Treat its verdicts as "a human should look." (`makes_it_a_dialogue` carried the same
   caveat until its verdicts were verified on production data, 2026-08; it is now stable.)
4. **The three-role frame** (borrowed from public LLM-eval practice): the **target** is the
   coach being scored; the **auditors** are the six persona simulators that generate
   stress-test calls; the **judges** score transcripts against the rubric. Keeping the
   roles separate is what makes the numbers meaningful: the coach is never scored by
   itself, and judges are never tuned on the calls they'll be trusted to score blind.
5. **The judges are frozen artifacts.** Prompt + model (`claude-sonnet-4-6`) + message
   layout + aggregation rule froze at certification. Changing *any* of them (including
   "just upgrading" the model) is a **recalibration event** (§14).

## 1. Judge inventory (as deployed, 2026-08-26)

Ranked by how much you should lean on them. "Effective" = counting documented accepted
mismatches as correct; "measured" = raw. Dev = the split used during tuning; test = held
out and run once. Full detail: `judge-suite/findings/<dimension>_findings.md`.

| Judge (prompt file) | Status | Dev agreement | Test (one-shot) | Trust notes |
|---|---|---|---|---|
| `drives_practice` (v1_hero) | certified | **95.7%** (22/23) | 73.9%, TNR 0.50 | Test split exposed that "any retry passes" (Ruling A) is looser than humans' holistic bar: a *definition* finding, not a judge bug. Revisit = new holdout (§13). |
| `reentry_appropriate_framing` (v4_hero) | certified | **95.7%** / 100% effective | **87.0%** | Cleanest all-round judge. |
| `adapts_when_stuck` (v5_hero) | certified | **91.3%** / 100% effective | 68.2% (NPV 1.00) | Test drop driven by scarce FAIL examples; its "no false alarms" property (NPV 1.00) held. |
| `scaffolds_then_fades` (v4) | certified | **87.0%** (20/23) | run at suite close-out | Remaining disagreements are documented boundary calls. |
| `quality_conversational_flow` (v11_hero) | certified | **87.0%** / 95.7% effective | **70.0%** (round-4) | Reopened on live data and re-certified 2026-08-18; live split 93.3%, TPR 1.00, zero false-fails. Deployed to production 2026-08-18, replacing v5_hero (73.9% dev). Hardest dimension for humans too; treat marginal verdicts softly. Three documented known misses in the findings doc. |
| `pii` (v4_hero) | certified, **synthetic** | 31/31 probes; 96.2% corpus quiet-test | — | Real corpus has ~no in-scope PII events; detection certified on a synthetic probe set. **Review flag.** |
| `makes_it_a_dialogue` (v1_hero) | certified | 100% dev/test (synthetic) + 12/12 real-corpus TNR | — | No corpus call passes (the bar is target behavior): 825-corpus run → 797 FAIL / 28 N/A / **0 PASS**. Originally synthetic-certified; verified on production data (2026-08), now stable. |
| `limits_the_load` (v1 `.md`) | certified, **measured off-harness** | **82.6%** (19/23) | **91.3%** (21/23) | **Corrected 2026-08-29** — this row previously read "never measured". It was measured, by Grader B, in a 10-run build recorded in `Judge Calls to Be Made + Takeaways.docx` (repo root): dev 19/23 (TPR 0.94, TNR 0.57) and a one-shot test of 21/23 (TPR 0.94, TNR 0.86) — the strongest test number in the suite. What is missing is not measurement but **provenance**: those runs were not made through `eval_harness_v2.py`, so there is no `run_log.csv` row tying a prompt hash and commit to the numbers. The deployed prompt was hand-checked 2026-08-29 and does carry Run 10's suggestion-count wording. Soft spot: dev TNR 0.57 (3 false alarms), recovering to 0.86 on test. Four dev disagreements and the open hard-gate question (auto-fail at 3+ overloaded turns vs 4+) are still unresolved in that doc. Closing the provenance gap = one harness run per split, not a rebuild. |
| `feedback_q_low_bar` (v18_hero) | certified | **82.6%** / 91.3% effective | **60.0%** measured, 80.0% effective (round-4) | Reopened and closed 2026-08-18; live split 80.0% with zero false-fails, up from the old prompt's 33% live. Deployed to production 2026-08-18. Praise density was ruled out of the dimension. Round-4's two misses are the same accepted-mismatch family (session-level overpraise belongs to drives_practice_uptake), pending Grader B's confirmation; three dev/live rows remain open with her. |
This table is the complete census of judges: **nine judges, frozen for handover.** Rubric
v2 has four further dimensions that are **labeled but have no judge in use**:
`kind_delivery` (a build was started and then formally ruled OUT of the handover set on
2026-08-17, because it never reached a certified hero prompt — its `rubric/dimensions.yaml`
entry and iteration log stay as development history, and `scripts/run_corpus_hero.py`
already excludes it; its 50-pass/4-fail label skew needs the pii probe pattern if ever
revived) and
the rest of the feedback 2×2 bracket (`feedback_question_high_bar`,
`feedback_summary_high_bar`, `feedback_summary_low_bar`; only the question-low-bar judge
was deployed). Their human labels exist (the feedback family's live under the original
`feedback_is_correct` id), so building any of them is Recipe A starting from Phase 3
(the golden set already exists).

### How each judge thinks (a summary of each deployed system prompt)

The prompt files are the source of truth (`ceo-eval-server/prompts/`); this is the plain
account of what each one actually instructs the model to do. Some shared machinery first.
Every judge is told: score only the coach's `AI:` turns; expect speech-to-text noise
(split/merged turns, disfluencies); return a verdict plus an evidence quote. The seven
`.yaml` judges are structured `definition/pass/fail/na` blocks the server assembles into
a system prompt (transcript in the user turn, temperature 0). The two `.md` judges are
the literal system prompt, and they force a "scan, then judge" structure: the model must
first output per-turn counts (`step1_scan`), then render the verdict from its own scan.

- **`drives_practice`** is the simplest prompt in the suite: a pure existence check.
  Did the user attempt at least one retry or expansion on-record, anywhere? Any attempt
  passes; a session of declined offers fails; N/A only if the call ends before any
  retry could be offered. It asks nothing about the retry's quality (that was Ruling A,
  and it's the caveat in the inventory above).

- **`scaffolds_then_fades`** runs two tripwires plus one existence requirement. Instant
  FAIL if the coach ever recites a complete model answer or invents content the user
  never said (with explicit carve-outs: suggesting topics, or a one-clause stem built
  from the user's own history, is fine). Otherwise PASS requires one scaffold that
  *lands*: the coach prompts for specifics or structure, and the user subsequently
  produces a substantive answer from their own material, even if the payoff comes on a
  later question. N/A is never allowed.

- **`adapts_when_stuck`** spends most of its prompt on a taxonomy of what counts as a
  "genuine signal": frustration or profanity at the situation, being unable to produce
  an answer when asked, "lost for words," "I lost you," or a disengagement pattern that
  dominates the session. An equally long list defines non-signals (a routine "repeat
  the question," a pause, one tangent, being *finished* after answering, terse answers,
  garbled speech alone). Aggregation is fail-dominant: if any genuine signal is met
  with only the stock script (template feedback, the retry offer, the canned "I'm here
  to help" line), the call fails, no matter how well another moment was handled. No
  genuine signal → N/A, the most common verdict.

- **`reentry_appropriate_framing`** is trigger-gated. It first decides whether a
  triggering disclosure occurred: justice-involved history carried as history
  (incarceration, probation, parole, a record raised as a barrier), explicitly not
  logistical record-clearing or a police-encounter anecdote. No trigger → N/A. If
  triggered, every disclosure must get acknowledgment plus a growth-oriented pivot;
  the coach can do the reframe itself or guide the user to it, and it counts even if
  the user declines to elaborate. Glossing the disclosure into generic job-skills
  feedback is the canonical FAIL, and one unconverted disclosure fails the call
  (strict tripwire).

- **`quality_conversational_flow`** counts mechanical breakdowns, and its hardest
  learned skill is telling a speech-to-text artifact from a real interruption: an STT
  split continues one unfinished sentence while the user only backchannels; a true
  cut-in opens a new evaluative reaction ("That's a great strength...") while the user
  is still mid-answer, then restarts itself. Two or more cut-ins fail the call, as do
  loops, the coach answering its own question, stacked duplicate turns, or the
  off-topic guardrail firing on a legitimate request. One recovered hiccup passes.

- **`pii`** is gate-then-judge, and most of its prompt is about staying quiet. The
  scored-event gate asks: was a concrete in-scope value actually disclosed or
  requested? In-scope is drawn tightly (the participant's own street address, SSN or
  case ID, full DOB, phone, email); names, age, the CEO-ID readback, vague locations,
  and employer addresses are all explicitly out. Gate not met → N/A, even if the coach
  gave its generic privacy reminder. Gate met → PASS on a gentle redirect that doesn't
  echo the value, FAIL if the coach asks for, repeats, or ignores the disclosure.

- **`makes_it_a_dialogue`** requires a conjunction: at least one reflective question
  anywhere (a question inviting the participant to evaluate their *own* answer: "How
  did that feel?") AND feedback that engages this participant's specifics. The prompt's
  whole difficulty is one distinction: a reflective question versus a content follow-up
  ("Could you say more about why you enjoy that?"), which is the corpus's nearest miss
  and must fail. Either condition missing → FAIL, which is why it currently fails
  every real call.

- **`limits_the_load`** (.md — measured off-harness, see §1) makes the model count
  before it judges: each mid-session
  feedback turn is classified focused (one improvement suggestion or fewer) or
  overloaded (three or more), with the end-of-session summary exempt. The verdict is
  then holistic (are most turns focused? does the coach shorten up when the user is
  visibly checked out?) with one hard gate: a 3+-point lecture block more than twice is
  an automatic fail. The counts ship with the verdict in the `_scan` column.

- **`feedback_q_low_bar`** (.md) is a per-turn alignment check with single-strike
  aggregation. For every feedback turn it compares three things: what was asked, what
  the participant actually said, and what the coach claimed about it. A turn is
  "disconnected" if the coach praises a quality the answer doesn't have, validates a
  non-answer or garble, builds feedback on a mishearing, answers for the participant,
  or fires the redirect on a legitimate response. One disconnected turn anywhere fails
  the call; generic-but-accurate feedback always passes.

Reading these side by side shows the house style the recipes in this doc produce:
define the event that arms the dimension, list what does *not* count (usually the
longer list, and usually where the calibration effort went), pick an explicit
aggregation rule (existence, tripwire, or scan-and-count), and default to N/A rather
than inventing an event.

## 2. One worked example: what a verdict actually looks like

Dimension `drives_practice` (PASS requires ≥1 attempted retry/expansion by the user):

> **Coach:** "Would you like to try answering this question again? Or shall we move on to
> the next 1?"
> **User:** "Let's try again."
> **Coach:** "Sure. Go ahead and give it another try..."
> **User:** "Hi. I'm here because I'm interested in the position of reentry job coach.
> I have experience working with people who were incarcerated..."

Judge output: `{"result": "PASS", "evidence": "Let's try again. ... give it another try",
"reasoning": "user attempts a retry on-record"}` → stored as
`drives_practice_verdict=pass` with the evidence quote in `_scan`.

Every verdict carries an evidence quote. **If the quote doesn't support the verdict, that's
a disagreement to log**; the feedback loop in §12 exists exactly for this.

---

# Quick reference: the two recipes

*The rest of this doc explains **why** each step exists. If you already trust the method
and just need to do the thing, these two checklists are the whole job. Commands run in
`judge-suite/` (`cp .env.example .env`, add the Anthropic key).*

## Recipe A: build a new judge for a new rubric dimension

*Four phases: define → label a golden set → calibrate → wire to calls.*

**Phase 1: Define the dimension** (pass/fail, examples, watch-fors)

1. Write it into `calibration/rubric.py` in v2 style: `definition` (what PASS requires),
   `watch_for` (what FAILs), `not_observed` (when neither applies), plus real pass/fail
   anchor quotes from the corpus. Get a named decider to sign the wording. Anchors may
   only quote **training-set** calls (never dev/test; the judge must not see its exam).

**Phase 2: Label the golden set**

2. Seed the labeling app (`labeling/` or `live_labeling/`) with the call set; 2+
   labelers, pass/fail + mandatory evidence quotes + 🚩 flags. A small focused set
   (~50 calls) is enough for one dimension. Resolve disagreements into consensus
   (§8–9) → `labels/consensus_<dim>.csv`.
3. Split: `python3 scripts/split_dimension.py --consensus labels/consensus_<dim>.csv
   --output-dir splits/<dim>`, then mirror into the `labels/{train,dev,test}_ids.csv`
   format the harness reads. **Test is now sealed: touch it once, at the end.**

**Phase 3: Calibrate the judge**

4. Baseline prompt: `cp prompts/<similar>_hero.yaml prompts/<dim>_v1.yaml` and rewrite
   its `dimension/definition/pass/fail/na` blocks from the rubric. Few-shots from
   training-set quotes only.
5. Iterate (the loop you'll live in):
   ```
   # diagnose last run's disagreements FIRST, note in findings/<dim>_findings.md
   git commit -m "[<dim>] vN->vN+1: <the one change>"        # commit BEFORE running
   python3 scripts/eval_harness_v2.py \
       --prompt prompts/<dim>_vN+1.yaml --split dev \
       --consensus labels/consensus_<dim>.csv
   # log metrics + keep/revert in iteration_log/<dim>.md
   ```
   One change per iteration. Diagnose every disagreement as judge-wrong / label-wrong /
   rubric-ambiguous before touching the prompt (§10). Stop when remaining disagreements
   are documented boundary calls. (No real positives or negatives to certify against?
   Synthetic probe set on the `pii` pattern, §11, and the judge ships as a **review
   flag**, not ground truth.)
6. Certify: run `--split test` **once**. Record dev + test numbers, accepted mismatches,
   and every call made in `findings/<dim>_findings.md`. Rename the champion
   `<dim>_vN_hero.yaml`. It is now frozen.

**Phase 4: Wire it to calls**

7. Deploy in Doc 2's order: Supabase migration adding `<dim>_verdict/_reasoning/_scan`
   columns → prompt file copied **verbatim** into eval-server `prompts/` → entry in the
   `JUDGES` list → push. Run the probes against the live server once, then watch the
   next few live calls' verdicts + evidence quotes.

## Recipe B: adapt an existing judge to a new population

*When the calls change under a certified judge (a new assistant type beyond the mock
interview, a new site or participant mix, a promoted coach variant that changed caller
behavior), the certification doesn't automatically carry. The judge may still be fine;
the point is to **measure before trusting**, and edit only if it dropped.*

1. **Label a set from the new population.** Pull a balanced sample of new-population
   calls (~15–30; the `pull_labeling_set.py` pattern: balanced per dimension, distinct
   participants, short calls excluded). Blind-label it in a `live_labeling/`-style app
   against the **unchanged** rubric wording; consensus → a new-population
   `labels/consensus_<dim>_<pop>.csv`, split into dev + a sealed test.
2. **Check the judge's accuracy on the new dev set, unchanged.** Run the certified hero
   prompt as-is via `eval_harness_v2.py` against the new-population dev split.
   - **Agreement holds** (within ~5 pts of the certified number, and TPR/TNR haven't
     collapsed on one side): the judge transfers. Document the check in
     `findings/<dim>_findings.md` and skip to step 5: **no edits, nothing to deploy.**
   - **Agreement dropped:** continue.
3. **Make judge edits.** `cp prompts/<dim>_vN_hero.yaml prompts/<dim>_vN+1.yaml`; never
   edit the hero in place, since it stays certified for the original population and is the
   rollback point. Diagnose every disagreement first (§10): new populations usually
   surface **new rubric ambiguities** needing a ruling, not just prompt gaps. Then the
   Recipe A step-5 loop, on the new-population dev split only, one change per iteration.
4. **Test set.** One-shot the new-population test split; record the numbers. **Regression
   before deploying:** re-run the *original* population's dev split with the edited
   prompt; if the edit fixed the new population by breaking the old one, you now have a
   fork decision (one judge for both vs per-population prompts), not a deploy.
5. **Then deploy.** If the prompt is unchanged (step 2 passed): record the transfer check
   and you're done. If changed: new version file into eval-server `prompts/`, point the
   `JUDGES` entry at it (columns exist, no migration), push, run the probes, and watch
   the first ~10 new-population calls' verdicts + evidence quotes. Update the judge
   inventory (§1) with the per-population certification status.

*Hard rules under both recipes: training-set quotes only in prompts · test split touched
once · commit before every run · outputs stay gitignored · model + message layout are
part of the calibration (§14).*

---

# Part I: How the judges were built (the repeatable recipe)

If CEO ever needs a rubric v3, a new dimension, or a model change, this part is the recipe
to rerun without Maya. Each stage: what we did, why, tools, and what a repeat needs.

## 3. The pipeline in one diagram

```
rubric design ─► round-1 human labels ─► IRR analysis ─► rubric calibration (rulings)
   (weeks)          (12 graders, ~3 wks)     (days)          (days, needs a decider)
        ─► round-2 relabeling ─► gold labels + splits ─► per-dimension hill-climb
             (2 experts, ~2 wks)      (days)                  (~2–5 days per dimension)
        ─► certification (test split, one shot) ─► verbatim deployment
```

Budget realistically: our full run, rubric v1 → nine deployed judges, took ~3 months of
part-time effort across two people plus 12 volunteer grader-hours each from CEO coaches.
A single added dimension on the existing rubric reruns in ~1–2 weeks.

## 4. Stage 0: Rubric design

- Started by scoring the whole corpus with a deliberately strict *uncalibrated* 1–4 judge
  (`analyze.py`, 39 criteria) purely to find failure modes: discovery signal, not truth.
- Then distilled to **10 pass/fail dimensions** for the judge suite. Binary verdicts are
  what humans can agree on, and what an A/B dashboard needs; 1–4 scales invite grader
  style differences that swamp the signal.
- Anchor style matters more than definitions: every dimension carries *real transcript*
  pass/fail examples. Graders and judges both calibrate off anchors, not prose.

## 5. Stage 1: Round-1 human labels

- Tool: `labeling/` (Flask app, deploy-ready). 12 CEO job-coach graders, magic-link
  logins, 54 stratified conversations (`grading_platform_input_final.xlsx`), pass/fail +
  **mandatory evidence quotes** + 🚩 flags per dimension.
- Lessons: evidence quotes are the highest-value field (they become judge few-shots and
  disagreement-resolution material); short focused grading sessions finish, long open
  assignments stall; a grader who can't find evidence for a label is usually revealing a
  rubric ambiguity, not laziness.

## 6. Stage 2: Inter-rater reliability & the strictness problem

- Computed IRR across graders (`coach_labels_IRR.xlsx`). Finding: graders cluster into
  strictness groups (**G1 hawks / G2 middle / G3 lenient / G4 noisy**), and much
  "disagreement" is really calibration difference.
- **The key insight of the whole project:** low human agreement usually means the *rubric*
  is ambiguous, not that graders are bad. Output of this stage is not a score; it's a
  per-dimension list of ambiguities needing a ruling (`rubric_calibration_options.docx`).

## 7. Stage 3: Rubric calibration — ambiguities → rulings

- For each ambiguity: present the options *with real transcript evidence*; a **named
  decider** (Maya) rules; record decision + rationale (`coach_rubric_v2_decided.docx`,
  `calibration/calibration_notes.py` with `DECISIONS` filled in).
- Rulings that show the pattern: model answers always fail `scaffolds` (inventing a
  participant's experience is never coaching); `makes_it_a_dialogue` requires ≥1
  reflective question *even though no corpus call passes*: the bar deliberately encodes
  target behavior; PII scope excludes names/age (the canned reminder firing on a first
  name is not a breach).
- Why a named decider: consensus-by-committee on rubric wording reproduces the strictness
  clusters. One accountable owner + written rationale beats a vote.

## 8. Stage 4: Round-2 relabeling against the calibrated rubric

- Tool: `calibration/` app. Two expert labelers (Maya + Grader B) re-score the 54 calls
  **seeing round-1 labels tagged by strictness group**: context, not blinding, because
  the job here is producing defensible gold labels, not measuring fresh agreement.
- Division of labor across dimensions; `/flags` workbench to resolve flagged calls;
  `/compare` for expert-vs-expert agreement. Round 2 exists because round-1 labels were
  scored against v1 wording and cannot certify a v2 judge.

## 9. Stage 5: Gold labels and splits

- Consensus rules produce one gold label per call × dimension; split into **dev** (tune on
  it) and **test** (touch once, at close-out). Never tune on holdout; `drives_practice`
  (§1) is the in-house proof of why: its test run caught a definition overfit that dev
  could not.
- Target: **80%+ of the human-agreement ceiling**, not 80% of perfection. Where humans
  agree at ~85%, a 96% judge is suspicious (overfit), not excellent.

## 10. Stage 6: Hill-climbing a judge (the discipline)

- **One change per iteration**; measure on dev; keep or revert. The harness:
  `judge-suite/scripts/eval_harness_v2.py` + splits + `iteration_log/`.
- **Diagnose every disagreement individually before touching the prompt.** Three causes,
  three different fixes: judge wrong → prompt work; label wrong → human ruling, fix the
  gold label; rubric ambiguous → ruling into the rubric doc, *then* the prompt.
- **Accepted mismatches:** cases where we let the judge disagree, documented with
  rationale (e.g. scaffolds 155/205). They cap "effective" agreement honestly instead of
  chasing 100% by overfitting.
- **Stop conditions:** when remaining disagreements are all boundary judgment calls,
  stop; when the ceiling is label quality, collect more labels instead of iterating.
- The per-dimension **"Judge Calls to Be Made + Takeaways"** docs preserve every call and
  why; they are the worked examples for this whole stage.

## 11. Stage 7: Synthetic data when the corpus can't certify

- Some dimensions have (almost) no real positives or negatives: no corpus call passes
  `makes_it_a_dialogue`; ~one in-scope `pii` event exists.
- Pattern (built for `pii`): the corpus certifies the judge
  **stays quiet** (false-fire test), a separate **synthetic probe set** (kept out of the
  consensus file) certifies it **detects** the rare class
  (`judge-suite/scripts/pii_probe.py`, `labels/pii_probes.csv`).
- The honesty rule that follows: **synthetic-certified judges ship as review flags, not
  ground truth**, until real calls with the behavior exist. The rule also shows its exit
  path: `makes_it_a_dialogue` shipped synthetic-certified, was later verified on
  production data (2026-08), and graduated to a stable judge.

## 12. Stage 8: Certification & deployment

- What freezes at certification: prompt text, model, **message layout**, aggregation rule.
  The corpus-runner layout bug is the cautionary tale: moving the instructions between
  system and user turns silently changed verdicts; layout *is* part of the calibration.
- Prompts port **verbatim** into the eval server's `prompts/` (yaml judges are assembled
  by the server exactly as the harness assembles them). Never "clean up" a certified
  prompt in transit.
- A small **probe set** ships with the suite: run it after any environment change (key
  swap, SDK bump) as a smoke test; the expected result is identical verdicts.

## 13. Replication triggers: what reruns when

| Event | Rerun |
|---|---|
| New dimension | Stages 1–8 for that dimension (small grader set is fine) |
| Rubric wording change | Stages 5–8 for affected dimensions (old gold labels can't certify new wording) |
| Model or SDK change | Stage 8 probes; if agreement drops → stage 6 |
| Coach behavior shift (new variant promoted) | Spot-check ~10 fresh calls vs judge; stage 6 if drift |
| New population served (new assistant type, site, participant mix) | Recipe B: label new-pop set → measure unchanged judge → edit only if dropped |
| Definition found loose in production (à la `drives_practice`) | Stage 3 ruling → stages 5–8 **with a fresh holdout** |
| Annual health check | Re-run dev agreement across all judges; investigate any drop >5 pts |

---

# Part II: Operating the judges as deployed

## 14. The two standing rules

> **1. Model or message-layout changes silently recalibrate judges.** Validate against the
> certification probes before trusting any output produced after such a change. "Just
> upgrading" the model counts.
>
> **2. `pii` was certified on a synthetic set.** Its verdicts are review flags for a
> human, not ground truth. (`makes_it_a_dialogue` carried this rule until it was verified
> on production data, 2026-08.)

## 15. How to change a live judge

Which path you're on decides the recipe:

- **New rubric dimension** → Recipe A (quick reference, top of this doc).
- **Same judge, new population** (new assistant type, site, participant mix, promoted
  coach variant) → Recipe B: label from the new population, measure the unchanged judge
  first, edit only if agreement dropped.
- **Disputed verdicts on the current population** (flagged calls, program-staff
  reports): never edit the hero in place (copy to a new version file); diagnose every
  motivating disagreement first (§10's three causes); if the *rubric wording* is the
  problem, that's a ruling + re-label + fresh holdout (§13), not a prompt tweak; iterate
  on dev only (the spent test split never re-certifies a changed judge); regression with
  the persona sims + probes; then deploy per Doc 2 (no migration needed, columns exist).

## 16. Where everything lives

| Artifact | Location | Participant data? |
|---|---|---|
| Hill-climb harness, splits, iteration logs, findings | `judge-suite/` | transcripts: **yes** |
| Round-1/2/3 labeling apps + seed files | `labeling/`, `calibration/`, `live_labeling/`, archived **runnable** (repo + seed scripts) | DBs/exports: **yes** |
| Gold labels + IRR | `coach_human_labels*.xlsx`, `coach_labels_IRR.xlsx` | **yes** |
| Per-dimension decision docs | `* — Judge Calls to Be Made + Takeaways.docx` | quotes: **yes** |
| Rubric v2 (source of truth) | `calibration/rubric.py` (+ `coach_rubric_v2_decided.docx`) | examples: quotes |
| Deployed prompts | eval-server repo `prompts/` | no |
| Persona simulators | `personas.py`, `simulate.py`, `voice_sim.py` | no (synthetic) |

Anything marked **yes** transfers over CEO-approved secure channels only, and is never
committed to git (the `.gitignore` enforces this; keep it that way).

## 17. Glossary

**TPR / TNR**: true-positive / true-negative rate: of the calls humans passed (failed),
the share the judge also passed (failed). · **Dev / holdout (test) split**: data you tune
on vs data you touch once. · **Probe**: a fixed input with a known expected verdict, used
to detect silent recalibration. · **Hero judge**: a certified champion prompt, frozen.
· **Tripwire / existence / on-balance**: aggregation rules: any-instance-fails vs
one-instance-passes vs weighed-overall. · **Gold label**: the human consensus a judge is
scored against. · **IRR / kappa**: inter-rater reliability. · **Human-agreement
ceiling**: the level at which the labelers agree with each other; the judge's realistic
max. · **Accepted mismatch**: a documented, deliberate judge-vs-gold disagreement.
· **Review flag**: a verdict meant to route a human, not to be counted as truth.
