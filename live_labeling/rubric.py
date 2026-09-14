"""Rubric for round 3 — the 9 dimensions the production eval server judges.

Definitions are NOT duplicated here: they load live from calibration/rubric.py
(Rubric v2 DECIDED) and are filtered to the eval server's 9 dimensions, so a
definition edit in the calibration rubric automatically shows up here too.
"""

import importlib.util
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "calibration" / "rubric.py"
_spec = importlib.util.spec_from_file_location("_calibration_rubric", _SRC)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

# The 9 dimensions judged by the eval server, by rubric-v2 id.
JUDGED_IDS = [
    "scaffolds_then_fades",
    "adapts_when_stuck",
    "reentry_appropriate_framing",
    "limits_the_load",
    "feedback_question_low_bar",
    "makes_it_a_dialogue",
    "drives_practice_uptake",
    "quality_conversational_flow",
    "pii",
]

SECTIONS = list(_mod.SECTIONS)
DIMENSIONS = [d for d in _mod.DIMENSIONS if d["id"] in JUDGED_IDS]

_missing = set(JUDGED_IDS) - {d["id"] for d in DIMENSIONS}
if _missing:
    raise RuntimeError(f"calibration/rubric.py is missing dimension(s): {sorted(_missing)}")
