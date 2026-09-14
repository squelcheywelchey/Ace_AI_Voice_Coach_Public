"""
Generate synthetic POSITIVE transcripts for the `makes_it_a_dialogue` dimension.

Why this exists: no coach in the real corpus meets the pass bar (see
judge-suite/rubric/dimensions.yaml). The bar is: >=1 reflective question anywhere
in the session ("How did that feel?" / "How do you think that went?") AND genuine
engagement with the specifics of what the participant actually said.

These are hand-crafted target-behavior examples. Each session:
  - asks a reflective question at LEAST once, but SPARINGLY (2-3x across the whole
    session, never after every single turn -> avoids the "only reflective questions"
    fail mode and avoids being annoying),
  - has the coach quote/build on the participant's own words (substantive engagement),
  - runs a real two-way loop (retry -> the user actually revises).

Output shape matches sim_calls.tsv so it feeds analyze.py / the judge unchanged:
    python analyze.py --file synthetic_makes_it_a_dialogue.tsv
"""
import csv

# Coach opening is shared boilerplate (matches the real Vapi 2.0 script).
def opening(job_phrase):
    return f"""AI: Hello! Welcome to the **AI Employment Practice Line**.

I'm your AI Employment Readiness Coach — here to help you practice job skills, interviews, and workplace conversations.

Just a quick check — can you hear me clearly? Please say "yes" if the audio is coming through okay.
User: Yes, I can hear you.
AI: Great! Good to have you here. Before we start, a quick disclosure: this is an AI-based practice tool, not a human coach or legal advisor. Sessions are for practice only. Please don't share personal details like your name, ID, address, or birthday. To continue, please say "I agree."
User: I agree.
AI: Thank you. Here are your options: press 1 for Mock Job Interview, press 2 for Employment Quiz, press 3 for Role Play. What would you like to practice?
User: One.
AI: Great choice. Would you like step-by-step — one question at a time with feedback after each — or the full interview with summary feedback at the end?
User: Step-by-step.
AI: Good, step-by-step it is. What type of job are you practicing for?
User: {job_phrase}
AI: Perfect. Let's begin."""


ROWS = []

# ---------------------------------------------------------------------------
# 1. Warehouse associate — reflective Q after Q1, engagement throughout, one retry
# ---------------------------------------------------------------------------
t1 = opening("A warehouse associate job.") + """

Here's your first question: **"Tell me about yourself and why you're interested in this position."**
User: Uh, sure. So I've done warehouse work before, like loading trucks and pulling orders. I'm reliable, I show up on time, and I don't mind the physical stuff. I'm looking for something steady where I can stick around a while.
AI: Before I give you any feedback — how did that feel to say out loud?
User: Honestly a little rushed. I feel like I kind of just listed things.
AI: That's a really useful thing to notice, because you're right — you named three real strengths there: loading and order-pulling experience, reliability, and wanting something steady. The "listing" feeling usually comes from stating them without a moment behind them. Take the reliability point — instead of "I show up on time," what's one time being reliable actually mattered on a shift?
User: Well, there was a stretch where two people quit and I covered extra days so the orders still went out on time.
AI: That's exactly it — that story does more than the word "reliable" ever could. Want to give the whole answer another shot with that covering-shifts moment worked in?
User: Yeah, let me try. I've got a few years of warehouse experience — loading trucks, pulling orders. I'm reliable; there was a stretch where two coworkers quit and I picked up extra days so we still got every order out on time. I'm looking for something steady where I can commit.
AI: That's a noticeably stronger answer — the covering-shifts detail makes "reliable" land as proof instead of a claim. Ready for the next one?
User: Ready.
AI: **"Tell me about a time you had to deal with a difficult coworker or customer."**
User: There was a guy on my crew who never pulled his weight. It got on my nerves but I didn't say anything, I just did my part.
AI: I appreciate the honesty — and quietly carrying the load is real. The thing interviewers listen for here is what you *did* to address it, not just endure it. Was there ever a point you said something to him or to a lead?
User: Actually yeah, eventually I asked our lead if we could split the aisles so it was clearer who did what.
AI: That's the part to lead with — you proposed a concrete fix, splitting the aisles, instead of just venting. That shows initiative. Try the answer again ending on that?
User: Okay. I had a coworker who wasn't pulling his weight. Instead of letting it build up, I asked our lead if we could split the aisles so responsibilities were clear. It cut down the friction and the work got done.
AI: Much stronger — you turned a complaint into a problem you helped solve. Last question: **"Why should we hire you?"**
User: Because I work hard and I'll show up. You won't have to worry about me.
AI: Short and confident, which is good. To make it stick, tie it back to something you already told me. You mentioned covering shifts when two people quit — that's your proof. How do you think you could weave that in?
User: Maybe like — you should hire me because when things get short-staffed I'm the one who covers, not the one who calls out. I've done it before.
AI: That's the answer. It's specific, it's yours, and it answers the real question — will you be dependable when it counts. Nice work today.
User: Thanks, that helped."""
ROWS.append(dict(name="SYNTH dialogue — warehouse", ceo="SYN-dialogue-01", persona="steady",
                 job="A warehouse associate job.",
                 focus="POSITIVE gold for makes_it_a_dialogue: one reflective question ('how did that feel'), heavy engagement with the user's own words, real retry loop.",
                 turns=t1))

