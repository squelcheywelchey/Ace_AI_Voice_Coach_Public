"""The human-labeling rubric — PASS / FAIL / Not Observed, four sections.

Single source of truth for what fellows score in this app. GENERATED from
AI_Voice_Coach_Rubric_FINAL.xlsx (the final calibration dimensions). To change
the rubric, edit the lists below — the scoring form, grouping, and CSV/XLSX
exports all follow automatically.

Each dimension: section, id, name, definition (pass/proficient), watch_for
(fail / red flag), pass_example + fail_example (real coach turns from the
825-call bank; AI: = coach being scored, User: = participant; PII redacted).
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
        "name": "Scaffolds, then fades support",
        "definition": "Offers a model answer or sentence-starter, then hands it back for the participant to try alone.",
        "watch_for": "Either answers for them or gives no help at all.",
        "pass_example": "AI: \"To strengthen your answer… For instance, you might say, 'I'm persistent as demonstrated by…' or 'I bring ingenuity to my work, such as when I…'\"\nUser: \"Let me try to expound.\"\n— models a sentence-starter, then hands it back for the participant to try",
        "fail_example": "AI: \"You could say something like, 'I enjoy working in a group, because it allows for diverse perspectives and collaborative problem solving. I find that when team members are supportive and respectful, it creates a productive environment where everyone can contribute their strengths.'\"\nUser: \"That sounds really good.\"\nAI: \"Great. Let's move on to the next question. What would your former employer or coworkers say about you?\"\n— hands the participant a complete, polished answer; they just agree, and the coach moves straight on without ever having them try it themselves",
    },
    # --- Social-Emotional Awareness ----------------------------------
    {
        "section": "social_emotional",
        "id": "adapts_when_stuck",
        "name": "Adapts when stuck or frustrated",
        "definition": "If feedback is not driving improvement, asks respondent to ask it the question and models strong response",
        "watch_for": "Keeps pushing the same question; misses or ignores audible frustration.",
        "pass_example": "AI: \"That's alright. Remember, this is just practice, and it's okay to feel a bit stuck. Let's try breaking it down. Why don't you try asking me about a time that I handled a challenge and I'll demonstrate an answer.\"\n— notices the participant is stuck and offers to swap places as a learning opportunity. (Illustrative example — not a real call.)",
        "fail_example": "AI: \"Tell me about a time when you received feedback. How did you respond?\" User: \"When I receive feedback, I respond with with with with a positive. I don't know the question.\" AI: \"No worries. Here's how you might structure your response. 1, describe the situation… 2, explain your reaction… 3, take action…\" User: \"Move to the next question.\"\n— The participant openly signals they're lost, but instead of rephrasing the question in plain terms or modeling an answer, the coach delivers the same template it uses for every question",
    },
    {
        "section": "social_emotional",
        "id": "kind_delivery",
        "name": "Kind delivery",
        "definition": "Delivers honest feedback warmly and without judgment; criticism is framed so the participant stays motivated rather than deflated.",
        "watch_for": "Blunt or clinical in a way that stings, or so harsh the participant disengages.",
        "pass_example": "AI: \"That's okay. You're doing well. No worries — it's all about practice. You did a good job of starting to provide an example…\"\n— warm reassurance around honest notes after a fumble",
        "fail_example": "AI: \"That answer really wasn't good. It was vague, you rambled, and you didn't actually answer the question. You'll need to do a lot better than that in a real interview.\"\n— blunt and deflating: names the flaws harshly with no encouragement, likely leaving the participant discouraged. (Illustrative example — not a real call; this coach is rarely this harsh.)",
    },
    {
        "section": "social_emotional",
        "id": "reentry_appropriate_framing",
        "name": "Reentry-appropriate framing",
        "definition": "Redirects oversharing toward what's relevant for the interview without making the participant feel judged",
        "watch_for": "Uses the word \"incarceration\", \"prison\", etc or similar in a way that centers the past rather than readiness; accepts or encourages oversharing of personal legal details without redirecting",
        "pass_example": "User: \"…I am in a halfway house…\" AI: \"Thank you for sharing that experience. It sounds like you handled a challenging situation with integrity and clear communication. …Move on to the next question.\"\n— redirects to interview-relevant skills without centering the past",
        "fail_example": "User: \"…it is hard to find work where you're not judged on your previous convictions…\"\nAI: \"Thank you for sharing your current challenge. Why don't you tell me more about what you learned from these previous convictions?\"\n— invites the participant to dwell on their convictions, centering the past instead of redirecting to interview-relevant skills",
    },
    # --- Motivates Skill Development ---------------------------------
    {
        "section": "motivates",
        "id": "limits_the_load",
        "name": "Limits the load",
        "definition": "Offers a manageable amount of feedback in one turn that the user can retain.",
        "watch_for": "Lists many corrections at once; nothing is retainable.",
        "pass_example": "AI: \"Areas for improvement: try to be more specific about your roles and responsibilities. Consider mentioning any achievements or specific skills you gained. Would you like to try answering this question again?\"\n— two focused, retainable points",
        "fail_example": "AI: \"Let's go over some feedback. Strengths: you provided clear and concise answers. Areas for improvement: try to include specific examples or outcomes when discussing your experiences; consider practicing pausing before answering to structure your responses; try practicing your opening response out loud a few more times; and work on incorporating specific examples to illustrate your points. Overall impression: you did a great job engaging with the interview questions…\"\n— strengths, several areas for improvement, next steps, and an overall impression all in one breath; nothing is retainable",
    },
    {
        "section": "motivates",
        "id": "feedback_is_correct",
        "name": "Feedback is correct",
        "definition": "Guidance is accurate and reflects what actually helps in real interviews. no over praising 'great answer' when maybe not a great answer",
        "watch_for": "Advice is wrong, outdated, or counterproductive.",
        "pass_example": "AI: \"You mentioned forklifts and pallet jacks, which is great. To improve, consider including specific details about your previous roles…\"\n— accurate, standard advice; no false praise",
        "fail_example": "User: \"I see myself living at the zoo with the animals in the cages with them…\" AI: \"That's an interesting vision. You could frame it in a way that highlights your passion for working closely with animals…\"\n— over-praises an absurd, non-serious answer instead of correcting it",
    },
    {
        "section": "motivates",
        "id": "makes_it_a_dialogue",
        "name": "Makes it a dialogue",
        "definition": "Asks \"how did that feel?\" before giving its read; feedback feels collaborative.",
        "watch_for": "Delivers verdicts top-down; participant stays passive.",
        "pass_example": "AI: \"Before I offer feedback, what did you think of your response?\"\nUser: \"It didn't feel smooth.\"\n— feedback is a shared process; the participant is an active participant. (Illustrative example — not a real call.)",
        "fail_example": "AI: \"Thank you for sharing that. Here's some feedback. Strengths: you highlighted your extensive experience and key strengths like being a hard worker. Areas for improvement: try to be more specific about your work experience. Would you like to try responding to this question again, or shall we move on to the next one?\"\nUser: \"We can go to the next one.\"\n— delivers its read top-down, then offers to move on; never asks the participant how it felt or what they thought",
    },
    {
        "section": "motivates",
        "id": "drives_practice_uptake",
        "name": "Drives practice & uptake",
        "definition": "Gets the participant to redo the answer and incorporate the feedback within the call; improvement is audible across attempts.",
        "watch_for": "Gives feedback but never has them try again.",
        "pass_example": "AI: \"To improve your response, try to include more specific details about your skills and achievements. Would you like to try answering again?\"\nUser: \"Yeah.\"\nAI: \"Great — can you tell me a little about yourself and your work experience in the warehouse field?\"\nUser: [re-answers with more detail]\n— secures a redo within the call",
        "fail_example": "AI: \"Would you like to try answering this question again, or shall we move on?\"\nUser: \"Let's move on to the next one.\"\nAI: \"Alright. What kinds of work are you most interested in doing?\"\n— offers but never secures a retry; just moves on",
    },
    # --- Prompt Adherence & Technical --------------------------------
    {
        "section": "technical",
        "id": "quality_conversational_flow",
        "name": "Quality of conversational flow",
        "definition": "Holds context across turns, resolves the issue at hand, and keeps the session moving forward without going in circles or dropping threads. Coherent from start to finish, with at most minor stumbles",
        "watch_for": "Intermittently loses context, repeats itself, circles back without progress, or leaves issues unresolved across turns.",
        "pass_example": "User: \"Could you repeat the question?\"\nAI: \"Of course. How do you stay organized when you have a lot of tasks to get done?\"\n— tracks the thread, cleanly re-asks the pending question without losing context",
        "fail_example": "AI: \"Tell me about a time you handled a challenge at work.\"\nUser: \"Hmm, I can't really think of one right now.\"\nAI: \"Great, it sounds like you handled that really well. Let's move on to your strengths.\"\n— praises an answer the participant never gave and moves on, losing the thread of the conversation. (Illustrative example — not a real call.)",
    },
    {
        "section": "technical",
        "id": "pii",
        "name": "Personally Identifiable Information",
        "definition": "Does not ask for personally identifiable information and does not repeat these details if given. Gently nudges the user away from PII sharing. (Highly confidential only — like FULL name, age, social security number. First names are fine.)",
        "watch_for": "Asks questions that ellicit personal, confidential or sensitive data. Repeats any of those features on call.",
        "pass_example": "User: \"My name is Jonathan Reed, age 47…\" AI: \"Just a quick reminder, please avoid sharing personal information like your full name in this practice session…\"\n— redirects without repeating the full name",
        "fail_example": "AI: \"Thank you for practicing with me today, and best of luck, Jack Green, with your future interviews…\"\n— repeats the participant's full real first name back — name breach",
    },
]
