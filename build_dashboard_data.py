"""Build the dashboard prototype from the NEW judge-suite scores (3 variants).

Reads the per-dimension CSVs produced by temp_judge_suite/run_corpus_temp.py:
  - production  -> data/judge_outputs/judge_results.csv        (transcript_id = pcpt row index)
  - 2.0 / 2.1   -> data/judge_outputs/judge_results_variants.csv (transcript_id = v20_*/v21_*)

Joins:
  - production transcript_id -> CEO ID (via the pcpt TSV) -> demographics (report*.csv)
  - variant   transcript_id -> coach + modality (via eval_corpus.tsv)

Adds a modality (voice/text) facet alongside demographics, and derives a per-call
"overall pass" (the suite scores dimensions, not an overall verdict): a call passes
if it doesn't trip the PII wire and passes >=60% of its observed dimensions.

Output: dashboard.html (data inlined).  Re-run:  python build_dashboard_data.py
"""

import argparse
import csv
import glob
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

csv.field_size_limit(10**7)

TEMPLATE = "dashboard_template.html"
OUTPUT = "dashboard.html"
PROD_CSV = "temp_judge_suite/data/judge_outputs/judge_results.csv"
VARIANTS_CSV = "temp_judge_suite/data/judge_outputs/judge_results_variants.csv"
CORPUS = "eval_corpus.tsv"
PCPT = "pcpt_mock_interview_v2.tsv"
DEMO_GLOB = "report*.csv"

# suite dimension id -> (display name, short section)
# Rubric v2 (2026-07-08): feedback_correct split into 4 brackets (question/summary x high/low).
DIMENSIONS = [
    ("scaffolds_fades", "Scaffolds (user's own material)", "Meeting"),
    ("adapts_when_stuck", "Adapts when stuck", "Social-emotional"),
    ("kind_delivery", "Kind delivery", "Social-emotional"),
    ("reentry_framing", "Reentry-appropriate framing", "Social-emotional"),
    ("limits_the_load", "Limits the load", "Motivates"),
    ("feedback_question_high_bar", "Question feedback — high bar", "Motivates"),
    ("feedback_question_low_bar", "Question feedback — low bar", "Motivates"),
    ("feedback_summary_high_bar", "Summary feedback — high bar", "Motivates"),
    ("feedback_summary_low_bar", "Summary feedback — low bar", "Motivates"),
    ("makes_dialogue", "Makes it a dialogue", "Motivates"),
    ("drives_practice", "Drives practice & uptake", "Motivates"),
    ("conversational_flow", "Quality of conversational flow", "Technical"),
    ("pii", "PII handling", "Technical"),
]
DIM_IDS = [d[0] for d in DIMENSIONS]
# Aspirational bars: pass = exceptional coaching, expected to fail on ~every current
# call. Excluded from the derived overall verdict so they don't drown it. Besides the
# *_high_bar brackets, makes_dialogue is aspirational by design — its pass bar is TARGET
# behavior no corpus coach meets (0 PASS across all 825), so it's excluded too.
ASPIRATIONAL_EXTRA = {"makes_dialogue"}
HIGH_BAR_DIMS = {d for d in DIM_IDS if d.endswith("_high_bar") or d in ASPIRATIONAL_EXTRA}

# The certified hero judges (judge-suite/outputs/corpus_hero_results.csv) use
# their own dimension ids; map them onto the dashboard's canonical ids so the
# same builder can render either source.
DIM_ALIASES = {
    "scaffolds_then_fades": "scaffolds_fades",
    "drives_practice_uptake": "drives_practice",
    "quality_conversational_flow": "conversational_flow",
    "reentry_appropriate_framing": "reentry_framing",
    "makes_it_a_dialogue": "makes_dialogue",
    # adapts_when_stuck, limits_the_load, pii already match.
}


