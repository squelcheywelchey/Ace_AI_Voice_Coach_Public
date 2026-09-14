"""Score the AI Voice Coach against the V1 Call Rubric (LLM-as-judge).

For each transcript (column E of the TSV), an LLM judge scores the COACH (the
"AI:" turns) on every rubric criterion (1-4 / N/A), sets failure-mode flags
(over-complimentary, bad feedback, no practice, coach stuck, PII breach), gives
an overall quality label, and supplies supporting quotes.

The rubric is the RUBRIC list below (transcribed from
AI_Voice_Coach_Call_Rubric_V1.xlsx) — edit it to change what gets scored; the
prompt and output schema are generated from it.

Results append to coach_eval.jsonl (one JSON per line). Runs are parallel and
resumable: rows already in the output file are skipped.

Usage:
    python analyze.py                       # sample (default 5) of the PCPT file
    python analyze.py --limit 50
    python analyze.py --all --yes --workers 8     # whole file, parallel, no prompt
    python analyze.py --file "Output - Participant training assistants - Cleaned Data All.tsv"

Key from .env (ANTHROPIC_API_KEY).
"""

import argparse
import csv
import json
import sys
import threading
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Literal

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, Field, create_model

load_dotenv()
csv.field_size_limit(10**7)

MODEL = "claude-opus-4-8"
DEFAULT_FILE = "pcpt_mock_interview_v2.tsv"
TRANSCRIPT_COL = "Transcript"
OUTPUT_FILE = "coach_eval.jsonl"

SECTIONS = {
    "A": "Meeting the participant where they're at",
    "B": "Social-emotional awareness",
    "C": "Motivates skill development",
    "D": "Voice & conversation design (phone-specific)",
    "E": "Prompt adherence & technical",
    "F": "Did the coach elicit good answers from the participant?",
}

