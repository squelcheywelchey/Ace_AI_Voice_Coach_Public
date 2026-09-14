"""Configuration for the round-3 LIVE A/B labeling app (Maya + Grader B).

Third labeling pass: 15 real production calls from the live-number A/B split
(selected by pull_labeling_set.py, roughly balanced pass/fail per judge
dimension). BLIND by design — the app never shows judge verdicts, prior labels,
or which A/B arm a call came from. Same stack and look as calibration/.

Local-first but deploy-ready, same pattern as calibration/config.py.
"""

import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent

DB_PATH = Path(os.environ.get("LIVE_LABELING_DB_PATH", HERE / "live_labeling.db"))

# The selected labeling set (written by pull_labeling_set.py).
SET_TSV = Path(os.environ.get("LIVE_LABELING_SET_TSV", PROJECT_ROOT / "labeling_set_live.tsv"))

# Pass / Fail / Not Observed — same scale as rounds 1-2.
SCORE_CHOICES = ["pass", "fail", "not_observed"]
SCORE_LABELS = {
    "pass": "Pass",
    "fail": "Fail",
    "not_observed": "Not Observed",
}

LABELERS = [
    ("Maya Welch", os.environ.get("LIVE_LABELING_PASSCODE_MAYA", "maya-live")),
    ("Grader B", os.environ.get("LIVE_LABELING_PASSCODE_ANKITA", "grader_b-live")),
]

# Division of labor. ROUND 4 (2026-08-12): 10 fresh calls, one dim each —
# Maya relabels quality_conversational_flow (certification holdout for the
# v11 judge), Grader B relabels feedback_question_low_bar (33% round-3 match,
# next hill-climb target). Round-3 4/5 split retired with that round (its
# labels live in live_round3_labels.csv + live_labeling/backups/).
DIM_SPLIT = {
    "Maya Welch": [
        "quality_conversational_flow",
    ],
    "Grader B": [
        "feedback_question_low_bar",
    ],
}


def dims_for(labeler_name: str):
    """The dimension ids this labeler scores (all of them if not in the split)."""
    ids = DIM_SPLIT.get(labeler_name)
    return ids if ids else [d["id"] for d in scored_rubric()]


def flask_secret_key() -> str:
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
    import rubric

    return list(rubric.DIMENSIONS)


def scored_rubric_grouped():
    import rubric

    grouped = []
    for key, name in rubric.SECTIONS:
        dims = [d for d in rubric.DIMENSIONS if d["section"] == key]
        if dims:
            grouped.append((name, dims))
    known = {k for k, _ in rubric.SECTIONS}
    orphans = [d for d in rubric.DIMENSIONS if d["section"] not in known]
    if orphans:
        grouped.append(("Other", orphans))
    return grouped