def dim_definitions():
    """Rubric-v2 definitions from calibration/rubric.py (source of truth), keyed
    by the dashboard's canonical dim ids.  {} if the rubric can't be loaded."""
    import importlib.util
    src = Path(__file__).resolve().parent / "calibration" / "rubric.py"
    try:
        spec = importlib.util.spec_from_file_location("_calibration_rubric", src)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:
        print(f"  ! couldn't load {src} ({e}) — dimension definitions omitted")
        return {}
    return {DIM_ALIASES.get(d["id"], d["id"]): {"def": d["definition"], "watch": d["watch_for"]}
            for d in mod.DIMENSIONS}

VARIANTS = [
    ("prod", "PCPT v2 (production)"),
    ("v20", "Voice Coach 2.0"),
    ("v21", "Voice Coach 2.1"),
]
COACH_TO_CODE = {"Voice Coach 2.0": "v20", "Voice Coach 2.1": "v21"}

PROMPT_DIFFS = {
    "v20|v21": [
        ("del", "Step 1: Interview Readiness Assessment — state \"Interview Ready\" or \"Needs More Work\" before feedback."),
        ("add", "(removed) — 2.1 goes straight to Strength → Improvement → Coaching → Retry, with no readiness verdict."),
    ],
}

UNKNOWN_DEMO = {"site": "Unknown", "population": "Unknown", "age": "Unknown",
                "gender": "Unknown", "race": "Unknown", "education": "Unknown"}
RACE_KEEP = {"Black or African American", "Hispanic or Latino", "White", "Asian",
             "American Indian/Alaskan Native"}


def norm(v):
    return "na" if v in (None, "", "N/A", "not_observed") else v


def age_bucket(raw):
    try:
        a = int(float(raw))
    except (ValueError, TypeError):
        return "Unknown"
    return "18-24" if a < 25 else "25-34" if a < 35 else "35-44" if a < 45 else "45-54" if a < 55 else "55+"


def race_rollup(raw):
    raw = (raw or "").strip()
    if not raw:
        return "Unknown"
    if ";" in raw:
        return "Two or more"
    return raw if raw in RACE_KEEP else "Other"


def gender_rollup(raw):
    raw = (raw or "").strip()
    return raw if raw in ("Male", "Female") else "Other / undisclosed"


def norm_ceo(cid):
    """Join key: trim + drop leading zeros (matches join_demographics.py)."""
    cid = (cid or "").strip()
    return cid.lstrip("0") or cid


DUR_ORDER = ["< 2 min", "2–5 min", "5–10 min", "10–20 min", "20+ min"]


def dur_bucket(minutes):
    """Call-duration facet bucket from minutes (accepts float/str)."""
    try:
        m = float(minutes)
    except (ValueError, TypeError):
        return "Unknown"
    return ("< 2 min" if m < 2 else "2–5 min" if m < 5 else
            "5–10 min" if m < 10 else "10–20 min" if m < 20 else "20+ min")


def day_iso(ts):
    """Parse an ISO or m/d/Y timestamp -> 'YYYY-MM-DD' (None if unparseable)."""
    ts = (ts or "").strip()
    for fmt in (None, "%m/%d/%Y %H:%M", "%m/%d/%Y"):
        try:
            d = (datetime.fromisoformat(ts.replace("Z", "+00:00")) if fmt is None
                 else datetime.strptime(ts, fmt)).date()
            return d.isoformat()
        except ValueError:
            continue
    return None


def week_bucket(ts):
    """Call-date facet bucket: ISO week starting Monday ('Wk of 2026-07-28').
    ISO date in the label means plain string sort = chronological sort."""
    day = day_iso(ts)
    if not day:
        return "Unknown"
    d = datetime.fromisoformat(day).date()
    return f"Wk of {(d - timedelta(days=d.weekday())).isoformat()}"