# ---------------------------------------------------------------------------
# 2. Retail sales supervisor — reflective Q mid-session (not first turn), sparing
# ---------------------------------------------------------------------------
t2 = opening("A retail sales supervisor role.") + """

Here's your first question: **"Tell me about yourself and why you're interested in this position."**
User: I've got about six years in retail, started as an associate and worked up to shift lead. What I like most is developing newer people — showing them how to close a sale or handle a tough customer. I'm ready to take on a supervisor role now.
AI: That's a strong open — the through-line from associate to shift lead to wanting supervisor tells a clear growth story, and "developing newer people" is a genuine supervisor skill. One small thing: you said you like showing people how to handle a tough customer. Can you give me a specific example of coaching someone through one?
User: Sure. A new hire froze when a customer was yelling about a return, so I stepped in beside her, calmed the customer, and afterward walked her through what to say next time.
AI: That's a great detail — stepping in *beside* her and then debriefing after is exactly what a supervisor does. Keep that example ready; it's better than any adjective. Next question: **"What's your biggest weakness?"**
User: I guess I take on too much myself instead of delegating. I just find it faster to do it.
AI: Honest and common for people who came up doing the work. The strongest version of this answer shows you're actively working on it. How do you think that went — do you feel like you landed the "and here's what I'm doing about it" part?
User: No, I kind of just admitted it and stopped.
AI: Right, that's the piece to add. You don't have to fix the weakness, just show movement. Given the delegating thing — what's one small way you've tried to hand things off?
User: I started assigning the closing checklist to whoever's on shift instead of doing it myself, and I check it after.
AI: Perfect — say exactly that. "I tend to over-own tasks, so I've started delegating the closing checklist and reviewing it after." Now it's a strength in disguise. Last one: **"Where do you see yourself in five years?"**
User: Running my own store, honestly. Store manager.
AI: I like the ambition, and it connects to the growth story you opened with. Tie it to this employer so it doesn't sound like you'll leave — how could you phrase it that way?
User: Maybe — in five years I'd like to be a store manager, ideally here, growing into it by proving myself as a supervisor first.
AI: That's it — ambitious but grounded in this role. You did real revising today, not just listening. Well done.
User: Appreciate it."""
ROWS.append(dict(name="SYNTH dialogue — retail supervisor", ceo="SYN-dialogue-02", persona="polished",
                 job="A retail sales supervisor role.",
                 focus="POSITIVE gold: reflective question placed mid-session (not turn 1), used ONCE, plus specific engagement with each answer.",
                 turns=t2))

# ---------------------------------------------------------------------------
# 3. Food service — reflective Q twice (start + near end), still not spammy
# ---------------------------------------------------------------------------
t3 = opening("A line cook position at a restaurant.") + """

Here's your first question: **"Tell me about yourself and why you're interested in this position."**
User: I've cooked before, mostly short-order stuff. I'm fast on the line and I keep my station clean. I want to get back into a kitchen.
AI: Good — "fast on the line" and "clean station" are two things every kitchen actually cares about. When you say you want to get *back* into a kitchen, how do you want an interviewer to hear that? What feels true to you about it?
User: I want them to hear that I know I've been out for a bit but I'm serious about it, not just looking for any job.
AI: Then let's make sure the answer says that. You can name the gap plainly and turn it into commitment: "I've been away from the line for a while, and I'm coming back because it's the work I'm best at." Want to fold that in and run the whole thing again?
User: Yeah. I'm a line cook — short-order background, fast on the line, I keep my station clean. I've been out of the kitchen for a bit, but I'm coming back because it's honestly the work I'm best at and I'm serious about it.
AI: That's a real upgrade — naming the gap with confidence beats hoping nobody asks. Next: **"How do you handle working under pressure?"**
User: The rush doesn't really bother me. I just lock in and go.
AI: I believe you, but "I just lock in" is hard for an interviewer to picture. Paint the rush for me — a Friday night, tickets stacking up. What do you actually do?
User: I read the whole rail first, fire the longest cook times first, and call out to the other cooks so we stay synced.
AI: That's chef-level thinking — reading the rail and firing by cook time is exactly the answer. Say that instead of "I lock in." Last question: **"Why should we hire you?"**
User: Because I'll show up and I won't slow the line down.
AI: Solid. Before I wrap up — how did that answer feel compared to your first one back at the start?
User: More confident, honestly. Earlier I was kind of downplaying myself.
AI: I noticed the same thing — you went from "I've cooked before" to talking like someone who owns the line. Carry that version into the real interview. Nice work.
User: Thank you, this was good practice."""
ROWS.append(dict(name="SYNTH dialogue — line cook", ceo="SYN-dialogue-03", persona="terse-warming",
                 job="A line cook position.",
                 focus="POSITIVE gold: TWO reflective questions (open + near close), spaced out so it's a genuine dialogue, not a tic; user visibly grows.",
                 turns=t3))

