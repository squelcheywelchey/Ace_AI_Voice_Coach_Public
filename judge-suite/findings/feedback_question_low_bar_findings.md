# feedback_question_low_bar — findings (live reopening 2026-08-12)

Baseline v6 (production .md, harness layout): dev 65.2% (15/23), live 33.3%
(5/15). All 18 disagreements across both splits fall into two clusters that
pull in opposite directions on different clauses.

## Cluster F1 — over-fires on warm handling of garbled/thin responses
Judge FAIL / humans PASS. Live: 019faf6c, 019fb437, 019fb47b, 019fb56f,
019fb918, 019fc98e. Dev: 120, 285, 440, 580, 619.
The "no real content" / "validates garbled as good" clauses fire whenever the
coach acknowledges a mangled or near-empty answer and moves on. RULING (Maya,
2026-08-12): STT errors must not be counted as participant bad responses —
garbled text is channel noise; warm acknowledgment + move-along passes.
Expected flips: the 11 rows above. Collateral watch: dev 122 (humans FAILED a
thin-answer call — check what distinguishes it before assuming; likely praise
intensity), and any true validates-nonsense-as-GOOD rows in train.

## Cluster F2 — misses unearned superlative praise
Judge PASS / humans FAIL. Live: 019faf19, 019fb5c2, 019fc523, 019fc89e (+
019fbae9, judge-correct this run but same pattern). Dev: 122, 179, 609.
Grader B's round-3 notes name the principle: "great and creative answer" to a
non-answer, "really strong answer" to a weak one, "genuine passion" not in
evidence, "way too high praise throughout... dangerous validation".
The judge's alignment-only lens reads superlatives as ordinary encouragement.
The humans' line, visible IN the live labels: mild process encouragement
("Nice work on that wrap", "That's a cleaner answer", "Thanks for that")
passes even on garbled answers; SUPERLATIVE or content-specific quality
attribution the answer doesn't demonstrate fails. Encode at the existing
quality-claim criterion, not as a new bar.
Expected flips: the 7 rows above. Collateral watch: praise-tier boundary is
fuzzy — mid-tier praise ("that was solid") may churn; F1 rows must not
re-fail (opposite direction ⇒ F1 and F2 are separate iterations by rule).

