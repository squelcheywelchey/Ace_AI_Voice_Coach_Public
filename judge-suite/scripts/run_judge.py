#!/usr/bin/env python3
"""
CEO Voice Coach Eval — Single Judge Runner
Scores transcripts against a single judge prompt.

Usage:
    python run_judge.py --prompt ../prompts/drives_practice_v1.yaml --transcripts ../transcripts/
    python run_judge.py --prompt ../prompts/drives_practice_v1.yaml --transcript ../transcripts/123.txt
"""

import os
import json
import argparse
import csv
import anthropic
from pathlib import Path
from datetime import datetime

from prompt_adapter import load_prompt_spec, norm_label

MODEL = "claude-sonnet-4-6"


def run_judge(client, spec, transcript_text):
    system_prompt, user_message = spec.build_messages(transcript_text)
    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}]
    )
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    data = json.loads(raw.strip())
    # Normalize whichever label key this prompt format emits (yaml "result" /
    # md "verdict") to PASS/FAIL/N/A.
    data["result"] = norm_label(spec.extract_result(data))
    return data


def main():
    parser = argparse.ArgumentParser(description="Run judge on transcripts")
    parser.add_argument("--prompt", required=True, help="Path to judge prompt YAML")
    parser.add_argument("--transcript", default=None, help="Single transcript file")
    parser.add_argument("--transcripts", default=None, help="Directory of transcript files")
    parser.add_argument("--output", default=None, help="Output CSV path")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)
    spec = load_prompt_spec(args.prompt)

    # Collect transcript files
    files = []
    if args.transcript:
        files = [Path(args.transcript)]
    elif args.transcripts:
        files = sorted(Path(args.transcripts).glob("*.txt"))
    else:
        print("ERROR: Provide --transcript or --transcripts")
        return

    print(f"\n  {spec.dimension} — scoring {len(files)} transcripts\n")

    results = []
    for f in files:
        tid = f.stem
        print(f"  {tid}...", end=" ")
        with open(f, "r") as fh:
            text = fh.read()
        try:
            output = run_judge(client, spec, text)
            results.append({
                "transcript_id": tid,
                "result": output["result"],
                "reasoning": output.get("reasoning", ""),
                "evidence": output.get("evidence", ""),
            })
            print(output["result"])
        except Exception as e:
            print(f"ERROR: {e}")
            results.append({"transcript_id": tid, "result": "ERROR", "reasoning": str(e), "evidence": ""})

    # Save output
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path(f"outputs/{spec.dimension}_{Path(args.prompt).stem}.csv")

    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["transcript_id", "result", "reasoning", "evidence"])
        writer.writeheader()
        writer.writerows(results)

    pass_count = sum(1 for r in results if r["result"] == "PASS")
    fail_count = sum(1 for r in results if r["result"] == "FAIL")
    na_count = sum(1 for r in results if r["result"] == "N/A")

    print(f"\n  PASS: {pass_count} | FAIL: {fail_count} | N/A: {na_count}")
    print(f"  Saved to: {output_path}\n")


if __name__ == "__main__":
    main()
