"""Set up the Vapi side of the persona simulations.

Two jobs:
  1. --list     Print every assistant in your Vapi account (id + name) so you
                can grab the test-coach's id for VAPI_COACH_ASSISTANT_ID.
  2. --create   Create one Vapi assistant per persona (from personas.py) on a
                cheap, non-Anthropic model, and save the resulting ids to
                vapi_personas.json (gitignored). simulate.py reads that file.

You only need ONE credential: VAPI_PRIVATE_KEY in .env. Assistants are
identified by id, not by per-assistant keys.

Usage:
    python vapi_setup.py --list
    python vapi_setup.py --create                 # create any missing personas
    python vapi_setup.py --create --force         # recreate all personas (new ids)
    python vapi_setup.py --update                 # push edited prompts into existing
                                                  #   assistants in place (ids unchanged)
    python vapi_setup.py --create --model gpt-4o-mini

Note: the Vapi REST endpoints (/assistant) are assumed from Vapi's current API.
If your account differs, the request/parse points are isolated in vapi_request()
and the create/list functions below — adjust there.
"""

from __future__ import annotations  # allow `X | Y` type hints on Python 3.9

import argparse
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

from personas import PERSONAS

load_dotenv()

API_BASE = "https://api.vapi.ai"
PERSONA_FILE = Path("vapi_personas.json")
DEFAULT_PERSONA_MODEL = "gpt-4o-mini"   # cheap, NOT our Anthropic key
DEFAULT_PERSONA_PROVIDER = "openai"


def _key() -> str:
    key = os.environ.get("VAPI_PRIVATE_KEY", "").strip()
    if not key:
        print("VAPI_PRIVATE_KEY is not set. Add it to .env (dashboard.vapi.ai -> API Keys, the PRIVATE key).")
        sys.exit(1)
    return key


def vapi_request(method: str, path: str, key: str, payload: dict | None = None) -> dict | list:
    url = f"{API_BASE}{path}"
    resp = requests.request(
        method,
        url,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    if not resp.ok:
        print(f"Vapi {method} {path} -> {resp.status_code}: {resp.text[:500]}")
        resp.raise_for_status()
    return resp.json() if resp.text else {}


def list_assistants(key: str) -> None:
    data = vapi_request("GET", "/assistant", key)
    assistants = data if isinstance(data, list) else data.get("results", data.get("data", []))
    if not assistants:
        print("No assistants found on this account.")
        return
    print(f"{'ID':<38}  NAME")
    print(f"{'-' * 38}  {'-' * 30}")
    for a in assistants:
        print(f"{a.get('id', '?'):<38}  {a.get('name', '(unnamed)')}")
    print(f"\n{len(assistants)} assistant(s). "
          "Copy the test-coach's id into .env as VAPI_COACH_ASSISTANT_ID.")


def create_persona_assistant(key: str, persona: dict, provider: str, model: str) -> str:
    payload = {
        "name": f"SIM persona: {persona['key']}",   # Vapi caps assistant names at 40 chars
        "model": {
            "provider": provider,
            "model": model,
            "messages": [{"role": "system", "content": persona["prompt"]}],
        },
    }
    result = vapi_request("POST", "/assistant", key, payload)
    return result["id"]


def create_personas(key: str, provider: str, model: str, force: bool) -> None:
    existing = json.loads(PERSONA_FILE.read_text()) if PERSONA_FILE.exists() else {}
    created = 0
    for persona in PERSONAS:
        pk = persona["key"]
        if pk in existing and not force:
            print(f"  = {pk:<14} already exists ({existing[pk]}) — skipping (use --force to recreate)")
            continue
        assistant_id = create_persona_assistant(key, persona, provider, model)
        existing[pk] = assistant_id
        created += 1
        PERSONA_FILE.write_text(json.dumps(existing, indent=2))  # save after each, so a mid-run failure doesn't lose progress
        print(f"  + {pk:<14} created -> {assistant_id}")
    PERSONA_FILE.write_text(json.dumps(existing, indent=2))
    print(f"\nWrote {len(existing)} persona id(s) to {PERSONA_FILE} ({created} new). "
          "simulate.py will read this file.")


def update_personas(key: str) -> None:
    """Push the current personas.py prompts into the EXISTING Vapi assistants
    (PATCH in place — ids unchanged, model/provider preserved)."""
    if not PERSONA_FILE.exists():
        print(f"{PERSONA_FILE} not found — nothing to update. Run --create first.")
        return
    existing = json.loads(PERSONA_FILE.read_text())
    updated = 0
    for persona in PERSONAS:
        pk = persona["key"]
        assistant_id = existing.get(pk)
        if not assistant_id:
            print(f"  ! {pk:<14} no id in {PERSONA_FILE} — skipping (use --create)")
            continue
        current = vapi_request("GET", f"/assistant/{assistant_id}", key)
        model_cfg = current.get("model", {}) or {}
        new_model = {
            "provider": model_cfg.get("provider", DEFAULT_PERSONA_PROVIDER),
            "model": model_cfg.get("model", DEFAULT_PERSONA_MODEL),
            "messages": [{"role": "system", "content": persona["prompt"]}],
        }
        vapi_request("PATCH", f"/assistant/{assistant_id}", key, {"model": new_model})
        updated += 1
        print(f"  ~ {pk:<14} prompt updated ({assistant_id})")
    print(f"\nUpdated {updated} persona assistant(s) in place — ids unchanged, "
          f"{PERSONA_FILE} still valid.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Set up Vapi assistants for persona simulations.")
    parser.add_argument("--list", action="store_true", help="List all assistants (id + name).")
    parser.add_argument("--create", action="store_true", help="Create persona assistants from personas.py.")
    parser.add_argument("--update", action="store_true", help="Push edited prompts into existing assistants in place (ids unchanged).")
    parser.add_argument("--force", action="store_true", help="Recreate personas even if already in vapi_personas.json.")
    parser.add_argument("--provider", default=DEFAULT_PERSONA_PROVIDER, help="Persona model provider (default openai).")
    parser.add_argument("--model", default=DEFAULT_PERSONA_MODEL, help="Persona model (default gpt-4o-mini — cheap).")
    args = parser.parse_args()

    if not (args.list or args.create or args.update):
        parser.print_help()
        return

    key = _key()
    if args.list:
        list_assistants(key)
    if args.update:
        update_personas(key)
    if args.create:
        create_personas(key, args.provider, args.model, args.force)


if __name__ == "__main__":
    main()