def load_demographics():
    # Union of ALL report*.csv exports, oldest first, so a newly dropped export
    # extends coverage (new enrollees) and overrides stale rows without needing
    # to delete the old file.
    files = sorted(glob.glob(DEMO_GLOB), key=os.path.getmtime)
    if not files:
        return {}
    demo = {}
    for path in files:
        # One row per ENROLLMENT — re-enrolled participants repeat with different
        # "Age at Enrollment"; keep the latest enrollment (max age) within a file.
        best_age = {}
        with open(path, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                key = norm_ceo(r["CEO Code"])
                try:
                    raw_age = int(float(r.get("Age at Enrollment") or 0))
                except (ValueError, TypeError):
                    raw_age = 0
                if key in best_age and raw_age < best_age[key]:
                    continue
                best_age[key] = raw_age
                demo[key] = {
                    "site": (r.get("CEO Location: Site Name") or "Unknown").replace("CEO ", "").strip() or "Unknown",
                    "population": (r.get("Referral Population") or "Unknown").strip() or "Unknown",
                    "age": age_bucket(r.get("Age at Enrollment")),
                    "gender": gender_rollup(r.get("Participant: Gender")),
                    "race": race_rollup(r.get("Participant: Race/Ethnicity")),
                    "education": (r.get("Education Level Sub-Category") or "Unknown").strip() or "Unknown",
                }
    return demo


def load_suite(path):
    """transcript_id -> {dim_id: (result, reasoning)}."""
    calls = defaultdict(dict)
    if not Path(path).exists():
        print(f"  ! {path} missing")
        return calls
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            did = DIM_ALIASES.get(r["dimension_id"], r["dimension_id"])
            # Hero results emit PASS/FAIL/N-A; the dashboard vocabulary is
            # lowercase pass/fail (N/A handled by norm()). Normalize case.
            res = (r.get("result") or "").strip()
            low = res.lower()
            res = "pass" if low == "pass" else "fail" if low == "fail" else res
            calls[r["transcript_id"]][did] = (res, r.get("reasoning", ""))
    return calls


def derive_overall(dims):
    """No overall verdict from the suite — derive one. Fail if PII tripped or the
    call passes <60% of observed dimensions. High-bar bracket dims are excluded:
    they define target behavior and fail nearly every current call by design."""
    if dims.get("pii") == "fail":
        return "fail"
    obs = [v for d, v in dims.items() if v in ("pass", "fail") and d not in HIGH_BAR_DIMS]
    if not obs:
        return "fail"
    return "pass" if sum(v == "pass" for v in obs) / len(obs) >= 0.6 else "fail"


def make_record(tid, dimmap, variant, demo):
    dims = {d: norm(dimmap.get(d, (None,))[0]) for d in DIM_IDS}
    why = {d: dimmap[d][1] for d in DIM_IDS
           if d in dimmap and dimmap[d][0] == "fail" and dimmap[d][1]}
    return {
        "id": tid, "ceo": demo.get("ceo", ""), "variant": variant,
        "recommend": derive_overall(dims), "dims": dims, "why": why,
        "summary": "", "demo": {k: demo.get(k, "Unknown")
                                for k in (*UNKNOWN_DEMO, "modality", "duration", "date")},
        "dur": demo.get("dur"), "day": demo.get("day"),
    }


def facet_options(records):
    facets = {}
    for key in ("site", "population", "age", "gender", "race", "education", "modality",
                "duration", "date"):
        present = {r["demo"][key] for r in records if r["demo"].get(key) and r["demo"][key] != "Unknown"}
        # duration gets its canonical short->long order; everything else sorts
        # (date labels embed an ISO date, so sorted = chronological)
        vals = [v for v in DUR_ORDER if v in present] if key == "duration" else sorted(present)
        if any(r["demo"].get(key, "Unknown") == "Unknown" for r in records):
            vals.append("Unknown")
        facets[key] = vals
    return facets


def main():
    ap = argparse.ArgumentParser(description="Build the coach-eval dashboard from judge scores.")
    ap.add_argument("--prod", default=PROD_CSV, help="production per-dimension CSV (transcript_id, dimension_id, result)")
    ap.add_argument("--pcpt", default=PCPT, help="TSV whose row order maps transcript_id -> CEO ID")
    ap.add_argument("--out", default=OUTPUT, help="output HTML path")
    ap.add_argument("--dims", default=None,
                    help="comma-separated canonical dimension ids to include (subset); default = all 13")
    ap.add_argument("--only-prod", action="store_true", help="render only the production variant (skip 2.0/2.1)")
    args = ap.parse_args()

    global DIMENSIONS, DIM_IDS, HIGH_BAR_DIMS, VARIANTS
    if args.dims:
        keep = [d.strip() for d in args.dims.split(",") if d.strip()]
        DIMENSIONS = [t for t in DIMENSIONS if t[0] in keep]
        DIM_IDS = [d[0] for d in DIMENSIONS]
        HIGH_BAR_DIMS = {d for d in DIM_IDS if d.endswith("_high_bar") or d in ASPIRATIONAL_EXTRA}
    if args.only_prod:
        VARIANTS = [v for v in VARIANTS if v[0] == "prod"]

    demo_map = load_demographics()
    pcpt_ceo = {}
    if Path(args.pcpt).exists():
        with open(args.pcpt, newline="", encoding="utf-8") as fh:
            for i, row in enumerate(csv.DictReader(fh, delimiter="\t")):
                raw_dur = row.get("Call Duration (minutes with decimal precision)")
                try:
                    raw_dur = round(float(raw_dur), 1)
                except (ValueError, TypeError):
                    raw_dur = None
                pcpt_ceo[str(i)] = (
                    str(row.get("CEO ID", "")).strip(),
                    dur_bucket(raw_dur),
                    week_bucket(row.get("Start time Pacific")),
                    raw_dur,
                    day_iso(row.get("Start time Pacific")),
                )

    records = []
    # production
    for tid, dimmap in load_suite(args.prod).items():
        ceo, dur, wk, raw_dur, day = pcpt_ceo.get(tid, ("", "Unknown", "Unknown", None, None))
        d = dict(demo_map.get(norm_ceo(ceo)) or UNKNOWN_DEMO)
        d["modality"] = "voice"
        d["ceo"] = ceo
        d["duration"] = dur
        d["date"] = wk
        d["dur"] = raw_dur
        d["day"] = day
        records.append(make_record(tid, dimmap, "prod", d))
    n_prod = len(records)

    # variants (2.0 / 2.1) — coach + modality from the corpus
    if not args.only_prod:
        corpus_meta = {}
        if Path(CORPUS).exists():
            with open(CORPUS, newline="", encoding="utf-8") as fh:
                for r in csv.DictReader(fh, delimiter="\t"):
                    corpus_meta[r["transcript_id"]] = (r["coach"], r["modality"])
        for tid, dimmap in load_suite(VARIANTS_CSV).items():
            coach, modality = corpus_meta.get(tid, (None, "?"))
            code = COACH_TO_CODE.get(coach)
            if not code:
                continue
            d = dict(UNKNOWN_DEMO)
            d["modality"] = modality
            d["ceo"] = ""
            records.append(make_record(tid, dimmap, code, d))

    variants = []
    for vid, label in VARIANTS:
        recs = [r for r in records if r["variant"] == vid]
        variants.append({
            "id": vid, "label": label, "n": len(recs),
            "hasDemo": any(r["demo"]["site"] != "Unknown" for r in recs),
        })

    defs = dim_definitions()
    payload = {
        "dimensions": [{"id": i, "name": n, "section": s, **defs.get(i, {})}
                       for i, n, s in DIMENSIONS],
        "facets": facet_options(records),
        "variants": variants,
        "promptDiffs": {k: [{"type": t, "text": x} for t, x in v] for k, v in PROMPT_DIFFS.items()},
        "records": records,
        "n": len(records),
        "source": "10-judge suite (per-dimension pass/fail); overall = derived (no PII trip + ≥60% dims pass)",
    }

    tpl = Path(TEMPLATE)
    if not tpl.exists():
        Path("dashboard_data.json").write_text(json.dumps(payload))
        print(f"  ! {TEMPLATE} missing — wrote dashboard_data.json only.")
        return
    html = tpl.read_text().replace("/*__DATA__*/{}", json.dumps(payload))
    Path(args.out).write_text(html)
    print(f"  wrote {args.out} ({round(len(html)/1024)} KB)")
    for v in variants:
        print(f"    {v['label']:<24} n={v['n']}")


if __name__ == "__main__":
    main()