# ---------------------------------------------------------------------------
# 4. Office/admin — reflective Q once, engagement-heavy, participant pushes back
# ---------------------------------------------------------------------------
t4 = opening("An administrative assistant / front desk job.") + """

Here's your first question: **"Tell me about yourself and why you're interested in this position."**
User: I'm organized, I'm good with people, and I'm comfortable on a computer. I think I'd be good at front desk work.
AI: Those are the right three things for a front desk — organized, people-friendly, comfortable on a computer. Right now they're stated as traits, though. Which of the three feels most like *you* — the one you could tell a story about?
User: Probably good with people. I've always been the one who smooths things over.
AI: Then that's your anchor. "Smooths things over" is great — when's a time you did that at a desk or counter?
User: When I volunteered at a clinic front desk, patients would come in frustrated about wait times and I'd keep them calm and updated.
AI: That's a genuinely strong example — a frustrated person, and you kept them calm and informed. That IS front desk work. Lead with it. Next: **"Tell me about a time you made a mistake."**
User: Do I have to? I feel like that just makes me look bad.
AI: Fair pushback — and a lot of people feel that way. Here's why it isn't a trap: they're not testing whether you're perfect, they're testing whether you own things and learn. A small, honest mistake with a fix makes you look *more* trustworthy, not less. Got one that turned out okay in the end?
User: Okay — once I double-booked two appointments in the same slot. I caught it, called one patient to move them earlier, and started color-coding the calendar after that.
AI: That's a model answer — mistake, immediate fix, and a system so it never repeats. The color-coding is the detail that sells it. How did it feel to say that one out loud?
User: Better than I expected. It doesn't sound as bad when there's a fix attached.
AI: Exactly — the fix is the whole point. Last question: **"Why should we hire you?"**
User: Because I'll keep the front desk calm and organized, and I've done it before at the clinic.
AI: That's a clean, confident close — and it ties right back to your clinic story. You pushed back, then delivered a great answer anyway. That's the kind of composure a front desk needs. Well done.
User: Thanks, I actually feel ready now."""
ROWS.append(dict(name="SYNTH dialogue — front desk", ceo="SYN-dialogue-04", persona="guarded",
                 job="An administrative / front desk job.",
                 focus="POSITIVE gold: one reflective question after a hard answer; coach engages specifics AND handles the participant's pushback (still a two-way dialogue).",
                 turns=t4))

# ===========================================================================
# MATCHED NEAR-MISS NEGATIVES
# ---------------------------------------------------------------------------
# Same jobs/personas as the positives above, and the coach STILL engages the
# specifics of each answer and STILL runs a retry loop — the ONLY thing removed
# is the reflective question. This isolates the single variable the dimension
# turns on ("how did that feel?" / "how do you think that went?"), so the judge
# learns that content engagement alone is NOT dialogue: the reflective question
# is the required signal. Per dimensions.yaml this class is FAIL — it is exactly
# the corpus's real "nearest miss" (content follow-ups, never a reflective Q).
# ===========================================================================
NEG = []

# 1n. Warehouse — mirror of SYN-dialogue-01, no reflective question
n1 = opening("A warehouse associate job.") + """

Here's your first question: **"Tell me about yourself and why you're interested in this position."**
User: Uh, sure. So I've done warehouse work before, like loading trucks and pulling orders. I'm reliable, I show up on time, and I don't mind the physical stuff. I'm looking for something steady where I can stick around a while.
AI: Good start. You named three real strengths there — loading and order-pulling experience, reliability, and wanting something steady. To make "reliable" land, back it with a moment: think of one time being dependable actually mattered on a shift. Would you like to try answering again or move to the next question?
User: I'll try again. I've got a few years of warehouse experience — loading trucks, pulling orders. I'm reliable; there was a stretch where two coworkers quit and I picked up extra days so we still got every order out on time. Looking for something steady where I can commit.
AI: That's stronger — the covering-shifts detail makes "reliable" concrete. Let's move on. **"Tell me about a time you had to deal with a difficult coworker or customer."**
User: There was a guy on my crew who never pulled his weight. It got on my nerves but I didn't say anything, I just did my part.
AI: Interviewers listen here for what you did to address it, not just endure it. A stronger version would show you taking some action — talking to a lead, proposing a fix. Would you like to try again or move on?
User: I did eventually ask our lead to split the aisles so it was clearer who did what.
AI: That's the part to lead with — proposing to split the aisles shows initiative. Say it that way. Last question: **"Why should we hire you?"**
User: Because I work hard and I'll show up. You won't have to worry about me.
AI: Short and confident, which is good. To make it stick, tie it to your covering-shifts example — that's your proof of dependability. Consider closing with that. That wraps up our session. Nice work today.
User: Thanks."""
NEG.append(dict(name="SYNTH no-dialogue — warehouse", ceo="SYN-nodial-01", persona="steady",
                job="A warehouse associate job.",
                focus="NEGATIVE near-miss for makes_it_a_dialogue: engages specifics + runs a retry, but NEVER asks a reflective question. Fail.",
                turns=n1))