## Order
v7 = F1 carve-out (Maya's ruling). v8 = F2 superlative criterion sharpening.

## Rulings (Grader B, 2026-08-18 — decision doc returned)
1. **Praise density is NOT this dimension.** Session-level overpraise on real
   but mediocre answers belongs to drives_practice_uptake / kind_delivery
   (Grader B's own round-3 flags on b5c2 and c523 are the precedent). Dev 122,
   179 and live b5c2, c523, c89e become **accepted mismatches** — labels
   unchanged, judge PASS accepted. Effective agreement counts them correct.
2. **bae9: label stands, the judge must catch it.** "That is a great and
   creative answer" on a self-referential non-answer (the participant used the
   session itself as their received-feedback example) is validating an answer
   that would not be accepted in an interview.
3. **Dev 580: RELABEL pass → fail.** The judge is correct that coaching built
   on "Yes. There were challenges." certifies a non-answer. Applied to
   labels/consensus_feedback_question_low_bar.csv and
   splits/feedback_q_low_bar/split_reference.csv. NOT synced: master_labels.csv
   (raw round-1/2 record on main) and the calibration app DB.
4. **Dev 619: judge correct, topic-mismatch tripwire stands.** Accepted
   mismatch (label unchanged); the coach should have told the participant they
   answered a different question.
5. **Dev 576: fail rationale supplied** — the coach repeatedly validates
   non-answers, converting contentless replies into traits and assets.

## Cluster F3 — certification of intelligible non-answers
Judge PASS / humans FAIL: dev 576, live bae9 (and dev 580 post-relabel, already
caught). Rulings 2/3/5 are one principle: when a response is intelligible but
supplies none of what the question asked, any coach move that turns it into
something positive — a good/great/creative answer, or an extracted trait,
interest, or virtue — is a quality claim. This is the exact behavior v9's
directionality carve-out exempted as "topic-value statements" and "bridging
remarks", which is why 576 churned across four runs: the carve-out was written
to protect 580, and 580 is now a fail. Distinct from F1 (garbled = channel
noise, still exempt) and from ruling 1 (high praise on real answers = out of
scope). → v11. Train anchor 437 ("It don't matter. I like money" →
"It's great to be motivated by financial goals") is quotable.

## Iteration outcome (2026-08-18)
Six versions run against F3. Two shapes failed and one worked.

- **v11 / v12 — a general non-answer trigger does not survive contact with the
  labels.** Defining "non-answer" as a fail condition caught 576 and bae9 but
  false-failed four dev rows (285, 391, 440, 577) that each contain one
  manufactured positive inside an otherwise sound session. Scoping it to a
  session-dominant pattern (v12) did not restrain it: a fail condition stated
  as a definition overrides carve-outs written after it. 577 is the decisive
  row — same CEO id as 576 (P-101), same coach move ("that's a great
  example" on a generic reply), opposite label. That boundary is a label
  ceiling, not a wording problem.
- **v13 / v14 — encoding ruling 2 costs faf19 wherever it is placed.** Both a
  standalone bullet and an embedded sentence caught bae9 and lost faf19, which
  escaped through the STT allowance ("coaching through what appears to be a
  language barrier"). A v10 replay in the same session reproduced exactly, so
  the flip was the edit, not model drift.
- **v15 — bounding the STT allowance by "don't certify qualities" is too
  coarse.** It re-broke c98e (restating words the participant did say and
  calling it a positive attitude), the F1 population Maya's ruling protects.
- **v16 — the working bound is INNER STATE.** Passion, enthusiasm, conviction,
  confidence, energy: no transcript evidences these when the words show nothing
  of the kind, and bad audio does not excuse the claim. Restating caught words
  with a modest attribute stays aligned. This caught faf19 and bae9 together
  and left every F1 row passing.
- **v17 — re-asserting an existing criterion at verdict time buys nothing.**
  Identical dev rows, and c98e false-failed again.
- **v18 (champion) — narrowing the self-referential clause to the AI call
  itself** recaptured 735, whose participant cited feedback from a program
  staff member earlier that day.

## Dimension state (champion v18_hero)
| split | measured | effective | error profile |
|---|---|---|---|
| dev | 19/23 (82.6%) | 21/23 (91.3%) | 1 false-fail, ruled correct (619) |
| live | 12/15 (80.0%) | 15/15 (100%) | zero false-fails |
| round-4 (certification, never tuned on) | 6/10 (60.0%) | 8/10 (80.0%) | 2 false-fails |

### Accepted mismatches (labels unchanged, judge accepted)
- **dev 179, live b5c2, live c523, live c89e** — ruling 1: session-level
  overpraise on real but mediocre answers belongs to drives_practice_uptake /
  kind_delivery, not here.
- **dev 619** — ruling 4: judge correct, the coach should have told the
  participant they answered a different question.
- **round-4 dcc3, ed19** — same family as ruling 1 (her notes: "is overpraise
  (borderline, wouldn't mind a pass)" and "Lots of overpraise"). Listed as
  accepted under ruling 1 pending her confirmation on fresh data.

### Open (need Grader B)
1. **Dev 580 regressed to pass.** She relabeled it fail because v10's judge
   failed it; v18 passes it, so the relabel now sits against the champion.
   Either the judge needs a rule that catches coaching built on "Yes. There
   were challenges." — every attempt at one this session over-fired — or 580
   goes back to pass, or it stands as a documented miss.
2. **Dev 609.** Human fail, judge pass across v9-v18; the coach's praise
   ("good start", "solid response", "great example") is mild by the praise-tier
   rule. Probably a ruling-1 row; confirm.
3. **The Q7 topic-mismatch tripwire, on fresh data.** She ruled it should stand
   (dev 619) and it then false-failed round-4 cee4 and d534 — the participant
   answers the received-feedback question with a story about something else and
   the coach praises it before redirecting. Fresh labels call that pass. Either
   the tripwire fires only when the coach never redirects, or 619 was the
   exception and the tripwire should be dropped.
