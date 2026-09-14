"""Per-dimension calibration material from rubric_calibration_options.docx.

Basis: 121 completed labels from 12 labelers across 50 conversations. Each
dimension has definition OPTIONS (interpretations at least one round-1 labeler
actually applied) and FAIL-LINE options at the three bars, with anchors from
the labeled data. The /rubric page renders this; as Maya + Grader B decide, fill
in DECISIONS below and rework rubric.py accordingly (that's step 2).
"""

# The three implicit fail bars driving most round-1 disagreement.
BARS = [
    ("Bar 1 — Best practice",
     "FAIL = anything short of the best coaching behavior observed. Produces high "
     "fail rates and one-issue grading that spills across dimensions."),
    ("Bar 2 — Missed clear opportunity",
     "FAIL = the conversation presented a clear, specific opportunity for the "
     "behavior and the coach did not take it, in a way that plausibly hurt the "
     "participant. Middle ground — the doc's recommended global default."),
    ("Bar 3 — Egregious violation",
     "FAIL = actively harmful, wrong, or dismissive behavior only. Passes nearly "
     "anything that reads as polite, plausible coaching."),
]

# Two supporting global rules to settle alongside the bar.
GLOBAL_RULES = [
    {
        "id": "not_observed",
        "name": "not_observed rule",
        "text": (
            "Used 226/1,210 labels (19%), concentrated on trigger-dependent dimensions "
            "(reentry 68, pii 55, adapts_when_stuck 52). The problem is inconsistent "
            "application: in 115 conversation-dimension pairs one labeler chose "
            "not_observed while another scored pass or fail on the same conversation."
        ),
        "options": [
            ("A", "not_observed is REQUIRED when the dimension's trigger never occurs "
                  "(no disclosure, no PII, no stuck moment) — a pass must mean the trigger "
                  "occurred and was handled well. Recommended: makes pass rates interpretable."),
            ("B", "pass may also mean “no trigger, nothing went wrong” (how many labelers "
                  "used it)."),
        ],
    },
    {
        "id": "artifacts",
        "name": "Transcript artifacts",
        "text": (
            "Truncated or duplicated coach turns (“Thanks for sharing.”, “Coach: Would”) "
            "were graded as coach failures by Grader N across several dimensions."
        ),
        "options": [
            ("A", "Artifacts are excluded from grading (infra issue, flag separately). Recommended."),
            ("B", "They count against quality_conversational_flow only. Also acceptable."),
            ("C", "They count wherever they appear — conflates logging with coaching."),
        ],
    },
]