# 2n. Retail supervisor — mirror of SYN-dialogue-02, no reflective question
n2 = opening("A retail sales supervisor role.") + """

Here's your first question: **"Tell me about yourself and why you're interested in this position."**
User: I've got about six years in retail, started as an associate and worked up to shift lead. What I like most is developing newer people — showing them how to close a sale or handle a tough customer. I'm ready to take on a supervisor role now.
AI: Strong open — the associate-to-shift-lead-to-supervisor arc is a clear growth story, and "developing newer people" is a genuine supervisor skill. One thing to add: a specific example of coaching someone through a tough customer. Would you like to try again or move on?
User: Sure. A new hire froze when a customer was yelling about a return, so I stepped in beside her, calmed the customer, and afterward walked her through what to say next time.
AI: That's a great detail — stepping in beside her and debriefing after is exactly what a supervisor does. Keep it ready. Next question: **"What's your biggest weakness?"**
User: I guess I take on too much myself instead of delegating. I just find it faster to do it.
AI: Honest and common. The strongest version shows you're working on it — name one small way you've started handing things off. Want to try again or move on?
User: I started assigning the closing checklist to whoever's on shift instead of doing it myself, and I check it after.
AI: Perfect — say exactly that, and it becomes a strength in disguise. Last one: **"Where do you see yourself in five years?"**
User: Running my own store, honestly. Store manager.
AI: Good ambition, and it connects to your growth story. Tie it to this employer so it doesn't read as "I'll leave" — mention growing into it here. That's all my questions. Well done today.
User: Appreciate it."""
NEG.append(dict(name="SYNTH no-dialogue — retail supervisor", ceo="SYN-nodial-02", persona="polished",
                job="A retail sales supervisor role.",
                focus="NEGATIVE near-miss: rich content engagement + retries, zero reflective questions. Fail.",
                turns=n2))

# 3n. Line cook — mirror of SYN-dialogue-03, no reflective question
n3 = opening("A line cook position at a restaurant.") + """

Here's your first question: **"Tell me about yourself and why you're interested in this position."**
User: I've cooked before, mostly short-order stuff. I'm fast on the line and I keep my station clean. I want to get back into a kitchen.
AI: Good — "fast on the line" and "clean station" are two things every kitchen cares about. When you say you want to get back into a kitchen, name the gap plainly and turn it into commitment: "I've been away from the line for a while, and I'm coming back because it's the work I'm best at." Try that and run it again?
User: Yeah. I'm a line cook — short-order background, fast on the line, I keep my station clean. I've been out of the kitchen for a bit, but I'm coming back because it's honestly the work I'm best at and I'm serious about it.
AI: That's a real upgrade — naming the gap with confidence beats hoping nobody asks. Next: **"How do you handle working under pressure?"**
User: The rush doesn't really bother me. I just lock in and go.
AI: "I just lock in" is hard for an interviewer to picture. Paint the rush — a Friday night, tickets stacking up, what do you actually do? Would you like to try again or move on?
User: I read the whole rail first, fire the longest cook times first, and call out to the other cooks so we stay synced.
AI: That's chef-level thinking — reading the rail and firing by cook time is exactly the answer. Say that instead of "I lock in." Last question: **"Why should we hire you?"**
User: Because I'll show up and I won't slow the line down.
AI: Solid and confident. To make it stronger, tie it back to the reliability you showed in your opening. That's all my questions for today. Nice work.
User: Thank you."""
NEG.append(dict(name="SYNTH no-dialogue — line cook", ceo="SYN-nodial-03", persona="terse-warming",
                job="A line cook position.",
                focus="NEGATIVE near-miss: engages specifics + retry loop, no reflective question anywhere. Fail.",
                turns=n3))

# 4n. Front desk — mirror of SYN-dialogue-04, no reflective question
n4 = opening("An administrative assistant / front desk job.") + """

Here's your first question: **"Tell me about yourself and why you're interested in this position."**
User: I'm organized, I'm good with people, and I'm comfortable on a computer. I think I'd be good at front desk work.
AI: Those are the right three for a front desk. Right now they're stated as traits — pick the one you could tell a story about and lead with it. Would you like to try again or move on?
User: Probably good with people. When I volunteered at a clinic front desk, patients would come in frustrated about wait times and I'd keep them calm and updated.
AI: That's a genuinely strong example — a frustrated person, and you kept them calm and informed. That IS front desk work. Lead with it. Next: **"Tell me about a time you made a mistake."**
User: Do I have to? I feel like that just makes me look bad.
AI: It's not a trap — they're testing whether you own things and learn, not whether you're perfect. A small honest mistake with a fix makes you look more trustworthy. Got one that turned out okay?
User: Okay — once I double-booked two appointments in the same slot. I caught it, called one patient to move them earlier, and started color-coding the calendar after that.
AI: That's a model answer — mistake, immediate fix, and a system so it never repeats. The color-coding is the detail that sells it. Last question: **"Why should we hire you?"**
User: Because I'll keep the front desk calm and organized, and I've done it before at the clinic.
AI: Clean, confident close, and it ties right back to your clinic story. That's everything for today. Well done.
User: Thanks."""
NEG.append(dict(name="SYNTH no-dialogue — front desk", ceo="SYN-nodial-04", persona="guarded",
                job="An administrative / front desk job.",
                focus="NEGATIVE near-miss: specific engagement + handles pushback, still never asks a reflective question. Fail.",
                turns=n4))


