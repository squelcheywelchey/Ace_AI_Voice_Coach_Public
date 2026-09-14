"""Storage for the round-3 live-labeling app — Postgres in production, SQLite locally.

Same dual-backend pattern as calibration/db.py (DATABASE_URL switches to
Postgres). No prior_labels table this round — labeling is blind.

Three tables:
  labelers      - Maya + Grader B
  items         - the 15 selected live production calls (arm stored for the
                  export only; never shown in the UI)
  assignments   - scoring state per (item, labeler)
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone

from config import DB_PATH

DATABASE_URL = os.environ.get("DATABASE_URL")
IS_PG = bool(DATABASE_URL)

if IS_PG:
    import psycopg
    from psycopg.rows import dict_row

_PK = "SERIAL PRIMARY KEY" if IS_PG else "INTEGER PRIMARY KEY AUTOINCREMENT"

SCHEMA = """
CREATE TABLE IF NOT EXISTS labelers (
    id        {PK},
    name      TEXT NOT NULL UNIQUE,
    passcode  TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS items (
    id           {PK},
    source_row   TEXT NOT NULL UNIQUE,
    ceo_id       TEXT,
    arm          TEXT,
    started_at   TEXT,
    duration_sec INTEGER,
    transcript   TEXT NOT NULL,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assignments (
    id            {PK},
    item_id       INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    labeler_id    INTEGER NOT NULL REFERENCES labelers(id) ON DELETE CASCADE,
    status        TEXT NOT NULL DEFAULT 'pending',
    scores_json   TEXT NOT NULL DEFAULT '{}',
    notes_json    TEXT NOT NULL DEFAULT '{}',
    flags_json    TEXT NOT NULL DEFAULT '[]',
    would_recommend TEXT,
    overall_notes TEXT,
    updated_at    TEXT,
    submitted_at  TEXT,
    UNIQUE(item_id, labeler_id)
);
""".replace("{PK}", _PK)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def Q(sql: str) -> str:
    return sql.replace("?", "%s") if IS_PG else sql


def connect():
    if IS_PG:
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


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


def init_db():
    conn = connect()
    try:
        for stmt in SCHEMA.split(";"):
            if stmt.strip():
                conn.execute(stmt)
        conn.commit()
    finally:
        conn.close()


# --- labelers ----------------------------------------------------------------

def labeler_by_passcode(passcode: str):
    return _query_one("SELECT * FROM labelers WHERE passcode = ?", (passcode.strip(),))


def labeler_by_id(lid: int):
    return _query_one("SELECT * FROM labelers WHERE id = ?", (lid,))


def all_labelers():
    return _query_all("SELECT * FROM labelers ORDER BY name")


# --- items / assignments -----------------------------------------------------

def item_by_id(item_id: int):
    return _query_one("SELECT * FROM items WHERE id = ?", (item_id,))


def assignment_by_id(assignment_id: int):
    return _query_one(
        """SELECT a.*, i.transcript, i.ceo_id, i.source_row, i.started_at,
                  i.duration_sec, l.name AS labeler_name
           FROM assignments a
           JOIN items i ON i.id = a.item_id
           JOIN labelers l ON l.id = a.labeler_id
           WHERE a.id = ?""",
        (assignment_id,),
    )


def assignments_for_labeler(labeler_id: int):
    return _query_all(
        """SELECT a.*, i.ceo_id, i.source_row, i.started_at, i.duration_sec
           FROM assignments a
           JOIN items i ON i.id = a.item_id
           WHERE a.labeler_id = ?
           ORDER BY i.started_at, a.id""",
        (labeler_id,),
    )


def all_assignments_full():
    return _query_all(
        """SELECT a.*, i.ceo_id, i.source_row, i.arm, i.started_at, i.duration_sec,
                  i.transcript, l.name AS labeler_name
           FROM assignments a
           JOIN items i ON i.id = a.item_id
           JOIN labelers l ON l.id = a.labeler_id
           ORDER BY i.started_at, l.name"""
    )


def save_assignment(assignment_id, scores, notes, flags, would_recommend, overall_notes, submit):
    status = "done" if submit else "in_progress"
    _write(
        """UPDATE assignments
           SET scores_json=?, notes_json=?, flags_json=?, would_recommend=?,
               overall_notes=?, status=?, updated_at=?, submitted_at=?
           WHERE id=?""",
        (
            json.dumps(scores),
            json.dumps(notes),
            json.dumps(sorted(flags)),
            would_recommend,
            overall_notes,
            status,
            now(),
            now() if submit else None,
            assignment_id,
        ),
    )


def save_flag_resolution(assignment_id, scores, notes, flags, would_recommend, overall_notes):
    """Targeted update from the flags workbench: rewrites scores/notes/flags but
    leaves status and submitted_at untouched (unlike save_assignment)."""
    _write(
        """UPDATE assignments
           SET scores_json=?, notes_json=?, flags_json=?, would_recommend=?,
               overall_notes=?, updated_at=?
           WHERE id=?""",
        (
            json.dumps(scores),
            json.dumps(notes),
            json.dumps(sorted(flags)),
            would_recommend,
            overall_notes,
            now(),
            assignment_id,
        ),
    )