# (section, id, name, proficient anchor, red-flag anchor)
RUBRIC = [
    ("A", "assesses_starting_level", "Assesses starting level",
     "Opens by asking about the participant's experience, target job, and confidence.",
     "Launches into mock questions cold; never asks what they want to work on."),
    ("A", "builds_on_what_they_share", "Builds on what they share",
     "Uses details the participant says aloud to shape the session.",
     "Ignores what they offer; runs a fixed script regardless."),
    ("A", "tailors_content_difficulty", "Tailors content & difficulty",
     "Adjusts mock questions to their level, goals, and target role.",
     "Generic questions unrelated to the participant's actual target job."),
    ("A", "calibrates_spoken_language", "Calibrates spoken language",
     "Plain, concrete words; no jargon; easy to follow by ear.",
     "Jargon, abstract wording, or sentences too long to track in audio."),
    ("A", "pitches_right_challenge", "Pitches the right challenge",
     "Questions stretch the participant a little without overwhelming them.",
     "So easy it's pointless, or so hard they freeze and disengage."),
    ("A", "reassesses_from_audio_cues", "Re-assesses from audio cues",
     "Picks up on hesitation, pauses, flat or tense tone and adjusts in the moment.",
     "Plows ahead on the original plan despite clear strain in the voice."),
    ("A", "scaffolds_then_fades", "Scaffolds, then fades support",
     "Offers a model answer or sentence-starter, then hands it back to try alone.",
     "Either answers for them or gives no help at all."),
    ("A", "confirms_understanding", "Confirms understanding aloud",
     "Asks the participant to recap/restate; treats a vague 'uh, yeah' as a cue to check again.",
     "Assumes it landed and moves on; mistakes silence for agreement."),
    ("A", "recalls_within_call", "Recalls within the call",
     "Refers back to things said earlier in the call so the participant feels heard.",
     "Forgets earlier answers; the participant has to repeat themselves."),

    ("B", "adapts_when_stuck", "Adapts when stuck or frustrated",
     "Hears short answers/sighs/'this is pointless' and switches approach.",
     "Keeps pushing the same question; ignores audible frustration."),
    ("B", "compassion_for_nerves", "Compassion for nerves",
     "Names nervousness as normal, slows the pace, lowers the stakes, allows restarts.",
     "Treats nerves as a flaw; rushes or pressures the participant."),
    ("B", "honest_but_kind", "Honest-but-kind feedback",
     "Truthful about what isn't working, tied to a specific moment, paired with a fix.",
     "Vague or falsely positive, or blunt in a way that deflates."),
    ("B", "supportive_encouraging", "Supportive & encouraging",
     "Warm tone, celebrates small wins, ends on a genuine strength.",
     "Focuses only on faults; tone feels cold or like a test."),
    ("B", "active_listening", "Active listening (audio)",
     "Reflects back what it heard, doesn't talk over, leaves space, follows hesitation gently.",
     "Interrupts, talks over, steers to a script, or fills every silence."),
    ("B", "recovers_focus", "Recovers participant focus after derailment",
     "When the participant loses the thread, acknowledges it lightly and re-orients them.",
     "Ignores the derailment, overcorrects, or lets the participant spiral."),
    ("B", "reentry_appropriate_framing", "Reentry-appropriate framing",
     "Redirects oversharing toward interview-relevant content without making them feel judged.",
     "Centers the participant's past/legal details, or encourages oversharing of them."),

    ("C", "anchors_to_audible_behavior", "Anchors to audible behavior",
     "Targets fixable spoken behaviors ('your voice trailed off', 'a lot of ums'), not the person.",
     "Judges who they are ('you sound unconfident') instead of what they did."),
    ("C", "concrete_actionable", "Concrete & actionable",
     "Each suggestion is a specific next move they can try on the spot.",
     "Vague advice ('be more confident') with nothing to act on."),
    ("C", "limits_the_load", "Limits the load",
     "Focuses on one to three changes for the participant to take away.",
     "Lists many corrections at once; nothing is retainable."),
    ("C", "feedback_is_correct", "Feedback is correct",
     "Guidance is accurate and reflects what helps in real interviews; no over-praising weak answers.",
     "Advice is wrong, outdated, or counterproductive."),
    ("C", "makes_it_a_dialogue", "Makes it a dialogue",
     "Asks 'how did that feel?' before giving its read; feedback feels collaborative.",
     "Delivers verdicts top-down; the participant stays passive."),
    ("C", "drives_practice_uptake", "Drives practice & uptake",
     "Gets the participant to redo the answer and incorporate feedback; improvement is audible across attempts.",
     "Gives feedback but never has them try again."),
    ("C", "frames_progress", "Frames progress as distance traveled",
     "Notes improvement from the first attempt to later ones to reinforce that effort works.",
     "Only points out how far short they fall."),

    ("D", "response_length_pacing", "Response length & pacing",
     "Short, digestible spoken turns; makes one point at a time.",
     "Long, dense replies that are hard to follow by ear and bury the point."),
    ("D", "turn_taking", "Turn-taking & interruptions",
     "Lets the participant finish; if barged in on, yields gracefully.",
     "Talks over the participant, cuts them off, or steamrolls pauses."),
    ("D", "natural_pace_pauses", "Natural pace & pauses",
     "Comfortable speaking rate; leaves silence for the participant to think.",
     "Rushes, or fills every pause so the participant has no room."),
    ("D", "conversational_flow", "Conversational flow",
     "Replies are timely and on-topic; the exchange feels like a real conversation.",
     "Non-sequiturs, repeated lines, or replies that don't fit what was said."),
    ("D", "handles_mishearing", "Handles mishearing gracefully",
     "When it mishears, asks the participant to repeat rather than guessing; recovers without derailing.",
     "Charges ahead on a misheard answer; gets stuck in a loop or confuses the participant."),
    ("D", "verbal_structure", "Verbal structure & signposting",
     "Frames the session at the start, signals transitions ('let's try one more'), recaps aloud.",
     "No structure; the participant can't tell where they are or what's next."),
    ("D", "stays_voice_appropriate", "Stays voice-appropriate",
     "Coaches only what's audible (tone, pace, filler words, clarity, energy).",
     "Tries to assess or coach body language it cannot actually hear."),

    ("E", "efficiency", "Efficiency",
     "Economical turns; no redundant re-prompting or bloated responses; acceptable latency.",
     "Verbose or redundant exchanges that add cost/lag without adding value."),
    ("E", "quality_conversational_flow", "Quality of conversational flow (technical)",
     "Holds context across turns, resolves the issue, keeps moving without circling; coherent throughout.",
     "Loses context, repeats itself, circles without progress, or leaves issues unresolved."),
    ("E", "scripted_questions", "Covers the scripted questions",
     "Covers the 8 scripted questions.",
     "Retries the same question more than twice, drifts off-topic, or runs the list rigidly without adapting."),
    ("E", "handles_derailment_technical", "Handles conversational derailment",
     "When fully off-script, steers back cleanly without being abrupt or losing the thread.",
     "Gets pulled along and loses structure, or redirects so abruptly it feels like a reset."),

    ("F", "elicits_specific_examples", "Elicits specific examples",
     "Participant backs claims with concrete instances; most answers have a 'for example' moment.",
     "Examples appear only when prompted, or claims stay abstract and unsupported."),
    ("F", "elicits_appropriate_details", "Elicits appropriate personal detail",
     "Personal details shared only where relevant to the role, framed professionally.",
     "Drifts into private/irrelevant disclosure, or so little that answers feel generic."),
    ("F", "elicits_elaboration", "Elicits elaboration",
     "Answers go beyond one line (2-4 sentences) with enough context to understand the point.",
     "One-word/one-line answers; the coach has to keep pulling for more."),
    ("F", "elicits_authentic_voice", "Elicits authentic voice",
     "Participant speaks in their own natural words from real experience.",
     "Leans on clichés or rehearsed lines."),
    ("F", "elicits_confidence", "Elicits confidence",
     "Participant delivers in a steady voice and commits without excessive hedging.",
     "Frequent self-undercutting, trailing off, or hedging."),
    ("F", "elicits_clarity", "Elicits clarity",
     "Each answer is easy to follow on first listen; filler stays minimal.",
     "Rambling, tangents, or fragments that obscure the point."),
]

