#!/usr/bin/env python3
"""Simple labeling interface for consensus labeling."""

from flask import Flask, render_template, request, redirect, jsonify
import pandas as pd
import json
from pathlib import Path
from datetime import datetime

app = Flask(__name__)
HERE = Path(__file__).parent

# Load test set
TEST_SET_PATH = HERE / "pulled_test_set.csv"
RESULTS_PATH = HERE / "labeling_results.csv"

# Rubric text (human-readable)
RUBRIC_TEXT = """
# Feedback to Questions — Low Bar Judge Rubric

## What We're Evaluating
Whether the coach's per-question feedback is **egregiously bad**. This is a LOW BAR — the coach passes unless the feedback shows they did not accurately process what the participant said.

### Passing means:
- Generic but sound advice passes
- Ordinary encouragement of a mediocre answer passes
- The coach's feedback accurately reflects what the participant actually said

## What Makes Feedback Disconnected (Failing)

A feedback turn **fails** if ANY of these are true:

1. **Fake quality claims** — Coach praises a specific quality (great detail, strong example) that the answer doesn't actually show
2. **Validating empty responses** — Coach gives substantive praise or meaningful feedback to an answer with no real content, even if they later ask for elaboration
3. **Validating nonsense** — Coach treats a nonsensical, incoherent, or garbled response as good
4. **Advice mismatch** — Coach gives advice that doesn't match the question that was asked
5. **Delivering the answer** — Coach answers the question for the participant instead of responding to what they actually said
6. **Treating repeats as new** — Coach responds to a repeated answer as if it's new information
7. **Off-topic redirect** — Coach redirects a legitimate, on-topic response to something else
8. **Wrong or harmful advice** — Coach gives factually wrong or harmful interview advice

## The Rule
A single disconnected turn anywhere in the session is enough to **fail**. Otherwise, **pass**.
"""

def load_test_set():
    """Load the test set."""
    if not TEST_SET_PATH.exists():
        return []
    df = pd.read_csv(TEST_SET_PATH)
    return df.to_dict('records')

def parse_transcript(transcript):
    """Parse transcript into AI/User turns."""
    import re
    turns = []
    # Split by AI: or User: markers
    parts = re.split(r'(AI:|User:)', transcript)

    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            speaker = 'AI' if parts[i] == 'AI:' else 'User'
            text = parts[i + 1].strip()
            if text:
                turns.append({
                    'speaker': speaker,
                    'text': text
                })
    return turns

def load_results():
    """Load existing labeling results."""
    if not RESULTS_PATH.exists():
        return {}
    df = pd.read_csv(RESULTS_PATH)
    results = {}
    for _, row in df.iterrows():
        key = (row['source_row'], row['labeler'])
        results[key] = {
            'label': row['label'],
            'reasoning': row['reasoning']
        }
    return results

def save_result(source_row, labeler, label, reasoning):
    """Save a single labeling result."""
    if RESULTS_PATH.exists():
        df = pd.read_csv(RESULTS_PATH)
    else:
        df = pd.DataFrame(columns=['source_row', 'labeler', 'label', 'reasoning', 'timestamp'])

    # Remove existing entry if present
    df = df[(df['source_row'] != source_row) | (df['labeler'] != labeler)]

    # Add new entry
    new_row = {
        'source_row': source_row,
        'labeler': labeler,
        'label': label,
        'reasoning': reasoning,
        'timestamp': datetime.now().isoformat()
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(RESULTS_PATH, index=False)

@app.route('/')
def index():
    """Landing page - select labeler."""
    return render_template('index.html')

@app.route('/label/<labeler>')
def label_view(labeler):
    """Labeling view for a specific labeler."""
    if labeler not in ['grader_b', 'maya']:
        return redirect('/')

    test_set = load_test_set()
    results = load_results()

    # Find first unlabeled case
    current_case = None
    for case in test_set:
        key = (case['source_row'], labeler)
        if key not in results:
            current_case = case
            break

    # If all labeled, show summary
    if not current_case:
        return render_template('summary.html', labeler=labeler, results=results, test_set=test_set)

    # Parse transcript into turns
    turns = parse_transcript(current_case['transcript'])

    return render_template('label.html',
                         labeler=labeler,
                         case=current_case,
                         turns=turns,
                         rubric=RUBRIC_TEXT,
                         total=len(test_set),
                         current=next(i for i, c in enumerate(test_set) if c == current_case) + 1)

@app.route('/api/save', methods=['POST'])
def api_save():
    """Save a labeling result."""
    data = request.json
    save_result(
        int(data['source_row']),
        data['labeler'].lower(),
        data['label'],
        data['reasoning']
    )
    return jsonify({'success': True})

@app.route('/api/results')
def api_results():
    """Get all results."""
    results = load_results()
    return jsonify(results)

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5003))
    app.run(debug=False, port=port, host='0.0.0.0')
