"""Parse a raw transcript string into (speaker, text) turns for display.

Transcripts in the TSV are a single line with inline "AI:" and "User:" markers
(no newlines between turns), e.g.:

    AI: Hello. ... User: Yes, sir. AI: Great. ...
"""

import re

# Split on each speaker marker, keeping the text up to the next marker.
_TURN_RE = re.compile(r"(AI|User):\s*(.*?)(?=(?:AI:|User:)|$)", re.DOTALL)


def parse_turns(transcript: str):
    """Return a list of {'speaker': 'AI'|'User', 'text': str} dicts."""
    if not transcript:
        return []
    turns = []
    for match in _TURN_RE.finditer(transcript):
        speaker = match.group(1)
        text = match.group(2).strip()
        if text:
            turns.append({"speaker": speaker, "text": text})
    # Fallback: if no markers matched, show the whole thing as one block.
    if not turns:
        turns.append({"speaker": "AI", "text": transcript.strip()})
    return turns
