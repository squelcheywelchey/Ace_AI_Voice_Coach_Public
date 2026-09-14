"""Build the A/B coach-eval dashboard from the LIVE Supabase eval output.

LEGACY / OFFLINE FALLBACK (demoted 2026-08-11). The live boards are served by
ceo-eval-server/dashboard.py on Railway, which is the SOURCE OF TRUTH for this
build logic — edit shared logic THERE and port it here, never the other
direction; dashboard_template.html is likewise canonical in ceo-eval-server
(copy it verbatim). This script is kept for offline builds joining the local
Salesforce report*.csv directly, without touching Supabase's
participant_demographics table.

Reads the `ceo_live_calls` table (written by the Railway eval server as real
Vapi voice calls land) and splits calls by `assistant_id` into Arm A vs Arm B,
then renders the SAME dashboard_template.html used for the pcpt/2.0/2.1 board —
so it looks identical, with the built-in per-dimension A-vs-B compare view.

Since 2026-07-28 the LIVE number also routes through the same webhook, so the
table mixes real participant calls with our test calls. Test calls use CEO ID
2222; the builder splits on that (plus a date guard: everything scored before
the live-number swap is test by definition) and writes TWO dashboards:
ab_dashboard.html (test calls) and live_dashboard.html (real calls).

Real-call records are joined to Salesforce demographics (report*.csv export, keyed
on CEO ID, latest enrollment wins) so the live board's site/population/age/gender/
race/education facets work; the live board enforces a min-cell of 10 (small-cell
suppression — participant data). Test calls (2222) stay Unknown.

Env (ceo_voice_coach/.env):  SUPABASE_URL, SUPABASE_KEY   (anon key is fine)
Run:    python build_ab_dashboard.py            ->  ab_dashboard.html + live_dashboard.html
        python build_ab_dashboard.py --selftest    (render 4 fake rows, no creds)
Re-run whenever new calls have landed to refresh the numbers.
"""

import argparse
import difflib
import hashlib
import json
import os
import re
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

from build_dashboard_data import (DUR_ORDER, dim_definitions, dur_bucket,
                                  load_demographics, norm_ceo, week_bucket)

load_dotenv()

TEMPLATE = "dashboard_template.html"
OUTPUT = "ab_dashboard.html"
OUTPUT_REAL = "live_dashboard.html"
# Renamed from ankita_test_calls 2026-08-11 (migration 011 in ceo-eval-server);
# override with SUPABASE_TABLE if querying a pre-migration database.
TABLE = os.environ.get("SUPABASE_TABLE", "ceo_live_calls")

# Test calls verify with CEO ID 2222 (keypad or spoken). Real participant calls
# can only exist after the live number was pointed at the webhook — anything
# scored before that moment is a test call even without a 2222 in the transcript
# (early test calls skipped ID verification or predate the 2222 convention).
TEST_CEO_ID = "2222"
LIVE_SINCE = "2026-07-28T00:04:37"  # UTC, live-number swap
TEST_ID_RE = re.compile(
    r"Keypad Entry:\s*2222\b"
    r"|\b2222\b"
    r"|\btwo[,\s]+two[,\s]+two[,\s]+two\b",
    re.I)

# assistant_id -> variant code, derived from the same ARM_A_ASSISTANT_ID /
# ARM_B_ASSISTANT_ID env vars the eval server routes on (set them in .env to
# match Railway). Hardcoded ids remain only as a fallback when the env vars
# are unset. Swapping a variant = env change, nothing else.
ARM_CODE = {
    os.environ.get("ARM_A_ASSISTANT_ID")
    or os.getenv("VAPI_ARM_A_ASSISTANT_ID", ""): "A",
    os.environ.get("ARM_B_ASSISTANT_ID")
    or os.getenv("VAPI_ARM_B_ASSISTANT_ID", ""): "B",
}
# FALLBACK labels only — the boards normally label each arm with its live
# Vapi assistant name (arm_variants below), so a variant swap needs no code
# edit at all. These show only when Vapi is unreachable or the key is unset.
VARIANTS = [
    ("A", "Arm A — 2.0 prompt (sonnet-4-6)"),
    ("B", "Arm B"),
]

