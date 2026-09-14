"""[low-code] Minimal eval harness — wire your prototype, write a handful of cases, run.

  1. Point call_prototype() at YOUR prototype (the default body is a working
     single-call baseline so the sample cases run out of the box).
  2. Edit test_cases.json — 5 cases is plenty to start.
  3. python run_eval.py            → calls the prototype, grades, saves results.json
     python run_eval.py --rejudge  → re-grades the saved outputs only (no model calls)
"""
import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable

# Load .env only if ANTHROPIC_API_KEY is not already in environment
if not os.environ.get("ANTHROPIC_API_KEY"):
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent / ".env")
    except ImportError:
        pass  # python-dotenv not available; rely on environment

from judge import judge

HERE = Path(__file__).parent
RESULTS = HERE / "results.json"
# RUBRIC = HERE / "prompts" / "limits_the_load_v2.md"
RUBRIC = HERE / "prompts" / "feedback_question_low_bar.md"


def call_prototype(input_data: dict) -> dict:
    """Return the judge's full response on the transcript.

    input_data should contain:
      - "transcript": the full transcript text to judge

    Returns the full judge response dict with step1_scan, verdict, and reasoning.
    """
    transcript = input_data.get("transcript", "")
    if not transcript:
        return {"verdict": "fail", "reasoning": "ERROR: no transcript provided"}

    result = judge(transcript, RUBRIC)
    # Store full response in input_data for reference
    input_data["_judge_response"] = result
    return result


def check(case: dict, output: object) -> tuple[bool, str]:
    """Return (passed, detail). check_type: exact | contains | custom.

    output can be a dict (full judge response) or string (just verdict).
    """
    expected = case.get("expected")
    kind = case.get("check_type", "exact")

    # Extract verdict if output is a dict
    verdict = output.get("verdict") if isinstance(output, dict) else output

    if kind == "exact":
        ok = str(verdict).strip().lower().rstrip(".!?,") == str(expected).strip().lower()
        return ok, f"expected {expected!r}, got {verdict!r}"
    if kind == "contains":
        ok = str(expected).lower() in str(verdict).lower()
        return ok, f"expected output to contain {expected!r}"
    if kind == "custom":
        fn = CUSTOM_CHECKS.get(str(expected))
        if fn is None:
            return False, f"no custom check registered as {expected!r} (add it to CUSTOM_CHECKS)"
        ok, detail = fn(case, verdict if isinstance(verdict, str) else str(verdict))
        return bool(ok), str(detail)
    return False, f"unknown check_type {kind!r}"


# --- custom checks: register yours here -----------------------------------
# A custom check takes (case, output) and returns (passed: bool, detail: str).
# Reference it from test_cases.json as {"check_type": "custom", "expected": "is_json"}.
CheckFn = Callable[[dict, str], tuple[bool, str]]


def is_json(_case: dict, output: str) -> tuple[bool, str]:
    try:
        json.loads(output)
        return True, "valid JSON"
    except Exception as e:
        return False, f"not JSON: {e}"


CUSTOM_CHECKS: dict[str, CheckFn] = {
    "is_json": is_json,
}


def get_git_commit() -> str:
    """Get current short commit hash from repo root."""
    try:
        # Find repo root by going up from script directory
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=HERE,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            return "unknown"

        repo_root = result.stdout.strip()

        # Now get the commit hash from repo root
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def get_dimension_name() -> str:
    """Extract dimension name from rubric prompt."""
    try:
        rubric_text = RUBRIC.read_text()
        # Look for the title in the rubric markdown
        for line in rubric_text.split('\n'):
            if line.startswith('# '):
                return line[2:].strip()
        return "unknown"
    except Exception:
        return "unknown"


def calculate_metrics(results: list) -> tuple:
    """Calculate TPR, TNR, and list of disagreements.

    Returns: (tp, tn, fp, fn, tpr, tnr, disagreement_names)
    """
    tp = tn = fp = fn = 0
    disagreements = []

    for result in results:
        expected = result.get('expected', '').lower()
        output = result.get('output', {})
        name = result.get('name', '')

        # Extract verdict from output (can be dict or string for backwards compat)
        if isinstance(output, dict):
            verdict = output.get('verdict', '').lower()
        else:
            verdict = str(output).lower()

        if expected == 'pass':
            if verdict == 'pass':
                tp += 1
            else:
                fn += 1
                disagreements.append(name)
        else:  # expected == 'fail'
            if verdict == 'fail':
                tn += 1
            else:
                fp += 1
                disagreements.append(name)

    tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    tnr = tn / (tn + fp) if (tn + fp) > 0 else 0.0

    return tp, tn, fp, fn, tpr, tnr, disagreements


