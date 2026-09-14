# CEO Voice Coach — Evaluation Suite

**MIT Bike Shop × Anthropic Fellowship | Summer 2026**

An LLM-as-judge evaluation suite for CEO's AI voice coach, which conducts mock job interviews with justice-impacted job seekers.

## What This Repo Contains

- **prompts/** — Judge prompt files, one per dimension per version. Never edit in place — copy to a new version file.
- **rubric/** — Dimension definitions, pass/fail criteria, and training set anchor examples.
- **labels/** — Human consensus labels and the train/dev/test split files.
- **scripts/** — Judge runner, eval harness, and label splitting utilities.
- **iteration_log/** — Running log per dimension: what changed, agreement before/after, keep/revert.
- **findings/** — Diagnostic notes written before each prompt edit.
- **outputs/** — (gitignored) Raw output CSVs from judge runs.

## Setup

```bash
cp .env.example .env
# Add your Anthropic API key to .env
```

## Workflow

1. Edit a prompt: copy `prompts/dim_vN.yaml` → `prompts/dim_vN+1.yaml`, make one change
2. Write diagnosis in `findings/dim_findings.md` before editing
3. Commit before running: `git commit -m "[dim] vN→vN+1: description"`
4. Run the harness: `python scripts/eval_harness.py --prompt prompts/dim_vN+1.yaml --split dev`
5. Log result in `iteration_log/dim.md`
6. Keep or revert

## Worked example: quality_conversational_flow (Maya)

Uses **`scripts/eval_harness_v2.py`** (Grader C's harness, from `judge_experiments_laura`):
per-run confusion matrix (TPR/TNR/PPV/NPV), append-only `iteration_log/run_log.csv`,
prompt content-hash + snapshot in `iteration_log/prompt_versions/`, and a browsable
HTML disagreements report. Splits were made with Grader B's `scripts/split_dimension.py`.

One-time setup (already done, commit `853a269`):

```bash
python3 scripts/split_dimension.py \
    --consensus labels/consensus_quality_conversational_flow.csv \
    --output-dir splits/quality_conversational_flow
# then mirror the split into labels/{train,dev,test}_ids.csv
# (source_row,ceo_id,dimension rows — the format eval_harness_v2 reads)
```

Each iteration:

```bash
# 1. diagnose from the last HTML report, note it in findings/
open outputs/quality_conversational_flow_vN_dev_disagreements.html

# 2. copy prompts/quality_conversational_flow_vN.yaml -> _vN+1.yaml, ONE change

# 3. commit BEFORE running
git commit -m "[quality_conversational_flow] vN->vN+1: <one change>"

# 4. run on dev (~23 judge calls)
python3 scripts/eval_harness_v2.py \
    --prompt prompts/quality_conversational_flow_v2.yaml --split dev \
    --consensus labels/consensus_quality_conversational_flow.csv

# 5. log metrics + keep/revert in iteration_log/quality_conversational_flow.md
#    (run_log.csv row is appended automatically)
```

`--model` overrides the judge model (default `claude-sonnet-4-6`); every run row
records prompt sha, git commit, and whether the prompt had uncommitted edits.
`--split test` only once, at the very end.

## Key Rules

- **Commit before you run** — the commit represents your intention, output is tied to that version
- **One edit per iteration** — change one thing, measure, decide
- **Training set quotes only** — never quote dev or test set transcripts in prompts
- **Test set touched once** — only after all iteration is complete
- **Outputs are gitignored** — reproducible from prompt + data, don't push CSVs

## Dimensions (10)

1. Scaffolds, then fades support
2. Adapts when stuck or frustrated
3. Kind delivery
4. Reentry-appropriate framing
5. Limits the load
6. Feedback is correct
7. Makes it a dialogue
8. Drives practice & uptake
9. Quality of conversational flow
10. PII handling
