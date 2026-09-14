# Scaffolds (builds from user's own material) — Findings

## Pre-v2 findings
**Date:** 2026-07-16
**Dev set run:** scaffolds_then_fades_v1 (69.6%, TPR 0.17, TNR 0.88 — 5 false-FAILs, 2 false-PASSes)

### Failure patterns observed

**Cluster 1 — judge requires a formal template (3 rows: 377, 735, 758, all consensus PASS).**
Judge reasoning on all three: "never provides structural scaffolding (templates,
fill-in-the-blank, frameworks)... only praises, critiques, and moves on." But the
humans pass these calls because the coach's *elicitation* works: the coach prompts
for specifics ("you might also mention specific challenges you faced as a team",
"consider sharing how you adjusted") and the user then produces a more detailed
answer from their own real experience (377: the spider-mites elaboration, the
step-by-step teaching adjustment; 758: the demolition-crew and
incomplete-instructions stories arrive after the coach's repeated
be-specific prompts). The humans treat a template as one *tool*, not the
definition — the definition is "coach draws details out of the user, then helps
structure them," and drawing-out alone, when it lands, counts.

**Cluster 2 — MODEL ANSWER / INVENTED tripwire misfires on suggestions that point
back at the user's own material (2 rows: 120, 376, both consensus PASS).**
Judge fired on "you could mention how working with FedEx helped you develop time
management" (120) and "you could mention your experience with inventory
management" (376). In both calls the user had ALREADY stated that material
(FedEx job, warehouse work) — the coach is pointing back at the user's own
history, which is exactly what scaffolding is. The tripwire should only fire when
the coach fabricates content with no basis in anything the user said, or
delivers a complete spoken-out answer to copy.

**False-PASSes confirm the "successful" requirement is real (155, 205, both
consensus FAIL).** In 205 the coach offers textbook templates on every question
but the user answers in 3 words and says "move on" every single time — no
improved answer is ever built, so the scaffold never lands. In 155 the session
derails and the one retry that happens is filled with the COACH's list
(task lists, prioritizing), not the user's own material. The judge credited the
offer; the humans require the outcome.

### Hypothesis for fix (v2, one conceptual change)
Scaffolding = successful elicitation, not template delivery:
- A scaffold counts when the coach prompts for the user's specifics (template OR
  plain drawing-out question) and the user subsequently produces a more
  detailed answer built from their own material.
- A coach suggestion that references material the user already stated is a
  scaffolding prompt, NOT a model answer / invention. Invention = content with
  no basis in anything the user said.
- Keep the outcome requirement explicit: offers that are always declined, or
  retries filled with the coach's suggested content, do not pass (protects
  155/205 → TNR).

---

## Open judge calls after v3 (82.6%, TPR 0.50, TNR 0.94) — need Maya's ruling
**Date:** 2026-07-16

The 4 remaining dev disagreements are boundary decisions, not prompt bugs.
One prompt-edit each; decide which (if any) to spend a v4 on.

**1. Model-answer stem vs. topic suggestion (row 120, consensus PASS, judge FAIL).**
Coach: "you might say something like, 'I have experience in customer service
where I developed strong communication skills'" — a one-clause recitable stem,
but anchored in work the user actually has. The rubric says model answers ALWAYS
fail; the humans passed this call. Where is the line — is a short stem built
from the user's real background a paraphrase (pass) or a model answer (fail)?
Judge currently fails it. Decision (Maya, 2026-07-16): ALLOW the stem — a short
recitable stem anchored in the user's real background is a paraphrase/topic
suggestion, not a model answer. Only a complete spoken-out answer fails. → v4

**2. How thin is too thin (row 205, consensus FAIL, judge PASS).**
After repeated prompting the user does add own material ("getting the order out
on time", "I can focus better... my own pace") — concrete but minimal. The judge
credits it; the humans didn't. Either raise the bar again (risk: 376/758 get
harder) or consider whether 205 is a stricter-than-definition label.
Decision (Maya, 2026-07-16): ALLOW the thin attempt — a genuine attempt built
from the user's own real material counts even when minimal. Echoes of the
coach's own suggested content still do NOT count. This sides with the judge on
205 (consensus label likely stricter than the definition — relabel candidate,
like Grader B's 619); row 213 may flip back to judge-PASS and become a second
accepted mismatch / relabel candidate. → v5

RESOLUTION (Maya, 2026-07-16, second ruling): explicit prompt language was
tried as v5 and REVERTED (it credited user forthcomingness without coach
uptake — 594, 329). Maya ruled that 155/205-style calls — coach gets real
examples from the user and the user puts them in their answer — SHOULD pass,
and that the v4 judge (which already passes them) is the version to keep.
Consensus labels are NOT changed (Maya's explicit call: no relabel). 155 and
205 therefore stand as documented accepted mismatches: measured dev agreement
for v4 stays 87.0% (20/23); under this ruling the judge is considered correct
on 22/23 (95.7%). Only open item remains judge call #3 (row 376).

**3. Stories elicited by a plain invitation (rows 376 & 758, consensus PASS, judge FAIL).**
In both calls the user delivers genuinely specific stories (758: demolition
crew, completing a task with incomplete instructions; 376: coordinating with
another team member) — but they arrive after a bare "Go ahead and share your
example" / a re-asked question, not after a be-specific coaching prompt. Humans
credit the coach with the scaffold; the judge doesn't see coach contribution.
Does a plain invitation + substantive user story = successful scaffold?
Decision (Maya, 2026-07-17): KEEP 376 AS A FAIL — a plain invitation is not a
scaffold; the judge's FAIL stands. No relabel (consistent with the standing
no-relabel policy): 376 becomes accepted mismatch #3. Note 758 is unaffected —
it already passes under v4 via the stem/coach-contribution reading.

---

## Dimension closed (2026-07-17)

v4 is the final judge for this dimension. All three dev disagreements are
ruled accepted mismatches (155, 205: judge-pass is right; 376: judge-fail is
right). Measured dev agreement 87.0% (20/23); judge considered correct on
23/23 under Maya's rulings. Labels unchanged throughout. Test split untouched
— run it once when the suite goes to final evaluation. Exported to the team
decision doc: "Scaffolds - Judge Calls to Be Made + Takeaways.docx".

---


---

## Test-set result (2026-07-17, final)

v4_hero on the held-out test split (n=23): **87.0% agreement** (TPR 0.83, TNR 0.88) — identical to dev. Disagreements:
- **Row 27** (consensus FAIL, judge PASS): coach's "give a specific example" prompt led the user to a concrete detail-orientation story from his own experience. Same shape as ruling #2's accepted mismatches — Maya to confirm whether this is an accepted mismatch.
- **Row 284** (consensus FAIL, judge PASS): coach's repeated example-prompts elicited a concrete HelloFresh warehouse story from the user's real history. Same shape as ruling #2 — Maya to confirm.
- **Row 522** (consensus PASS, judge FAIL): judge holds that retries never produced substantive content built from the user's own material.

Test split is spent; these are report-only, not tuning targets.