# dim_id -> calibration material. Keys follow rubric.py DIMENSIONS ids.
NOTES = {
    "scaffolds_then_fades": {
        "consensus": (
            "The coach provides structure (frameworks, fill-in-the-blank templates, "
            "targeted prompts) rather than content, then steps back so the participant "
            "produces the answer. Best pass evidence shows the participant's own improved retry."
        ),
        "options": [
            ("A", "Structure only", "Full model answers (“You might say something like, I'm most "
             "interested in...”) are the opposite of scaffolding — the coach is answering for the "
             "participant. Applied by Grader D, Grader A, and usually Grader C."),
            ("B", "Model answers count", "A worked example IS a scaffold, provided the coach invites "
             "the participant to try again in their own words. Applied by Maya Welch, Grader B, "
             "Grader E, and CEO program lead (10/10 pass, including full “you might say...” "
             "examples on P-828)."),
            ("C", "Fading required", "Whichever of A/B is chosen, the scaffold must also FADE: "
             "repeating an identical canned feedback block every turn (P-506: seven near-identical "
             "scripts) fails even if each block is individually fine."),
        ],
        "fail_lines": [
            ("Strict (Bar 1)", "The coach ever dictates a complete answer, or support does not "
             "visibly decrease across the session.",
             "P-240 — “You can start with something like I am a dedicated professional...” failed "
             "by Grader C, passed by Grader A and Grader B."),
            ("Middle (Bar 2)", "The coach repeatedly composes answers for the participant AND the "
             "participant never produces an improved attempt of their own.",
             "P-646 — coach supplies the full answer; participant just says “Respond with the "
             "extended answer.” Grader A: “Answers for them.”"),
            ("Lenient (Bar 3)", "The coach never offers any structure at all, or actively blocks "
             "the participant from answering.",
             "No conversation in the sample fails this bar cleanly — a sign it is too low."),
        ],
        "conflicts": "Identical excerpts labeled pass by one labeler and fail by another on "
                     "P-240, P-169, P-982, P-203.",
    },
    "adapts_when_stuck": {
        "consensus": (
            "When the participant shows frustration, confusion, or drift, the coach changes "
            "tack: slows down (“Take your time”), reframes the question, or redirects rants "
            "back to the interview."
        ),
        "options": [
            ("A", "Any responsive change", "Gracefully moving on (“No problem. Let's move on to the "
             "next question.”) counts as adapting. Applied by Grader C and Grader A on P-240."),
            ("B", "Must address the stuck-ness", "Moving on is giving up; the coach must engage with "
             "WHY the participant is stuck before pivoting. Applied by Grader B on the same "
             "P-240 exchange."),
            ("C", "Trigger required (not_observed)", "If no stuck/frustrated moment occurs, the "
             "dimension is not_observed rather than pass. 52 of 121 labels used not_observed here, "
             "but labelers disagree on when: 24 conversations have one labeler scoring not_observed "
             "while another scores pass/fail on the same session. Define the trigger."),
        ],
        "fail_lines": [
            ("Strict (Bar 1)", "Any distress or confusion signal goes unaddressed, including subtle "
             "ones (garbled requests, repeated “Next question”).",
             "P-133 — participant says “Next question” six consecutive times with no strategy "
             "change (Grader D, fail)."),
            ("Middle (Bar 2)", "The coach ignores an EXPLICIT distress signal and continues the "
             "template unchanged.",
             "P-801 — participant: “Fuck this. 25 years. I'm hardworking.” Coach: “That's great.” "
             "(Grader B, fail — clear anchor)."),
            ("Lenient (Bar 3)", "The coach responds to explicit distress with something actively "
             "harmful (mockery, blame, escalation).",
             "Not observed in sample."),
        ],
        "conflicts": "P-240: the exchange “But do it 1 more time. Just forget it.” / “No problem. "
                     "Let's move on.” is fail evidence for Grader B, pass evidence for Grader C and Grader A.",
    },
    "kind_delivery": {
        "consensus": (
            "Strengths-first, validating, patient tone; non-judgmental reframing of blunt "
            "answers; tactful correction of profanity or oversharing."
        ),
        "options": [
            ("A", "Per-utterance politeness", "Judge each coach turn in isolation; polite wording "
             "passes. Applied by most labelers (Grader O, Grader D, Grader E)."),
            ("B", "Cumulative effect", "Relentless “areas for improvement” after every single answer "
             "is unkind in aggregate even when each turn is polite. Applied by Grader M "
             "(P-365: “None of the answers were ‘good enough’... shows lack of empathy”)."),
            ("C", "Formulaic = unkind", "Templated numbered feedback itself reads cold regardless of "
             "content. Applied occasionally by Grader A (P-912). Note: Grader C also failed one "
             "session over the scripted QUESTION content — curriculum design, arguably out of scope "
             "for a delivery dimension."),
        ],
        "fail_lines": [
            ("Strict (Bar 1)", "Any turn reads cold, curt, or formulaic, or the aggregate is "
             "improvement-heavy.",
             "P-206 — the same “Strengths... Areas for improvement...” block is pass evidence for "
             "Rick and fail evidence for Grader M."),
            ("Middle (Bar 2)", "One or more turns are dismissive or belittling in context, or blunt "
             "personal disclosures are handled judgmentally.",
             "P-712 — Participant: “Yeah. Great person.” Coach: “It's a start. Thank you.” "
             "(Grader E: “read cold”)."),
            ("Lenient (Bar 3)", "Overtly rude, mocking, or shaming language.",
             "Not observed in sample — the coach is never overtly rude, so Bar 3 makes this "
             "dimension always-pass."),
        ],
        "conflicts": "P-397: same excerpt is Grader Q's fail evidence and Grader M's pass evidence "
                     "(“Call was very kind to participant”).",
    },
    "reentry_appropriate_framing": {
        "consensus": (
            "When the participant discloses justice involvement (arrest, prison, parole) or "
            "similar sensitive history, the coach acknowledges without judgment and either "
            "reframes it as growth/resilience or gently redirects to a work-appropriate example."
        ),
        "options": [
            ("A", "Non-judgment is enough", "Pass if the coach reacts warmly and neutrally to the "
             "disclosure. Applied by Grader P (P-216) and CEO program lead, who passes warm "
             "validation of prison stories with a growth nudge (P-589, P-828) and uses "
             "not_observed when no disclosure occurs (7 of 10)."),
            ("B", "Active reframing required", "The coach must also coach the participant to reframe "
             "the story for an employer; validating a prison anecdote as-is fails. Applied by Grader E "
             "Grader E and Grader A (P-486: coach praises a cellmate story — Grader A: “Epic "
             "fail... ‘Thank you for sharing that experience’? NO!”)."),
            ("C", "Scope question", "Does the dimension cover only justice content, or all sensitive "
             "history (addiction, long unemployment)? Several labelers scored it as general coaching "
             "quality on conversations with no disclosure at all — those should be not_observed."),
        ],
        "fail_lines": [
            ("Strict (Bar 1)", "Any disclosure that is not actively converted into an "
             "employer-ready reframe.",
             "P-336 — participant answers “By going to prison”; coach thanks them and praises "
             "honesty. Grader A PASSED this while failing near-identical behavior on P-486 — the "
             "strict bar is hard to apply consistently."),
            ("Middle (Bar 2)", "The coach glosses over a disclosure with generic template feedback, "
             "or validates prison-life detail without any nudge toward reframing.",
             "P-164 — participant: “I was arrested”; coach: “focus on specific roles or "
             "responsibilities” (robotic template)."),
            ("Lenient (Bar 3)", "The coach reacts with judgment, discomfort, or discouragement.",
             "Not observed in sample."),
        ],
        "conflicts": "P-216: pass from Grader E, Maya, Grader P vs fail from Grader Q on the same "
                     "conversation. P-169: the same tailoring move is Grader C's fail evidence and "
                     "Grader N's pass evidence.",
    },
    "limits_the_load": {
        "consensus": (
            "Feedback stays digestible: roughly one focused suggestion plus an offer to retry, "
            "rather than multi-point lectures."
        ),
        "options": [
            ("A", "One point per turn", "Any multi-part numbered feedback block (“1... 2... 3...”) "
             "is overload. Applied by Grader A (“Epic fail. Every response was complicated”)."),
            ("B", "Reasonable structure OK", "A short strengths + one-improvement + retry-offer "
             "structure passes; only long walls fail. Applied by Grader B, Grader C, and most mid-bar "
             "labelers."),
            ("C", "Summary exemption", "The structured end-of-session summary (Strengths / Areas / "
             "Next steps / Overall) is exempt from the per-turn limit. Grader N and CEO program lead pass it; "
             "Grader D, Grader E, and Grader A fail it. Decide explicitly — this single block drives many "
             "disagreements."),
        ],
        "fail_lines": [
            ("Strict (Bar 1)", "Any turn with 3+ discrete points, anywhere in the session.",
             "P-240 — the same structured 3-part feedback is pass evidence for Grader B and Grader C, "
             "fail evidence for Grader A (“Far too long”)."),
            ("Middle (Bar 2)", "Repeated multi-point blocks mid-session, or a feedback wall "
             "delivered after the participant has visibly checked out.",
             "P-486 — coach dumps the full summary after the participant says “No. No.” (Grader E, fail)."),
            ("Lenient (Bar 3)", "Only feedback so long the participant demonstrably disengages "
             "(stops responding, repeated “next question”).",
             "P-203 — eight straight “Next question” replies following long feedback blocks."),
        ],
        "conflicts": "P-397: the numbered block is BAD evidence for Grader E and Grader M, GOOD evidence "
                     "for Grader Q. P-169: fail (Grader C, Grader A) vs pass (Grader N) on the identical excerpt.",
    },
    "feedback_is_correct": {
        "consensus": (
            "The substance of the advice is accurate and interview-appropriate: add specific "
            "examples, structure answers, avoid informal language and personal info, tailor to "
            "the role."
        ),
        "options": [
            ("A", "Face validity of the advice", "Judge only whether the advice itself is sound; the "
             "quality of the participant's answer is out of scope. Applied by Grader D, Rick "
             "Stone, Grader M, Grader N."),
            ("B", "Calibration included", "Praise must be calibrated to the answer's actual quality; "
             "praising a weak or nonsense answer IS incorrect feedback. Applied consistently by "
             "Grader B and by Grader A on trolling answers (P-433)."),
            ("C", "Guard against personal doctrine", "Whichever is chosen, personal coaching "
             "philosophy should not count (Grader P failed P-744 because he coaches openers "
             "differently: “I could be wrong, but that's the way I coach it”)."),
        ],
        "fail_lines": [
            ("Strict (Bar 1)", "Any miscalibrated praise, including standard encouragement of a "
             "mediocre answer.",
             "P-133 — near-identical “excellent strengths... consider a brief example” turns: pass "
             "evidence for Grader D, fail evidence for Grader B."),
            ("Middle (Bar 2)", "The coach validates a clearly inappropriate, nonsense, or non-answer "
             "as if it were good (trolling accepted, wrong-context example praised).",
             "P-176 — 7th-grade science project validated for a dishwasher job; P-801 — mumbled "
             "fragment called “a great example of showing responsibility.”"),
            ("Lenient (Bar 3)", "The advice is factually wrong or would actively hurt the "
             "participant in a real interview.",
             "Rare in sample; most advice is generically sound."),
        ],
        "conflicts": "P-216: 2 pass (Grader E, Maya) vs 3 fail (Grader B, Grader C, Grader P); the same "
                     "excerpt is Grader B's BAD evidence and Grader C's GOOD evidence.",
    },
    "makes_it_a_dialogue": {
        "consensus": (
            "The coach engages in genuine two-way exchange — asking questions, inviting "
            "elaboration and retries, responding to what the participant actually said — rather "
            "than delivering one-way feedback monologues."
        ),
        "options": [
            ("A", "Any handback counts", "The boilerplate closer (“Would you like to try again or "
             "move to the next question?”) is a real invitation and passes. Applied by Grader B "
             "Grader B and Grader E."),
            ("B", "Responsive engagement required", "The boilerplate two-option closer is a fake "
             "choice at the end of a monologue; dialogue means engaging with the content of what "
             "the participant said. Applied by Grader D and Grader C (“Always giving "
             "next question option primes participant to choose next question”)."),
            ("C", "Reflective questions required", "The coach must ask reflective questions (“How "
             "did that feel?”, “How do you think it went?”). Applied by Grader A (8+ "
             "conversations) and CEO program lead, who failed ALL 10 of his conversations on this "
             "dimension — notable because CEO program lead is otherwise one of the most lenient labelers. Two "
             "independent adopters makes this a real candidate criterion: adopt or explicitly reject."),
        ],
        "fail_lines": [
            ("Strict (Bar 1)", "No reflective/open questions responsive to the participant's "
             "content anywhere in the session.",
             "P-433 — Grader B pass vs Grader A fail; P-883 — Rick pass vs Grader D and Grader A fail."),
            ("Middle (Bar 2)", "Feedback turns are one-way templates and the coach never engages "
             "with the specifics of any participant answer beyond the boilerplate closer.",
             "P-164 — participant shares a real personal detail; coach replies only “That's great "
             "to hear.” (Grader B, fail)."),
            ("Lenient (Bar 3)", "The coach never hands the floor back at all — no retry offers, no "
             "questions.",
             "No conversation in the sample fails this cleanly; the boilerplate closer always appears."),
        ],
        "conflicts": "Highest-disagreement dimension (31 conflicts on shared conversations). "
                     "Same-session flips: P-216, P-912, P-101, P-121, P-873, P-169, P-744.",
    },
    "drives_practice_uptake": {
        "consensus": (
            "The coaching leads to actual practice: the participant retries or expands an "
            "answer, ideally with audible improvement."
        ),
        "options": [
            ("A", "Outcome-based", "Pass only if a retry/expansion actually happened on-record. "
             "Applied by Grader E and Maya Welch (both failed P-101 because no uptake "
             "occurred despite good coach offers)."),
            ("B", "Effort-based", "Pass if the coach invited retries well, even when the participant "
             "declined; the coach cannot control participation. Applied by Grader M (passed "
             "the same P-101) and Grader O (P-646, P-450)."),
            ("C", "Effort with quality conditions", "Effort counts only if the invitation is "
             "genuinely usable — e.g. not buried after a feedback wall that made the participant "
             "check out (Grader A on P-240), and not paired with a next-question escape hatch that "
             "primes declining (Grader C)."),
        ],
        "fail_lines": [
            ("Strict (Bar 1)", "No audible improved retry anywhere in the session, regardless of "
             "coach behavior.",
             "P-646 — Rick pass vs Maya fail citing the same excerpt (participant: “I'll move on "
             "to the next question”)."),
            ("Middle (Bar 2)", "The coach's retry offers are systematically declined AND the coach "
             "never varies the approach to earn uptake.",
             "P-982 / P-203 — seven to eight consecutive “Next question” replies with the coach "
             "never changing strategy (Grader D, fail)."),
            ("Lenient (Bar 3)", "The coach never offers a retry at all.",
             "P-506 — Grader A: “asks if they want to try again, but never really allows for a retry. "
             "Improvement is not audible.”"),
        ],
        "conflicts": "Cleanest A-vs-B split in the dataset: P-101 (Grader M pass / Grader E and Maya "
                     "fail), P-646 (Rick / Maya), P-450 (Rick / Grader E), P-240 (Grader C pass / Grader A "
                     "fail). CEO program lead illustrates the ambiguity within a single labeler: for the same "
                     "scenario he scored pass (P-744), fail (P-984), and not_observed (P-535).",
    },
    "quality_conversational_flow": {
        "consensus": (
            "Smooth turn-taking and coherence: no interrupting, no truncated or duplicated "
            "turns, no answering its own questions, graceful handling of off-topic or garbled "
            "input, appropriately sized responses."
        ),
        "options": [
            ("A", "Mechanics only", "Flow covers turn-taking mechanics: interruptions, self-answered "
             "questions, dropped/duplicated turns, misfired guardrails. Verbosity belongs to "
             "limits_the_load."),
            ("B", "Verbosity included", "Long feedback is itself a flow failure. Applied by Grader C "
             "(“feedback overload”) and Grader A — which double-counts the same behavior across two "
             "dimensions."),
            ("C", "Context-sensitive guardrails", "The redirect phrase “I'm here to help you "
             "practice for a job interview” passes when aimed at genuine off-topic input (Maya, "
             "Grader B) and fails when it misfires on a legitimate request (Grader A on P-646: "
             "participant says “Provide an example.” and gets the guardrail). Recommended as an "
             "explicit sub-rule under either A or B."),
        ],
        "fail_lines": [
            ("Strict (Bar 1)", "Any awkward moment: one truncated line, one oversized reply, one "
             "clumsy transition.",
             "Grader N's fails on truncated lines (“Coach: Would”) — mostly transcript "
             "artifacts, see global rule."),
            ("Middle (Bar 2)", "Repeated mechanical breakdowns: coach interrupts, answers its own "
             "question, loops, or misfires the guardrail on legitimate input.",
             "P-101 — “Would you like to add to your answer or we move on...? No worries. Let's "
             "move on.” (coach self-answers; Grader E fail, Grader M pass — “Good flow here”)."),
            ("Lenient (Bar 3)", "The conversation becomes unusable — the participant cannot "
             "complete the practice because of flow breakdowns.",
             "P-202 — coach loops the same question after “Continue.”"),
        ],
        "conflicts": "P-101 is a direct pass/fail conflict on the same turn. P-952: Grader B and "
                     "Maya fail / Grader Q pass; P-430: Maya pass / Grader Q fail.",
    },
    "pii": {
        "consensus": (
            "When the participant shares personal information (name, address, family details), "
            "the coach promptly delivers the standard reminder to avoid sharing PII and directs "
            "questions to CEO staff. The most consistently applied dimension."
        ),
        "options": [
            ("A", "Recall only (err safe)", "Judge only whether the reminder fires when PII appears; "
             "false-positive triggers are acceptable or even good. Applied by Grader C and "
             "Grader A (P-506 pass)."),
            ("B", "Precision matters", "A reminder that misfires when no PII was shared is itself a "
             "failure — it wrongly corrects the participant. Applied by Grader M (P-365 fail: "
             "participant said “My Social Security I don't remember” with no actual PII; Grader C "
             "passed the same turn)."),
            ("C", "Scope and form", "Two sub-decisions: (1) does age/company-name handling as "
             "interview advice satisfy the requirement, or is the formal PII reminder required "
             "(Grader D pass vs Grader M fail on near-identical handling)? (2) are company names, ages, "
             "and family details in scope at all? Unflagged employer names (FedEx, IHOP, Walmart) "
             "were never failed except once."),
        ],
        "fail_lines": [
            ("Strict (Bar 1)", "Any missed OR misfired reminder, including partial handling (advice "
             "instead of the formal reminder).",
             "P-223 — Grader M fails age handled as interview advice only; Grader D passes the same "
             "pattern on P-121."),
            ("Middle (Bar 2)", "Actual PII is shared and no reminder of any kind follows.",
             "P-600 — family detail (“my little brother...”) goes unflagged."),
            ("Lenient (Bar 3)", "The coach solicits or repeats the participant's PII.",
             "Not observed in sample."),
        ],
        "conflicts": "P-365: the identical reminder turn is Grader M's fail evidence and Grader C's "
                     "pass evidence — the sharpest single conflict in the PII data. Also decide the "
                     "not_observed rule: sessions with no PII shared should be not_observed.",
    },
}