# FALLBACK for the "Key takeaways" bar on the Prompt change tab — used only when
# takeaways can't be generated (no ANTHROPIC_API_KEY / API failure). The normal
# path is build_prompt_takeaways(): Claude summarizes the LIVE A-vs-B prompts at
# build time, cached in TAKEAWAYS_CACHE by prompt hash so the bar always matches
# the deployed prompts and re-runs are free until a prompt changes.
PROMPT_TAKEAWAYS = [
    "<b>The turn loop (Steps A–H):</b> every question now runs segue → ONE question → judge the answer WEAK/STRONG → reflective prompt → capped feedback → one re-attempt rep. 2.0 just asked, lectured feedback, and moved on.",
    "<b>Reflective prompt before feedback on weak answers</b> — a library of prompts (short-answer vs off-target groups) makes the participant assess their own answer first. Targets <i>makes it a dialogue</i>, the #1 corpus failure (~100% ≤2).",
    "<b>Practice is directed, not offered:</b> \"Give it another shot\" instead of \"wanna try again?\"; every answer gets exactly one rep; a decline ends the question — no re-asking or negotiating. Targets <i>drives practice &amp; uptake</i>.",
    "<b>Feedback is capped</b> at one thing that worked + at most two improvements, spoken in 1–2 sentences. Targets <i>limits the load</i>.",
    "<b>Honesty rules:</b> weak answers may not be validated as \"great\" — anchored, direct feedback. Targets over-praise (72% of corpus calls).",
    "<b>Scaffolding rule:</b> may hand the first few words to unstick, never a full model answer. Targets <i>scaffolds (user's own material)</i>.",
    "<b>PII scope narrowed &amp; reentry framing added:</b> only real PII triggers an interruption (CEO ID readback explicitly fine); mentions of incarceration/parole get an acknowledging response, not silence.",
]

# Supabase judge column stem -> dashboard canonical dim id.
JUDGE_TO_DIM = {
    "scaffolds_then_fades": "scaffolds_fades",
    "adapts_when_stuck": "adapts_when_stuck",
    "reentry_appropriate_framing": "reentry_framing",
    "limits_the_load": "limits_the_load",
    "feedback_q_low_bar": "feedback_question_low_bar",
    "makes_it_a_dialogue": "makes_dialogue",
    "drives_practice": "drives_practice",
    "quality_conversational_flow": "conversational_flow",
    "pii": "pii",
}

# dim id -> (display name, section).  Only the 9 dimensions the eval server judges.
DIMENSIONS = [
    ("scaffolds_fades", "Scaffolds (user's own material)", "Meeting"),
    ("adapts_when_stuck", "Adapts when stuck", "Social-emotional"),
    ("reentry_framing", "Reentry-appropriate framing", "Social-emotional"),
    ("limits_the_load", "Limits the load", "Motivates"),
    ("feedback_question_low_bar", "Question feedback — low bar", "Motivates"),
    ("makes_dialogue", "Makes it a dialogue", "Motivates"),
    ("drives_practice", "Drives practice & uptake", "Motivates"),
    ("conversational_flow", "Quality of conversational flow", "Technical"),
    ("pii", "PII handling", "Technical"),
]
DIM_IDS = [d[0] for d in DIMENSIONS]
# makes_dialogue is an aspirational/target bar — excluded from the derived overall
# so it doesn't drown the verdict (same rule as the corpus dashboard).
ASPIRATIONAL = {"makes_dialogue"}

UNKNOWN_DEMO = {"site": "Unknown", "population": "Unknown", "age": "Unknown",
                "gender": "Unknown", "race": "Unknown", "education": "Unknown"}


def norm(v):
    v = (v or "").strip().lower()
    if v in ("pass",):
        return "pass"
    if v in ("fail",):
        return "fail"
    return "na"  # "", n/a, na, not_observed, error


def derive_overall(dims):
    """No overall verdict is stored — derive one. Fail if PII tripped or the call
    passes <60% of its observed (non-aspirational) dimensions."""
    if dims.get("pii") == "fail":
        return "fail"
    obs = [v for d, v in dims.items() if v in ("pass", "fail") and d not in ASPIRATIONAL]
    if not obs:
        return "fail"
    return "pass" if sum(v == "pass" for v in obs) / len(obs) >= 0.6 else "fail"


