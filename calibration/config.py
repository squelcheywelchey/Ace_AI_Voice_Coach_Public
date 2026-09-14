"""Configuration for the round-2 calibration labeling app (Maya + Grader B).

Local-first but deploy-ready, same pattern as labeling/config.py: every
environment-specific value reads from an env var with a local default.
"""

import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent

DB_PATH = Path(os.environ.get("CALIBRATION_DB_PATH", HERE / "calibration.db"))

# Source spreadsheets for seeding (round-1 labels + the transcripts they graded).
LABELS_XLSX = Path(
    os.environ.get("CALIBRATION_LABELS_XLSX", PROJECT_ROOT / "coach_human_labels (2) copy.xlsx")
)
TRANSCRIPTS_XLSX = Path(
    os.environ.get("CALIBRATION_TRANSCRIPTS_XLSX", PROJECT_ROOT / "grading_platform_input_final.xlsx")
)

# Pass / Fail / Not Observed — same scale as round 1.
SCORE_CHOICES = ["pass", "fail", "not_observed"]
SCORE_LABELS = {
    "pass": "Pass",
    "fail": "Fail",
    "not_observed": "Not Observed",
}

# The two round-2 labelers. Fixed passcodes so links stay stable across reseeds;
# override in production via env vars.
LABELERS = [
    ("Maya Welch", os.environ.get("CALIBRATION_PASSCODE_MAYA", "maya-cal2")),
    ("Grader B", os.environ.get("CALIBRATION_PASSCODE_ANKITA", "grader_b-cal2")),
    ("Grader C", os.environ.get("CALIBRATION_PASSCODE_LAURA", "grader_c-cal2")),
]

# Division of labor: each labeler scores half the rubric (dimension numbers
# follow rubric.py order, 1-10). Overall impression is answered by both.
DIM_SPLIT = {
    "Maya Welch": [  # dimensions 1-5 + 12 (flow moved from Grader B 2026-07-08)
        "scaffolds_then_fades",
        "adapts_when_stuck",
        "kind_delivery",
        "reentry_appropriate_framing",
        "limits_the_load",
        "quality_conversational_flow",
    ],
    "Grader B": [  # dimensions 6-11, 13 (feedback_is_correct split into 4 brackets 2026-07-08)
        "feedback_question_high_bar",
        "feedback_question_low_bar",
        "feedback_summary_high_bar",
        "feedback_summary_low_bar",
        "makes_it_a_dialogue",
        "drives_practice_uptake",
        "pii",
    ],
    "Grader C": [  # feedback brackets + uptake on a hand-picked call set (2026-07-08)
        "feedback_question_high_bar",
        "feedback_question_low_bar",
        "feedback_summary_high_bar",
        "feedback_summary_low_bar",
        "drives_practice_uptake",
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
