"""Flask web app: human labelers score AI Voice Coach transcripts against the
rubric, side-by-side, seeing only the transcripts assigned to them.

Run locally:
    cd labeling && python app.py
    # then open http://127.0.0.1:5000  (admin passcode: see config.ADMIN_PASSCODE)

Deploy-ready: set FLASK_SECRET_KEY, LABELING_DB_PATH, LABELING_ADMIN_PASSCODE and
serve with gunicorn (`gunicorn app:app`). No code changes needed.
"""

import csv
import io
import json
import os
import random
import re
from collections import defaultdict
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    Response,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

import config
import db
import load_calibration
from transcript import parse_turns

app = Flask(__name__)
app.secret_key = config.flask_secret_key()

db.init_db()
db.ensure_admin(config.ADMIN_PASSCODE)  # works under gunicorn too, not just __main__


# --- auth helpers ----------------------------------------------------------

@app.before_request
def load_user():
    g.user = None
    lid = session.get("labeler_id")
    if lid:
        g.user = db.labeler_by_id(lid)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user:
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user:
            return redirect(url_for("login", next=request.path))
        if not g.user["is_admin"]:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


@app.context_processor
def inject_user():
    return {"user": g.user}


@app.template_filter("speaker_rows")
def speaker_rows(text):
    """Put each speaker on its own row: break before an 'AI:'/'User:' marker."""
    if not text:
        return text
    return re.sub(r"[ \t]+(AI:|User:)", r"\n\1", text)


def _strip_annotation(text):
    """Drop the trailing '— …' explanation line we attach to rubric examples.
    In the quiz it would give away whether the example is a pass or a fail."""
    lines = (text or "").split("\n")
    while lines and lines[-1].lstrip().startswith("—"):
        lines = lines[:-1]
    return "\n".join(lines).rstrip()


def quiz_questions():
    """Stable-ordered list of quiz items: each rubric pass/fail example with its
    correct label. Order is fixed so form fields (q0, q1, …) grade reliably.
    `example_quiz` has the giveaway explanation stripped; `example` keeps it
    (shown on the results page as part of the correction)."""
    qs = []
    for c in config.scored_rubric():
        for which in ("pass", "fail"):
            example = c.get(f"{which}_example")
            if example:
                qs.append({
                    "dim_id": c["id"], "dim_name": c["name"],
                    "definition": c["definition"], "watch_for": c.get("watch_for", ""),
                    "example": example, "example_quiz": _strip_annotation(example),
                    "correct": which,
                })
    return qs


def needs_quiz(user):
    """A non-admin labeler who hasn't completed the one-time rubric check."""
    if not user or user["is_admin"]:
        return False
    done = user["quiz_done_at"] if "quiz_done_at" in user.keys() else None
    return not done


def _parse_json_list(raw):
    """Parse a form field holding a JSON array of strings; tolerate junk."""
    if not raw:
        return []
    try:
        val = json.loads(raw)
        return [str(x) for x in val] if isinstance(val, list) else []
    except (ValueError, TypeError):
        return []


# --- auth routes -----------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        code = request.form.get("passcode", "").strip()
        user = db.labeler_by_passcode(code)
        if user:
            session["labeler_id"] = user["id"]
            nxt = request.form.get("next") or request.args.get("next")
            return redirect(nxt or url_for("index"))
        flash("That passcode wasn't recognized. Check it and try again.", "error")
    return render_template("login.html", next=request.args.get("next", ""))


@app.route("/l/<passcode>")
def magic_login(passcode):
    """Magic link: visiting it logs the labeler straight in."""
    user = db.labeler_by_passcode(passcode)
    if user:
        session["labeler_id"] = user["id"]
        return redirect(url_for("index"))
    flash("That link isn't valid.", "error")
    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/faq")
@login_required
def faq():
    return render_template("faq.html")


# --- one-time rubric check (quiz) -----------------------------------------

@app.route("/quiz")
@login_required
def quiz():
    if g.user["is_admin"]:
        return redirect(url_for("admin"))
    if not needs_quiz(g.user):
        return redirect(url_for("index"))
    questions = quiz_questions()
    # Group the two examples per dimension so fellows label which is which.
    # Keep each example's global index (q0, q1, …) for grading; shuffle the
    # order within a dimension so the pass example isn't always first.
    by_dim = {}
    for i, q in enumerate(questions):
        grp = by_dim.setdefault(q["dim_id"], {
            "dim_name": q["dim_name"], "definition": q["definition"],
            "watch_for": q["watch_for"], "examples": [],
        })
        grp["examples"].append({"idx": i, "text": q["example_quiz"]})
    groups = list(by_dim.values())
    for grp in groups:
        random.shuffle(grp["examples"])
    return render_template("quiz.html", groups=groups, total=len(questions))