def make_record(row, variant, demo_map=None):
    dims, why = {}, {}
    for stem, did in JUDGE_TO_DIM.items():
        res = norm(row.get(f"{stem}_verdict"))
        dims[did] = res
        if res == "fail":
            rsn = (row.get(f"{stem}_reasoning") or "").strip()
            if rsn:
                why[did] = rsn
    cid = (row.get("ceo_id") or "").strip()
    ident = ((cid if cid != TEST_CEO_ID else "")
             or (row.get("customer_number") or "")[-4:]
             or (row.get("call_id") or "")[:8] or "call")
    # Salesforce demographics join (report*.csv via build_dashboard_data loader),
    # keyed on the CEO ID captured at phone verification. Test calls (2222) and
    # unverified calls fall through to Unknown.
    demo = dict((demo_map or {}).get(norm_ceo(cid)) or UNKNOWN_DEMO)
    demo["modality"] = "voice"
    try:
        dur_min = float(row.get("duration_sec")) / 60
    except (ValueError, TypeError):
        dur_min = None
    ts = (row.get("started_at") or row.get("scored_at") or "")
    demo["duration"] = dur_bucket(dur_min)
    demo["date"] = week_bucket(ts)
    return {
        "id": row.get("call_id", ""), "ceo": ident, "variant": variant,
        "recommend": derive_overall(dims), "dims": dims, "why": why,
        "summary": (row.get("transcript") or "")[:0], "demo": demo,
        # raw usage fields for the Usage page
        "dur": round(dur_min, 1) if dur_min is not None else None,
        "day": ts[:10] if ts else None,
    }


def is_test_call(row):
    """Test call = verified with CEO ID 2222, or scored before the live swap."""
    if TEST_ID_RE.search(row.get("transcript") or ""):
        return True
    scored = (row.get("scored_at") or "").replace("Z", "")
    return not scored or scored < LIVE_SINCE


def has_real_ceo_id(row):
    """Real participant = a CEO ID was actually captured at verification.
    Drops live-number calls that died before ID verification (no ceo_id)."""
    cid = (row.get("ceo_id") or "").strip()
    return bool(cid) and cid != TEST_CEO_ID


def facet_options(records):
    facets = {}
    for key in ("site", "population", "age", "gender", "race", "education", "modality",
                "duration", "date"):
        present = {r["demo"][key] for r in records
                   if r["demo"].get(key) and r["demo"][key] != "Unknown"}
        # duration keeps its canonical short->long order; date labels embed an ISO
        # date so sorted() = chronological
        vals = [v for v in DUR_ORDER if v in present] if key == "duration" else sorted(present)
        if any(r["demo"].get(key, "Unknown") == "Unknown" for r in records):
            vals.append("Unknown")
        facets[key] = vals
    return facets


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fetch_assistant(aid, key):
    """Pull an assistant's system prompt + model from Vapi."""
    r = requests.get(f"https://api.vapi.ai/assistant/{aid}",
                     headers={"Authorization": f"Bearer {key}"}, timeout=30)
    r.raise_for_status()
    a = r.json()
    model = a.get("model") or {}
    sys_prompt = "\n".join(m.get("content", "") for m in (model.get("messages") or [])
                           if m.get("role") == "system")
    return {"prompt": sys_prompt, "model": model.get("model", "?"), "name": a.get("name", aid)}


def fetch_arm_prompts():
    """Pull both arms' assistants (system prompt + model) from Vapi.
    Returns {"A": {...}, "B": {...}} or None when unavailable."""
    key = os.environ.get("VAPI_PRIVATE_KEY", "")
    if not key:
        print("  ! VAPI_PRIVATE_KEY not set — skipping prompt diff")
        return None
    ids = {code: aid for aid, code in ARM_CODE.items()}
    try:
        return {"A": fetch_assistant(ids["A"], key),
                "B": fetch_assistant(ids["B"], key)}
    except Exception as e:
        print(f"  ! prompt fetch failed ({e}) — skipping prompt diff")
        return None


