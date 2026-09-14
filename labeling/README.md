# Coach Labeling — human calibration web app

A small web app for the Phase-2 human-calibration round: job coaches log in with a
private passcode, see only the transcripts assigned to them, and score the AI Voice
Coach against the rubric side-by-side. Progress is tracked in SQLite and all scores
are downloadable as CSV/XLSX (to compare against the LLM judge in `coach_eval.jsonl`).

## What it does

- **Passcode login** — each labeler gets a private passcode + magic link (`/l/<passcode>`).
  No passwords, no email/OAuth.
- **Side-by-side scoring** — transcript (rendered as Coach/Participant turns) on the left,
  the **10 selected rubric criteria** (1–4 / N/A, with anchors + notes) on the right.
  Save draft or submit.
- **Admin dashboard** — add labelers, import transcripts from any project TSV, assign them,
  watch done/in-progress/total per labeler, and download all scores.

The rubric is **not** redefined here — it's imported live from `../analyze.py` (the source
of truth). To change which 10 categories are scored, edit `SCORED_CRITERIA` in `config.py`.

## Run locally

```bash
pip install -r ../requirements.txt
cd labeling
python app.py          # http://127.0.0.1:5000  (admin passcode: see below)
```

On first run an **Admin** login is created. The default admin passcode is
`admin-dev-passcode` (override with the `LABELING_ADMIN_PASSCODE` env var). Log in,
then use the admin page to add labelers, import + assign transcripts, and download scores.

### Quick bootstrap from the terminal (optional)

```bash
python seed.py admin
python seed.py add-labeler "CEO program lead" "Grader C"
python seed.py import pcpt_mock_interview_v2.tsv --random 30
python seed.py assign "CEO program lead"
python seed.py status
```

## Deploy (Render)

The repo includes `render.yaml` (a Blueprint) and a root `Procfile`.

1. Push the repo to GitHub (already connected here).
2. In Render: **New → Blueprint**, connect this repo. Render reads `render.yaml`
   and creates a web service + a 1 GB persistent disk at `/var/data`.
3. When prompted, set **`LABELING_ADMIN_PASSCODE`** to a private value (your admin
   login). `FLASK_SECRET_KEY` is auto-generated; `LABELING_DB_PATH` points at the disk.
4. Deploy. Open the URL → log in at `/l/<your-admin-passcode>`.
5. **Seed the data:** on the admin page, use **“Load a calibration round”** to upload
   the assignments `.xlsx` (CEO ID · Annotator · Transcript). This creates the fellow
   accounts, transcripts, and assignments. Their passcodes/magic links then show on
   the admin page — send each fellow their link.

The persistent disk is what keeps fellows' scores across restarts/redeploys (it
requires a paid Starter instance, ~$7/mo — cancellable after the test). You can
keep editing the rubric/UI and redeploy with `git push`; scores on the disk persist.

Any host that runs a Python web process works (Railway/Fly via the `Procfile`); just
ensure the DB path is on a persistent volume and the same env vars are set.

**Don't** run `load_calibration.py --fresh` against a live DB once fellows have
started — it resets everything.

## Data / privacy

`labeling.db` holds participant transcripts and is **gitignored** — never commit it.
