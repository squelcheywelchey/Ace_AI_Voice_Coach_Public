#!/usr/bin/env python3
"""
CEO Voice Coach Eval — Eval Harness
Runs a judge prompt against the dev (or test) set and computes agreement.

Usage:
    python eval_harness.py --prompt ../prompts/drives_practice_v1.yaml --split dev

Requires:
    - labels/consensus_labels.csv (with consensus_label column)
    - labels/dev_ids.csv or labels/test_ids.csv
    - Transcript files accessible
"""

import os
import sys
import json
import yaml
import argparse
import csv
import anthropic
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
MODEL = "claude-sonnet-4-6"

# Try to import krippendorff; if not installed, alpha will be skipped
try:
    import krippendorff
    import numpy as np
    HAS_KRIPPENDORFF = True
except ImportError:
    HAS_KRIPPENDORFF = False


def compute_krippendorff_alpha(results):
    """Compute Krippendorff's alpha between judge and human labels."""
    if not HAS_KRIPPENDORFF:
        return None

    # Encode labels as numbers: PASS=1, FAIL=0
    label_map = {"PASS": 1, "FAIL": 0}
    human_vals = []
    judge_vals = []
    for r in results:
        if r["human"] in label_map and r["judge"] in label_map:
            human_vals.append(label_map[r["human"]])
            judge_vals.append(label_map[r["judge"]])

    if len(human_vals) < 2:
        return None

    # krippendorff expects a reliability data matrix: rows = raters, cols = items
    data = np.array([human_vals, judge_vals])
    try:
        return krippendorff.alpha(reliability_data=data, level_of_measurement="nominal")
    except Exception:
        return None


def load_prompt(prompt_path):
    with open(prompt_path, "r") as f:
        return yaml.safe_load(f)


def build_system_prompt(p):
    return f"""You are an expert evaluator of AI voice coaching sessions.

Your task is to evaluate one specific coaching dimension:

DIMENSION: {p['dimension']}

DEFINITION:
{p['definition']}

PASS — what it looks like:
{p['pass']}

FAIL — what it looks like:
{p['fail']}

N/A — when to use it:
{p['na']}

Evaluate ONLY this dimension. Base your judgment solely on what is observable in the transcript.

Respond in JSON only. No markdown, no code blocks, no extra text:
{{"result": "PASS" or "FAIL" or "N/A", "evidence": "<copy the key exchange verbatim, max 200 chars>", "reasoning": "<one sentence explaining your verdict>"}}"""


