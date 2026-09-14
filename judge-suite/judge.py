"""[low-code] Rubric LLM-judge — one function, one prompt template.

judge(transcript, rubric_path) -> {"verdict": "pass" | "partial" | "fail", "reasoning": str}

Use as a `custom` check in ../eval-harness/run_eval.py, or call directly.
Calibrate against a human-labeled golden set before trusting the verdicts —
see ../../guides/designing-a-test-set.md.
"""
import json
import os
import re
from pathlib import Path
from typing import Union
from pydantic import BaseModel

if not os.environ.get("ANTHROPIC_API_KEY"):
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent / ".env")
    except ImportError:
        pass

import anthropic

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")  # see MODELS.md
_VALID = {"pass", "partial", "fail"}
_DEFAULT_RUBRIC = Path(__file__).parent / "prompts" / "limits_the_load_v2.md"


class Step1Scan(BaseModel):
    total_mid_session_feedback_turns: int
    focused_count: int
    overloaded_count: int
    participant_checked_out: bool


class JudgeResponse(BaseModel):
    step1_scan: Step1Scan
    verdict: str
    reasoning: str


def judge(transcript: str, rubric_path: Union[str, Path] = _DEFAULT_RUBRIC) -> dict:
    """Grade `transcript` against the rubric in `rubric_path`."""
    rubric = Path(rubric_path).read_text()
    system = rubric.replace("{transcript}", transcript)
    try:
        resp = anthropic.Anthropic().messages.create(
            model=MODEL,
            max_tokens=1024,
            temperature=0,
            system=system,
            messages=[{"role": "user", "content": "Output ONLY valid JSON (no other text) with step1_scan, verdict, and reasoning fields. step1_scan MUST contain total_mid_session_feedback_turns, focused_count, overloaded_count, and participant_checked_out."}],
        )
    except anthropic.APIError as e:
        return {"verdict": "fail", "reasoning": f"judge API error: {type(e).__name__}: {e}"}

    text = next((b.text for b in resp.content if b.type == "text"), "")
    try:
        # Strip markdown code blocks if present
        text = text.strip()
        if text.startswith("```"):
            # Remove opening ``` and language tag (e.g., ```json)
            text = re.sub(r"^```(?:json)?\n?", "", text)
            # Remove closing ```
            text = re.sub(r"\n?```$", "", text)
            text = text.strip()

        result = json.loads(text)
        verdict = str(result.get("verdict", "")).lower()
        if verdict not in _VALID:
            verdict = "fail"
        return result
    except Exception:
        return {"verdict": "fail", "reasoning": f"judge returned non-JSON: {text[:200]}"}


if __name__ == "__main__":
    import sys
    print(json.dumps(judge(Path(sys.argv[1]).read_text(),
                           sys.argv[2] if len(sys.argv) > 2 else _DEFAULT_RUBRIC),
                     indent=2))