@app.route("/quiz", methods=["POST"])
@login_required
def quiz_submit():
    if g.user["is_admin"]:
        abort(403)
    questions = quiz_questions()
    results, correct = [], 0
    for i, q in enumerate(questions):
        answer = request.form.get(f"q{i}", "")
        ok = answer == q["correct"]
        if ok:
            correct += 1
        results.append({**q, "answer": answer or "(blank)", "ok": ok})
    db.mark_quiz_done(g.user["id"])  # one-time: never gated again
    return render_template(
        "quiz_results.html", results=results, correct=correct, total=len(questions)
    )


# --- labeler views ---------------------------------------------------------

@app.route("/")
@login_required
def index():
    if g.user["is_admin"]:
        return redirect(url_for("admin"))
    if needs_quiz(g.user):
        return redirect(url_for("quiz"))
    rows = db.assignments_for_labeler(g.user["id"])
    done = sum(1 for r in rows if r["status"] == "done")
    return render_template("dashboard.html", rows=rows, done=done, total=len(rows))


@app.route("/item/<int:assignment_id>")
@login_required
def item(assignment_id):
    if needs_quiz(g.user):
        return redirect(url_for("quiz"))
    a = db.assignment_by_id(assignment_id)
    if not a:
        abort(404)
    if a["labeler_id"] != g.user["id"] and not g.user["is_admin"]:
        abort(403)
    turns = parse_turns(a["transcript"])
    grouped = config.scored_rubric_grouped()
    saved_scores = json.loads(a["scores_json"] or "{}")
    saved_notes = json.loads(a["notes_json"] or "{}")
    saved_evidence = json.loads((a["evidence_json"] if "evidence_json" in a.keys() else None) or "{}")
    step = request.args.get("step", "1")
    if step not in ("1", "2", "3"):
        step = "1"
    return render_template(
        "item.html",
        a=a,
        turns=turns,
        grouped=grouped,
        n_dims=len(config.scored_rubric()),
        score_choices=config.SCORE_CHOICES,
        score_labels=config.SCORE_LABELS,
        saved_scores=saved_scores,
        saved_notes=saved_notes,
        saved_evidence=saved_evidence,
        initial_step=step,
    )


@app.route("/item/<int:assignment_id>/save", methods=["POST"])
@login_required
def save_item(assignment_id):
    a = db.assignment_by_id(assignment_id)
    if not a:
        abort(404)
    if a["labeler_id"] != g.user["id"] and not g.user["is_admin"]:
        abort(403)

    submit = request.form.get("action") == "submit"
    criteria = config.scored_rubric()
    scores, notes, evidence = {}, {}, {}
    for c in criteria:
        cid = c["id"]
        val = request.form.get(f"score_{cid}", "").strip()
        if val in config.SCORE_CHOICES:
            scores[cid] = val
        note = request.form.get(f"note_{cid}", "").strip()
        if note:
            notes[cid] = note
        # dragged-in evidence quotes per bucket (JSON arrays from the form)
        good = _parse_json_list(request.form.get(f"evidence_good_{cid}"))
        bad = _parse_json_list(request.form.get(f"evidence_bad_{cid}"))
        if good or bad:
            evidence[cid] = {"good": good, "bad": bad}
    overall_notes = request.form.get("overall_notes", "").strip() or None
    # "Overall impression" — would you recommend this coach? (pass/fail, stored in overall_quality)
    recommend = request.form.get("would_recommend", "").strip()
    recommend = recommend if recommend in ("pass", "fail") else None
    step = request.form.get("current_step", "1")  # keep the labeler where they were

    if submit:
        missing = [c["name"] for c in criteria if c["id"] not in scores]
        if not recommend:
            missing.append("Overall impression")
        if missing:
            flash(
                "Saved as draft — to submit, mark Pass/Fail on every dimension. Missing: "
                + ", ".join(missing),
                "error",
            )
            db.save_assignment(
                assignment_id, scores, notes, evidence, recommend, overall_notes, submit=False
            )
            return redirect(url_for("item", assignment_id=assignment_id, step=step))

    db.save_assignment(
        assignment_id, scores, notes, evidence, recommend, overall_notes, submit=submit
    )
    if submit:
        flash("Submitted. Thank you!", "ok")
        return redirect(url_for("index"))
    flash("Draft saved.", "ok")
    return redirect(url_for("item", assignment_id=assignment_id, step=step))


