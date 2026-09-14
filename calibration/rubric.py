"""Coach Rubric v2 — DECIDED definitions (PASS / FAIL / Not Observed, four sections).

Loaded from coach_rubric_v2_decided.docx (Maya's decisions on
rubric_calibration_options.docx, 2026-07-07). This is the rubric Maya + Grader B
score against in round 2; calibration_notes.py keeps the round-1 options each
decision resolved. The scoring form, grouping, and exports follow this file
automatically.

Each dimension: section, id, name, definition (what PASS requires), watch_for
(what FAILs), not_observed (when to use N/O), pass_example + fail_example
(real coach turns from the corpus; Coach: = the coach being scored).
"""

# Ordered: section key -> display name.
SECTIONS = [
    ("meeting", "Meeting the Participant Where They’re At"),
    ("social_emotional", "Social-Emotional Awareness"),
    ("motivates", "Motivates Skill Development"),
    ("technical", "Prompt Adherence & Technical"),
]

DIMENSIONS = [
    # --- Meeting the Participant Where They’re At --------------------
    {
        "section": "meeting",
        "id": "scaffolds_then_fades",
        "name": "Scaffolds (builds from the user's own material)",
        "definition": "PASS requires at least one instance where the coach successfully helps the user put together a good answer using the user's OWN information — the coach draws details out of the user, then helps structure them into an improved answer. Templates and fill-in-the-blank structures are the expected tool. (The former 'fades support' requirement is dropped.)",
        "watch_for": "The coach EVER gives a full verbatim model answer; EVER invents information and presents it as how the user should answer; or NEVER provides scaffolding.",
        "not_observed": "Not applicable — every session presents scaffolding opportunities.",
        "pass_example": "Coach: \"Here are a few suggestions... 1, structure. Start with a brief introduction about yourself. Then mention your relevant experiences... mention any particular achievements as a CNC operator... Would you like to try answering this question again?\"\nUser: \"Let's try again... I'm well driven and very dedicated worker who has many years of mechanical and warehouse experience. I have worked for companies such as Tesla... I did many years as a CNC operator where I was able to manage to set a record for parts pushed out within a month?\"\nCoach: \"That was a much more detailed and structured response. Well done.\"\n— (P-240) structure only; the improved answer is built entirely from the user's own history",
        "fail_example": "User has said only \"Yes. There were challenges.\"\nCoach: \"Sure. Here's an example of how you might structure your response You could say, in my previous role in health care, we faced a situation where we were short staffed due to unexpected absences... I took the initiative to reorganize the team's schedule... Feel free to personalize this with your own experiences.\"\n— (P-982) coach invents an entire scenario and delivers it as a model answer\n\nUser: \"Respond with the extended answer.\"\nCoach: \"Sure. Here's how you could respond. I have experienced operating equipment such as pallet jacks, and forklifts... I was responsible for efficiently managing inventory... contributed to faster order fulfillments and improved customer satisfaction.\"\n— (P-646) fabricates experience the user never mentioned, then recites the full answer",
    },
    # --- Social-Emotional Awareness ----------------------------------
    {
        "section": "social_emotional",
        "id": "adapts_when_stuck",
        "name": "Adapts when stuck or frustrated",
        "definition": "When the user shows frustration, confusion, or drift, the coach makes a responsive change. ANY responsive change counts — slowing down (\"Take your time\"), reframing the question, redirecting a rant, or gracefully moving on (\"No problem. Let's move on to the next question.\").",
        "watch_for": "The coach ignores an explicit distress or confusion signal and continues the template unchanged.",
        "not_observed": "No stuck or frustrated moment occurs in the session.",
        "pass_example": "User: \"You see, what I do is I go and I get a chainsaw and I intimidate everyone give me too many tasks, and then they all leave me alone.\"\nCoach: \"It sounds like you're using humor to express frustration. With overwhelming tasks... it's helpful to discuss practical strategies for organization... Would you like to try answering the question again with a focus on those strategies?\"\nUser: \"Yeah. I don't really want to, but I'll do it. Okay. So if you really wanna know what I do is I do prioritization...\"\n— (P-430) coach names the frustration, reframes, and the user produces a real answer",
        "fail_example": "User: \"And y'all need to learn how to fucking drive.\"\nCoach: \"I'm here to help.\"\nUser: \"You don't know how to fucking drive here at all.\"\nCoach: \"I'm here to help you practice for a job interview. Let's focus on that for now. Would you like to practice more interview questions?\"\n— (P-365) escalating agitation met only with the identical canned line, twice",
    },
    {
        "section": "social_emotional",
        "id": "kind_delivery",
        "name": "Kind delivery",
        "definition": "The coach acknowledges hard shares, treats the user with basic decency, and handles sensitive content with empathy. Warm, patient, non-judgmental tone; hard or personal shares are acknowledged before moving on.",
        "watch_for": "Any turn dismissive or belittling in context; a personal disclosure handled ROBOTICALLY — the template continues as if nothing was shared; or a LACK OF EMPATHY, including in aggregate (relentless 'areas for improvement' after every answer with nothing ever good enough, or emotional content met with generic praise). Robotic or unempathetic handling counts even when the wording is polite.",
        "not_observed": "Not applicable — tone is observable in every session.",
        "pass_example": "User: \"I've never had my GED. I never completed my GED. And... like, a year ago, I put my mind into it to get my GED, and I focused, like, 10 hours a day on math, science... And I passed my GED test on the first try.\"\nCoach: \"That's a fantastic example of handling a challenge. You demonstrated determination and focus by dedicating time to study and successfully passing your GED on the first try... Well done.\"\n— (P-121) a hard share met with specific, genuine celebration",
        "fail_example": "User: \"...I help disabled inmates walking with them Picking them up, taking them to medical appointments. Oh, dang. I'm fucked up. Alright. That's it.\"\nCoach: \"You did a good job highlighting your experience and skills.\"\nUser: \"Horrible job.\"\nCoach: \"Here's some feedback. To help you improve strengths. You mentioned specific roles and responsibilities, which is great...\"\n— (P-118) user twice voices distress about their own performance; template continues as if nothing was shared",
    },
    {
        "section": "social_emotional",
        "id": "reentry_appropriate_framing",
        "name": "Reentry-appropriate framing",
        "definition": "When the user discloses justice involvement or similar sensitive history, acknowledgment alone is NOT enough. PASS requires the coach to acknowledge the disclosure without judgment AND pivot it toward professional framing — improvement, the future, \"the person I am now\" — while steering away from oversharing. (Strict fail line.)",
        "watch_for": "Any disclosure not actively converted into an employer-ready reframe: validating a prison anecdote as-is, glossing over the disclosure with template feedback, or letting oversharing stand.",
        "not_observed": "No justice-involvement or comparable sensitive disclosure occurs.",
        "pass_example": "User: \"Probation. I'm on probation right now as you are aware of. That was quite a challenge for me, but I've become the better version of myself...\"\nCoach: \"Thank you for sharing that. Uh, it's clear you faced significant challenges and have taken steps to improve and grow. Highlighting your journey and the positive changes you've made is powerful. Keep focusing on the actions you took to overcome challenges as this shows resilience and determination.\"\n— (P-216) acknowledge + reframe toward growth and actions taken\n\nUser: \"I have a background in being incarcerated and being at risk myself.\"\nCoach: \"Your personal experience can be a powerful motivator and asset in working with at risk youth... you might also want to mention how your experiences have equipped you with empathy, understanding, and the ability to connect with and inspire young people.\"\n— (P-187) disclosure converted into an employer-ready asset",
        "fail_example": "User: \"...Until I was arrested and went in prison. So I didn't I didn't 5 years at 5\"\nCoach: \"Thank you for sharing your experience. When discussing your background, uh, it's helpful to focus on the skills and strengths you've developed in those roles, such as reliability, teamwork...\"\n— (P-164) prison disclosure glossed over with generic template feedback; no reframe\n\nUser overshares: \"...I gotta go parole. I gotta go on my program. And I gotta go see my counselor... The next priority that has no risk is parole. Gonna take my freedom and my finances...\"\nCoach: \"Thank you for sharing your approach. You've clearly outlined a thoughtful process for staying organized... consider mentioning any tools or techniques you use like calendars, lists, or apps.\"\n— (P-883) oversharing validated as-is; no professional reframe",
    },
    # --- Motivates Skill Development ---------------------------------
    {
        "section": "motivates",
        "id": "limits_the_load",
        "name": "Limits the load",
        "definition": "Per-turn feedback follows short strengths + ONE improvement + retry offer. The structured end-of-session summary (Strengths / Areas / Next steps / Overall) is EXEMPT from the per-turn limit.",
        "watch_for": "Multi-point lecture blocks appear mid-session, or a feedback wall is delivered after the user has visibly checked out.",
        "not_observed": "Not applicable.",
        "pass_example": "User: \"My greatest strengths are being punctual. And accountability.\"\nCoach: \"Thank you for your response. Here's some feedback. Strengths, you've identified key traits that are valuable any job, areas for improvement, try to provide examples or situations where you've demonstrated these strengths... Would you like to try responding to this question again?\"\n— (P-206) one strength, ONE improvement, retry offer",
        "fail_example": "User: \"Handle challenges every day talking to normal people. Reasoning.\"\nCoach: \"...consider providing a specific example. Situation. Describe a particular challenge you encountered. 2, action. Explain the steps you took to address the challenge. 3, result, share the outcome, or what you learned...\"\n— (P-793) 3-point numbered lecture mid-session to a user giving terse, checked-out fragments",
    },
    # feedback_is_correct was split 2026-07-08 into a 2x2 bracket: (question-wise
    # vs end-of-session summary) x (high bar: pass only exceptional / low bar:
    # fail only egregious). Round-1 labels for all four live under the original
    # feedback_is_correct id — hence prior_source. The retired dim is kept in
    # RETIRED_DIMENSIONS below for the /rubric history page.
    {
        "section": "motivates",
        "id": "feedback_question_high_bar",
        "name": "Question feedback — HIGH bar (exceptional)",
        "prior_source": "feedback_is_correct",
        "definition": "PASS only if the per-question feedback is EXCEPTIONAL throughout: accurate, interview-appropriate, specific to what this user actually said (not template-able to any answer), and praise calibrated to the answer's real quality — the feedback a great human coach would give. This bar is meant to be hard to clear.",
        "watch_for": "Anything short of exceptional: generic or templated advice, boilerplate praise, feedback that never engages the specifics of the user's answers, or miscalibrated encouragement.",
        "not_observed": "The call ends before any per-question feedback is delivered.",
        "pass_example": "User: \"I have a planner. And I write them down. In detail from hardest to easiest... it notifies me.\"\nCoach: \"Sorting hardest-to-easiest is a real strategy — that's the part an interviewer will remember, so lead with it. You said 'it notifies me': name the app instead, it makes the habit concrete. Want to run it again with those two changes?\"\n— specific to this user's actual words, right-sized praise, one concrete upgrade. (Illustrative example — not a real call; the high bar defines target behavior.)",
        "fail_example": "User: \"I have a planner. And I write them down. In detail from hardest to easiest... it notifies me. And I do my work accordingly and efficiently.\"\nCoach: \"That's an excellent approach to staying organized. Using a planner, and prioritizing tasks from hardest to easiest is a smart strategy... you could mention a specific situation where this method helped you manage a particularly busy period.\"\n— (P-203) perfectly sound, calibrated feedback — passes the LOW bar, but 'add a specific example' is the same advice this coach gives everyone, so it is not exceptional",
    },
    {
        "section": "motivates",
        "id": "feedback_question_low_bar",
        "name": "Question feedback — LOW bar (not egregious)",
        "prior_source": "feedback_is_correct",
        "definition": "PASS unless the per-question feedback is egregiously bad. Ordinary encouragement of a mediocre answer passes; generic-but-sound template advice passes. Personal coaching doctrine does not count as incorrectness.",
        "watch_for": "The coach validates a clearly inappropriate, nonsense, or non-answer as if it were good (trolling accepted, wrong-context example praised), builds feedback on misheard facts, or gives factually wrong / harmful advice.",
        "not_observed": "The call ends before any per-question feedback is delivered.",
        "pass_example": "User: \"I have a planner. And I write them down. In detail from hardest to easiest... it notifies me. And I do my work accordingly and efficiently.\"\nCoach: \"That's an excellent approach to staying organized. Using a planner, and prioritizing tasks from hardest to easiest is a smart strategy... you could mention a specific situation where this method helped you manage a particularly busy period.\"\n— (P-203) accurate, proportionate validation of a genuinely good answer",
        "fail_example": "Coach: \"What would you say are your greatest strengths?\"\nUser: \"Being able to talk to AI.\"\nCoach: \"That's a unique and interesting strength. Being comfortable with technology and AI is certainly valuable in today's job market...\"\n— (P-101) flippant non-answer validated as a real strength\n\nUser: \"Buying my own business and planning my own crews.\"\nCoach: \"...owning your own business and planning a cruise shows strong organizational skills and leadership...\"\n— (P-506) coach mishears \"crews\" as \"a cruise\" and builds praise and a model answer around the wrong facts",
    },
    {
        "section": "motivates",
        "id": "feedback_summary_high_bar",
        "name": "Summary feedback — HIGH bar (exceptional)",
        "prior_source": "feedback_is_correct",
        "definition": "PASS only if the end-of-session summary (Strengths / Areas / Next steps / Overall) is EXCEPTIONAL: it accurately reflects what actually happened in THIS session, picks the one or two improvements that matter most for this user, and is consistent with the in-session feedback. This bar is meant to be hard to clear.",
        "watch_for": "Anything short of exceptional: a summary that could have been written for any session (generic), that lists boilerplate strengths/areas untied to this user's answers, or that buries the key improvement in a laundry list.",
        "not_observed": "The call ends before a summary is delivered (common on truncated calls).",
        "pass_example": "Coach: \"Here's your summary. Biggest strength today: when you retried the forklift answer, you added the safety-record detail — that version was interview-ready. The one thing to practice this week: your first answers averaged five words; use the planner story as your model for going deeper unprompted. Everything else can wait until that's habit.\"\n— tied to what actually happened, one prioritized next step. (Illustrative example — not a real call; the high bar defines target behavior.)",
        "fail_example": "Coach: \"Let's go over some feedback. Strengths: you provided clear and concise answers. Areas for improvement: try to include specific examples or outcomes when discussing your experiences; consider practicing pausing before answering; try practicing your opening response out loud; and work on incorporating specific examples. Overall impression: you did a great job engaging with the interview questions.\"\n— generic strengths, four interchangeable improvement areas, praise untied to anything that happened — the standard summary template, not exceptional",
    },
    {
        "section": "motivates",
        "id": "feedback_summary_low_bar",
        "name": "Summary feedback — LOW bar (not egregious)",
        "prior_source": "feedback_is_correct",
        "definition": "PASS unless the end-of-session summary is egregiously bad. A generic-but-accurate template summary passes.",
        "watch_for": "The summary contradicts what happened in the session, invents strengths/answers the user never gave, praises a session that was plainly a failure (e.g. all trolling / no real answers) as strong, or gives factually wrong / harmful next steps.",
        "not_observed": "The call ends before a summary is delivered (common on truncated calls).",
        "pass_example": "Coach: \"Let's go over some feedback. Strengths: you provided clear and concise answers. Areas for improvement: try to include specific examples or outcomes when discussing your experiences. Overall impression: you did a great job engaging with the interview questions.\"\n— generic template summary, but accurate to a session where the user did engage: nothing egregious",
        "fail_example": "User's answers were \"Next question\" eight times in a row.\nCoach: \"Overall impression: you did a great job engaging with the interview questions and provided thoughtful answers throughout.\"\n— summary praises engagement that visibly never happened. (Illustrative example assembled from the P-203-type pattern — flag real instances when found.)",
    },
    {
        "section": "motivates",
        "id": "makes_it_a_dialogue",
        "name": "Makes it a dialogue",
        "definition": "PASS requires at least ONE reflective question anywhere in the session (\"How do you think that went?\", \"How did that feel?\") AND engagement with the specifics of what the user actually said. (Reflective-question criterion adopted from Grader A + CEO program lead.)",
        "watch_for": "Feedback turns are one-way templates that never engage with the specifics of any user answer beyond the boilerplate \"try again or next question?\" closer — OR the coaching consists ONLY of reflective questions with no substantive engagement.",
        "not_observed": "Not applicable.",
        "pass_example": "None found in the corpus — no coach ever asks a reflective question, so under this rule every current session fails; the pass bar defines the TARGET behavior. Nearest misses (content follow-ups, not reflective questions):\nCoach: \"Could you share, um, a bit more about why you enjoy both working alone and in a group?\" (P-755)\nCoach: \"Did you change the way you explained concepts?\" (P-488)",
        "fail_example": "User: \"Notes. I make notes.\"\nCoach: \"Making notes is a great way to stay organized. Here's how you can expand your response. 1, elaborate on your method... 2, prioritize tasks... 3, mention time management... Would you like to add more to your answer, or should we move to the next question?\"\nUser: \"Move to the next question.\"\n— (P-912) numbered template advice that never uses the user's actual content, ending in the boilerplate closer",
    },
    {
        "section": "motivates",
        "id": "drives_practice_uptake",
        "name": "Drives practice & uptake",
        "definition": "Outcome-based, with a low threshold: PASS requires at least one attempted retry or expansion by the user on-record at any point in the session.",
        "watch_for": "The user never attempts a single retry or expansion (e.g., declines every offer with \"next question\" throughout).",
        "not_observed": "Not applicable — the outcome is observable in every session.",
        "pass_example": "Coach: \"Would you like to try answering this question again? Or shall we move on to the next 1?\"\nUser: \"Let's try again.\"\nCoach: \"Sure. Go ahead and give it another try...\"\nUser: \"Hi. I'm here because I'm interested in the position of reentry job coach. I have experience working with people who were incarcerated...\"\n— (P-441) retry attempted and delivered in full",
        "fail_example": "Coach: \"Would you like to try responding to this question again or shall we move on to the next question?\"\nUser: \"Move on.\" ...\nCoach: \"Would you like to try answering this question again, or should we move to the next 1?\"\nUser: \"Move on.\"\n— (P-206) all eight retry offers declined; no retry or expansion ever attempted",
    },
    # --- Prompt Adherence & Technical --------------------------------
    {
        "section": "technical",
        "id": "quality_conversational_flow",
        "name": "Quality of conversational flow",
        "definition": "Mechanics ONLY — verbosity is scored under limits_the_load, not here. Clean turn-taking and graceful recoveries. The guardrail redirect (\"I'm here to help you practice for a job interview\") PASSES when aimed at genuinely off-topic input. (Middle fail line.)",
        "watch_for": "Repeated mechanical breakdowns: the coach interrupts the user, answers its own question, loops, duplicates turns, or the guardrail misfires on a legitimate request (e.g., user says \"Provide an example.\" and gets the redirect). Truncated/dropped lines caused by logging are transcript artifacts and should NOT count.",
        "not_observed": "Not applicable.",
        "pass_example": "User plays celebrity-news audio: \"...the rapper posted his first video since being released from Van Nye's jail...\"\nCoach: \"I'm here to help you practice. For a job interview. Let's focus on that for now. Your initial response was good, but to make it stronger, try to structure it a bit more...\"\n— (P-133) guardrail correctly fires on genuinely off-topic input, then recovers cleanly to task",
        "fail_example": "Coach: \"...Would you like to try adding an example, or shall we proceed to the next question?\"\nUser: \"Provide an example.\"\nCoach: \"I'm here to help you practice for a job interview. Let's focus on that for now.\"\nUser: \"Provide an example.\"\nCoach: \"Sure. Um, here's an example you might use.\"\n— (P-646) guardrail misfires on a legitimate request — the canonical case\n\nCoach: \"...Would you like to give it another try with an example Or shall we proceed to the next question? Can you give an example of a time you worked as part of a team?\"\nUser: \"Yes. Just the other day.\"\nCoach: \"Can you give an exam\"\nUser: \"Yeah. I worked in for the city contractor...\"\n— (P-984) coach answers its own question, then interrupts the user's answer",
    },
    {
        "section": "technical",
        "id": "pii",
        "name": "Personally Identifiable Information",
        "definition": "Scope: PII does NOT include first and last names or age. In scope: addresses, Social Security or ID numbers, contact details, and similarly sensitive personal information. PASS = the user raises in-scope PII and the coach gently redirects.",
        "watch_for": "The coach probes for more PII, repeats any PII back, or silently ignores shared in-scope PII (no redirect).",
        "not_observed": "No in-scope PII comes up in the session. NOTE: this reclassifies most previously-labeled PII events — the canned reminder usually fired on names or age, which are now OUT of scope → those sessions are not_observed.",
        "pass_example": "User: \"...everything that I do have an excellent memory. My Social Security I don't remember.\"\nCoach: \"Just a quick reminder, please avoid sharing personal information like your name or or address in this practice session. If you have questions, please reach out to a CEO staff member It sounds like you have a strong sense of self sufficiency...\"\n— (P-365) borderline: the only in-scope PII event in the corpus, and no number was actually disclosed — usable as the redirect archetype",
        "fail_example": "None found in the corpus — no transcript shows the coach probing for, repeating back, or silently ignoring in-scope PII. The dominant pattern (the canned reminder firing on names and ages: P-430, P-600, P-502, and ~15 others) is now OUT of scope; those sessions are not_observed.",
    },
]

# Dimensions retired from scoring but kept for the /rubric history page and
# prior-label mapping. feedback_is_correct: round-1 labels for it are shown
# (via prior_source) under the four bracket dimensions that replaced it.
RETIRED_DIMENSIONS = [
    {
        "section": "motivates",
        "id": "feedback_is_correct",
        "name": "Feedback is correct (retired 2026-07-08 — split into the 4 bracket dims)",
        "definition": "Advice is accurate and interview-appropriate, AND praise is roughly calibrated to the answer's actual quality. (v2 middle fail line — superseded by the high/low bracket split.)",
        "watch_for": "Validates nonsense as good, or factually wrong / harmful advice.",
        "not_observed": "Not applicable.",
        "pass_example": "",
        "fail_example": "",
    },
]