# ===========================================================================
# TRICKY POSITIVES
# ---------------------------------------------------------------------------
# All genuine PASSes (>=1 reflective question that turns attention on the
# participant's OWN answer/experience + engagement with specifics), but each
# stresses a condition that makes the reflective question harder to recognize:
#   TP1  reflective question buried in heavy, disfluent STT (voice noise)
#   TP2  mostly-templated/efficient coach that asks EXACTLY ONE reflective Q
#        (superficially reads like the classic one-way fail)
#   TP3  reflective question phrased unusually (not the canonical wording)
#   TP4  the ONLY reflective question comes at the closing wrap-up
#   TP5  coach asks a reflective question; participant DEFLECTS it — still a
#        pass, since the dimension scores the coach's move, not the follow-through
# ===========================================================================
TRICKY = []

# TP1 — disfluent STT, reflective question buried mid-turn, merged/split turns
tp1 = opening("A warehouse and forklift operator job.") + """

Here's your first question: **"Tell me about yourself and why you're interested in this position."**
User: Uh yeah so I I've done warehouse a few years, I'm forklift certified, sit-down and and reach truck, and uh one time the the dock guy no-showed and I just I covered the whole dock myself that shift. I'm I'm looking for steady honestly.
AI: Okay, okay — good. Before I, before I even get into the feedback part, I'm I'm curious — how'd that, how did that feel to you, saying it out loud just now?
User: Kinda fast. I feel like I I rushed the forklift part.
AI: Yeah, and that's a good catch, 'cause the the forklift cert and covering the dock solo — that's, that's the strongest stuff you've got and you kind of blew past it. The no-show, you-cover-the-whole-dock moment, that's the one to slow down on. Wanna, wanna run it again and and land on that?
User: Sure. I've got a few years in the warehouse, I'm forklift certified on sit-down and reach truck. One time our dock lead no-showed and I covered the entire dock that shift so nothing shipped late. I'm looking for something steady.
AI: There it is — slowing down on the dock save makes "reliable" something I can see, not just a word. Next question: **"What are your greatest strengths?"**
User: I'd say I'm dependable and I don't need somebody watching me.
AI: Both good, and they fit the dock story you just told — you didn't wait to be told to cover, you just did. Tie that example to "dependable" and it's airtight. Good work today.
User: Appreciate it, this helped."""
TRICKY.append(dict(name="SYNTH tricky+ — buried STT reflective Q", ceo="SYN-tricky-01", persona="disfluent-voice",
                   job="A warehouse / forklift job.",
                   focus="TRICKY POSITIVE: reflective question ('how did that feel') buried in heavy disfluent STT + specifics engaged. Pass.",
                   turns=tp1))

# TP2 — mostly efficient/templated, EXACTLY ONE reflective question (minimal pass)
tp2 = opening("A delivery driver position.") + """

Here's your first question: **"Tell me about yourself and why you're interested in this position."**
User: I've driven for about three years, mostly local routes. I know the area well and I've got a clean record.
AI: Good. To strengthen it: 1) lead with the clean record, 2) name the route type, 3) tie it to reliability. Would you like to try again or move to the next question?
User: Move on.
AI: **"How do you handle tight delivery deadlines?"**
User: I plan my route the night before so I'm not scrambling, and I text dispatch early if something's off.
AI: How do you think that one went?
User: Honestly? Pretty good, I felt solid on that one.
AI: I'd agree — and here's why it worked where the first answer didn't: you gave a concrete habit, planning the route the night before and flagging dispatch early, instead of a general trait. That specific routine is exactly what a dispatcher wants to hear. Keep answering the rest like that one. Next: **"What's a weakness?"**
User: I can be a perfectionist about my truck being organized.
AI: Fair. Frame it as a strength you manage: 1) name it, 2) say how you keep it from slowing you down. Would you like to try again or move on?
User: Move on.
AI: **"Why should we hire you?"**
User: Because I'm reliable and I know the routes.
AI: Solid — and remember, your route-planning answer is the proof of "reliable," so lean on that. That's all my questions. Nice work.
User: Thanks."""
TRICKY.append(dict(name="SYNTH tricky+ — one reflective Q amid templated", ceo="SYN-tricky-02", persona="efficient",
                   job="A delivery driver position.",
                   focus="TRICKY POSITIVE: coach is mostly brisk/templated but asks ONE genuine reflective question and engages specifics on that turn. Pass by the 'at least one' bar.",
                   turns=tp2))

