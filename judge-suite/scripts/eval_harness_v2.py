#!/usr/bin/env python3
"""
CEO Voice Coach Eval — Eval Harness (v2)
Runs a judge prompt against the dev (or test) set and reports how well the
judge's labels agree with the human CONSENSUS labels.

Differences from eval_harness.py:
  - Krippendorff's alpha removed entirely.
  - Metrics renamed to standard confusion-matrix rates:
        pass_recall    -> TPR (true positive rate)
        fail_recall    -> TNR (true negative rate)
        pass_precision -> PPV (positive predictive value)
        fail_precision -> NPV (negative predictive value)
  - "human" renamed to "consensus" throughout (the value is the reconciled
    consensus_label, not any single rater).

Positive class = PASS = "coach drives practice".
    TPR = of transcripts the consensus says PASS, how many the judge caught.
    TNR = of transcripts the consensus says FAIL, how many the judge caught.

Data source: a per-dimension consensus CSV (e.g. data/consensus_drives_practice.csv)
with columns: source_row, ceo_id, dimension, consensus_label, individual_labels,
excerpt. The judge evaluates the `excerpt` text directly (no separate transcript
files). Rows are keyed by `source_row` (unique) since a ceo_id can recur.

Usage:
    python eval_harness_v2.py --prompt ../prompts/drives_practice.yaml --split dev \\
        --consensus ../../data/consensus_drives_practice.csv

Requires:
    - a consensus CSV (--consensus) with source_row / consensus_label / excerpt columns
    - labels/dev_ids.csv or labels/test_ids.csv (columns: source_row, ceo_id, dimension)
"""

import os
import sys
import json
import yaml
import argparse
import csv
import re
import hashlib
import subprocess
import html as html_lib
import anthropic
from pathlib import Path
from datetime import datetime

from prompt_adapter import load_prompt_spec

csv.field_size_limit(10 ** 7)  # excerpts can be long

BASE_DIR = Path(__file__).parent.parent
MODEL = "claude-sonnet-4-6"
DEFAULT_CONSENSUS = (BASE_DIR / ".." / ".." / "data" / "consensus_drives_practice.csv").resolve()

# Load ANTHROPIC_API_KEY from ceo_voice_coach/.env if python-dotenv is present.
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR.parent / ".env")
except ImportError:
    pass

# Append-only run log + prompt-version archive, so every prompt change is
# traceable in the stats over time. The prompt is fingerprinted by a content
# hash (not just its filename) — that's what identifies the exact prompt text
# behind each row even when a file is edited in place.
RUN_LOG_PATH = BASE_DIR / "iteration_log" / "run_log.csv"
PROMPT_ARCHIVE_DIR = BASE_DIR / "iteration_log" / "prompt_versions"
RUN_LOG_FIELDS = [
    "timestamp", "dimension", "split", "model", "prompt_file", "version",
    "prompt_sha8", "git_commit", "prompt_dirty",
    "n", "agreement", "tpr", "tnr", "ppv", "npv", "na_recall",
    "tp", "fp", "tn", "fn", "false_fire", "false_abstain", "disagreements_file",
]


def prompt_fingerprint(prompt_path):
    """(short sha, raw bytes) of the prompt file's exact contents."""
    raw = Path(prompt_path).read_bytes()
    return hashlib.sha256(raw).hexdigest()[:8], raw


def git_state(prompt_path):
    """(short commit sha, is_dirty) for the prompt file's repo.
    is_dirty = the prompt file has uncommitted changes (what you evaluated
    differs from the committed version). ('', False) if not a git repo."""
    d = Path(prompt_path).resolve().parent
    try:
        commit = subprocess.run(
            ["git", "-C", str(d), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True).stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(d), "status", "--porcelain", str(Path(prompt_path).resolve())],
            capture_output=True, text=True, check=True).stdout.strip()
        return commit, bool(status)
    except Exception:
        return "", False


def archive_prompt(prompt_path, sha8, raw):
    """Snapshot the exact prompt text under iteration_log/prompt_versions/,
    keyed by content hash. Idempotent: an unchanged prompt is not re-copied."""
    PROMPT_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(prompt_path).suffix or ".yaml"
    dest = PROMPT_ARCHIVE_DIR / f"{Path(prompt_path).stem}_{sha8}{ext}"
    if not dest.exists():
        dest.write_bytes(raw)
    return dest


