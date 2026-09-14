"""Aggregate every coach-call source into ONE normalized corpus the judges score.

Sources:
  - Local TEXT simulations  (simulate.py output TSVs)     -> modality=text
  - Vapi VOICE / manual calls (websocketCall records)     -> modality=voice

Output: eval_corpus.tsv, one row per call, with a globally-unique transcript_id
and coach/modality/source tags so run_corpus_temp.py can score them and the
dashboard can slice by coach AND modality. Transcripts are already in AI:/User:
form from both sources, so no re-formatting is needed.

    python aggregate_calls.py

The Vapi /call list endpoint is flaky (intermittently returns empty / drops the
connection), so fetches retry with backoff.
"""

import csv
import hashlib
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()
csv.field_size_limit(10**7)

API = "https://api.vapi.ai"
OUT = "eval_corpus.tsv"
FIELDS = ["transcript_id", "coach", "modality", "source", "assistant_id", "call_id",
          "started_at", "Transcript"]

# coach code -> (label, vapi assistant id). Code is used in transcript_ids.
COACHES = {
    "v20": ("Voice Coach 2.0", os.getenv("VAPI_COACH_V20_ID", "")),
    "v21": ("Voice Coach 2.1", os.getenv("VAPI_COACH_V21_ID", "")),
    "prod": ("PCPT v2 (production)", os.getenv("VAPI_COACH_PROD_ID", "")),
}
# coach code -> local text-sim TSV file(s). 2.1's runs are split across two files;
# they're deduped on transcript content. 2.0's test files are intentionally excluded.
TEXT_SIMS = {
    "v20": ["sim_calls.tsv"],
    "v21": ["sim_v2_1.tsv", "sim_calls_2.1.tsv"],
}


def fetch_calls(assistant_id, tries=30):
    """The Vapi /call list is flaky (partial/empty responses), so accumulate the
    UNION by call id across several attempts to approach the complete set."""
    key = os.environ["VAPI_PRIVATE_KEY"].strip()
    url = f"{API}/call?assistantId={assistant_id}&limit=100"
    seen = {}
    stable = 0
    for _ in range(tries):
        try:
            r = requests.get(url, headers={"Authorization": f"Bearer {key}"}, timeout=90)
            j = r.json()
            if isinstance(j, list):
                before = len(seen)
                for c in j:
                    if c.get("id"):
                        seen[c["id"]] = c
                if seen:  # only judge stability once we actually have data
                    stable = stable + 1 if len(seen) == before else 0
                    if stable >= 5:  # 5 non-empty attempts added nothing new -> complete
                        break
        except Exception:
            pass
        time.sleep(1.5)
    return list(seen.values())


def usable(tx):
    """A real two-way exchange, not a greeting-then-hangup stub."""
    return "AI:" in tx and "User:" in tx and len(tx) >= 200


def voice_rows(code, assistant_id):
    rows, seen = [], set()
    for c in fetch_calls(assistant_id):
        cid = c.get("id", "")
        if c.get("status") != "ended" or cid in seen:
            continue
        seen.add(cid)
        tx = (c.get("transcript") or (c.get("artifact") or {}).get("transcript") or "").strip()
        if not usable(tx):
            continue
        rows.append({
            "transcript_id": f"{code}_voice_{cid.replace('-', '')[:20]}",  # full id — first 8 chars collide (time-ordered)
            "coach": COACHES[code][0], "modality": "voice", "source": "vapi",
            "assistant_id": assistant_id, "call_id": cid,
            "started_at": (c.get("startedAt") or "")[:19], "Transcript": tx,
        })
    return rows


def text_rows(code, files):
    """Read one or more text-sim TSVs for a coach, deduping on transcript content
    (the 2.1 runs overlap by ~4 sims across files)."""
    rows, seen, idx = [], set(), 0
    for path in files:
        if not Path(path).exists():
            print(f"  ! {path} missing — skipping")
            continue
        with open(path, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh, delimiter="\t"):
                tx = (r.get("Transcript") or "").strip()
                if not usable(tx):
                    continue
                sig = hashlib.md5(tx.encode()).hexdigest()
                if sig in seen:
                    continue
                seen.add(sig)
                rows.append({
                    "transcript_id": f"{code}_text_{idx}",
                    "coach": COACHES[code][0], "modality": "text", "source": "sim",
                    "assistant_id": COACHES[code][1], "call_id": r.get("CEO ID", ""),
                    "started_at": "", "Transcript": tx,
                })
                idx += 1
    return rows


def main():
    all_rows = []
    print("Text simulations:")
    for code, files in TEXT_SIMS.items():
        rows = text_rows(code, files)
        print(f"  {code:<5} {'+'.join(files):<32} -> {len(rows)} calls (deduped)")
        all_rows += rows
    print("Vapi voice / manual calls:")
    for code in ("v20", "v21"):
        rows = voice_rows(code, COACHES[code][1])
        print(f"  {code:<5} {COACHES[code][1][:8]}         -> {len(rows)} calls")
        all_rows += rows

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, delimiter="\t")
        w.writeheader()
        w.writerows(all_rows)

    from collections import Counter
    by = Counter((r["coach"], r["modality"]) for r in all_rows)
    print(f"\nWrote {len(all_rows)} calls to {OUT}:")
    for (coach, mod), n in sorted(by.items()):
        print(f"  {coach:<24} {mod:<6} {n}")
    print(f"\nScore them:  cd temp_judge_suite && "
          f"python run_corpus_temp.py --file ../{OUT} --all --yes")


if __name__ == "__main__":
    main()