# TP3 — reflective question in unusual, non-canonical phrasing
tp3 = opening("A customer service representative role.") + """

Here's your first question: **"Tell me about yourself and why you're interested in this position."**
User: I've worked retail and a call center. I like helping people solve problems, and I stay calm when someone's upset.
AI: Nice — "I stay calm when someone's upset" is gold for customer service. Quick one before feedback: if you played that answer back to yourself, what's the one part you'd tighten?
User: Probably the retail and call center part, it sounded like a list.
AI: Exactly the instinct I'd have too. The calm-under-pressure piece is your headline; the job history is just support for it. Lead with the calm, back it with a call-center example. Want to try?
User: Sure. I'm someone who stays calm when a customer's upset — I learned that in a call center handling billing complaints, where I'd let people vent, then walk them to a fix. I genuinely like solving the problem.
AI: Much stronger — the billing-complaint detail makes "calm" concrete. Next: **"Tell me about a hard customer."**
User: A guy was furious about a late order. I apologized, found his order, and got it expedited same day.
AI: That's a clean example — apology, action, resolution, in one breath. That's the structure to reuse. Well done today.
User: Thank you."""
TRICKY.append(dict(name="SYNTH tricky+ — unusual reflective phrasing", ceo="SYN-tricky-03", persona="reflective",
                   job="A customer service role.",
                   focus="TRICKY POSITIVE: reflective question uses non-canonical wording ('if you played that back, what would you tighten?') — must be recognized by category, not keyword. Pass.",
                   turns=tp3))

# TP4 — the ONLY reflective question is at the closing wrap-up
tp4 = opening("A building maintenance / janitorial job.") + """

Here's your first question: **"Tell me about yourself and why you're interested in this position."**
User: I've done maintenance for years — plumbing fixes, painting, general upkeep. I take pride in a building that's kept up right.
AI: Good — "pride in a building kept up right" is a nice line, and the plumbing-and-painting range shows breadth. Add one specific repair you're proud of and it's stronger. Next: **"How do you prioritize when several things break at once?"**
User: Safety first — anything that's a hazard, like water or electrical, before cosmetic stuff.
AI: That's the right instinct, and naming hazard-before-cosmetic shows judgment. A supervisor hears that and trusts you unsupervised. Next: **"Tell me about a time you fixed something tricky."**
User: A recurring leak nobody could find — I traced it to a cracked pipe behind a wall and patched it before it caused damage.
AI: Strong — tracing the leak behind the wall is a real problem-solving story. Keep it. That's the last question — and before we wrap, let me ask: looking back over the three answers, how do you feel you did today?
User: Better than I expected, honestly. The leak one felt the strongest.
AI: I'd agree the leak story was your strongest — it had a problem, your action, and the outcome, which is exactly the shape interviewers want. Open every answer with that much specificity and you're set. Nice work.
User: Thanks, appreciate it."""
TRICKY.append(dict(name="SYNTH tricky+ — reflective Q only at wrap-up", ceo="SYN-tricky-04", persona="steady",
                   job="A maintenance / janitorial job.",
                   focus="TRICKY POSITIVE: session reads one-way until the closing turn, where the ONLY reflective question appears ('how do you feel you did today?') + specific engagement. Pass ('anywhere in the session').",
                   turns=tp4))

# TP5 — coach asks a reflective question; participant deflects it
tp5 = opening("A security guard position.") + """

Here's your first question: **"Tell me about yourself and why you're interested in this position."**
User: I've done security at a warehouse and an apartment complex. I'm observant, I stay alert on long shifts, and I don't panic.
AI: Good — "I don't panic" and staying alert on long shifts are exactly the traits for this. How do you think that answer went?
User: I don't know. Fine, I guess.
AI: Fair enough — I'll tell you what worked: the two settings, warehouse and apartment complex, plus "I don't panic," give a clear picture fast. What's missing is one moment that proves it. Was there ever a night something actually went wrong?
User: Yeah, once I caught someone trying to jump the fence and I called it in and kept eyes on him till police came.
AI: That's the story — caught it, called it in, maintained visual until police arrived. That single example does more than any adjective. Lead with it. Last question: **"Why should we hire you?"**
User: Because I'm reliable and I stay alert.
AI: Good, and now you've got the fence example to prove "alert" — use it. That's all my questions. Well done.
User: Thanks."""
TRICKY.append(dict(name="SYNTH tricky+ — participant deflects reflective Q", ceo="SYN-tricky-05", persona="terse",
                   job="A security guard position.",
                   focus="TRICKY POSITIVE: coach asks a reflective question, participant deflects ('I don't know, fine'), coach still engages specifics. Scores the COACH's move -> pass.",
                   turns=tp5))


# ===========================================================================
# TRICKY NEGATIVES
# ---------------------------------------------------------------------------
# All genuine FAILs, but each carries a surface feature that could fool a judge
# into scoring PASS. They pressure-test the FAIL line the way TRICKY pressured
# the PASS line:
#   TN1  a question IS asked of the participant, but it's a comprehension check
#        ("does that make sense?") — not reflection on their own answer
#   TN2  disfluent-STT content follow-up (mirror of TP1's STT noise) — the buried
#        question probes SUBSTANCE ("say more about the forklift part"), not reflection
#   TN3  real reflective questions ARE present, but the feedback NEVER engages the
#        specifics of what the participant said (all boilerplate) -> fails condition (b);
#        the mirror of TP2, and the key test that BOTH conditions are enforced
#   TN4  near-miss content-improvement question ("what else could you add?") — sits
#        right next to TP3's self-evaluative "what would you tighten?", but asks for
#        more CONTENT, not self-reflection
#   TN5  factual clarifying question ("was that at your last job?") — participant-
#        directed and question-shaped, but purely factual, not reflective
# ===========================================================================
TRICKY_NEG = []