# Failure-mode flags (separate from rubric scores — for fast category filtering).
FLAGS = [
    ("over_complimentary", "Coach praised weak/empty answers or inflated without honest critique."),
    ("bad_feedback", "Coach's feedback was wrong, vague, generic, or unhelpful."),
    ("participant_did_not_practice", "Coach never got the participant to actually practice or redo an answer."),
    ("coach_got_stuck", "Coach looped, repeated itself, misunderstood, broke, or derailed."),
    ("pii_breach", "REAL PII mishandled: the coach revealed or echoed the participant's name, home address, "
                   "phone number, SSN/date of birth, or specific identifying legal/case details, OR solicited "
                   "or failed to redirect such a disclosure. IMPORTANT: do NOT flag the routine CEO ID number "
                   "readback/confirmation during identity verification ('I heard your CEO ID as ...') — echoing "
                   "the CEO ID is an expected, by-design verification step and is NOT a breach."),
]

# Coach value-add lens: does the coach BUILD a struggling participant, vs. just
# riding an already-strong one? Growth = skill/confidence-building coach behaviors;
# baseline = the participant's own answer quality (Section F).
GROWTH_DIMS = ["drives_practice_uptake", "frames_progress", "scaffolds_then_fades", "adapts_when_stuck",
               "compassion_for_nerves", "supportive_encouraging", "recovers_focus", "makes_it_a_dialogue",
               "honest_but_kind"]
BASELINE_DIMS = [cid for sec, cid, *_ in RUBRIC if sec == "F"]


def _mean_scores(rec: dict, keys) -> "float | None":
    vals = [int(rec[k]) for k in keys if rec.get(k) not in (None, "N/A")]
    return sum(vals) / len(vals) if vals else None


def value_add(rec: dict):
    """Coach growth minus participant baseline. High = coach lifted a weak participant."""
    g = _mean_scores(rec, GROWTH_DIMS)
    b = _mean_scores(rec, BASELINE_DIMS)
    return None if (g is None or b is None) else round(g - b, 2)


