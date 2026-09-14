"""Run persona-vs-coach text simulations against the AI Voice Coach (Vapi).

Drives a two-session Vapi /chat loop: the coach assistant (under test) and a
persona assistant (a synthetic CEO participant from personas.py) take turns. The
coach's turns become "AI:" lines and the persona's become "User:" lines — the
exact transcript format analyze.py expects — so the output drops straight into
the existing judge:

    python simulate.py                      # all personas, one run each
    python simulate.py --persona terse --runs 3
    python simulate.py --max-turns 30 --out sim_calls.tsv
    python simulate.py --dry-run            # validate setup, no API calls
    # then score the synthetic calls with the existing judge:
    python analyze.py --file sim_calls.tsv

Needs in .env:  VAPI_PRIVATE_KEY, VAPI_COACH_ASSISTANT_ID.
Persona assistant ids come from vapi_personas.json (see vapi_setup.py).

Caveat: this is a TEXT loop. It stress-tests CONTENT behaviors (over-praise,
vague feedback, redirecting/PII, the no-practice-loop, getting stuck). It does
NOT exercise the phone-specific / audible-delivery rubric dimensions (Section D,
anchors_to_audible_behavior) — those need a real voice test.
"""

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

from personas import PERSONAS, PERSONAS_BY_KEY

load_dotenv()

API_BASE = "https://api.vapi.ai"
PERSONA_FILE = Path("vapi_personas.json")
DEFAULT_OUT = "sim_calls.tsv"
END_TOKEN = "<END_CALL>"
SEED_INPUT = "Hello?"   # nudge to elicit the coach's opening greeting

# Coach session-CLOSE cues only — a BACKSTOP. The persona's <END_CALL> is the
# primary end signal. Deliberately does NOT match per-question score lines
# ("Score: 3 out of 5"), which fire after every step-by-step answer and must
# never end the call.
END_PATTERNS = [
    r"\bgood ?bye\b", r"\btake care\b", r"\bbest of luck\b",
    r"\bhave a (great|good|wonderful) (day|one)\b",
    r"\bthis (concludes|wraps up) (our|the|your)\b",
    r"\bthanks? (for|so much for) practic",
]
_END_RE = re.compile("|".join(END_PATTERNS), re.IGNORECASE)


def _require(var: str) -> str:
    val = os.environ.get(var, "").strip()
    if not val:
        print(f"{var} is not set. Add it to .env (see .env.example).")
        sys.exit(1)
    return val


def load_persona_ids() -> dict:
    if not PERSONA_FILE.exists():
        print(f"{PERSONA_FILE} not found. Create persona assistants first:\n"
              "    python vapi_setup.py --create")
        sys.exit(1)
    return json.loads(PERSONA_FILE.read_text())


def vapi_request(path: str, key: str, payload: dict) -> dict:
    resp = requests.post(
        f"{API_BASE}{path}",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    if not resp.ok:
        raise RuntimeError(f"Vapi POST {path} -> {resp.status_code}: {resp.text[:400]}")
    return resp.json() if resp.text else {}


def open_session(key: str, assistant_id: str, name: str) -> str:
    """Create a Vapi session for an assistant; return its id (holds conversation state)."""
    data = vapi_request("/session", key, {"assistantId": assistant_id, "name": name})
    return data["id"]


def extract_text(resp: dict) -> str:
    """Pull only the assistant's SPOKEN reply out of a /chat response.

    Vapi returns tool-call carriers (role=assistant, content=None) and tool
    results (role=tool, content=<raw JSON/error>) in the same output list. We
    keep only role=assistant messages with real text, so tool noise never lands
    in the transcript.
    """
    parts = []
    for msg in resp.get("output") or resp.get("messages") or []:
        if not isinstance(msg, dict) or msg.get("role") != "assistant":
            continue
        content = msg.get("content")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):  # content may be a list of {type,text} parts
            parts.extend(p.get("text", "") for p in content if isinstance(p, dict))
    return "\n".join(p for p in parts if p).strip()


def say(key: str, session_id: str, text: str) -> str:
    """Send `text` into a session and return the assistant's reply."""
    resp = vapi_request("/chat", key, {"sessionId": session_id, "input": text})
    return extract_text(resp)


def coach_name(key: str, coach_id: str) -> str:
    """Best-effort human name for a coach assistant id (for the Coach Name column)."""
    try:
        resp = requests.get(
            f"{API_BASE}/assistant/{coach_id}",
            headers={"Authorization": f"Bearer {key}"}, timeout=30)
        resp.raise_for_status()
        return resp.json().get("name", "") or coach_id[:8]
    except Exception:
        return coach_id[:8]