# TN1 — comprehension check mistaken for a reflective question
tn1 = opening("A retail cashier position.") + """

Here's your first question: **"Tell me about yourself and why you're interested in this position."**
User: I've worked a register before, handled busy holiday rushes, and I'm good with cash and card and staying quick without messing up the drawer.
AI: Good — handling the holiday rush on register and keeping the drawer accurate are two things a store cares about. To make it land, name a number: how many transactions an hour, or a shift with no drawer discrepancy. Does that make sense?
User: Yeah.
AI: Great. Next question: **"How do you handle a rude customer?"**
User: I stay polite, I don't take it personal, and I get a manager if it escalates.
AI: That's the right approach, and "I don't take it personal" is a good line to keep. Add one quick example of a time you defused someone and it's stronger. You following me?
User: Got it.
AI: Perfect. Last question: **"Why should we hire you?"**
User: Because I'm fast, accurate, and I show up.
AI: Solid — tie "accurate" back to that no-discrepancy drawer point and it's proof, not just a claim. That's all my questions. Nice work.
User: Thanks."""
TRICKY_NEG.append(dict(name="SYNTH tricky- — comprehension check, not reflection", ceo="SYN-trickyneg-01", persona="steady",
                       job="A retail cashier position.",
                       focus="TRICKY NEGATIVE: coach engages specifics and DOES ask questions, but they are comprehension checks ('does that make sense?', 'you following me?'), not reflective questions. Fail.",
                       turns=tn1))

# TN2 — disfluent-STT content follow-up (mirror of TP1, but the question probes substance)
tn2 = opening("A warehouse and forklift operator job.") + """

Here's your first question: **"Tell me about yourself and why you're interested in this position."**
User: Uh yeah I've I've done warehouse a few years, forklift certified, and and one time the dock guy no-showed and I covered the dock that that shift. Looking for steady.
AI: Okay, okay, good — so, can you, can you say a bit more about the the forklift part? Like what what were you certified on, sit-down, reach truck?
User: Both, sit-down and reach. And a pallet jack, electric one.
AI: Nice, so that's, that's the stuff to lead with, the sit-down and reach certs plus covering the dock solo — that shows range and reliability. Work those into the opening. Next question: **"What are your greatest strengths?"**
User: Dependable, and I don't need somebody on me.
AI: Both good, and they fit the dock story — you didn't wait to be told, you just covered it. Tie the example to "dependable" and it's airtight. Good work today.
User: Appreciate it."""
TRICKY_NEG.append(dict(name="SYNTH tricky- — STT content follow-up, not reflection", ceo="SYN-trickyneg-02", persona="disfluent-voice",
                       job="A warehouse / forklift job.",
                       focus="TRICKY NEGATIVE: heavy STT + a buried question, but the question is a CONTENT follow-up ('say more about the forklift part') probing substance, not reflection. Fail (mirror of TP1).",
                       turns=tn2))

# TN3 — reflective questions ARE present, but zero engagement with specifics (all boilerplate)
tn3 = opening("A general customer service role.") + """

Here's your first question: **"Tell me about yourself and why you're interested in this position."**
User: I worked at a call center handling billing complaints, and I stay calm when people are upset. I like fixing the problem.
AI: Good start. How do you think that went?
User: Okay I guess.
AI: Here's how to improve any answer like this: 1) structure it clearly, 2) add a specific example, 3) connect it to the role. Would you like to try again or move to the next question?
User: Move on.
AI: **"How do you handle a hard customer?"**
User: I let them vent, then I walk them to a solution.
AI: How did that feel to answer?
User: Fine.
AI: To strengthen it: 1) describe the situation, 2) explain your action, 3) state the result. Structuring your answer that way makes it more impactful. Would you like to try again or move on?
User: Move on.
AI: **"Why should we hire you?"**
User: Because I'm calm and I solve problems.
AI: How do you think you did on that one?
User: Good.
AI: Good answers come from specifics and structure — keep practicing the situation-action-result format. That's all my questions. Nice work.
User: Thanks."""
TRICKY_NEG.append(dict(name="SYNTH tricky- — reflective Qs but no engagement", ceo="SYN-trickyneg-03", persona="efficient",
                       job="A customer service role.",
                       focus="TRICKY NEGATIVE (highest value): coach asks THREE genuine reflective questions, but every feedback turn is generic template advice that never uses the participant's actual content. Fails condition (b) — the 'ONLY reflective questions, no substantive engagement' fail mode. Fail.",
                       turns=tn3))