def update_disagreements_html(results: list) -> None:
    """Regenerate disagreements.html with latest results data."""
    html_path = HERE / "disagreements.html"
    json_data = json.dumps(results)

    # Get dimension name from rubric
    dimension = get_dimension_name()

    # Calculate overall accuracy
    correct = sum(1 for r in results if r.get("passed"))
    total = len(results)
    accuracy = correct / total if total > 0 else 0

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Judge Disagreements — {dimension}</title>
    <style>
        :root {{
            --bg-primary: #ffffff;
            --text-primary: #212121;
            --text-secondary: #616161;
            --border: #d0d0d0;
            --success: #388e3c;
            --error: #d32f2f;
        }}
        @media (prefers-color-scheme: dark) {{
            :root {{
                --bg-primary: #1a1a1a;
                --text-primary: #ffffff;
                --text-secondary: #b0b0b0;
                --border: #424242;
            }}
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            font-size: 15px;
            line-height: 1.5;
            color: var(--text-primary);
            background: var(--bg-primary);
        }}
        .container {{
            display: grid;
            grid-template-columns: 240px 1fr;
            min-height: 100vh;
        }}
        .header {{
            grid-column: 1 / -1;
            padding: 2rem;
            border-bottom: 1px solid var(--border);
        }}
        .header h1 {{
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 0.25rem;
        }}
        .header p {{
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-bottom: 1rem;
        }}
        .accuracy-box {{
            font-size: 0.9rem;
            line-height: 1.4;
        }}
        .accuracy-label {{
            color: var(--text-secondary);
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}
        .accuracy-value {{
            font-size: 1.1rem;
            font-weight: 600;
            margin-top: 0.25rem;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.75rem;
            margin-top: 1rem;
            font-size: 0.8rem;
        }}
        .metric-box {{
            padding: 0.75rem;
            border: 2px solid var(--border);
            border-radius: 4px;
            text-align: center;
        }}
        .metric-label {{
            font-size: 0.65rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: var(--text-secondary);
            margin-bottom: 0.25rem;
        }}
        .metric-value {{
            font-size: 1.25rem;
            font-weight: 700;
        }}
        .metric-box.good {{
            border-color: var(--success);
        }}
        .metric-box.bad {{
            border-color: var(--error);
        }}
        .sidebar {{
            padding: 1.5rem;
            border-right: 1px solid var(--border);
        }}
        .sidebar input {{
            width: 100%;
            padding: 0.6rem;
            margin-bottom: 1rem;
            border: 1px solid var(--border);
            border-radius: 3px;
            background: var(--bg-primary);
            color: var(--text-primary);
            font-size: 0.85rem;
        }}
        .sidebar h3 {{
            font-size: 0.7rem;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
            color: var(--text-secondary);
            font-weight: 600;
            letter-spacing: 0.04em;
        }}
        .sidebar button {{
            width: 100%;
            padding: 0.6rem;
            margin-bottom: 0.4rem;
            border: 1px solid var(--border);
            border-radius: 3px;
            background: var(--bg-primary);
            color: var(--text-primary);
            cursor: pointer;
            font-size: 0.85rem;
            transition: all 0.15s ease;
        }}
        .sidebar button:hover {{
            border-color: var(--text-primary);
        }}
        .sidebar button.active {{
            background: var(--text-primary);
            color: var(--bg-primary);
            border-color: var(--text-primary);
        }}
        .main {{
            padding: 2rem;
            overflow-y: auto;
        }}
        .card {{
            border: 1px solid var(--border);
            border-radius: 4px;
            margin-bottom: 1rem;
            background: var(--bg-primary);
        }}
        .card-header {{
            padding: 1rem;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
        }}
        .card-id {{
            font-family: monospace;
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin-bottom: 0.4rem;
        }}
        .card-verdict {{
            display: flex;
            gap: 0.75rem;
            align-items: center;
            font-size: 0.8rem;
        }}
        .verdict-label {{
            display: inline-block;
            padding: 0.3rem 0.5rem;
            border-radius: 3px;
            font-weight: 600;
            color: var(--text-primary);
        }}
        .verdict-label.pass {{
            border: 1px solid var(--success);
            color: var(--success);
        }}
        .verdict-label.fail {{
            border: 1px solid var(--error);
            color: var(--error);
        }}
        .toggle-btn {{
            padding: 0.4rem 0.8rem;
            border: 1px solid var(--border);
            background: var(--bg-primary);
            border-radius: 3px;
            cursor: pointer;
            font-size: 0.8rem;
            white-space: nowrap;
        }}
        .toggle-btn:hover {{
            border-color: var(--text-primary);
        }}
        .card-content {{
            display: none;
            padding: 1rem;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
        }}
        .card.expanded .card-content {{
            display: grid;
        }}
        .card-section {{
            min-width: 0;
        }}
        .card-section h4 {{
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: var(--text-secondary);
            margin-bottom: 0.5rem;
        }}
        .reasoning {{
            font-size: 0.85rem;
            line-height: 1.5;
            border-left: 2px solid var(--border);
            padding-left: 0.75rem;
        }}
        .transcript {{
            font-family: monospace;
            font-size: 0.8rem;
            line-height: 1.5;
            max-height: 300px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-word;
        }}
        .speaker-turn {{
            margin-bottom: 0.5rem;
        }}
        .speaker-label {{
            font-weight: 600;
            color: var(--text-secondary);
            margin-bottom: 0.1rem;
        }}
        .empty-state {{
            text-align: center;
            padding: 2rem;
            color: var(--text-secondary);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Judge Disagreements</h1>
            <p>{dimension} rubric</p>
            <div class="accuracy-box">
                <div class="accuracy-label">Accuracy</div>
                <div class="accuracy-value">{correct}/{total} ({accuracy*100:.0f}%)</div>
            </div>
            <div class="metrics-grid">
                <div class="metric-box good"><div class="metric-label">TP</div><div class="metric-value" id="tp">—</div></div>
                <div class="metric-box bad"><div class="metric-label">FP</div><div class="metric-value" id="fp">—</div></div>
                <div class="metric-box bad"><div class="metric-label">FN</div><div class="metric-value" id="fn">—</div></div>
                <div class="metric-box good"><div class="metric-label">TN</div><div class="metric-value" id="tn">—</div></div>
            </div>
        </div>
        <div class="sidebar">
            <input type="text" id="search" placeholder="Search by ID...">
            <h3>Filters</h3>
            <button class="filter-btn active" data-filter="all">All</button>
            <button class="filter-btn" data-filter="pass-to-fail">Label: pass → Fail</button>
            <button class="filter-btn" data-filter="fail-to-pass">Label: fail → Pass</button>
        </div>
        <div class="main" id="main"><div class="empty-state">Loading...</div></div>
    </div>
    <script>
        let allResults = {json_data};
        let disagreements = [];
        let currentFilter = 'all';

        function calculateMetrics() {{
            let tp = 0, tn = 0, fp = 0, fn = 0;
            for (const r of allResults) {{
                const exp = (r.expected || '').toLowerCase();
                const output = r.output || {{}};
                const out = (typeof output === 'object' ? (output.verdict || '') : (output || '')).toLowerCase();
                if (exp === 'pass') {{
                    tp += out === 'pass' ? 1 : 0;
                    fn += out !== 'pass' ? 1 : 0;
                }} else {{
                    tn += out === 'fail' ? 1 : 0;
                    fp += out !== 'fail' ? 1 : 0;
                }}
            }}
            document.getElementById('tp').textContent = tp;
            document.getElementById('fp').textContent = fp;
            document.getElementById('fn').textContent = fn;
            document.getElementById('tn').textContent = tn;
        }}

        function formatTranscript(text) {{
            if (!text) return '';
            const html = text.replace(/</g, '&lt;').replace(/>/g, '&gt;');
            const parts = html.split(/(User:|AI:)/);
            let result = '';
            for (let i = 1; i < parts.length; i += 2) {{
                const speaker = parts[i].replace(':', '').trim();
                const content = (parts[i + 1] || '').trim();
                if (content) {{
                    result += `<div class="speaker-turn"><div class="speaker-label">${{speaker}}:</div><div>${{content}}</div></div>`;
                }}
            }}
            return result;
        }}

        function render(search = '') {{
            let filtered = disagreements.filter(d => {{
                const match = !search || d.name.includes(search);
                const output = d.output || {{}};
                const verdict = (typeof output === 'object' ? (output.verdict || '') : (output || '')).toLowerCase();
                const typeMatch =
                    currentFilter === 'all' ||
                    (currentFilter === 'pass-to-fail' && d.expected === 'pass' && verdict === 'fail') ||
                    (currentFilter === 'fail-to-pass' && d.expected === 'fail' && verdict === 'pass');
                return match && typeMatch;
            }}).sort((a, b) => parseInt(a.name.split('_')[2]) - parseInt(b.name.split('_')[2]));

            if (!filtered.length) {{
                document.getElementById('main').innerHTML = '<div class="empty-state"><h3>No disagreements found</h3></div>';
                return;
            }}

            document.getElementById('main').innerHTML = filtered.map(d => {{
                const output = d.output || {{}};
                const j = (typeof output === 'object' ? output : {{}});
                const s = j.step1_scan || {{}};
                const verdict = (typeof output === 'object' ? (output.verdict || '') : (output || ''));
                const id = d.name.split('_')[2];
                return `
                    <div class="card">
                        <div class="card-header">
                            <div>
                                <div class="card-id">source_row_${{id}}</div>
                                <div class="card-verdict">
                                    <span class="verdict-label ${{d.expected}}">Label: ${{d.expected}}</span>
                                    <span style="color: var(--text-secondary);">→</span>
                                    <span class="verdict-label ${{verdict}}">Judge: ${{verdict}}</span>
                                </div>
                            </div>
                            <button class="toggle-btn">View</button>
                        </div>
                        <div class="card-content" style="display: none;">
                            <div class="card-section">
                                <h4>Reasoning</h4>
                                <div class="reasoning">${{j.reasoning || '(none)'}}</div>
                            </div>
                            <div class="card-section">
                                <h4>Transcript</h4>
                                <div class="transcript">${{formatTranscript(d.input?.transcript || '')}}</div>
                            </div>
                        </div>
                    </div>
                `;
            }}).join('');

            document.querySelectorAll('.toggle-btn').forEach(btn => {{
                btn.onclick = () => btn.closest('.card').querySelector('.card-content').style.display =
                    btn.closest('.card').querySelector('.card-content').style.display === 'grid' ? 'none' : 'grid';
            }});
        }}

        disagreements = allResults.filter(r => {{
            const output = r.output || {{}};
            const verdict = (typeof output === 'object' ? (output.verdict || '') : (output || '')).toLowerCase();
            return r.expected.toLowerCase() !== verdict;
        }});
        calculateMetrics();
        render();

        document.querySelectorAll('.filter-btn').forEach(btn => {{
            btn.onclick = (e) => {{
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                currentFilter = e.target.dataset.filter;
                render();
            }};
        }});

        document.getElementById('search').oninput = (e) => render(e.target.value);
    </script>
</body>
</html>'''

    html_path.write_text(html)


def log_run(results: list, passed: int) -> None:
    """Append run metrics to run_log.csv."""
    log_path = HERE / "run_log.csv"

    # Calculate metrics
    tp, tn, fp, fn, tpr, tnr, disagreements = calculate_metrics(results)
    total_cases = len(results)
    accuracy = passed / total_cases if total_cases > 0 else 0.0

    # Define column order
    fieldnames = ["timestamp", "dimension", "commit_hash", "accuracy", "tpr", "tnr", "total", "correct", "disagreements"]

    # Prepare row
    row = {
        "timestamp": datetime.now().isoformat(),
        "dimension": get_dimension_name(),
        "commit_hash": get_git_commit(),
        "accuracy": f"{accuracy:.3f}",
        "tpr": f"{tpr:.3f}",
        "tnr": f"{tnr:.3f}",
        "total": total_cases,
        "correct": passed,
        "disagreements": ",".join(disagreements),
    }

    # Create file with headers if it doesn't exist
    if not log_path.exists():
        with open(log_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

    # Append row
    with open(log_path, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writerow(row)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cases", nargs="?", default=str(HERE / "test_cases.json"))
    ap.add_argument("--rejudge", action="store_true",
                    help="re-grade saved outputs in results.json without re-calling the prototype")
    args = ap.parse_args()

    cases = json.loads(Path(args.cases).read_text())
    saved = {}
    if args.rejudge:
        if not RESULTS.exists():
            print("✗ --rejudge needs a prior results.json; run once without the flag first.")
            return 1
        saved = {r["name"]: r.get("output", "") for r in json.loads(RESULTS.read_text())}

    results, passed = [], 0
    for i, case in enumerate(cases, 1):
        name = case.get("id") or case.get("name", f"case {i}")
        try:
            output = saved[name] if args.rejudge else call_prototype(case.get("input", {}))
        except KeyError:
            print(f"✗ {name}: no saved output to rejudge (re-run without --rejudge)")
            continue
        except Exception as e:  # noqa: BLE001 — surface any prototype error
            print(f"✗ {name}: prototype raised {type(e).__name__}: {e}")
            results.append({"name": name, "error": str(e)})
            continue
        ok, detail = check(case, output)
        passed += int(ok)
        print(f"{'✓' if ok else '✗'} {name}: {detail}")
        result_entry = {"name": name, "input": case.get("input"),
                        "expected": case.get("expected"), "check_type": case.get("check_type"),
                        "output": output, "passed": ok}
        results.append(result_entry)

    if not args.rejudge:
        RESULTS.write_text(json.dumps(results, indent=2))
        log_run(results, passed)
        update_disagreements_html(results)

    print(f"\n{passed}/{len(cases)} passed")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