def is_value_add_candidate(rec: dict) -> bool:
    """Weak participant baseline AND the coach drove real practice or named progress."""
    b = _mean_scores(rec, BASELINE_DIMS)
    if b is None or b > 2.5:
        return False
    dpu, fp = rec.get("drives_practice_uptake"), rec.get("frames_progress")
    built = (dpu not in (None, "N/A") and int(dpu) >= 3) or (fp not in (None, "N/A") and int(fp) >= 3)
    return built


ScoreLit = Literal["1", "2", "3", "4", "N/A"]
_print_lock = threading.Lock()
_file_lock = threading.Lock()


def build_rubric_text() -> str:
    lines = []
    for letter, title in SECTIONS.items():
        lines.append(f"\n{letter}. {title}")
        for sec, cid, name, proficient, red in RUBRIC:
            if sec == letter:
                lines.append(f"  - {cid} — {name}\n      proficient: {proficient}\n      red flag: {red}")
    return "\n".join(lines)


def build_flags_text() -> str:
    return "\n".join(f"  - {fid}: {desc}" for fid, desc in FLAGS)


SYSTEM_PROMPT = f"""\
You are an expert evaluator (LLM-as-judge) scoring an AI job-interview coach
against a call-evaluation rubric.

Context: "CEO" is the Center for Employment Opportunities, a reentry-employment
nonprofit. Participants call an AI Voice Coach by phone to practice mock
interviews. In the transcript, "AI:" is the coach and "User:" is the
participant. Score the COACH — the "AI:" turns. (Section F scores how well the
coach drew good answers out of the participant.)

This is a voice-only transcript: judge only what is audible/textual, not visual.
Be a calibrated, skeptical judge — do NOT inflate. Use the 1-4 scale:
  4 = Exemplary (consistent and skillful — a model example)
  3 = Proficient (reliably demonstrated; meets the standard)
  2 = Developing (inconsistent or partial; emerging but not reliable)
  1 = Needs attention (rarely shown, absent, or worked against the participant)
  N/A = no opportunity to observe this behavior on this call

Score EVERY criterion. For each criterion you score 1 or 2, add a red_flags
entry with the criterion id and a short supporting quote.

Also set these boolean failure-mode flags (true only if clearly present), and
add a flag_evidence entry (flag id + short quote) for each one set true:
{build_flags_text()}

Give an overall quality label:
  - strong: a clearly good session that scores well across multiple important
    dimensions — worth holding up as a positive example
  - weak: clear problems against the rubric / one or more failure-mode flags
  - edge_case: unusual or interesting (very short, off-the-rails, broken,
    ambiguous, or novel behavior) — worth a human look regardless of good/bad

RUBRIC:
{build_rubric_text()}"""


class RedFlag(BaseModel):
    criterion: str = Field(description="The criterion id that was scored 1 or 2.")
    quote: str = Field(description="A short quote (label AI/User) showing the problem.")


class FlagEvidence(BaseModel):
    flag: str = Field(description="The failure-mode flag id that was set true.")
    quote: str = Field(description="A short quote (label AI/User) supporting the flag.")


# Build the output model dynamically from the rubric + flags.
_fields = {
    "overall_quality": (Literal["strong", "weak", "edge_case"], Field(description="Overall triage label.")),
    "summary": (str, Field(description="2-3 sentences on the coach's overall performance (note why if edge_case).")),
}
for _fid, _desc in FLAGS:
    _fields[_fid] = (bool, Field(description=_desc))
for _sec, _cid, _name, _prof, _red in RUBRIC:
    _fields[_cid] = (ScoreLit, Field(description=_name))
_fields["red_flags"] = (list[RedFlag], Field(description="One entry per criterion scored 1 or 2, with a quote."))
_fields["flag_evidence"] = (list[FlagEvidence], Field(description="One entry per failure-mode flag set true, with a quote."))
CoachScore = create_model("CoachScore", **_fields)


def load_rows(tsv_path: Path):
    with open(tsv_path, newline="", encoding="utf-8") as fh:
        for i, row in enumerate(csv.DictReader(fh, delimiter="\t")):
            transcript = (row.get(TRANSCRIPT_COL) or "").strip()
            if transcript:
                yield i, row, transcript


