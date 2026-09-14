"""Configuration for the human-labeling web app.

Local-first but deploy-ready: every environment-specific value reads from an
env var with a sensible local default, so deploying is a matter of setting env
vars (FLASK_SECRET_KEY, LABELING_DB_PATH, LABELING_ADMIN_PASSCODE), not editing
code.

The rubric the labelers score lives in rubric.py (pass/fail, four sections,
definition + examples per dimension). To change the rubric, edit rubric.py.
"""

import os
import sys
from pathlib import Path

# --- paths -----------------------------------------------------------------
HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent

# Make the project root importable so we can reuse RUBRIC/SECTIONS from analyze.py.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = Path(os.environ.get("LABELING_DB_PATH", HERE / "labeling.db"))

# --- scoring scale ---------------------------------------------------------
# Pass / Fail / Not Observed. "Not Observed" = the call gave no chance to judge
# this dimension (carried over from the V1 rubric's "no chance to observe").
SCORE_CHOICES = ["pass", "fail", "not_observed"]
SCORE_LABELS = {
    "pass": "Pass",
    "fail": "Fail",
    "not_observed": "Not Observed",
}

# --- secrets ---------------------------------------------------------------
# Admin passcode. Defaults to a dev value for local use; OVERRIDE in production
# via the LABELING_ADMIN_PASSCODE env var.
ADMIN_PASSCODE = os.environ.get("LABELING_ADMIN_PASSCODE", "admin-dev-passcode")


def flask_secret_key() -> str:
    """Stable Flask session-signing key.

    Prefers FLASK_SECRET_KEY (set this in production). For local dev, persists a
    random key to a gitignored file so sessions survive restarts.
    """
    env = os.environ.get("FLASK_SECRET_KEY")
    if env:
        return env
    key_file = HERE / ".secret_key"
    if key_file.exists():
        return key_file.read_text().strip()
    import secrets

    key = secrets.token_hex(32)
    key_file.write_text(key)
    return key


def scored_rubric():
    """Flat list of every dimension labelers score (from rubric.py)."""
    import rubric  # the labeling rubric (pass/fail, 4 sections)

    return list(rubric.DIMENSIONS)


def scored_rubric_grouped():
    """Dimensions grouped by section, in section order: [(section_name, [dims]), ...]."""
    import rubric

    section_names = dict(rubric.SECTIONS)
    grouped = []
    for key, name in rubric.SECTIONS:
        dims = [d for d in rubric.DIMENSIONS if d["section"] == key]
        if dims:
            grouped.append((name, dims))
    # any dimension whose section key isn't in SECTIONS (typo guard) goes last
    known = {k for k, _ in rubric.SECTIONS}
    orphans = [d for d in rubric.DIMENSIONS if d["section"] not in known]
    if orphans:
        grouped.append(("Other", orphans))
    return grouped
