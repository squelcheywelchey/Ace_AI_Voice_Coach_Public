"""Storage for the labeling app — Postgres in production, SQLite locally.

If DATABASE_URL is set (e.g. a Neon/Render Postgres connection string), the app
uses Postgres; otherwise it falls back to a local SQLite file. SQL is written
once with '?' placeholders and adapted per backend.

Transactions are managed explicitly with commit()/close() rather than
`with conn:` — psycopg3 *closes* the connection when used as a context manager,
while sqlite3 does not, so the explicit form behaves the same on both.

Three tables:
  labelers     - who can log in (name + private passcode; admin flag)
  items        - transcripts pulled in for review
  assignments  - which labeler reviews which item, plus their scores/status
"""

from __future__ import annotations

import json
import os
import secrets
import sqlite3
from datetime import datetime, timezone

from config import DB_PATH

DATABASE_URL = os.environ.get("DATABASE_URL")
IS_PG = bool(DATABASE_URL)

if IS_PG:
    import psycopg
    from psycopg import errors as _pg_errors
    from psycopg.rows import dict_row

    INTEGRITY_ERRORS = (sqlite3.IntegrityError, _pg_errors.IntegrityError)
else:
    INTEGRITY_ERRORS = (sqlite3.IntegrityError,)

_PK = "SERIAL PRIMARY KEY" if IS_PG else "INTEGER PRIMARY KEY AUTOINCREMENT"

SCHEMA = """
CREATE TABLE IF NOT EXISTS labelers (
    id        {PK},
    name      TEXT NOT NULL,
    passcode  TEXT NOT NULL UNIQUE,
    is_admin  INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    quiz_done_at TEXT
);

CREATE TABLE IF NOT EXISTS items (
    id          {PK},
    source_file TEXT NOT NULL,
    source_row  INTEGER NOT NULL,
    ceo_id      TEXT,
    assistant   TEXT,
    duration    TEXT,
    transcript  TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    UNIQUE(source_file, source_row)
);

CREATE TABLE IF NOT EXISTS assignments (
    id            {PK},
    item_id       INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    labeler_id    INTEGER NOT NULL REFERENCES labelers(id) ON DELETE CASCADE,
    status        TEXT NOT NULL DEFAULT 'pending',
    scores_json   TEXT NOT NULL DEFAULT '{}',
    notes_json    TEXT NOT NULL DEFAULT '{}',
    evidence_json TEXT NOT NULL DEFAULT '{}',
    overall_quality TEXT,
    overall_notes TEXT,
    updated_at    TEXT,
    submitted_at  TEXT,
    UNIQUE(item_id, labeler_id)
);
""".replace("{PK}", _PK)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def Q(sql: str) -> str:
    """Adapt '?' placeholders to the active backend ('%s' for Postgres)."""
    return sql.replace("?", "%s") if IS_PG else sql


def connect():
    if IS_PG:
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# --- low-level helpers (explicit commit/close; no `with conn:`) -------------

def _query_one(sql, params=()):
    conn = connect()
    try:
        return conn.execute(Q(sql), params).fetchone()
    finally:
        conn.close()


def _query_all(sql, params=()):
    conn = connect()
    try:
        return conn.execute(Q(sql), params).fetchall()
    finally:
        conn.close()


def _write(sql, params=()):
    conn = connect()
    try:
        conn.execute(Q(sql), params)
        conn.commit()
    finally:
        conn.close()


# Idempotent column adds for DBs created before a column existed (no-op if present).
MIGRATIONS = [
    "ALTER TABLE assignments ADD COLUMN evidence_json TEXT NOT NULL DEFAULT '{}'",
    "ALTER TABLE labelers ADD COLUMN quiz_done_at TEXT",
]


def init_db():
    conn = connect()
    try:
        for stmt in SCHEMA.split(";"):
            if stmt.strip():
                conn.execute(stmt)
        conn.commit()
        for migration in MIGRATIONS:
            try:
                conn.execute(migration)
                conn.commit()
            except Exception:
                conn.rollback()
    finally:
        conn.close()