def build_prompt_diffs(arms):
    """Line-diff Arm A's system prompt against Arm B's -> template promptDiffs.
    Rendered by the 'prompt change behind it' panel when a compare arm is picked."""
    a, b = arms["A"], arms["B"]
    lines = []
    if a["model"] != b["model"]:
        lines.append({"type": "del", "text": esc(f"model: {a['model']}")})
        lines.append({"type": "add", "text": esc(f"model: {b['model']}")})
    for line in difflib.unified_diff(a["prompt"].splitlines(), b["prompt"].splitlines(),
                                     lineterm="", n=0):
        if line[:3] in ("+++", "---") or line.startswith("@@"):
            continue
        txt = line[1:].strip()
        if txt:
            lines.append({"type": "del" if line[0] == "-" else "add", "text": esc(txt)})
    if len(lines) > 400:
        extra = len(lines) - 400
        lines = lines[:400] + [{"type": "add", "text": f"… {extra} more changed lines"}]
    print(f"  prompt diff: {a['name']} vs {b['name']} — {len(lines)} changed lines")
    return {"A|B": lines} if lines else {}


TAKEAWAYS_CACHE = "prompt_takeaways_cache.json"  # gitignored — keyed by prompt hash
TAKEAWAYS_MODEL = "claude-opus-5"

TAKEAWAYS_SCHEMA = {
    "type": "object",
    "properties": {
        "takeaways": {
            "type": "array",
            "items": {"type": "string"},
            "description": "5-8 takeaway bullets; each is the inner HTML of one <li>",
        }
    },
    "required": ["takeaways"],
    "additionalProperties": False,
}

TAKEAWAYS_SYSTEM = """\
You write the "Key takeaways" bar for an A/B eval dashboard at CEO (Center for
Employment Opportunities — a reentry-employment nonprofit; participants practice
job interviews with a phone-based AI coach). Arm A is the incumbent coach system
prompt, Arm B is the candidate. Your audience is program staff and job coaches,
not engineers.

Summarize what actually changed between the two prompts and why it matters,
grounded ONLY in the two prompts provided — never invent changes.

Output 5-8 takeaways. Each takeaway is the inner HTML of one <li>:
- Start with a short <b>bold lead phrase:</b> then 1-2 plain sentences.
- Where a change clearly targets one of the dashboard's judged dimensions, name
  it in <i>italics</i> (e.g. <i>makes it a dialogue</i>, <i>drives practice &amp;
  uptake</i>, <i>limits the load</i>).
- Concrete over abstract: quote short phrases from the prompts where punchy.
- Order by importance: structural/behavioral changes first, minor tweaks last.
- Inline HTML only (<b>, <i>, &amp;); no <li> tags, no markdown, no headings.

Known corpus context you may reference when a change targets it: the incumbent
coach lectures instead of running a practice loop — makes_it_a_dialogue ~100%
failing, no practice uptake ~60%, over-complimentary ~72%, and PII handling
issues (note: reading back the CEO ID during verification is by design, NOT a
breach)."""


