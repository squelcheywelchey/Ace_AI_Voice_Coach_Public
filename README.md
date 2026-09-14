# CEO Voice Coach — Evaluation System

An LLM-as-judge system that scores the quality of an AI job-interview coach, built
during the MIT Bike Shop × Anthropic Social Impact Fellowship (2026).

**"CEO" here is the Center for Employment Opportunities**, a reentry-employment
nonprofit, not a chief executive. The AI Voice Coach is a phone line their
participants call to practise for job interviews: the caller verifies an ID, picks
Mock Interview / Job Quiz / Role Play, practises out loud, and gets spoken and SMS
feedback.

**The thing being evaluated is the coach, not the participant.** Every judge in this
repo scores the coach's turns.

> **No participant data is in this repository.** See [DATA.md](DATA.md) for what was
> withheld, what was redacted, and what you can still run.

## The problem this solves

A voice coach either helps someone walk into an interview more prepared, or it
doesn't, and call volume makes it impossible for job coaches to listen to every call
and say which. The question is whether an LLM judge can stand in for a human job
coach reliably enough to steer product decisions.

That question has a measurable answer: how often does the judge agree with the
humans? The target was 80%+ agreement with job-coach labels on held-out calls.

## What's here

### The rubric
Twelve to thirteen dimensions of coaching quality, scored pass/fail, grouped into
four sections: meeting the participant where they're at, social-emotional awareness,
motivating skill development, and prompt adherence.

The definitions live in `calibration/rubric.py` (v2, the decided version),
`labeling/rubric.py` (v1, round 1), and `judge-suite/rubric/dimensions.yaml`. Each
dimension carries a pass and a fail anchor quoted from a real call, which is what
makes the bar concrete enough to apply. Nine of these dimensions run against live
production calls.

### The judges
`judge-suite/prompts/` holds every version of every judge prompt, including the
`*_hero.yaml` champions. Prompts are never edited in place; each iteration becomes a
new numbered file, so the full lineage is readable.

### The tuning record
`judge-suite/iteration_log/` is the part worth reading. One file per dimension,
recording each prompt change, what was predicted, what actually happened to
agreement, and whether the change was kept or reverted. It also records the
mismatches ruled to be *label* errors rather than judge errors, and why.

`judge-suite/findings/` holds the diagnostic notes written before each edit.

Two representative results: the conversational-flow judge closed at 93.3% agreement
on live calls and 87.0% on dev; the scaffolding judge at 87.0% on both dev and test.
Not every dimension got there, and the logs are candid about which did not and why.

### The harness
```bash
python analyze.py --file data/sim_calls.tsv    # score transcripts against the rubric
python summarize.py                            # aggregate report, weakest dimensions
python export.py                               # one filterable row per call
```

`judge-suite/scripts/` has the eval harness, the judge runner, and the split tools.
`judge-suite/eval-server/` is the production webhook service: Vapi posts a finished
call, the judges score it, results land in Postgres.

### The simulators
Real calls are a fixed corpus, so the coach is also stress-tested with synthetic
callers. Six personas in `personas.py` (polished, distracted, restart-loop, nervous,
terse, opts-out), each a different failure mode.

```bash
python simulate.py --persona terse   # text loop, cheap
python voice_sim.py --persona terse  # real voice call via Vapi Simulations
```

Both write transcripts in the same shape the judge already reads. Sample output is
in `data/`.

### The labeling apps
Three Flask apps for the human side of calibration, all the same stack:

- `labeling/`: round 1, twelve graders scoring a shared set
- `calibration/`: round 2, re-scoring while seeing round-1 labels grouped by how
  strictly each grader graded
- `live_labeling/`: round 3, blind labeling of live production calls

Each needs a database seeded from data that isn't published, so they run but start
empty.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env    # add ANTHROPIC_API_KEY
```

Vapi simulation and dashboard scripts need additional keys and assistant IDs; the
scripts read them from the environment and fail loudly if they're missing.

## Things worth knowing before reading the logs

**The judges are calibrated against human consensus, not truth.** Agreement numbers
say the judge matches how these particular job coaches scored these particular calls.

**Human graders disagreed with each other a lot.** Round 1 produced four distinct
strictness clusters. A good part of this project was deciding what the bar should be
before a judge could be tuned to hit it.

**Some dimensions were reopened after deployment.** A judge that agrees on the
tuning corpus can drift on live calls, which come from a different distribution.
That reopening is in the logs too.

## Layout

```
analyze.py, judge.py, summarize.py, export.py   rubric scoring + reporting
simulate.py, voice_sim.py, personas.py          synthetic caller harness
so_eval.py, vapi_setup.py                       Vapi structured-output bridge
judge-suite/prompts/                            every judge prompt version
judge-suite/rubric/                             dimension definitions
judge-suite/iteration_log/                      per-dimension tuning record
judge-suite/findings/                           pre-edit diagnostics
judge-suite/scripts/                            eval harness + runners
judge-suite/eval-server/                        production webhook service
labeling/, calibration/, live_labeling/         human labeling apps
data/                                           synthetic sample transcripts
```

## Status and license

Built as fellowship work through 2026 and handed over to CEO, who now own the
production deployment. This repository is a public snapshot of the evaluation
system, kept separate from the working repository.

No license is set yet. Ask before reusing.