def gen_passcode(name: str) -> str:
    """Readable-ish private passcode, e.g. 'maya-7f3a9c'."""
    slug = "".join(c for c in name.lower() if c.isalnum())[:8] or "user"
    return f"{slug}-{secrets.token_hex(3)}"


# --- labelers --------------------------------------------------------------

def add_labeler(name: str, is_admin: bool = False, passcode: str | None = None):
    """Insert a labeler and return (id, passcode). Looks the id up by passcode
    (unique) so it works on both backends without lastrowid/RETURNING."""
    code = passcode or gen_passcode(name)
    conn = connect()
    try:
        conn.execute(
            Q("INSERT INTO labelers (name, passcode, is_admin, created_at) VALUES (?,?,?,?)"),
            (name, code, 1 if is_admin else 0, now()),
        )
        conn.commit()
        row = conn.execute(Q("SELECT id FROM labelers WHERE passcode = ?"), (code,)).fetchone()
    finally:
        conn.close()
    return row["id"], code


def ensure_admin(passcode: str):
    """Create the admin login if none exists (idempotent; safe under gunicorn)."""
    if any(l["is_admin"] for l in all_labelers()):
        return
    try:
        add_labeler("Admin", is_admin=True, passcode=passcode)
    except INTEGRITY_ERRORS:
        pass  # another worker created it first


def mark_quiz_done(labeler_id: int):
    _write("UPDATE labelers SET quiz_done_at=? WHERE id=?", (now(), labeler_id))


def delete_labeler(labeler_id: int):
    """Remove a (non-admin) labeler and, via ON DELETE CASCADE, their assignments."""
    _write("DELETE FROM labelers WHERE id=? AND is_admin=0", (labeler_id,))


def labeler_by_passcode(passcode: str):
    return _query_one("SELECT * FROM labelers WHERE passcode = ?", (passcode.strip(),))


def labeler_by_id(lid: int):
    return _query_one("SELECT * FROM labelers WHERE id = ?", (lid,))


def all_labelers():
    return _query_all("SELECT * FROM labelers ORDER BY is_admin DESC, name")


# --- items -----------------------------------------------------------------

def add_item(source_file, source_row, ceo_id, assistant, duration, transcript):
    """Insert a transcript; returns item id. No-op-safe on duplicates."""
    conn = connect()
    try:
        conn.execute(
            Q("""INSERT INTO items
                 (source_file, source_row, ceo_id, assistant, duration, transcript, created_at)
                 VALUES (?,?,?,?,?,?,?) ON CONFLICT DO NOTHING"""),
            (source_file, source_row, ceo_id, assistant, duration, transcript, now()),
        )
        conn.commit()
        row = conn.execute(
            Q("SELECT id FROM items WHERE source_file=? AND source_row=?"),
            (source_file, source_row),
        ).fetchone()
    finally:
        conn.close()
    return row["id"]


def all_items():
    return _query_all("SELECT * FROM items ORDER BY source_file, source_row")


def item_by_id(item_id: int):
    return _query_one("SELECT * FROM items WHERE id = ?", (item_id,))


# --- assignments -----------------------------------------------------------

def assign(item_id: int, labeler_id: int):
    _write(
        """INSERT INTO assignments (item_id, labeler_id, updated_at)
           VALUES (?,?,?) ON CONFLICT DO NOTHING""",
        (item_id, labeler_id, now()),
    )


def unassign(item_id: int, labeler_id: int):
    _write("DELETE FROM assignments WHERE item_id=? AND labeler_id=?", (item_id, labeler_id))


def assignment_status_map():
    """{(item_id, labeler_id): status} for every assignment."""
    rows = _query_all("SELECT item_id, labeler_id, status FROM assignments")
    return {(r["item_id"], r["labeler_id"]): r["status"] for r in rows}


def delete_items(item_ids):
    """Delete transcripts (and, via ON DELETE CASCADE, their assignments)."""
    conn = connect()
    try:
        for i in item_ids:
            conn.execute(Q("DELETE FROM items WHERE id=?"), (i,))
        conn.commit()
    finally:
        conn.close()