# --- admin views -----------------------------------------------------------

@app.route("/admin")
@admin_required
def admin():
    labelers = [l for l in db.all_labelers() if not l["is_admin"]]
    assignments = db.all_assignments_full()
    # progress per labeler
    progress = {}
    for l in labelers:
        mine = [a for a in assignments if a["labeler_id"] == l["id"]]
        progress[l["id"]] = {
            "total": len(mine),
            "done": sum(1 for a in mine if a["status"] == "done"),
            "in_progress": sum(1 for a in mine if a["status"] == "in_progress"),
        }
    items = db.all_items()
    # which annotators each transcript is currently assigned to
    assigned_names = defaultdict(list)
    for a in assignments:
        assigned_names[a["item_id"]].append(a["labeler_name"])
    tsv_files = sorted(p.name for p in config.PROJECT_ROOT.glob("*.tsv"))
    return render_template(
        "admin.html",
        labelers=labelers,
        progress=progress,
        items=items,
        assignments=assignments,
        assigned_names=assigned_names,
        n_items=len(items),
        tsv_files=tsv_files,
        base_url=request.host_url.rstrip("/"),
    )


@app.route("/admin/labeler", methods=["POST"])
@admin_required
def admin_add_labeler():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Enter a name.", "error")
        return redirect(url_for("admin"))
    _, code = db.add_labeler(name)
    flash(f"Added {name}. Passcode: {code}", "ok")
    return redirect(url_for("admin"))


@app.route("/admin/labeler/delete", methods=["POST"])
@admin_required
def admin_delete_labeler():
    lid = request.form.get("labeler_id", type=int)
    if lid:
        db.delete_labeler(lid)
        flash("Removed that annotator and any of their assignments/scores.", "ok")
    return redirect(url_for("admin"))


@app.route("/admin/import", methods=["POST"])
@admin_required
def admin_import():
    fname = request.form.get("source_file", "").strip()
    mode = request.form.get("mode", "first")
    value = request.form.get("value", "").strip()
    path = config.PROJECT_ROOT / fname
    if not fname or not path.exists():
        flash("Pick a valid TSV file.", "error")
        return redirect(url_for("admin"))

    imported = import_rows(path, mode, value)
    flash(f"Imported {imported} transcript(s) from {fname}.", "ok")
    return redirect(url_for("admin"))


@app.route("/admin/load_calibration", methods=["POST"])
@admin_required
def admin_load_calibration():
    """Seed a calibration round from an uploaded assignments .xlsx
    (CEO ID | Annotator | Transcript) — the deploy-friendly way to load data."""
    f = request.files.get("calfile")
    if not f or not f.filename.lower().endswith(".xlsx"):
        flash("Choose a .xlsx assignments file to upload.", "error")
        return redirect(url_for("admin"))
    try:
        from openpyxl import load_workbook

        ws = load_workbook(f, data_only=True).worksheets[0]
        counts = load_calibration.load_assignments(ws, source_name=f.filename)
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("admin"))
    msg = (f"Loaded {counts['transcripts']} transcript(s), {counts['fellows']} "
           f"fellow(s), {counts['assignments']} assignment(s).")
    if counts["new_fellows"]:
        msg += " New: " + ", ".join(f"{n} ({c})" for n, c in counts["new_fellows"])
    flash(msg, "ok")
    return redirect(url_for("admin"))


@app.route("/admin/reset", methods=["POST"])
@admin_required
def admin_reset():
    if request.form.get("confirm") != "RESET":
        flash("Reset not confirmed.", "error")
        return redirect(url_for("admin"))
    db.clear_round_data()
    flash("Cleared all graders, transcripts, and scores. Upload a file to start a fresh round.", "ok")
    return redirect(url_for("admin"))


@app.route("/admin/assign", methods=["POST"])
@admin_required
def admin_assign():
    """Bulk-assign the checked transcripts to the chosen annotator. Re-assigning
    a transcript that's already assigned is a no-op, so a transcript can be given
    to several annotators by assigning it once per annotator (multi-rater)."""
    labeler_id = request.form.get("labeler_id", type=int)
    item_ids = request.form.getlist("item_ids", type=int)
    if not labeler_id:
        flash("Pick an annotator from the dropdown first.", "error")
        return redirect(url_for("admin"))
    if not item_ids:
        flash("Check at least one transcript to assign.", "error")
        return redirect(url_for("admin"))
    for iid in item_ids:
        db.assign(iid, labeler_id)
    flash(f"Assigned {len(item_ids)} transcript(s).", "ok")
    return redirect(url_for("admin"))


