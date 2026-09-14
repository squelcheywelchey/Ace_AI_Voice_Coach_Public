#!/usr/bin/env python3
"""
PII probe runner — the detection-half instrument for the pii dimension.

WHY THIS EXISTS: the real corpus has 0 fail examples (52 N/A / 1 pass), so the
standard eval_harness can only prove the judge STAYS QUIET (no false-fires). It
cannot prove the judge CATCHES a coach asking for / repeating / ignoring in-scope
PII, nor that the name/age/CEO-ID carve-outs hold. Those need positive examples,
which do not exist in the corpus — so they are hand-authored here.

These probes are SYNTHETIC and are deliberately kept OUT of labels/consensus_pii.csv
so they never contaminate the real human labels. Each probe carries an `expect`
(PASS/FAIL/N/A) that is the AUTHOR's intended verdict — a target for the judge to
hit, ratified by the team, not a human consensus label.

Usage:
    python3 scripts/pii_probe.py --prompt prompts/pii_v1.yaml
"""
import os, sys, csv, argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from eval_harness_v2 import run_judge, norm_label, MODEL
from prompt_adapter import load_prompt_spec
import anthropic

BASE_DIR = Path(__file__).parent.parent
PROBES = BASE_DIR / "labels" / "pii_probes.csv"

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR.parent / ".env")
except ImportError:
    pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--probes", default=str(PROBES))
    args = ap.parse_args()

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    spec = load_prompt_spec(args.prompt)

    rows = list(csv.DictReader(open(args.probes)))
    print(f"\n{'='*70}\n  PII PROBE SET — {args.prompt}  ({len(rows)} synthetic cases)\n{'='*70}\n")

    n_ok = 0
    buckets = {}
    misses = []
    for r in rows:
        expect = norm_label(r["expect"])
        out = run_judge(client, spec, r["transcript"], args.model)
        got = norm_label(out["result"])
        ok = got == expect
        n_ok += ok
        b = r["bucket"]
        buckets.setdefault(b, [0, 0])
        buckets[b][0] += ok
        buckets[b][1] += 1
        icon = "✅" if ok else "❌"
        print(f"  {icon} [{b:22}] {r['id']:20} expect {expect:5} got {got:5}  — {r['desc']}")
        if not ok:
            misses.append((r, got, out.get("reasoning", "")))

    print(f"\n{'-'*70}")
    print(f"  OVERALL: {n_ok}/{len(rows)} ({n_ok/len(rows):.0%})")
    for b, (ok, tot) in sorted(buckets.items()):
        print(f"    {b:24} {ok}/{tot}")
    if misses:
        print(f"\n  MISSES ({len(misses)}):")
        for r, got, reason in misses:
            print(f"    {r['id']}: expected {r['expect']}, got {got}")
            print(f"       judge reasoning: {reason}")
    print()


if __name__ == "__main__":
    main()
