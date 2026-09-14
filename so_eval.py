"""Run a Vapi Structured Output's definition LOCALLY over simulated calls.

Vapi structured outputs only execute on real *voice call* artifacts, so they
can't natively score our text /chat simulations. A Vapi "ai" structured output
is, under the hood, just an LLM scoring a transcript against a prompt + schema.
This script fetches a structured output's definition live from Vapi (by id, so
it stays in sync with what you edit in the dashboard) and applies that exact
definition to each transcript in a sim TSV, using the same Anthropic model.

You get the score on synthetic calls now, and a sandbox to tune the SO's prompt
before it goes live on real voice calls.

Usage:
    python so_eval.py                          # default SO over sim_calls.tsv
    python so_eval.py --id <so-id> --file sim_calls.tsv
    python so_eval.py --model claude-opus-4-8  # override the SO's own model

Keys from .env: VAPI_PRIVATE_KEY (fetch the SO definition) + ANTHROPIC_API_KEY (score).
"""

import argparse
import csv
import os
import sys
from collections import Counter
from pathlib import Path

import anthropic
import requests
from dotenv import load_dotenv
from pydantic import BaseModel, Field, create_model

load_dotenv()
csv.field_size_limit(10**7)

DEFAULT_SO_ID = os.getenv("VAPI_STRUCTURED_OUTPUT_ID", "")  # drives_practice_and_uptake
DEFAULT_FILE = "sim_calls.tsv"


def fetch_so(so_id: str, key: str) -> dict:
    r = requests.get(f"https://api.vapi.ai/structured-output/{so_id}",
                     headers={"Authorization": f"Bearer {key}"}, timeout=30)
    r.raise_for_status()
    return r.json()


def build_output_model(so: dict):
    """Build a Pydantic output model from the SO's JSON schema (scalar int/number)."""
    schema = so.get("schema", {}) or {}
    desc = schema.get("description") or so.get("description", "")
    t = schema.get("type")
    if t not in ("integer", "number"):
        sys.exit(f"so_eval currently supports scalar integer/number structured outputs; "
                 f"got type={t!r}. Extend build_output_model() for object schemas.")
    constraints = {}
    if schema.get("minimum") is not None:
        constraints["ge"] = schema["minimum"]
    if schema.get("maximum") is not None:
        constraints["le"] = schema["maximum"]
    py_type = int if t == "integer" else float
    Model = create_model(
        "SOResult",
        value=(py_type, Field(description=desc, **constraints)),
        evidence=(str, Field(description="One short quote or reason justifying the value (label AI/User).")),
    )
    return Model, desc


def main() -> None:
    ap = argparse.ArgumentParser(description="Run a Vapi structured output locally over simulated calls.")
    ap.add_argument("--id", default=DEFAULT_SO_ID, help="Structured output id (default: drives_practice_and_uptake).")
    ap.add_argument("--file", default=DEFAULT_FILE, help=f"Sim TSV to score (default {DEFAULT_FILE}).")
    ap.add_argument("--model", default=None, help="Override the model (default: the SO's own model).")
    args = ap.parse_args()

    vkey = os.environ.get("VAPI_PRIVATE_KEY", "").strip()
    if not vkey:
        sys.exit("VAPI_PRIVATE_KEY not set (needed to fetch the SO definition).")
    so = fetch_so(args.id, vkey)
    model = args.model or (so.get("model") or {}).get("model") or "claude-opus-4-8"
    Model, desc = build_output_model(so)

    path = Path(args.file)
    if not path.exists():
        sys.exit(f"File not found: {path}")
    with open(path, newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh, delimiter="\t") if (r.get("Transcript") or "").strip()]
    if not rows:
        sys.exit(f"No transcripts found in {path}.")

    print(f"SO: {so['name']}  ·  model: {model}  ·  {len(rows)} call(s) from {path.name}")
    print(f"Rubric: {desc}\n")

    client = anthropic.Anthropic(max_retries=4)
    system = (f"You are a Vapi structured-output extractor named '{so['name']}'. "
              f"{so.get('description', '')}\n\n"
              f"Score the COACH (the 'AI:' turns) on this single dimension, returning the value "
              f"per the rubric plus one short piece of supporting evidence.\nRubric: {desc}")

    dist: Counter = Counter()
    total = 0.0
    n = 0
    for r in rows:
        try:
            ev = client.messages.parse(
                model=model, max_tokens=600, system=system,
                messages=[{"role": "user", "content": f"<transcript>\n{r['Transcript']}\n</transcript>"}],
                output_format=Model,
            ).parsed_output
        except Exception as e:
            print(f"  {r.get('Persona', '?'):13} FAILED — {type(e).__name__}: {e}")
            continue
        print(f"  {r.get('Persona', '?'):13} value={ev.value}  — {ev.evidence[:100]}")
        dist[ev.value] += 1
        total += ev.value
        n += 1

    if n:
        print(f"\n  n={n}  ·  mean={total / n:.2f}  ·  dist={dict(sorted(dist.items()))}")


if __name__ == "__main__":
    main()
