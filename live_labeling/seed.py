"""Seed live_labeling.db from the selected production-call set.

Reads config.SET_TSV (labeling_set_live.tsv, written by pull_labeling_set.py),
loads the calls as items — arm is stored for the export but never shown in the
UI, and the judge verdict columns in the TSV are deliberately NOT loaded, so
labeling stays blind — then creates the two labelers and assigns every call to
both (each scores their own DIM_SPLIT half).

Idempotent: wipes and reloads (including any round-3 scores!).

Run:  /usr/bin/python3 seed.py
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
import db


def _assignments_table_exists() -> bool:
    try:
        db._query_one("SELECT 1 FROM assignments LIMIT 1")
        return True
    except Exception:
        return False


def read_calls():
    if not config.SET_TSV.exists():
        raise SystemExit(f"{config.SET_TSV} not found — run pull_labeling_set.py first.")
    with open(config.SET_TSV, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    calls = []
    for r in rows:
        if not (r.get("call_id") and r.get("Transcript")):
            continue
        try:
            dur = int(float(r.get("duration_sec") or 0))
        except ValueError:
            dur = None
        calls.append({
            "source_row": r["call_id"],
            "ceo_id": (r.get("CEO ID") or "").strip(),
            "arm": (r.get("arm") or "").strip(),
            "started_at": (r.get("started_at") or "").strip(),
            "duration_sec": dur,
            "transcript": r["Transcript"],
        })
    return calls


def main():
    if db.IS_PG:
        # Seeding wipes everything, including any round-3 scores already entered.
        existing = db._query_one(
            "SELECT COUNT(*) AS n FROM assignments WHERE status != 'pending'"
        ) if _assignments_table_exists() else None
        n_scored = existing["n"] if existing else 0
        print(f"Target: REMOTE Postgres ({n_scored} scored assignment(s) present).")
        answer = input("This WIPES all transcripts and round-3 scores in that "
                       "database. Type WIPE to continue: ").strip()
        if answer != "WIPE":
            print("Aborted — nothing changed.")
            return
    db.init_db()
    calls = read_calls()

    conn = db.connect()
    try:
        ts = db.now()
        for table in ("assignments", "items", "labelers"):
            conn.execute(f"DELETE FROM {table}")

        for c in sorted(calls, key=lambda c: c["started_at"]):
            conn.execute(
                db.Q("""INSERT INTO items
                        (source_row, ceo_id, arm, started_at, duration_sec, transcript, created_at)
                        VALUES (?,?,?,?,?,?,?)"""),
                (c["source_row"], c["ceo_id"], c["arm"], c["started_at"],
                 c["duration_sec"], c["transcript"], ts),
            )
        item_ids = [r["id"] for r in conn.execute("SELECT id FROM items").fetchall()]

        for name, code in config.LABELERS:
            conn.execute(
                db.Q("INSERT INTO labelers (name, passcode, created_at) VALUES (?,?,?)"),
                (name, code, ts),
            )
        labeler_ids = [r["id"] for r in conn.execute("SELECT id FROM labelers").fetchall()]
        for iid in item_ids:
            for lid in labeler_ids:
                conn.execute(
                    db.Q("INSERT INTO assignments (item_id, labeler_id, updated_at) VALUES (?,?,?)"),
                    (iid, lid, ts),
                )
        conn.commit()
    finally:
        conn.close()

    print(f"Loaded {len(item_ids)} calls, "
          f"{len(config.LABELERS)} labelers x {len(item_ids)} assignments.")
    for name, code in config.LABELERS:
        print(f"  {name}: passcode {code}  (magic link: /l/{code})  "
              f"dims: {', '.join(config.dims_for(name))}")


if __name__ == "__main__":
    main()
