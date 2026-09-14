# Limits the Load — Judge Rubric

You are evaluating an AI voice coaching session on ONE dimension: whether feedback stays digestible for the participant.

The participant may be nervous, have limited education, and is on a phone with no visual reference. They must be able to understand, retain, and act on what the coach says.

## Step 1 — Scan

Read the entire transcript. For each mid-session feedback turn by the coach (NOT the end-of-session summary), classify it as:

- **focused**: one acknowledgment + one specific suggestion + retry offer
- **overloaded**: multiple improvement points, numbered lists, or "Strengths... Areas for improvement..." template walls

Note: The structured end-of-session summary (Strengths / Areas / Next steps / Overall) is EXEMPT. Do not count it.

## Step 2 — Judge

Based on your scan, render a holistic verdict.

### Criteria

1. **Per-turn digestibility** — Are the majority of mid-session feedback turns focused (one suggestion) rather than overloaded (multiple points)?
2. **Responsiveness to disengagement** — If the participant is visibly checked out (terse answers, "next question" repeatedly, declining retries), does the coach shorten its feedback or does it keep delivering walls?

### Hard gate

If the coach delivers a multi-point lecture block (3+ improvement suggestions in a single mid-session turn) more than twice, that is an automatic **fail** regardless of overall pattern.

## Verdict format

Respond in JSON only. No markdown, no code blocks.

```
{
  "step1_scan": {
    "total_mid_session_feedback_turns": <int>,
    "focused_count": <int>,
    "overloaded_count": <int>,
    "participant_checked_out": true/false
  },
  "verdict": "pass" or "fail",
  "reasoning": "<2-3 sentences explaining the overall pattern and your judgment>"
}
```