def build_prompt_takeaways(arms):
    """Generate the Key-takeaways bullets from the LIVE prompts with Claude.
    Cached by a hash of both prompts+models: re-runs reuse the cache verbatim
    (stable wording, no API cost) until either arm's prompt actually changes.
    Falls back to the hand-curated PROMPT_TAKEAWAYS list on any failure."""
    a, b = arms["A"], arms["B"]
    fingerprint = hashlib.sha256(
        json.dumps([a["model"], a["prompt"], b["model"], b["prompt"]]).encode()
    ).hexdigest()

    cache_path = Path(TAKEAWAYS_CACHE)
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text())
            if cached.get("hash") == fingerprint and cached.get("takeaways"):
                print(f"  takeaways: cache hit ({len(cached['takeaways'])} bullets, prompts unchanged)")
                return cached["takeaways"]
        except (json.JSONDecodeError, OSError):
            pass  # unreadable cache -> regenerate

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("  ! ANTHROPIC_API_KEY not set — using hand-curated takeaways")
        return PROMPT_TAKEAWAYS

    try:
        import anthropic
        client = anthropic.Anthropic()
        dims = ", ".join(n for _, n, _ in DIMENSIONS)
        response = client.messages.create(
            model=TAKEAWAYS_MODEL,
            max_tokens=16000,
            system=TAKEAWAYS_SYSTEM,
            output_config={"format": {"type": "json_schema", "schema": TAKEAWAYS_SCHEMA}},
            messages=[{"role": "user", "content": (
                f"Judged dimensions on the dashboard: {dims}\n\n"
                f"=== ARM A (incumbent): {a['name']} · model {a['model']} ===\n{a['prompt']}\n\n"
                f"=== ARM B (candidate): {b['name']} · model {b['model']} ===\n{b['prompt']}"
            )}],
        )
        if response.stop_reason == "refusal":
            raise RuntimeError("model refused the request")
        text = next(blk.text for blk in response.content if blk.type == "text")
        takeaways = json.loads(text)["takeaways"]
        cache_path.write_text(json.dumps({
            "hash": fingerprint,
            "model": TAKEAWAYS_MODEL,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "takeaways": takeaways,
        }, indent=2))
        print(f"  takeaways: generated {len(takeaways)} bullets with {TAKEAWAYS_MODEL} -> {TAKEAWAYS_CACHE}")
        return takeaways
    except Exception as e:
        print(f"  ! takeaway generation failed ({e}) — using hand-curated takeaways")
        return PROMPT_TAKEAWAYS


def fetch_rows(url, key):
    """Page through the whole table via PostgREST."""
    H = {"apikey": key, "Authorization": f"Bearer {key}"}
    rows, step, off = [], 1000, 0
    while True:
        r = requests.get(
            f"{url}/rest/v1/{TABLE}",
            params={"select": "*", "order": "scored_at.asc"},
            headers={**H, "Range": f"{off}-{off + step - 1}"},
            timeout=30,
        )
        r.raise_for_status()
        batch = r.json()
        rows += batch
        if len(batch) < step:
            return rows
        off += step


def selftest_rows():
    """Four fake rows (2 A, 2 B) so the render can be verified without creds."""
    def mk(cid, aid, overrides):
        row = {"call_id": cid, "assistant_id": aid, "customer_number": "+1555000" + cid[-4:]}
        for stem in JUDGE_TO_DIM:
            row[f"{stem}_verdict"] = overrides.get(stem, "pass")
        return row
    ids = {code: aid for aid, code in ARM_CODE.items()}
    A, B = ids["A"], ids["B"]
    return [
        mk("aaaa1111", A, {"makes_it_a_dialogue": "fail", "drives_practice": "fail"}),
        mk("aaaa2222", A, {"limits_the_load": "fail", "feedback_q_low_bar": "fail",
                           "makes_it_a_dialogue": "fail"}),
        mk("bbbb1111", B, {"makes_it_a_dialogue": "fail"}),
        mk("bbbb2222", B, {"pii": "fail", "makes_it_a_dialogue": "fail"}),
    ]


def arm_variants(arms):
    """Arm display labels from the live Vapi assistant names ("Arm B — <name>"),
    so putting a new variant into the test is purely the env change — the board
    picks up the new assistant's name on the next build. Falls back to the
    static VARIANTS list when Vapi is unreachable/unconfigured."""
    if not arms:
        return VARIANTS
    return [(code, f"Arm {code} — {arms[code]['name']}") for code, _ in VARIANTS]