def run_judge(client, system_prompt, transcript_text):
    message = client.messages.create(
        model=MODEL,
        max_tokens=500,
        system=system_prompt,
        messages=[{"role": "user", "content": f"TRANSCRIPT:\n\n{transcript_text}"}]
    )
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def load_split_ids(split_name):
    split_file = BASE_DIR / "labels" / f"{split_name}_ids.csv"
    ids = []
    with open(split_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                ids.append(line)
    return ids


def load_labels(dimension):
    labels_file = BASE_DIR / "labels" / "consensus_labels.csv"
    labels = {}
    with open(labels_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["dimension"] == dimension:
                labels[row["transcript_id"]] = row["consensus_label"].upper()
    return labels


def compute_agreement(results):
    """Compute agreement metrics between judge and human labels."""
    total = len(results)
    if total == 0:
        return {}

    matches = sum(1 for r in results if r["match"])
    agreement = matches / total

    # Compute per-class metrics
    tp = sum(1 for r in results if r["human"] == "PASS" and r["judge"] == "PASS")
    fp = sum(1 for r in results if r["human"] == "FAIL" and r["judge"] == "PASS")
    tn = sum(1 for r in results if r["human"] == "FAIL" and r["judge"] == "FAIL")
    fn = sum(1 for r in results if r["human"] == "PASS" and r["judge"] == "FAIL")

    pass_precision = tp / (tp + fp) if (tp + fp) > 0 else None
    fail_precision = tn / (tn + fn) if (tn + fn) > 0 else None
    pass_recall = tp / (tp + fn) if (tp + fn) > 0 else None
    fail_recall = tn / (tn + fp) if (tn + fp) > 0 else None

    return {
        "total": total,
        "matches": matches,
        "agreement": agreement,
        "pass_precision": pass_precision,
        "fail_precision": fail_precision,
        "pass_recall": pass_recall,
        "fail_recall": fail_recall,
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
    }


def main():
    parser = argparse.ArgumentParser(description="Run eval harness")
    parser.add_argument("--prompt", required=True, help="Path to judge prompt YAML")
    parser.add_argument("--split", default="dev", choices=["dev", "test"], help="Which split to evaluate on")
    parser.add_argument("--transcripts-dir", default=None, help="Directory containing transcript files")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)
    prompt_data = load_prompt(args.prompt)
    system_prompt = build_system_prompt(prompt_data)
    dimension = prompt_data["dimension"]

    # Load split IDs and labels
    split_ids = load_split_ids(args.split)
    labels = load_labels(dimension)

    if not split_ids:
        print(f"ERROR: No IDs found in {args.split}_ids.csv")
        sys.exit(1)

    if not labels:
        print(f"ERROR: No labels found for dimension '{dimension}' in consensus_labels.csv")
        sys.exit(1)

    print(f"\n{'='*55}")
    print(f"  EVAL HARNESS — {dimension}")
    print(f"  Prompt: {args.prompt}")
    print(f"  Split:  {args.split} ({len(split_ids)} transcripts)")
    print(f"  Model:  {MODEL}")
    print(f"{'='*55}\n")

    results = []
    disagreements = []

    for tid in split_ids:
        if tid not in labels:
            print(f"  Skipping {tid} — no label for {dimension}")
            continue

        human_label = labels[tid]
        if human_label == "N/A":
            print(f"  Skipping {tid} — N/A label")
            continue

        # Find transcript file
        transcript_file = None
        if args.transcripts_dir:
            transcript_dir = Path(args.transcripts_dir)
        else:
            transcript_dir = BASE_DIR

        # Try various naming patterns
        for pattern in [f"transcript_{tid}.txt", f"{tid}.txt"]:
            candidate = transcript_dir / pattern
            if candidate.exists():
                transcript_file = candidate
                break

        if not transcript_file:
            print(f"  Skipping {tid} — transcript file not found")
            continue

        print(f"  Scoring {tid}...", end=" ")
        with open(transcript_file, "r") as f:
            text = f.read()

        try:
            output = run_judge(client, system_prompt, text)
            judge_label = output["result"]
            match = judge_label == human_label
            icon = "✅" if match else "❌"

            results.append({
                "transcript_id": tid,
                "human": human_label,
                "judge": judge_label,
                "match": match,
                "reasoning": output.get("reasoning", ""),
                "evidence": output.get("evidence", ""),
            })

            if not match:
                disagreements.append(results[-1])

            print(f"Human: {human_label} | Judge: {judge_label} {icon}")

        except Exception as e:
            print(f"ERROR: {e}")

    # Compute and print metrics
    metrics = compute_agreement(results)
    alpha = compute_krippendorff_alpha(results)

    # Extract version from prompt filename (e.g. drives_practice_v2.yaml -> v2)
    prompt_stem = Path(args.prompt).stem
    version = prompt_stem.split("_")[-1] if "_v" in prompt_stem else prompt_stem
    run_date = datetime.now().strftime("%Y-%m-%d")

    print(f"\n{'='*55}")
    print(f"  RESULTS — {dimension} on {args.split} set")
    print(f"{'='*55}")
    if alpha is not None:
        alpha_status = "✓ reliable" if alpha >= 0.8 else "~ tentative" if alpha >= 0.67 else "✗ below threshold"
        print(f"  Kripp. alpha:   {alpha:.3f} ({alpha_status})")
    else:
        if not HAS_KRIPPENDORFF:
            print(f"  Kripp. alpha:   not available (pip install krippendorff numpy)")
        else:
            print(f"  Kripp. alpha:   N/A (not enough data)")
    print(f"  Agreement:      {metrics.get('matches', 0)}/{metrics.get('total', 0)} ({metrics.get('agreement', 0):.1%})")
    print(f"  Pass precision: {metrics.get('pass_precision', 'N/A'):.2f}" if metrics.get('pass_precision') is not None else "  Pass precision: N/A")
    print(f"  Fail precision: {metrics.get('fail_precision', 'N/A'):.2f}" if metrics.get('fail_precision') is not None else "  Fail precision: N/A")
    print(f"  Pass recall:    {metrics.get('pass_recall', 'N/A'):.2f}" if metrics.get('pass_recall') is not None else "  Pass recall:    N/A")
    print(f"  Fail recall:    {metrics.get('fail_recall', 'N/A'):.2f}" if metrics.get('fail_recall') is not None else "  Fail recall:    N/A")
    print(f"\n  Confusion matrix:")
    print(f"                  Judge PASS  Judge FAIL")
    print(f"  Human PASS      {metrics.get('tp', 0):>5}       {metrics.get('fn', 0):>5}")
    print(f"  Human FAIL      {metrics.get('fp', 0):>5}       {metrics.get('tn', 0):>5}")

    if disagreements:
        print(f"\n  DISAGREEMENTS ({len(disagreements)}):")
        for d in disagreements:
            print(f"    {d['transcript_id']}: Human={d['human']}, Judge={d['judge']}")
            print(f"      Reasoning: {d['reasoning']}")
            print(f"      Evidence: {d['evidence'][:120]}")

    # Save disagreements to CSV
    output_name = Path(args.prompt).stem + f"_{args.split}_disagreements.csv"
    output_path = BASE_DIR / "outputs" / output_name
    os.makedirs(BASE_DIR / "outputs", exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["transcript_id", "human", "judge", "reasoning", "evidence"])
        writer.writeheader()
        writer.writerows(disagreements)

    print(f"\n  Disagreements saved to: {output_path}")

    # Print Google Sheet copy-paste row
    alpha_str = f"{alpha:.3f}" if alpha is not None else "N/A"
    pp = f"{metrics['pass_precision']:.2f}" if metrics.get('pass_precision') is not None else "N/A"
    fp = f"{metrics['fail_precision']:.2f}" if metrics.get('fail_precision') is not None else "N/A"
    pr = f"{metrics['pass_recall']:.2f}" if metrics.get('pass_recall') is not None else "N/A"
    fr = f"{metrics['fail_recall']:.2f}" if metrics.get('fail_recall') is not None else "N/A"
    agr = f"{metrics['agreement']:.1%}" if metrics.get('agreement') is not None else "N/A"

    print(f"\n{'='*55}")
    print(f"  COPY TO GOOGLE SHEET (tab-separated):")
    print(f"{'='*55}")
    print(f"  {dimension}\t{version}\t{run_date}\t\t{alpha_str}\t{agr}\t{pp}\t{fr}\t")
    print(f"\n  Columns: Dimension | Version | Date | What Changed | Alpha | Agreement | Pass Precision | Fail Recall | Decision")
    print(f"  (Fill in 'What Changed' and 'Decision' manually)")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()