def log_run(row):
    """Append one row to the run log. If the log's header is out of date
    (e.g. a new field was added), rewrite it with the current schema,
    backfilling missing fields on old rows as blank."""
    RUN_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if RUN_LOG_PATH.exists():
        with open(RUN_LOG_PATH, newline="") as f:
            existing = list(csv.DictReader(f))
    header_ok = bool(existing) and set(existing[0].keys()) == set(RUN_LOG_FIELDS)
    with open(RUN_LOG_PATH, "a" if header_ok else "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RUN_LOG_FIELDS, extrasaction="ignore")
        if not header_ok:
            writer.writeheader()
            for old in existing:
                writer.writerow({k: old.get(k, "") for k in RUN_LOG_FIELDS})
        writer.writerow(row)


# Prompt loading + system-prompt assembly now live in prompt_adapter.py so this
# harness can run BOTH structured .yaml judges and self-contained .md judges
# (e.g. Grader B's two-step limits_the_load_v2.md). See load_prompt_spec().


def _robust_json_parse(raw):
    """Parse the judge's JSON tolerantly: strip code fences, drop trailing
    commas, and fall back to extracting the first {...} block."""
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    for candidate in (text, re.sub(r",(\s*[}\]])", r"\1", text)):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    # From the first "{", decode just the first JSON object and ignore any
    # trailing "extra data" the model appended after it.
    start = text.find("{")
    if start != -1:
        for candidate in (text[start:], re.sub(r",(\s*[}\]])", r"\1", text[start:])):
            try:
                obj, _ = json.JSONDecoder().raw_decode(candidate)
                return obj
            except json.JSONDecodeError:
                pass
    raise ValueError(f"could not parse JSON from: {raw[:200]!r}")


def run_judge(client, spec, transcript_text, model, retries=2):
    """One judge verdict. temperature=0 for reproducibility where supported
    (newer models like Opus 4.8 deprecate it — we drop it automatically);
    tolerant JSON parse with a couple of retries so a rare malformed response
    doesn't silently drop the row. `spec` (from load_prompt_spec) builds the
    system/user messages and extracts the label for whichever prompt format
    (.yaml -> "result", .md -> "verdict") is in use."""
    system_prompt, user_message = spec.build_messages(transcript_text)
    last_err = None
    send_temp = True
    attempts = 0
    while attempts < retries + 1:
        kwargs = dict(
            model=model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        if send_temp:
            kwargs["temperature"] = 0
        try:
            message = client.messages.create(**kwargs)
        except anthropic.BadRequestError as e:
            if send_temp and "temperature" in str(e).lower():
                send_temp = False  # this model rejects temperature — retry without it
                continue
            raise
        attempts += 1
        raw = message.content[0].text.strip()
        try:
            data = _robust_json_parse(raw)
        except (ValueError, json.JSONDecodeError) as e:
            last_err = e
            continue
        result = norm_label(spec.extract_result(data))
        if result not in ("PASS", "FAIL", "N/A"):
            last_err = ValueError(f"bad result value: {spec.extract_result(data)!r}")
            continue
        data["result"] = result
        return data
    raise ValueError(f"judge returned unparseable output after {retries + 1} attempts: {last_err}")


def load_split_ids(split_name, dimension):
    """Read a split file (columns: source_row, ceo_id, dimension) and return the
    list of source_row ids for the given dimension."""
    split_file = BASE_DIR / "labels" / f"{split_name}_ids.csv"
    ids = []
    with open(split_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("dimension", dimension) == dimension:
                ids.append(row["source_row"])
    return ids


def norm_label(x):
    """Canonicalize a label to PASS / FAIL / N/A. The consensus CSV writes
    'not_observed' while the judge emits 'N/A' — both mean the same class and
    must compare equal."""
    u = str(x).strip().upper()
    if u in ("NOT_OBSERVED", "NOT OBSERVED", "NA", "N/A", "NONE", ""):
        return "N/A"
    return u


def load_consensus(consensus_path, dimension):
    """Read the consensus CSV, keyed by source_row (unique). Returns
    {source_row: {"label": PASS/FAIL/N/A, "excerpt": str, "ceo_id": str}}."""
    consensus = {}
    with open(consensus_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["dimension"] != dimension:
                continue
            consensus[row["source_row"]] = {
                "label": norm_label(row["consensus_label"]),
                "excerpt": row["excerpt"],
                "ceo_id": row.get("ceo_id", ""),
            }
    return consensus


def compute_agreement(results):
    """Agreement metrics between judge and consensus labels, over three classes
    (PASS / FAIL / N/A). PASS = positive class.

    N/A is scored, not skipped: for not-observed-heavy dimensions the judge's
    job is largely to abstain correctly, and a judge that fires PASS/FAIL on a
    calm call (false-fire) must be penalized. So:
      - tpr/tnr are recall over ALL consensus-PASS / consensus-FAIL rows, so a
        judge that abstains (N/A) on a scoreable row is counted as a miss.
      - ppv/npv are precision over ALL judge-PASS / judge-FAIL predictions, so a
        judge that fires on a truly-N/A row is counted against it.
      - false_fire  = consensus N/A but judge said PASS/FAIL (the worst error).
      - false_abstain = consensus PASS/FAIL but judge said N/A.
    """
    total = len(results)
    if total == 0:
        return {}

    matches = sum(1 for r in results if r["match"])
    agreement = matches / total

    def cnt(c, j):
        return sum(1 for r in results if r["consensus"] == c and r["judge"] == j)

    # PASS = positive class
    tp = cnt("PASS", "PASS")
    fp = cnt("FAIL", "PASS")
    tn = cnt("FAIL", "FAIL")
    fn = cnt("PASS", "FAIL")
    pass_as_na = cnt("PASS", "N/A")
    fail_as_na = cnt("FAIL", "N/A")
    na_correct = cnt("N/A", "N/A")
    na_as_pass = cnt("N/A", "PASS")
    na_as_fail = cnt("N/A", "FAIL")

    n_pass = tp + fn + pass_as_na          # all consensus PASS
    n_fail = tn + fp + fail_as_na          # all consensus FAIL
    n_na = na_correct + na_as_pass + na_as_fail  # all consensus N/A
    judge_pass = tp + fp + na_as_pass      # all judge PASS
    judge_fail = tn + fn + na_as_fail      # all judge FAIL

    false_fire = na_as_pass + na_as_fail       # invented a signal on a calm call
    false_abstain = pass_as_na + fail_as_na    # missed a real signal

    def rate(num, den):
        return num / den if den > 0 else None

    return {
        "total": total,
        "matches": matches,
        "agreement": agreement,
        "tpr": rate(tp, n_pass),   # of consensus-PASS, judge said PASS
        "tnr": rate(tn, n_fail),   # of consensus-FAIL, judge said FAIL
        "ppv": rate(tp, judge_pass),  # when judge says PASS, how often right
        "npv": rate(tn, judge_fail),  # when judge says FAIL, how often right
        "na_recall": rate(na_correct, n_na),  # of consensus-N/A, judge abstained
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "pass_as_na": pass_as_na, "fail_as_na": fail_as_na,
        "na_correct": na_correct, "na_as_pass": na_as_pass, "na_as_fail": na_as_fail,
        "n_pass": n_pass, "n_fail": n_fail, "n_na": n_na,
        "false_fire": false_fire, "false_abstain": false_abstain,
    }


def fmt(x):
    return f"{x:.2f}" if x is not None else "N/A"


def _fmt_transcript(text):
    """Escape a transcript and put each AI:/User: turn on its own line."""
    esc = html_lib.escape(text or "")
    esc = re.sub(r"\s*(AI:|User:)\s*", r'<br><span class="spk">\1</span> ', esc)
    return re.sub(r"^(<br>)+", "", esc)


def _badge(label):
    cls = {"PASS": "pass", "FAIL": "fail"}.get(str(label).upper(), "na")
    return f'<span class="badge {cls}">{html_lib.escape(str(label))}</span>'


def generate_disagreements_html(disagreements, metrics, meta):
    """Self-contained HTML report of judge-vs-consensus disagreements."""
    if disagreements:
        cards = ""
        for d in disagreements:
            cards += f"""
      <div class="card">
        <div class="card-head">
          <span class="tid">row {html_lib.escape(str(d['transcript_id']))} <span class="sub">· ceo {html_lib.escape(str(d.get('ceo_id','')))}</span></span>
          <span class="labels">Consensus {_badge(d['consensus'])} <span class="vs">vs</span> Judge {_badge(d['judge'])}</span>
        </div>
        <div class="field"><div class="k">Judge reasoning</div><div class="v">{html_lib.escape(d.get('reasoning',''))}</div></div>
        <div class="field"><div class="k">Judge evidence (quoted from transcript)</div><div class="v evidence">{html_lib.escape(d.get('evidence',''))}</div></div>
        <details><summary>Full transcript</summary><div class="transcript">{_fmt_transcript(d.get('transcript',''))}</div></details>
      </div>"""
    else:
        cards = '<p class="empty">No disagreements — the judge matched consensus on every scored transcript. 🎉</p>'

    m = metrics
    dirty = ' <span class="dirty">+uncommitted edits</span>' if meta.get("prompt_dirty") else ""
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html_lib.escape(meta['dimension'])} — disagreements ({html_lib.escape(meta['split'])})</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, Segoe UI, Helvetica, Arial, sans-serif; background: #fafafa; color: #1a1a1a; padding: 32px 40px; max-width: 900px; margin: 0 auto; }}
  h1 {{ font-size: 20px; font-weight: 650; }}
  .meta {{ font-size: 12px; color: #777; margin: 4px 0 20px; line-height: 1.6; }}
  .meta code {{ background: #eee; padding: 1px 5px; border-radius: 3px; font-size: 11px; }}
  .dirty {{ color: #b45309; font-weight: 600; }}
  .stats {{ display: flex; flex-wrap: wrap; gap: 22px; margin-bottom: 28px; padding: 16px 20px; background: #fff; border: 1px solid #e6e6e6; border-radius: 8px; }}
  .stat .val {{ font-size: 26px; font-weight: 700; }}
  .stat .label {{ font-size: 11px; color: #888; margin-top: 2px; text-transform: uppercase; letter-spacing: .04em; }}
  h2 {{ font-size: 14px; font-weight: 600; margin-bottom: 12px; color: #444; }}
  .card {{ background: #fff; border: 1px solid #e6e6e6; border-radius: 8px; padding: 16px 18px; margin-bottom: 14px; }}
  .card-head {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-wrap: wrap; gap: 8px; }}
  .tid {{ font-weight: 650; font-size: 14px; }}
  .tid .sub {{ font-weight: 400; color: #999; }}
  .vs {{ color: #aaa; margin: 0 4px; font-size: 12px; }}
  .badge {{ display: inline-block; padding: 2px 9px; border-radius: 20px; font-size: 12px; font-weight: 650; }}
  .badge.pass {{ background: #dcfce7; color: #166534; }}
  .badge.fail {{ background: #fee2e2; color: #991b1b; }}
  .badge.na {{ background: #e5e7eb; color: #4b5563; }}
  .field {{ margin: 8px 0; }}
  .k {{ font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: #999; margin-bottom: 2px; }}
  .v {{ font-size: 13px; line-height: 1.5; }}
  .evidence {{ font-style: italic; color: #555; }}
  details {{ margin-top: 10px; }}
  summary {{ cursor: pointer; font-size: 12px; color: #2563eb; }}
  .transcript {{ margin-top: 10px; padding: 12px 14px; background: #f6f7f9; border-radius: 6px; font-size: 12.5px; line-height: 1.7; max-height: 360px; overflow-y: auto; }}
  .transcript .spk {{ font-weight: 700; color: #333; }}
  .empty {{ background: #fff; border: 1px solid #e6e6e6; border-radius: 8px; padding: 24px; text-align: center; color: #555; }}
  table.cm {{ border-collapse: collapse; margin-bottom: 28px; background: #fff; }}
  table.cm th {{ font-size: 11px; font-weight: 600; color: #777; padding: 8px 14px; text-align: center; }}
  table.cm th.row {{ text-align: right; }}
  table.cm td {{ padding: 12px 18px; text-align: center; border: 1px solid #e6e6e6; min-width: 96px; }}
  table.cm td .n {{ font-size: 22px; font-weight: 700; display: block; }}
  table.cm td .cell {{ font-size: 10px; text-transform: uppercase; letter-spacing: .05em; color: #888; }}
  table.cm td.ok {{ background: #f0fdf4; }}
  table.cm td.ok .n {{ color: #166534; }}
  table.cm td.bad {{ background: #fef2f2; }}
  table.cm td.bad .n {{ color: #991b1b; }}
</style></head><body>
  <h1>{html_lib.escape(meta['dimension'])} — judge vs consensus disagreements</h1>
  <div class="meta">
    split <strong>{html_lib.escape(meta['split'])}</strong> &middot; {html_lib.escape(meta['run_time'])} &middot; {html_lib.escape(meta['model'])}<br>
    prompt <code>{html_lib.escape(meta['prompt_file'])}</code> &middot; sha <code>{html_lib.escape(meta['prompt_sha8'])}</code> &middot; git <code>{html_lib.escape(meta['git_commit'] or 'n/a')}</code>{dirty}
  </div>
  <div class="stats">
    <div class="stat"><div class="val">{m.get('total',0)}</div><div class="label">scored</div></div>
    <div class="stat"><div class="val">{m.get('agreement',0):.0%}</div><div class="label">agreement</div></div>
    <div class="stat"><div class="val">{fmt(m.get('tpr'))}</div><div class="label">TPR</div></div>
    <div class="stat"><div class="val">{fmt(m.get('tnr'))}</div><div class="label">TNR</div></div>
    <div class="stat"><div class="val">{fmt(m.get('na_recall'))}</div><div class="label">N/A recall</div></div>
    <div class="stat"><div class="val">{m.get('false_fire',0)}</div><div class="label">false-fires</div></div>
    <div class="stat"><div class="val">{m.get('false_abstain',0)}</div><div class="label">false-abstains</div></div>
    <div class="stat"><div class="val">{len(disagreements)}</div><div class="label">disagreements</div></div>
  </div>
  <h2>Confusion matrix — judge vs consensus</h2>
  <table class="cm">
    <tr><th></th><th>Judge PASS</th><th>Judge FAIL</th><th>Judge N/A</th></tr>
    <tr><th class="row">Consensus PASS</th>
        <td class="ok"><span class="n">{m.get('tp',0)}</span><span class="cell">TP</span></td>
        <td class="bad"><span class="n">{m.get('fn',0)}</span><span class="cell">FN</span></td>
        <td class="bad"><span class="n">{m.get('pass_as_na',0)}</span><span class="cell">false-abstain</span></td></tr>
    <tr><th class="row">Consensus FAIL</th>
        <td class="bad"><span class="n">{m.get('fp',0)}</span><span class="cell">FP</span></td>
        <td class="ok"><span class="n">{m.get('tn',0)}</span><span class="cell">TN</span></td>
        <td class="bad"><span class="n">{m.get('fail_as_na',0)}</span><span class="cell">false-abstain</span></td></tr>
    <tr><th class="row">Consensus N/A</th>
        <td class="bad"><span class="n">{m.get('na_as_pass',0)}</span><span class="cell">false-fire</span></td>
        <td class="bad"><span class="n">{m.get('na_as_fail',0)}</span><span class="cell">false-fire</span></td>
        <td class="ok"><span class="n">{m.get('na_correct',0)}</span><span class="cell">correct N/A</span></td></tr>
  </table>
  <h2>Disagreements ({len(disagreements)})</h2>
  {cards}
</body></html>"""


def main():
    parser = argparse.ArgumentParser(description="Run eval harness (v2, no alpha)")
    parser.add_argument("--prompt", required=True, help="Path to judge prompt YAML")
    parser.add_argument("--split", default="dev", choices=["dev", "test", "live", "round4"], help="Which split to evaluate on (live = round-3 production calls; round4 = round-4 relabel set)")
    parser.add_argument("--consensus", default=str(DEFAULT_CONSENSUS),
                        help="Path to the per-dimension consensus CSV (source_row, consensus_label, excerpt)")
    parser.add_argument("--model", default=MODEL,
                        help=f"Judge model (default {MODEL}); logged with each run")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)
    spec = load_prompt_spec(args.prompt)
    dimension = spec.dimension

    # Load split IDs (source_rows) and the consensus CSV (labels + excerpts)
    split_ids = load_split_ids(args.split, dimension)
    consensus = load_consensus(args.consensus, dimension)

    if not split_ids:
        print(f"ERROR: No source_rows found in {args.split}_ids.csv for dimension '{dimension}'")
        sys.exit(1)

    if not consensus:
        print(f"ERROR: No rows for dimension '{dimension}' in {args.consensus}")
        sys.exit(1)

    print(f"\n{'='*55}")
    print(f"  EVAL HARNESS v2 — {dimension}")
    print(f"  Prompt:    {args.prompt}")
    print(f"  Split:     {args.split} ({len(split_ids)} rows)")
    print(f"  Consensus: {args.consensus}")
    print(f"  Model:     {args.model}")
    print(f"  Positive class: PASS (coach drives practice)")
    print(f"{'='*55}\n")

    results = []
    disagreements = []
    errored = []

    for sr in split_ids:
        if sr not in consensus:
            print(f"  Skipping source_row {sr} — not in consensus CSV for {dimension}")
            continue

        consensus_label = consensus[sr]["label"]
        # N/A is a real, scored class for not-observed-heavy dimensions
        # (e.g. adapts_when_stuck): correct abstention IS the behavior under
        # test, and a judge that invents a signal on a calm call must be
        # penalized. So N/A rows are NO LONGER skipped.

        excerpt = consensus[sr]["excerpt"]
        ceo_id = consensus[sr]["ceo_id"]
        if not excerpt or not excerpt.strip():
            print(f"  Skipping source_row {sr} — empty excerpt")
            continue

        label = f"row {sr} (ceo {ceo_id})"
        print(f"  Scoring {label}...", end=" ")

        try:
            output = run_judge(client, spec, excerpt, args.model)
            judge_label = norm_label(output["result"])
            match = judge_label == consensus_label
            icon = "✅" if match else "❌"

            results.append({
                "transcript_id": sr,
                "ceo_id": ceo_id,
                "consensus": consensus_label,
                "judge": judge_label,
                "match": match,
                "reasoning": output.get("reasoning", ""),
                "evidence": output.get("evidence", ""),
                "transcript": excerpt,
            })

            if not match:
                disagreements.append(results[-1])

            print(f"Consensus: {consensus_label} | Judge: {judge_label} {icon}")

        except Exception as e:
            print(f"ERROR: {e}")
            errored.append((sr, str(e)))

    # Compute and print metrics
    metrics = compute_agreement(results)

    # Extract version from prompt filename (e.g. drives_practice_v2.yaml -> v2)
    prompt_stem = Path(args.prompt).stem
    version = prompt_stem.split("_")[-1] if "_v" in prompt_stem else prompt_stem
    run_date = datetime.now().strftime("%Y-%m-%d")

    print(f"\n{'='*55}")
    print(f"  RESULTS — {dimension} on {args.split} set")
    print(f"{'='*55}")
    print(f"  Agreement:  {metrics.get('matches', 0)}/{metrics.get('total', 0)} ({metrics.get('agreement', 0):.1%})")
    print(f"  TPR (true positive rate — PASS recall):  {fmt(metrics.get('tpr'))}")
    print(f"  TNR (true negative rate — FAIL recall):  {fmt(metrics.get('tnr'))}")
    print(f"  PPV (PASS precision):                    {fmt(metrics.get('ppv'))}")
    print(f"  NPV (FAIL precision):                    {fmt(metrics.get('npv'))}")
    print(f"  N/A recall (correct abstention):         {fmt(metrics.get('na_recall'))}")
    print(f"  False-fires (calm call, judge scored it):  {metrics.get('false_fire', 0)}")
    print(f"  False-abstains (real signal, judge N/A):   {metrics.get('false_abstain', 0)}")
    print(f"\n  Confusion matrix (rows = consensus, cols = judge):")
    print(f"                   Judge PASS  Judge FAIL  Judge N/A")
    print(f"  Consensus PASS   {metrics.get('tp', 0):>7}     {metrics.get('fn', 0):>7}    {metrics.get('pass_as_na', 0):>7}")
    print(f"  Consensus FAIL   {metrics.get('fp', 0):>7}     {metrics.get('tn', 0):>7}    {metrics.get('fail_as_na', 0):>7}")
    print(f"  Consensus N/A    {metrics.get('na_as_pass', 0):>7}     {metrics.get('na_as_fail', 0):>7}    {metrics.get('na_correct', 0):>7}")

    if errored:
        print(f"\n  ⚠️  {len(errored)} row(s) ERRORED and were excluded from metrics: {[e[0] for e in errored]}")

    if disagreements:
        print(f"\n  DISAGREEMENTS ({len(disagreements)}) — judge vs consensus:")
        for d in disagreements:
            print(f"    {d['transcript_id']}: Consensus={d['consensus']}, Judge={d['judge']}")
            print(f"      Reasoning: {d['reasoning']}")
            print(f"      Evidence: {d['evidence'][:120]}")

    # Fingerprint + git state (shared by the HTML report and the run log)
    sha8, raw = prompt_fingerprint(args.prompt)
    archive_path = archive_prompt(args.prompt, sha8, raw)
    git_commit, prompt_dirty = git_state(args.prompt)
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs(BASE_DIR / "outputs", exist_ok=True)
    stem = Path(args.prompt).stem

    # Save disagreements to CSV
    output_path = BASE_DIR / "outputs" / f"{stem}_{args.split}_disagreements.csv"
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["transcript_id", "consensus", "judge", "reasoning", "evidence"],
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(disagreements)
    print(f"\n  Disagreements (CSV):  {output_path}")

    # Save disagreements as a browsable HTML report
    html_path = BASE_DIR / "outputs" / f"{stem}_{args.split}_disagreements.html"
    html_path.write_text(generate_disagreements_html(disagreements, metrics, {
        "dimension": dimension,
        "split": args.split,
        "run_time": run_time,
        "model": args.model,
        "prompt_file": Path(args.prompt).name,
        "prompt_sha8": sha8,
        "git_commit": git_commit,
        "prompt_dirty": prompt_dirty,
    }))
    print(f"  Disagreements (HTML): {html_path}")

    # Append to the run log
    log_run({
        "timestamp": run_time,
        "dimension": dimension,
        "split": args.split,
        "model": args.model,
        "prompt_file": Path(args.prompt).name,
        "version": version,
        "prompt_sha8": sha8,
        "git_commit": git_commit,
        "prompt_dirty": "dirty" if prompt_dirty else "clean",
        "n": metrics.get("total", 0),
        "agreement": f"{metrics.get('agreement', 0):.4f}" if metrics.get("agreement") is not None else "",
        "tpr": fmt(metrics.get("tpr")),
        "tnr": fmt(metrics.get("tnr")),
        "ppv": fmt(metrics.get("ppv")),
        "npv": fmt(metrics.get("npv")),
        "na_recall": fmt(metrics.get("na_recall")),
        "tp": metrics.get("tp", 0),
        "fp": metrics.get("fp", 0),
        "tn": metrics.get("tn", 0),
        "fn": metrics.get("fn", 0),
        "false_fire": metrics.get("false_fire", 0),
        "false_abstain": metrics.get("false_abstain", 0),
        "disagreements_file": output_path.name,
    })
    dirty_flag = " +dirty" if prompt_dirty else ""
    print(f"  Run logged to: {RUN_LOG_PATH}  (sha {sha8}, git {git_commit or 'n/a'}{dirty_flag})")
    print(f"  Prompt snapshot: {archive_path.relative_to(BASE_DIR)}")

    # Print Google Sheet copy-paste row
    agr = f"{metrics['agreement']:.1%}" if metrics.get('agreement') is not None else "N/A"

    print(f"\n{'='*55}")
    print(f"  COPY TO GOOGLE SHEET (tab-separated):")
    print(f"{'='*55}")
    print(f"  {dimension}\t{version}\t{run_date}\t\t{agr}\t{fmt(metrics.get('tpr'))}\t{fmt(metrics.get('tnr'))}\t")
    print(f"\n  Columns: Dimension | Version | Date | What Changed | Agreement | TPR | TNR | Decision")
    print(f"  (Fill in 'What Changed' and 'Decision' manually)")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()