def render(records, out, source, args, min_cell=None, prompt_diffs=None, takeaways=None,
           variant_labels=None):
    variants = [{"id": code, "label": label,
                 "n": sum(r["variant"] == code for r in records),
                 "hasDemo": any(r["variant"] == code and r["demo"]["site"] != "Unknown"
                                for r in records)}
                for code, label in (variant_labels or VARIANTS)]

    defs = dim_definitions()
    payload = {
        "dimensions": [{"id": i, "name": n, "section": s, **defs.get(i, {})}
                       for i, n, s in DIMENSIONS],
        "facets": facet_options(records),
        "variants": variants,
        "promptDiffs": prompt_diffs or {},
        "promptTakeaways": (takeaways or []) if prompt_diffs else [],
        "records": records,
        "n": len(records),
        "source": source,
    }

    tpl = Path(TEMPLATE)
    if not tpl.exists():
        data_out = Path(out).with_suffix(".json")
        data_out.write_text(json.dumps(payload))
        print(f"  ! {TEMPLATE} missing — wrote {data_out} only.")
        return
    html = tpl.read_text().replace("/*__DATA__*/{}", json.dumps(payload))
    mc = args.min_cell if min_cell is None else min_cell
    if mc != 8:
        html = html.replace("const MIN_CELL = 8;", f"const MIN_CELL = {mc};", 1)
    if args.refresh > 0:
        html = html.replace('<meta charset="utf-8">',
                            f'<meta charset="utf-8">\n<meta http-equiv="refresh" content="{args.refresh}">', 1)
    Path(out).write_text(html)
    print(f"  wrote {out} ({round(len(html) / 1024)} KB)  ·  {len(records)} scored calls")
    for v in variants:
        print(f"    {v['label']:<34} n={v['n']}")


def main():
    ap = argparse.ArgumentParser(description="Build the A/B dashboards (test + real calls) from Supabase eval output.")
    ap.add_argument("--out", default=OUTPUT, help="output file for the TEST-calls dashboard")
    ap.add_argument("--out-real", default=OUTPUT_REAL, help="output file for the REAL-calls dashboard")
    ap.add_argument("--refresh", type=int, default=0, metavar="SECONDS",
                    help="inject a <meta refresh> so the page auto-reloads every N seconds (0 = off)")
    ap.add_argument("--min-cell", type=int, default=8, metavar="N",
                    help="override the small-sample threshold (rates hidden below N calls); template default 8")
    ap.add_argument("--selftest", action="store_true",
                    help="render 4 fake rows instead of querying Supabase (no creds needed)")
    args = ap.parse_args()

    if args.selftest:
        rows = selftest_rows()
    else:
        url = os.environ.get("SUPABASE_URL", "").rstrip("/")
        key = os.environ.get("SUPABASE_KEY", "")
        if not (url and key):
            raise SystemExit("Set SUPABASE_URL and SUPABASE_KEY in .env (or use --selftest).")
        rows = fetch_rows(url, key)

    demo_map = load_demographics()
    if demo_map:
        print(f"  demographics loaded: {len(demo_map)} participants (report*.csv)")
    else:
        print("  ! no report*.csv demographics export found — facets will be Unknown")

    test_recs, real_recs, skipped, unverified = [], [], 0, 0
    for row in rows:
        code = ARM_CODE.get(row.get("assistant_id"))
        if not code:
            skipped += 1
            continue
        if is_test_call(row):
            test_recs.append(make_record(row, code))
        elif has_real_ceo_id(row):
            real_recs.append(make_record(row, code, demo_map))
        else:
            unverified += 1
    if skipped:
        print(f"  {skipped} rows skipped (other assistant_id)")
    if unverified:
        print(f"  {unverified} live rows dropped (no verified CEO ID)")
    matched = sum(r["demo"]["site"] != "Unknown" for r in real_recs)
    if real_recs:
        print(f"  live calls matched to demographics: {matched}/{len(real_recs)}")

    arms = None if args.selftest else fetch_arm_prompts()
    prompt_diffs = build_prompt_diffs(arms) if arms else {}
    takeaways = build_prompt_takeaways(arms) if arms and prompt_diffs else []
    variant_labels = arm_variants(arms)

    judged_by = ("scored by the 9-judge eval server (Supabase ceo_live_calls); "
                 "overall = derived (no PII trip + ≥60% of observed dims pass)")
    render(test_recs, args.out,
           f"TEST calls (CEO ID {TEST_CEO_ID} or pre-live) {judged_by}", args,
           prompt_diffs=prompt_diffs, takeaways=takeaways, variant_labels=variant_labels)
    # Live board shows justice-involved participants' demographics — HANDOVER_PLAN
    # small-cell rule: never show rates for a slice under 10 calls.
    render(real_recs, args.out_real,
           f"REAL participant calls (live number, verified CEO ID) {judged_by}", args,
           min_cell=max(args.min_cell, 10), prompt_diffs=prompt_diffs, takeaways=takeaways,
           variant_labels=variant_labels)


if __name__ == "__main__":
    main()
