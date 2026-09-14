"""Run persona-vs-coach VOICE simulations against the AI Voice Coach (Vapi).

The sibling of simulate.py. Where simulate.py drives a text /chat loop we
orchestrate ourselves, this uses Vapi's NATIVE Simulations feature: Vapi stands
up a synthetic "tester" agent (our persona, with its own voice) and runs it on a
real simulated voice call against the coach — full STT -> coach -> TTS — then
records and transcribes it. No phone number is needed (websocket transport).

Why bother going to voice: only a real voice artifact exercises the phone-
specific / audible-delivery rubric dimensions (Section D, anchors_to_audible_
behavior) and the coach's real mishearings. It's also the production-aligned
path — Vapi structured outputs and the eventual BYOM judge run on voice-call
artifacts, which this produces.

The Vapi object model (all under /eval/simulation):
    personality  the tester agent  (model + voice + system prompt = the persona)
    scenario     instructions + evaluations (>=1 required by the API)
    simulation   pairs a scenario + personality
    run          executes simulation(s) vs target.assistantId over a transport
                 (vapi.websocket = voice, vapi.webchat = chat)

We create one personality+scenario+simulation per persona once, cache their ids
in vapi_voice_sim.json (gitignored), then a run reuses them. Output is written
in the SAME AI:/User: transcript shape analyze.py expects, plus the recording
URL, so scoring is unchanged:

    python voice_sim.py --setup            # create the Vapi objects (non-billable)
    python voice_sim.py --dry-run          # show what would run, no API calls
    python voice_sim.py --mode chat        # cheap plumbing smoke-test (no voice min.)
    python voice_sim.py                     # VOICE run, all personas  (BILLABLE)
    python voice_sim.py --persona terse     # one persona
    python analyze.py --file voice_sim_calls.tsv   # score with the same judge

Needs in .env:  VAPI_PRIVATE_KEY, VAPI_COACH_ASSISTANT_ID.

NOTE: a voice run consumes Vapi voice minutes AND the coach's Anthropic model
usage — it costs money. --setup and --dry-run do not; chat mode skips voice
minutes but still runs the coach model.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

from personas import PERSONAS, PERSONAS_BY_KEY

load_dotenv()
csv.field_size_limit(10**7)

API_BASE = "https://api.vapi.ai"
CACHE_FILE = Path("vapi_voice_sim.json")   # {persona_key: {personality, scenario, simulation}}
DEFAULT_OUT = "voice_sim_calls.tsv"
PERSONA_MODEL = ("openai", "gpt-4o-mini")  # cheap, NOT our Anthropic key (matches simulate.py)
TESTER_VOICE = {"provider": "vapi", "voiceId": "Elliot"}  # known-good on this account
POLL_SECONDS = 6
POLL_TIMEOUT = 1800  # 30 min hard cap per run (a run may hold several queued voice calls)

FIELDS = ["Assistant Name", "CEO ID", "Persona", "Coach", "Coach Name",
          "Target Job", "Eval Focus", "Mode", "Turns", "Stop Reason",
          "Recording URL", "Transcript"]


def _require(var: str) -> str:
    val = os.environ.get(var, "").strip()
    if not val:
        print(f"{var} is not set. Add it to .env (see .env.example).")
        sys.exit(1)
    return val


def vapi(method: str, path: str, key: str, payload: dict | None = None) -> dict | list:
    resp = requests.request(
        method, f"{API_BASE}{path}",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload, timeout=120,
    )
    if not resp.ok:
        raise RuntimeError(f"Vapi {method} {path} -> {resp.status_code}: {resp.text[:500]}")
    return resp.json() if resp.text else {}


def load_cache() -> dict:
    return json.loads(CACHE_FILE.read_text()) if CACHE_FILE.exists() else {}


def save_cache(cache: dict) -> None:
    CACHE_FILE.write_text(json.dumps(cache, indent=2))


def voice_persona_prompt(persona: dict) -> str:
    """The persona's system prompt, adapted for native voice sims.

    personas.py is written for OUR text loop, where the persona signals the end
    by emitting the literal token <END_CALL>. In a native voice sim the call
    ends on its own, and a TTS voice literally reading "<END_CALL>" would be
    nonsense — so we strip that instruction. Everything else (saying menu
    numbers aloud, the behavior block) is already voice-appropriate.
    """
    p = persona["prompt"]
    # Drop the "...output the token <END_CALL> on its own line, then stop." clause.
    p = re.sub(r"and\s+output the token <END_CALL> on its own line, then stop\.",
               "and then simply stop talking.", p)
    p = p.replace("<END_CALL>", "")
    return p


def ensure_objects(key: str, persona: dict, cache: dict, force: bool) -> dict:
    """Create personality/scenario/simulation for a persona if missing; cache ids."""
    pk = persona["key"]
    entry = cache.get(pk, {})
    if entry.get("simulation") and not force:
        return entry

    provider, model = PERSONA_MODEL
    personality = vapi("POST", "/eval/simulation/personality", key, {
        "name": f"SIM voice: {pk}"[:40],
        "assistant": {
            "model": {"provider": provider, "model": model,
                      "messages": [{"role": "system", "content": voice_persona_prompt(persona)}]},
            "voice": TESTER_VOICE,
        },
    })["id"]

    scenario = vapi("POST", "/eval/simulation/scenario", key, {
        "name": f"SIM scenario: {pk}"[:40],
        "instructions": (
            f"You are a CEO participant practicing a mock interview by phone for "
            f"{persona['job']}. Follow your persona exactly. When the coach offers a "
            f"numbered menu, choose the mock-interview / step-by-step options and say "
            f"the number aloud. Stay in character for the whole call."
        ),
        # The API requires >=1 evaluation. We score externally with analyze.py, so
        # this is a placeholder pass-signal; real rubric dims can be added here later.
        "evaluations": [{
            "structuredOutput": {"name": "call_completed",
                                 "schema": {"type": "boolean",
                                            "description": "The coach ran an interview to a natural close."}},
            "comparator": "=", "value": True, "required": False,
        }],
    })["id"]

    simulation = vapi("POST", "/eval/simulation", key, {
        "name": f"SIM: {pk}"[:40],
        "scenarioId": scenario, "personalityId": personality,
    })["id"]

    entry = {"personality": personality, "scenario": scenario, "simulation": simulation}
    cache[pk] = entry
    save_cache(cache)
    return entry


def transport_for(mode: str) -> dict:
    return {"provider": "vapi.websocket" if mode == "voice" else "vapi.webchat"}


def start_run(key: str, sim_ids: list[str], coach_id: str, mode: str) -> str:
    run = vapi("POST", "/eval/simulation/run", key, {
        "simulations": [{"type": "simulation", "simulationId": sid} for sid in sim_ids],
        "target": {"type": "assistant", "assistantId": coach_id},
        "transport": transport_for(mode),
    })
    return run["id"]


def poll_run(key: str, run_id: str) -> dict:
    waited = 0
    while True:
        run = vapi("GET", f"/eval/simulation/run/{run_id}", key)
        status = (run.get("status") or "").lower()
        print(f"  run {run_id[:8]}… status={status or '?'}  ({waited}s)")
        if status in ("ended", "completed", "failed", "error", "cancelled"):
            return run
        if waited >= POLL_TIMEOUT:
            print("  ! poll timeout — returning last run state")
            return run
        time.sleep(POLL_SECONDS)
        waited += POLL_SECONDS


def fetch_items(key: str, run_id: str, run: dict) -> list[dict]:
    """Items may be inline on the run or under /item — handle both."""
    items = run.get("items") or run.get("results")
    if items:
        return items
    data = vapi("GET", f"/eval/simulation/run/{run_id}/item", key)
    if isinstance(data, dict):
        return data.get("results") or data.get("items") or []
    return data or []


# --- transcript extraction. Confirmed item shape (chat + voice):
#     item.metadata.call.transcript  -> ready-made "User:/AI:" string (what
#         analyze.py wants), item.metadata.call.messages -> [{role,message}]
#     recordingUrl (voice mode) lives on the same call object. ---

def _messages_to_transcript(messages: list) -> str:
    """Fallback: build AI:/User: lines from the role-based message list."""
    lines = []
    for m in messages or []:
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        text = (m.get("message") or m.get("content") or "").strip()
        if not text or role not in ("assistant", "bot", "user", "customer"):
            continue
        lines.append(f"{'AI' if role in ('assistant', 'bot') else 'User'}: {text}")
    return "\n".join(lines)


def extract_call(item: dict) -> dict:
    call = (item.get("metadata") or {}).get("call") or item.get("call") or {}
    # Prefer rebuilding from messages: it drops tool_calls/tool_call_result noise
    # (e.g. the coach's end-of-call spreadsheet write) that Vapi's ready-made
    # transcript string bakes in as bogus "AI:" lines. Fall back to that string.
    transcript = _messages_to_transcript(call.get("messages") or [])
    if not transcript:
        transcript = (call.get("transcript") or "").strip()
    turns = sum(1 for ln in transcript.splitlines() if ln[:4] in ("AI: ", "User")) if transcript else 0
    recording = (call.get("recordingUrl") or call.get("stereoRecordingUrl")
                 or call.get("recording") or "")
    return {"transcript": transcript, "turns": turns, "recording": recording}


def persona_for_item(item: dict, sim_to_persona: dict) -> dict | None:
    sid = item.get("simulationId") or (item.get("simulation") or {}).get("id")
    return sim_to_persona.get(sid)


def write_rows(out_path: Path, rows: list[dict]) -> None:
    new_file = not out_path.exists()
    with open(out_path, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, delimiter="\t")
        if new_file:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


def coach_name(key: str, coach_id: str) -> str:
    """Best-effort human name for a coach assistant id (for the Coach Name column)."""
    try:
        return vapi("GET", f"/assistant/{coach_id}", key).get("name", "") or coach_id[:8]
    except Exception:
        return coach_id[:8]


def run_against_coach(key: str, coach_id: str, cname: str, sim_to_persona: dict,
                      mode: str, run_status_note: str, want_raw: bool) -> list[dict]:
    """Run all selected simulations against one coach; return output rows."""
    sim_ids = list(sim_to_persona)
    billing = "  (BILLABLE — voice minutes + coach model)" if mode == "voice" else "  (coach model only)"
    print(f"\n=== Coach {cname} ({coach_id[:8]}…) — {mode} run over {len(sim_ids)} sim(s){billing} ===")
    run_id = start_run(key, sim_ids, coach_id, mode)
    run = poll_run(key, run_id)
    items = fetch_items(key, run_id, run)

    if want_raw:
        print("\n--- RAW items ---"); print(json.dumps(items, indent=2)[:6000])
    if not items:
        print("  No items returned. Re-run with --raw to inspect the run shape.")
        return []

    rows = []
    for item in items:
        persona = persona_for_item(item, sim_to_persona) or {"key": "?", "name": "?", "job": "", "focus": ""}
        call = extract_call(item)
        rows.append({
            "Assistant Name": f"VOICE SIM {persona['name']}",
            "CEO ID": f"VSIM-{persona['key']}",
            "Persona": persona["key"],
            "Coach": coach_id,
            "Coach Name": cname,
            "Target Job": persona.get("job", ""),
            "Eval Focus": persona.get("focus", ""),
            "Mode": mode,
            "Turns": call["turns"],
            "Stop Reason": (item.get("status") or run.get("status") or "").lower(),
            "Recording URL": call["recording"],
            "Transcript": call["transcript"],
        })
        flag = "" if call["transcript"] else "  ! empty transcript (try --raw)"
        print(f"  {persona['key']:<14} turns={call['turns']:<3} "
              f"rec={'yes' if call['recording'] else 'no'}{flag}")
    return rows


def select_personas(name: str) -> list[dict]:
    if name == "all":
        return PERSONAS
    if name in PERSONAS_BY_KEY:
        return [PERSONAS_BY_KEY[name]]
    print(f"Unknown persona '{name}'. Options: all, {', '.join(PERSONAS_BY_KEY)}")
    sys.exit(1)


def main() -> None:
    ap = argparse.ArgumentParser(description="Run native Vapi VOICE simulations of personas vs the coach.")
    ap.add_argument("--persona", default="all", help="Persona key, or 'all' (default).")
    ap.add_argument("--mode", choices=["voice", "chat"], default="voice",
                    help="voice (real audio, BILLABLE) or chat (cheap plumbing test). Default voice.")
    ap.add_argument("--setup", action="store_true",
                    help="Only create/refresh the Vapi simulation objects (non-billable), then exit.")
    ap.add_argument("--force", action="store_true", help="Recreate Vapi objects even if cached.")
    ap.add_argument("--coach", action="append", metavar="ASSISTANT_ID",
                    help="Target coach assistant id. Repeat to run each persona against "
                         "several coaches (e.g. 2.0 vs 2.1). Default: VAPI_COACH_ASSISTANT_ID.")
    ap.add_argument("--out", default=DEFAULT_OUT, help=f"Output TSV (default {DEFAULT_OUT}).")
    ap.add_argument("--dry-run", action="store_true", help="Show what would run; no API calls.")
    ap.add_argument("--raw", action="store_true", help="Dump raw run/items JSON (debug the item shape).")
    args = ap.parse_args()

    selected = select_personas(args.persona)
    coach_id = os.environ.get("VAPI_COACH_ASSISTANT_ID", "").strip()

    if args.dry_run:
        cache = load_cache()
        print("DRY RUN — no API calls.\n")
        print(f"Mode               : {args.mode}{'  (BILLABLE)' if args.mode == 'voice' else ''}")
        print(f"Coach assistant id : {coach_id or '(VAPI_COACH_ASSISTANT_ID not set)'}")
        print(f"Cache file         : {CACHE_FILE} ({'found' if CACHE_FILE.exists() else 'missing — will --setup'})\n")
        for p in selected:
            sim = cache.get(p["key"], {}).get("simulation", "(not created — run --setup)")
            print(f"  - {p['key']:<14} {p['name']:<38} -> sim {sim}")
        print("\nLooks right? Drop --dry-run (and pass --setup first if objects are missing).")
        return

    key = _require("VAPI_PRIVATE_KEY")
    coaches = args.coach or [_require("VAPI_COACH_ASSISTANT_ID")]
    cache = load_cache()

    # 1) Ensure the Vapi objects exist for each selected persona.
    print(f"Ensuring Vapi simulation objects for {len(selected)} persona(s)…")
    for p in selected:
        entry = ensure_objects(key, p, cache, args.force)
        print(f"  {p['key']:<14} sim={entry['simulation']}")
    if args.setup:
        print("\nSetup complete (non-billable). Run a voice sim with:  python voice_sim.py")
        return

    # 2) One run per coach, each covering all selected simulations.
    sim_to_persona = {cache[p["key"]]["simulation"]: p for p in selected}
    print(f"\nTargets: {len(coaches)} coach(es) × {len(selected)} persona(s) "
          f"= {len(coaches) * len(selected)} {args.mode} call(s).")
    all_rows = []
    for coach_id in coaches:
        cname = coach_name(key, coach_id)
        all_rows += run_against_coach(key, coach_id, cname, sim_to_persona,
                                      args.mode, "", args.raw)

    if all_rows:
        write_rows(Path(args.out), all_rows)
        print(f"\nWrote {len(all_rows)} voice-sim call(s) to {args.out}")
        print(f"Score them:  python analyze.py --file {args.out}")
    else:
        print("\nNo calls produced output — nothing written.")


if __name__ == "__main__":
    main()
