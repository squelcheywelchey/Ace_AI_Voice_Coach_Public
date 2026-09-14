"""Round-1 labeler groups (G1–G4) from rubric_calibration_options.docx.

Groups cluster the 12 round-1 labelers by the fail bar they implicitly applied.
Every round-1 label shown in the app is tagged with its labeler's group so
Maya + Grader B can read disagreements as bar disputes, not noise.
"""

GROUPS = {
    "G1": {
        "label": "G1 · Bar-1 hawks",
        "short": "Bar 1 (strict)",
        "fail_rate": "0.55",
        "alpha": "0.50",
        "desc": (
            "FAIL = anything short of the best coaching behavior observed. "
            "One-issue lenses that spill across dimensions: Grader A = verbosity + "
            "reflective questions; Grader B = over-praise; Grader C = verbosity + "
            "“next-question option primes declining.”"
        ),
    },
    "G2": {
        "label": "G2 · Bar-2 middle",
        "short": "Bar 2 (missed clear opportunity)",
        "fail_rate": "0.41–0.53",
        "alpha": "0.42",
        "desc": (
            "FAIL = the conversation presented a clear, specific opportunity for the "
            "behavior and the coach didn't take it, in a way that plausibly hurt the "
            "participant. Outcome-based uptake (Maya, Grader E); Grader D is the most "
            "dimension-disciplined."
        ),
    },
    "G3": {
        "label": "G3 · Bar-3 lenient",
        "short": "Bar 3 (egregious only)",
        "fail_rate": "0.10–0.28",
        "alpha": "0.28",
        "desc": (
            "FAIL = actively harmful, wrong, or dismissive behavior only. Pass anything "
            "polite and plausible; effort-based uptake; heaviest not_observed users. "
            "CEO program lead is G3 on 9 dimensions but applies the G1 reflective-question criterion "
            "on makes_it_a_dialogue (10/10 fail)."
        ),
    },
    "G4": {
        "label": "G4 · Noisy",
        "short": "Noisy (evidence-quality issues)",
        "fail_rate": "0.35–0.55",
        "alpha": "0.04",
        "desc": (
            "Not a bar preference: evidence is non-probative (participant-only quotes, "
            "transcript artifacts, holistic ratings in wrong columns). Alpha ~0 = "
            "coin-flip agreement — read these labels with caution."
        ),
    },
}

LABELER_GROUP = {
    "Grader A": "G1",
    "Grader B": "G1",
    "Grader C": "G1",
    "Maya Welch": "G2",
    "Grader E": "G2",
    "Grader D": "G2",
    "Grader O": "G3",
    "Grader P": "G3",
    "Grader M": "G3",
    "CEO program lead": "G3",
    "Grader Q": "G4",
    "Grader N": "G4",
}


def group_of(labeler_name: str) -> str:
    return LABELER_GROUP.get(labeler_name, "G4")