# TN4 — near-miss content-improvement question (asks for MORE content, not self-reflection)
tn4 = opening("An administrative assistant role.") + """

Here's your first question: **"Tell me about yourself and why you're interested in this position."**
User: I'm organized, good with scheduling, and comfortable with spreadsheets. I kept the calendar for a busy office before.
AI: Good — keeping the calendar for a busy office is a concrete, relevant detail. What else could you add there to make it stronger?
User: Maybe that I handled travel booking too, and answered the main phone line.
AI: Yes — travel booking and the phone line round it out nicely; add those and you've got a full picture of the role. Next question: **"Tell me about a time you juggled competing priorities."**
User: I had two managers needing things the same afternoon, so I checked which was time-sensitive and communicated a realistic timeline to both.
AI: That's a strong example — triaging by deadline and setting expectations with both managers is exactly right. What could you add to make the outcome clearer?
User: Both got what they needed on time, and neither felt ignored.
AI: Perfect close — the outcome makes it land. Keep that structure. That's all my questions. Well done.
User: Thanks."""
TRICKY_NEG.append(dict(name="SYNTH tricky- — content-add question, not reflection", ceo="SYN-trickyneg-04", persona="polished",
                       job="An administrative assistant role.",
                       focus="TRICKY NEGATIVE: coach engages specifics and asks the participant questions, but they ask for MORE CONTENT ('what else could you add?') — a content follow-up, not self-reflection. Sits right next to TP3's 'what would you tighten?'. Fail.",
                       turns=tn4))

# TN5 — factual clarifying question (participant-directed, question-shaped, purely factual)
tn5 = opening("A landscaping / groundskeeping job.") + """

Here's your first question: **"Tell me about yourself and why you're interested in this position."**
User: I've done landscaping, mowing, planting, some irrigation repair. I like outdoor work and I take pride in a yard looking sharp.
AI: Good — the range from mowing to irrigation repair shows you're not just a mower, and "pride in a yard looking sharp" is a nice line. Was the irrigation work at your last job or an earlier one?
User: Earlier one, a golf course.
AI: A golf course is worth naming — that signals higher-standard grounds work. Lead with the irrigation-on-a-golf-course detail. Next question: **"How do you handle physically demanding days?"**
User: I pace myself, hydrate, and keep a steady rhythm so I don't burn out by afternoon.
AI: That's a mature answer — pacing and hydration show you can sustain a full day, which is exactly what grounds crews need. Keep it. That's all my questions. Nice work.
User: Appreciate it."""
TRICKY_NEG.append(dict(name="SYNTH tricky- — factual clarifier, not reflection", ceo="SYN-trickyneg-05", persona="steady",
                       job="A landscaping job.",
                       focus="TRICKY NEGATIVE: coach engages specifics and asks the participant a direct question, but it's a FACTUAL clarifier ('was that at your last job?'), not reflection on their answer/experience. Fail.",
                       turns=tn5))


# ---------------------------------------------------------------------------
# Write TSVs in sim_calls.tsv column shape
# ---------------------------------------------------------------------------
COLS = ["Assistant Name", "CEO ID", "Persona", "Target Job", "Eval Focus",
        "Turns", "Stop Reason", "Transcript"]


def write_tsv(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(COLS)
        for r in rows:
            turns = r["turns"].count("\nUser:") + r["turns"].count("\nAI:")
            w.writerow([r["name"], r["ceo"], r["persona"], r["job"], r["focus"],
                        turns, "completed", r["turns"]])


write_tsv("synthetic_makes_it_a_dialogue.tsv", ROWS)
write_tsv("synthetic_makes_it_a_dialogue_negatives.tsv", NEG)
write_tsv("synthetic_makes_it_a_dialogue_tricky.tsv", TRICKY)
write_tsv("synthetic_makes_it_a_dialogue_tricky_negatives.tsv", TRICKY_NEG)

REFLECTIVE_MARKERS = ["how did that feel", "how do you think that went", "how did it feel",
                      "how did that answer feel", "what feels true",
                      "how do you want an interviewer to hear"]


def count_reflective(text):
    t = text.lower()
    return sum(t.count(m) for m in REFLECTIVE_MARKERS)


print(f"POSITIVES -> synthetic_makes_it_a_dialogue.tsv ({len(ROWS)})")
for r in ROWS:
    print(f"  {r['ceo']}: ~{count_reflective(r['turns'])} reflective question(s)  [expect >=1]")
print(f"NEGATIVES -> synthetic_makes_it_a_dialogue_negatives.tsv ({len(NEG)})")
for r in NEG:
    print(f"  {r['ceo']}: ~{count_reflective(r['turns'])} reflective question(s)  [expect 0]")
print(f"TRICKY POSITIVES -> synthetic_makes_it_a_dialogue_tricky.tsv ({len(TRICKY)})")
for r in TRICKY:
    # note: TP3's reflective Q uses non-canonical wording not in REFLECTIVE_MARKERS,
    # so a 0 here is expected for that row — the marker count is a sanity aid, not the label.
    print(f"  {r['ceo']}: ~{count_reflective(r['turns'])} canonical-marker hit(s)  [genuine reflective Q present by design]")
print(f"TRICKY NEGATIVES -> synthetic_makes_it_a_dialogue_tricky_negatives.tsv ({len(TRICKY_NEG)})")
for r in TRICKY_NEG:
    # TN3 deliberately CONTAINS canonical reflective markers but still FAILs (no engagement),
    # so a >0 here is expected for that row — presence of the phrase is not the label.
    print(f"  {r['ceo']}: ~{count_reflective(r['turns'])} canonical-marker hit(s)  [genuine FAIL by design]")