def already_done(path: Path) -> set:
    done = set()
    if path.exists():
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        done.add(json.loads(line)["row"])
                    except Exception:
                        pass
    return done


def evaluate(client: anthropic.Anthropic, transcript: str):
    response = client.messages.parse(
        model=MODEL,
        max_tokens=5000,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Score the coach in this session:\n\n<transcript>\n{transcript}\n</transcript>",
        }],
        output_format=CoachScore,
    )
    return response.parsed_output


def main() -> None:
    parser = argparse.ArgumentParser(description="Score the AI Voice Coach against the V1 rubric.")
    parser.add_argument("--file", default=DEFAULT_FILE)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--all", action="store_true", help="Score every row (confirms first unless --yes).")
    parser.add_argument("--workers", type=int, default=8, help="Parallel judge calls (default 8).")
    parser.add_argument("--yes", action="store_true", help="Skip the cost confirmation (for background runs).")
    args = parser.parse_args()

    tsv_path = Path(args.file)
    if not tsv_path.exists():
        print(f"File not found: {tsv_path}")
        sys.exit(1)

    out_path = Path(OUTPUT_FILE)
    done = already_done(out_path)
    rows = [r for r in load_rows(tsv_path) if r[0] not in done]
    if not args.all:
        rows = rows[: args.limit]

    if not rows:
        print("Nothing to do (all selected rows already scored).")
        return

    if args.all and not args.yes and sys.stdin.isatty():
        ans = input(f"About to score {len(rows)} transcripts (~${len(rows) * 0.05:.0f}). Continue? [y/N] ")
        if ans.strip().lower() != "y":
            print("Cancelled.")
            sys.exit(0)

    if done:
        print(f"Resuming — {len(done)} already scored, {len(rows)} to go.")
    print(f"Scoring {len(rows)} transcripts with {args.workers} workers...")

    client = anthropic.Anthropic(max_retries=5)
    quality_counts: Counter = Counter()
    flag_counts: Counter = Counter()
    score_sums: dict = defaultdict(lambda: [0, 0])
    completed = 0
    total = len(rows)

    def work(item):
        idx, row, transcript = item
        ev = evaluate(client, transcript)
        return idx, row.get("CEO ID", "?"), ev.model_dump()

    with open(out_path, "a", encoding="utf-8") as out, \
            ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(work, item): item[0] for item in rows}
        for fut in as_completed(futures):
            idx = futures[fut]
            try:
                idx, ceo_id, data = fut.result()
            except anthropic.AuthenticationError:
                print("Auth failed — check ANTHROPIC_API_KEY in .env.")
                sys.exit(1)
            except Exception as e:
                with _print_lock:
                    print(f"  ! row {idx} failed: {type(e).__name__}: {e}")
                continue

            with _file_lock:
                out.write(json.dumps({"row": idx, "ceo_id": ceo_id, **data}) + "\n")
                out.flush()

            quality_counts[data["overall_quality"]] += 1
            on_flags = [fid for fid, _ in FLAGS if data.get(fid)]
            for fid in on_flags:
                flag_counts[fid] += 1
            for _sec, cid, *_ in RUBRIC:
                if data.get(cid) not in (None, "N/A"):
                    score_sums[cid][0] += int(data[cid])
                    score_sums[cid][1] += 1

            completed += 1
            with _print_lock:
                tag = ",".join(on_flags) if on_flags else "-"
                print(f"[{completed}/{total}] row {idx} CEO {ceo_id} · {data['overall_quality']:<9} flags={tag}")

    print(f"\n{'=' * 72}\nDONE — {completed} scored")
    print("  quality:", dict(quality_counts))
    print("  flags:", dict(flag_counts) or "none")
    means = sorted(((s / n, cid, n) for cid, (s, n) in score_sums.items() if n), key=lambda x: x[0])
    print("\n  weakest dimensions (mean, low = worse):")
    for mean, cid, n in means[:10]:
        print(f"      {mean:.2f}  {cid}  (n={n})")
    print(f"\n  appended to {OUTPUT_FILE}  →  run:  python summarize.py")


if __name__ == "__main__":
    main()