@app.route("/admin/transcripts/delete", methods=["POST"])
@admin_required
def admin_delete_items():
    ids = request.form.getlist("item_ids", type=int)
    if not ids:
        flash("Check at least one transcript to delete.", "error")
        return redirect(url_for("admin"))
    db.delete_items(ids)
    flash(f"Deleted {len(ids)} transcript(s) and any scores on them.", "ok")
    return redirect(url_for("admin"))


@app.route("/admin/export.csv")
@admin_required
def export_csv():
    rows, cols = export_rows()
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=coach_human_labels.csv"},
    )


@app.route("/admin/export.xlsx")
@admin_required
def export_xlsx():
    from openpyxl import Workbook

    rows, cols = export_rows()
    wb = Workbook()
    ws = wb.active
    ws.title = "Human labels"
    ws.append(cols)
    for r in rows:
        ws.append([r.get(c, "") for c in cols])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return Response(
        buf.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=coach_human_labels.xlsx"},
    )


# --- shared helpers --------------------------------------------------------

def import_rows(path: Path, mode: str, value: str) -> int:
    """Pull selected rows from a TSV into the items table. Returns count added.

    mode: 'first' (first N), 'random' (random N), 'rows' (comma-separated row
    numbers, 1-based over data rows).
    """
    csv.field_size_limit(10 ** 7)
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        all_rows = list(enumerate(reader, start=1))  # (row_no, dict)

    # find the transcript / ceo columns flexibly
    fields = all_rows[0][1].keys() if all_rows else []
    tcol = next((c for c in fields if c.strip().lower() == "transcript"), "Transcript")
    ccol = next((c for c in fields if c.strip().lower() == "ceo id"), "CEO ID")
    acol = next((c for c in fields if "assistant" in c.lower()), None)
    dcol = next((c for c in fields if "duration" in c.lower()), None)

    rows = [r for r in all_rows if (r[1].get(tcol) or "").strip()]

    if mode == "rows":
        wanted = {int(x) for x in value.replace(" ", "").split(",") if x.isdigit()}
        chosen = [r for r in rows if r[0] in wanted]
    else:
        try:
            n = int(value)
        except ValueError:
            n = 25
        chosen = random.sample(rows, min(n, len(rows))) if mode == "random" else rows[:n]

    count = 0
    for row_no, rec in chosen:
        db.add_item(
            source_file=path.name,
            source_row=row_no,
            ceo_id=(rec.get(ccol) or "").strip(),
            assistant=(rec.get(acol) or "").strip() if acol else "",
            duration=(rec.get(dcol) or "").strip() if dcol else "",
            transcript=rec.get(tcol, ""),
        )
        count += 1
    return count


def export_rows():
    """Flatten every assignment into one dict per (labeler, transcript)."""
    criteria = config.scored_rubric()
    cols = [
        "labeler",
        "ceo_id",
        "source_file",
        "source_row",
        "status",
        "submitted_at",
        "would_recommend",
    ]
    cols += [c["id"] for c in criteria]
    cols += [f"note_{c['id']}" for c in criteria]
    cols += [f"{c['id']}__good_evidence" for c in criteria]
    cols += [f"{c['id']}__bad_evidence" for c in criteria]
    cols += ["overall_notes"]

    out = []
    for a in db.all_assignments_full():
        scores = json.loads(a["scores_json"] or "{}")
        notes = json.loads(a["notes_json"] or "{}")
        evidence = json.loads((a["evidence_json"] if "evidence_json" in a.keys() else None) or "{}")
        row = {
            "labeler": a["labeler_name"],
            "ceo_id": a["ceo_id"],
            "source_file": a["source_file"],
            "source_row": a["source_row"],
            "status": a["status"],
            "submitted_at": a["submitted_at"] or "",
            "would_recommend": a["overall_quality"] or "",
            "overall_notes": a["overall_notes"] or "",
        }
        for c in criteria:
            ev = evidence.get(c["id"], {})
            row[c["id"]] = scores.get(c["id"], "")
            row[f"note_{c['id']}"] = notes.get(c["id"], "")
            row[f"{c['id']}__good_evidence"] = " || ".join(ev.get("good", []))
            row[f"{c['id']}__bad_evidence"] = " || ".join(ev.get("bad", []))
        out.append(row)
    return out, cols


if __name__ == "__main__":
    print(f"[app] Admin passcode: {config.ADMIN_PASSCODE}")
    # Port 5000 is taken by macOS AirPlay Receiver, so default to 5001.
    port = int(os.environ.get("PORT", "5001"))
    app.run(debug=True, host="127.0.0.1", port=port)