def run_one(key: str, coach_id: str, cname: str, persona: dict, persona_id: str, max_turns: int) -> dict:
    """Run a single coach<->persona conversation; return a transcript row."""
    coach_session = open_session(key, coach_id, f"coach-{persona['key']}")
    persona_session = open_session(key, persona_id, f"persona-{persona['key']}")

    turns: list[tuple[str, str]] = []
    stop_reason = "max_turns"

    # Bootstrap: get the coach's opening greeting, then let the persona respond.
    coach_text = say(key, coach_session, SEED_INPUT)
    if coach_text:
        turns.append(("AI", coach_text))
    persona_text = say(key, persona_session, coach_text or SEED_INPUT)

    for _ in range(max_turns):
        if END_TOKEN in persona_text:
            persona_text = persona_text.replace(END_TOKEN, "").strip()
            if persona_text:
                turns.append(("User", persona_text))
            stop_reason = "persona_ended"
            break
        if persona_text:
            turns.append(("User", persona_text))

        coach_text = say(key, coach_session, persona_text)
        if coach_text:
            turns.append(("AI", coach_text))
        if _END_RE.search(coach_text):
            stop_reason = "coach_wrapup"
            break

        persona_text = say(key, persona_session, coach_text)

    transcript = "\n".join(f"{spk}: {txt}" for spk, txt in turns)
    return {
        "Assistant Name": f"SIM {persona['name']}",
        "CEO ID": f"SIM-{persona['key']}",
        "Persona": persona["key"],
        "Coach": coach_id,
        "Coach Name": cname,
        "Target Job": persona["job"],
        "Eval Focus": persona["focus"],
        "Turns": len(turns),
        "Stop Reason": stop_reason,
        "Transcript": transcript,
    }


FIELDS = ["Assistant Name", "CEO ID", "Persona", "Coach", "Coach Name",
          "Target Job", "Eval Focus", "Turns", "Stop Reason", "Transcript"]


def write_rows(out_path: Path, rows: list[dict]) -> None:
    new_file = not out_path.exists()
    with open(out_path, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, delimiter="\t")
        if new_file:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


def dry_run(personas: list[dict], coaches: list[str], have_ids: dict) -> None:
    print("DRY RUN — no API calls.\n")
    print(f"Coach assistant id : {', '.join(c for c in coaches if c) or '(VAPI_COACH_ASSISTANT_ID not set)'}")
    print(f"Vapi key present   : {'yes' if os.environ.get('VAPI_PRIVATE_KEY') else 'NO'}")
    print(f"Persona id file    : {PERSONA_FILE} ({'found' if PERSONA_FILE.exists() else 'MISSING'})\n")
    print("Personas to run:")
    for p in personas:
        pid = have_ids.get(p["key"], "(no id — run vapi_setup.py --create)")
        print(f"  - {p['key']:<14} {p['name']:<38} -> {pid}")
    print("\nLooks right? Drop --dry-run to execute.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run persona-vs-coach text simulations.")
    parser.add_argument("--persona", default="all", help="Persona key to run, or 'all' (default).")
    parser.add_argument("--runs", type=int, default=1, help="Runs per persona (default 1).")
    parser.add_argument("--coach", action="append", metavar="ASSISTANT_ID",
                        help="Target coach assistant id. Repeat to run each persona against "
                             "several coaches (e.g. 2.0 vs 2.1). Default: VAPI_COACH_ASSISTANT_ID.")
    parser.add_argument("--max-turns", type=int, default=30, help="Hard cap on turns per call (default 30).")
    parser.add_argument("--out", default=DEFAULT_OUT, help=f"Output TSV (default {DEFAULT_OUT}).")
    parser.add_argument("--dry-run", action="store_true", help="Validate setup without calling the API.")
    args = parser.parse_args()

    if args.persona == "all":
        selected = PERSONAS
    elif args.persona in PERSONAS_BY_KEY:
        selected = [PERSONAS_BY_KEY[args.persona]]
    else:
        print(f"Unknown persona '{args.persona}'. Options: all, {', '.join(PERSONAS_BY_KEY)}")
        sys.exit(1)

    coach_id = os.environ.get("VAPI_COACH_ASSISTANT_ID", "").strip()

    if args.dry_run:
        dry_run(selected, args.coach or [coach_id], load_persona_ids() if PERSONA_FILE.exists() else {})
        return

    key = _require("VAPI_PRIVATE_KEY")
    coaches = args.coach or [_require("VAPI_COACH_ASSISTANT_ID")]
    persona_ids = load_persona_ids()

    rows = []
    total = len(selected) * args.runs * len(coaches)
    n = 0
    for coach_id in coaches:
        cname = coach_name(key, coach_id)
        if len(coaches) > 1:
            print(f"\n=== Coach {cname} ({coach_id[:8]}…) ===")
        for persona in selected:
            persona_id = persona_ids.get(persona["key"])
            if not persona_id:
                print(f"  ! no Vapi id for persona '{persona['key']}' — run: python vapi_setup.py --create")
                continue
            for run in range(args.runs):
                n += 1
                label = f"[{n}/{total}] {persona['key']}" + (f" run {run + 1}" if args.runs > 1 else "")
                try:
                    row = run_one(key, coach_id, cname, persona, persona_id, args.max_turns)
                    rows.append(row)
                    print(f"{label}: {row['Turns']} turns, stop={row['Stop Reason']}")
                except Exception as e:
                    print(f"{label}: FAILED — {type(e).__name__}: {e}")

    if rows:
        write_rows(Path(args.out), rows)
        print(f"\nWrote {len(rows)} simulated call(s) to {args.out}")
        print(f"Score them:  python analyze.py --file {args.out}")
    else:
        print("\nNo calls completed — nothing written.")


if __name__ == "__main__":
    main()