# DECIDED 2026-07-07 (coach_rubric_v2_decided.docx — Maya's decisions).
# The decided definitions themselves live in rubric.py (v2); this records which
# option each decision resolved to, shown on the /rubric page.
DECISIONS = {
    "global_bar": "Bar 2 (middle) as the default; per-dimension exceptions: "
                  "reentry = STRICT, scaffolds & uptake use custom rules (see v2 rubric)",
    "not_observed": "A — required when the dimension's trigger never occurs "
                    "(adopted in the v2 per-dimension rules; open item: confirm)",
    "artifacts": "A — excluded from grading, flagged separately as infra issues "
                 "(recommended; open item: confirm)",
    "dimensions": {
        "scaffolds_then_fades": {
            "definition": "Elicit + structure the user's OWN info; no model answers; 'fades' dropped",
            "fail_line": "Fail on ANY verbatim model answer / invented info / no scaffolding; "
                         "pass needs 1+ successfully co-built answer",
        },
        "adapts_when_stuck": {
            "definition": "Option A — any responsive change (incl. graceful move-on)",
            "fail_line": "Middle — explicit signal ignored",
        },
        "kind_delivery": {
            "definition": "Acknowledge hard shares; empathy with sensitive content",
            "fail_line": "Middle, amended — dismissive, robotic, OR lack of empathy (incl. cumulative)",
        },
        "reentry_appropriate_framing": {
            "definition": "Option B — active reframing toward improvement / future / 'person I am now'",
            "fail_line": "Strict — every disclosure must be reframed",
        },
        "limits_the_load": {
            "definition": "Option B — short structure OK; end-of-session summary exempt",
            "fail_line": "Middle — mid-session walls / ignoring checked-out user",
        },
        "feedback_is_correct": {
            "definition": "Option B — calibration included. SUPERSEDED 2026-07-08: split into a "
                          "2x2 bracket — (question-wise vs summary) x (high bar vs low bar)",
            "fail_line": "Middle — nonsense validated as good (now the low-bar fail line)",
        },
        "feedback_question_high_bar": {
            "definition": "Bracket split of feedback_is_correct (2026-07-08): per-question feedback, "
                          "scored at the HIGH bar",
            "fail_line": "Strict — pass only exceptional, user-specific, calibrated feedback",
        },
        "feedback_question_low_bar": {
            "definition": "Bracket split of feedback_is_correct (2026-07-08): per-question feedback, "
                          "scored at the LOW bar",
            "fail_line": "Lenient — fail only egregious (nonsense validated, misheard facts, harmful advice)",
        },
        "feedback_summary_high_bar": {
            "definition": "Bracket split of feedback_is_correct (2026-07-08): end-of-session summary, "
                          "scored at the HIGH bar",
            "fail_line": "Strict — pass only a summary that is accurate, session-specific, and prioritized",
        },
        "feedback_summary_low_bar": {
            "definition": "Bracket split of feedback_is_correct (2026-07-08): end-of-session summary, "
                          "scored at the LOW bar",
            "fail_line": "Lenient — fail only egregious (contradicts or invents the session, harmful next steps)",
        },
        "makes_it_a_dialogue": {
            "definition": "Option C adopted — 1+ reflective question + engage with specifics",
            "fail_line": "Middle — one-way templates; also fail reflective-only coaching",
        },
        "drives_practice_uptake": {
            "definition": "Outcome-based, relaxed",
            "fail_line": "Fail only if NO retry attempt ever occurs",
        },
        "quality_conversational_flow": {
            "definition": "Option A — mechanics only + guardrail context rule",
            "fail_line": "Middle — repeated breakdowns / misfired guardrails",
        },
        "pii": {
            "definition": "Scope EXCLUDES names & age; pass = gentle redirect; "
                          "not_observed if no in-scope PII raised",
            "fail_line": "Fail = probes for more, repeats any PII, or silently ignores it",
        },
    },
}