def clear_round_data():
    """Delete all transcripts, graders (non-admin), and assignments — for a clean
    slate before loading a new round. Keeps the admin login."""
    conn = connect()
    try:
        conn.execute("DELETE FROM items")                     # cascades assignments
        conn.execute("DELETE FROM labelers WHERE is_admin=0")  # cascades any remaining
        conn.commit()
    finally:
        conn.close()


def import_round(source_name, new_graders, item_specs, assignment_pairs):
    """Bulk-load a calibration round in ONE connection (fast over remote Postgres).

    new_graders:      [(name, passcode), ...]   graders not already in the DB
    item_specs:       [(source_row, ceo_id, transcript), ...]  one per transcript
    assignment_pairs: [(source_row, grader_name), ...]         one per assignment

    All inserts are ON CONFLICT DO NOTHING, so re-running is safe/idempotent.
    """
    conn = connect()
    try:
        ts = now()
        for name, code in new_graders:
            conn.execute(
                Q("INSERT INTO labelers (name, passcode, is_admin, created_at) "
                  "VALUES (?,?,?,?) ON CONFLICT DO NOTHING"),
                (name, code, 0, ts),
            )
        for src, ceo, txt in item_specs:
            conn.execute(
                Q("""INSERT INTO items
                     (source_file, source_row, ceo_id, assistant, duration, transcript, created_at)
                     VALUES (?,?,?,?,?,?,?) ON CONFLICT DO NOTHING"""),
                (source_name, src, ceo, "calibration", "", txt, ts),
            )
        conn.commit()

        labelers = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM labelers").fetchall()}
        items = {r["source_row"]: r["id"] for r in
                 conn.execute(Q("SELECT id, source_row FROM items WHERE source_file=?"),
                              (source_name,)).fetchall()}
        for src, grader in assignment_pairs:
            iid, lid = items.get(src), labelers.get(grader)
            if iid and lid:
                conn.execute(
                    Q("INSERT INTO assignments (item_id, labeler_id, updated_at) "
                      "VALUES (?,?,?) ON CONFLICT DO NOTHING"),
                    (iid, lid, ts),
                )
        conn.commit()
    finally:
        conn.close()


def assignment_by_id(assignment_id: int):
    return _query_one(
        """SELECT a.*, i.transcript, i.ceo_id, i.assistant, i.duration,
                  i.source_file, i.source_row, l.name AS labeler_name
           FROM assignments a
           JOIN items i ON i.id = a.item_id
           JOIN labelers l ON l.id = a.labeler_id
           WHERE a.id = ?""",
        (assignment_id,),
    )


def assignments_for_labeler(labeler_id: int):
    return _query_all(
        """SELECT a.*, i.ceo_id, i.assistant, i.source_row
           FROM assignments a
           JOIN items i ON i.id = a.item_id
           WHERE a.labeler_id = ?
           ORDER BY i.source_row, a.id""",
        (labeler_id,),
    )


def save_assignment(assignment_id, scores, notes, evidence, overall_quality, overall_notes, submit):
    status = "done" if submit else "in_progress"
    _write(
        """UPDATE assignments
           SET scores_json=?, notes_json=?, evidence_json=?, overall_quality=?,
               overall_notes=?, status=?, updated_at=?, submitted_at=?
           WHERE id=?""",
        (
            json.dumps(scores),
            json.dumps(notes),
            json.dumps(evidence),
            overall_quality,
            overall_notes,
            status,
            now(),
            now() if submit else None,
            assignment_id,
        ),
    )


def all_assignments_full():
    """Every assignment joined with item + labeler, for the admin view / export."""
    return _query_all(
        """SELECT a.*, i.ceo_id, i.assistant, i.source_file, i.source_row,
                  l.name AS labeler_name
           FROM assignments a
           JOIN items i ON i.id = a.item_id
           JOIN labelers l ON l.id = a.labeler_id
           ORDER BY l.name, a.id"""
    )
