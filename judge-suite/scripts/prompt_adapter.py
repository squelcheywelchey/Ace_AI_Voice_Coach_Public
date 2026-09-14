#!/usr/bin/env python3
"""Shared judge-prompt adapter.

Two prompt formats coexist in this repo and the corpus/agreement runners must
handle EITHER:

  .yaml  — structured fields (dimension / definition / pass / fail / na). The
           harness wraps them in a fixed system prompt and expects the model to
           return {"result": "PASS"/"FAIL"/"N/A", "evidence", "reasoning"}.
           (Maya's hero judges: pii_v4_hero.yaml, reentry_..._v4_hero.yaml, …)

  .md    — the file IS the entire prompt, self-contained (e.g. Grader B's two-step
           scan->judge limits_the_load_v2.md / feedback_question_low_bar.md).
           `{transcript}` is substituted into it and the model returns
           {"verdict": "pass"/"fail", ...}. The dimension is taken from the
           filename (limits_the_load_v2.md -> limits_the_load).

`load_prompt_spec(path)` returns a PromptSpec that hides the difference:
  spec.dimension                 -> str
  spec.build_messages(transcript) -> (system_prompt, user_message)
  spec.extract_result(data)       -> the raw label the model emitted
                                     ("result" for yaml, "verdict" for md)

Callers normalize the raw label with norm_label().
"""

import re
import yaml
from pathlib import Path


def norm_label(x):
    """Canonicalize any label to PASS / FAIL / N/A. Handles both the yaml
    `result` (PASS/FAIL/N/A) and the md `verdict` (pass/fail), plus the
    consensus CSV's `not_observed`."""
    u = str(x).strip().upper()
    if u in ("NOT_OBSERVED", "NOT OBSERVED", "NA", "N/A", "NONE", ""):
        return "N/A"
    return u


# The system-prompt wrapper for structured .yaml judges. Kept verbatim from the
# original build_system_prompt() so yaml behaviour is byte-for-byte unchanged.
def _build_yaml_system(p):
    return f"""You are an expert evaluator of AI voice coaching sessions.

Your task is to evaluate one specific coaching dimension:

DIMENSION: {p['dimension']}

DEFINITION:
{p['definition']}

PASS — what it looks like:
{p['pass']}

FAIL — what it looks like:
{p['fail']}

N/A — when to use it:
{p['na']}

Evaluate ONLY this dimension. Base your judgment solely on what is observable in the transcript.

Respond in JSON only. No markdown, no code blocks, no extra text:
{{"result": "PASS" or "FAIL" or "N/A", "evidence": "<copy the key exchange verbatim, max 200 chars>", "reasoning": "<one sentence explaining your verdict>"}}"""


# For .md prompts that embed {transcript} themselves, the transcript goes into
# the system prompt and the user turn is just a "return JSON" nudge (mirrors
# judge.py, the existing md runner).
_MD_USER_NUDGE = (
    "Output ONLY valid JSON (no other text), exactly in the verdict format "
    "specified above."
)


def _dimension_from_filename(path):
    """limits_the_load_v2.md -> limits_the_load ; feedback_q_low_bar_hero.md ->
    feedback_q_low_bar. Strips a trailing _v<N> and/or _hero marker."""
    stem = Path(path).stem
    stem = re.sub(r"_v\d+$", "", stem)      # drop _v2
    stem = re.sub(r"_hero$", "", stem)      # drop _hero
    stem = re.sub(r"_v\d+$", "", stem)      # drop _v2 if it preceded _hero
    return stem


class PromptSpec:
    def __init__(self, dimension, build_messages, extract_result, kind):
        self.dimension = dimension
        self.build_messages = build_messages    # transcript -> (system, user)
        self.extract_result = extract_result    # data(dict) -> raw label str
        self.kind = kind                        # "yaml" | "md"


def load_prompt_spec(prompt_path):
    """Load a judge prompt of either format and return a uniform PromptSpec."""
    path = Path(prompt_path)
    ext = path.suffix.lower()

    if ext in (".yaml", ".yml"):
        p = yaml.safe_load(path.read_text())
        system = _build_yaml_system(p)

        def build_messages(transcript, _system=system):
            return _system, f"TRANSCRIPT:\n\n{transcript}"

        return PromptSpec(
            dimension=p["dimension"],
            build_messages=build_messages,
            extract_result=lambda data: data.get("result", ""),
            kind="yaml",
        )

    # .md / .txt: the file is the whole prompt.
    template = path.read_text()
    has_placeholder = "{transcript}" in template

    def build_messages(transcript, _t=template, _ph=has_placeholder):
        if _ph:
            return _t.replace("{transcript}", transcript), _MD_USER_NUDGE
        # No placeholder: treat the file as a system prompt and append the
        # transcript as the user turn, like the yaml path.
        return _t, f"TRANSCRIPT:\n\n{transcript}"

    return PromptSpec(
        dimension=_dimension_from_filename(path),
        build_messages=build_messages,
        # md prompts emit "verdict"; fall back to "result" defensively.
        extract_result=lambda data: data.get("verdict", data.get("result", "")),
        kind="md",
    )
