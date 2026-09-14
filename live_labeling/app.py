"""Flask app: round-3 labeling of LIVE A/B production calls (Maya + Grader B).

15 real participant calls from the live-number A/B split, selected by
pull_labeling_set.py to be roughly balanced pass/fail per judge dimension.
BLIND: no judge verdicts, no prior labels, no A/B arm anywhere in the UI.
Division of labor: Maya scores 4 dimensions, Grader B 5 (incl. pii); the overall
impression is answered by both. Same stack and look as calibration/.

Run locally:
    cd live_labeling && /usr/bin/python3 seed.py && /usr/bin/python3 app.py
    # then open http://127.0.0.1:5003 — logins: /l/maya-live, /l/grader_b-live

Deploy-ready: set FLASK_SECRET_KEY, DATABASE_URL (Postgres) and serve with
gunicorn (`gunicorn app:app`); run seed.py once against the same DATABASE_URL.
"""

import csv
import io
import json
import os
import re
from functools import wraps

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
from transcript import parse_turns

app = Flask(__name__)
app.secret_key = config.flask_secret_key()

db.init_db()


# --- auth --------------------------------------------------------------------

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


@app.context_processor
def inject_globals():
    return {"user": g.user}


@app.template_filter("fromjson")
def fromjson(s):
    try:
        return json.loads(s or "[]")
    except (ValueError, TypeError):
        return []


@app.template_filter("dur_min")
def dur_min(seconds):
    try:
        return f"{round(float(seconds) / 60)} min"
    except (ValueError, TypeError):
        return "—"


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


# --- dimension-split helpers ----------------------------------------------------

def my_grouped_dims(labeler_name):
    """This labeler's share of the rubric, grouped by section, keeping each
    dimension's GLOBAL number (1-9) so numbering matches the rubric page:
    [(section_name, [(num, dim), ...]), ...]"""
    mine = set(config.dims_for(labeler_name))
    numbers = {d["id"]: i + 1 for i, d in enumerate(config.scored_rubric())}
    grouped = []
    for section_name, dims in config.scored_rubric_grouped():
        kept = [(numbers[d["id"]], d) for d in dims if d["id"] in mine]
        if kept:
            grouped.append((section_name, kept))
    return grouped


def my_dim_range(labeler_name):
    """Human-readable '1–4' / '5–9' style label for this labeler's dimensions:
    consecutive numbers compress into en-dash runs."""
    mine = set(config.dims_for(labeler_name))
    nums = sorted(i + 1 for i, d in enumerate(config.scored_rubric()) if d["id"] in mine)
    runs, start = [], nums[0]
    for prev, n in zip(nums, nums[1:] + [None]):
        if n != prev + 1:
            runs.append(str(start) if start == prev else f"{start}–{prev}")
            start = n
    return ", ".join(runs)


# --- labeler views -------------------------------------------------------------

@app.route("/")
@login_required
def index():
    rows = db.assignments_for_labeler(g.user["id"])
    done = sum(1 for r in rows if r["status"] == "done")
    # the other labeler's status per item, for the shared-progress column
    others = {}
    for l in db.all_labelers():
        if l["id"] == g.user["id"]:
            continue
        for a in db.assignments_for_labeler(l["id"]):
            others[a["item_id"]] = {"name": l["name"].split()[0], "status": a["status"]}
    return render_template(
        "dashboard.html", rows=rows, done=done, total=len(rows),
        others=others, dim_range=my_dim_range(g.user["name"]),
    )


@app.route("/item/<int:assignment_id>")
@login_required
def item(assignment_id):
    a = db.assignment_by_id(assignment_id)
    if not a:
        abort(404)
    if a["labeler_id"] != g.user["id"]:
        abort(403)
    turns = parse_turns(a["transcript"])
    return render_template(
        "item.html",
        a=a,
        turns=turns,
        grouped=my_grouped_dims(g.user["name"]),
        dim_range=my_dim_range(g.user["name"]),
        score_choices=config.SCORE_CHOICES,
        score_labels=config.SCORE_LABELS,
        saved_scores=json.loads(a["scores_json"] or "{}"),
        saved_notes=json.loads(a["notes_json"] or "{}"),
        saved_flags=set(json.loads(a["flags_json"] or "[]")),
    )


@app.route("/item/<int:assignment_id>/save", methods=["POST"])
@login_required
def save_item(assignment_id):
    a = db.assignment_by_id(assignment_id)
    if not a:
        abort(404)
    if a["labeler_id"] != g.user["id"]:
        abort(403)

    submit = request.form.get("action") == "submit"
    mine = set(config.dims_for(g.user["name"]))
    criteria = [c for c in config.scored_rubric() if c["id"] in mine]
    scores, notes, flags = {}, {}, []
    for c in criteria:
        val = request.form.get(f"score_{c['id']}", "").strip()
        if val in config.SCORE_CHOICES:
            scores[c["id"]] = val
        note = request.form.get(f"note_{c['id']}", "").strip()
        if note:
            notes[c["id"]] = note
        if request.form.get(f"flag_{c['id']}"):
            flags.append(c["id"])
    if request.form.get("flag_overall"):
        flags.append("overall")
    overall_notes = request.form.get("overall_notes", "").strip() or None
    recommend = request.form.get("would_recommend", "").strip()
    recommend = recommend if recommend in ("pass", "fail") else None

    db.save_assignment(assignment_id, scores, notes, flags, recommend, overall_notes, submit=submit)
    if submit:
        # Partial submits are allowed — start with the most important dimensions.
        missing = [c["name"] for c in criteria if c["id"] not in scores]
        if missing:
            flash("Submitted with unscored dimension(s): " + ", ".join(missing)
                  + " — reopen the call anytime to fill them in.", "ok")
        else:
            flash("Submitted. Thank you!", "ok")
        return redirect(url_for("index"))
    flash("Draft saved.", "ok")
    return redirect(url_for("item", assignment_id=assignment_id))


# --- rubric reference ------------------------------------------------------------

@app.route("/rubric")
@login_required
def rubric_page():
    numbers = {d["id"]: i + 1 for i, d in enumerate(config.scored_rubric())}
    split = {name: set(dims) for name, dims in config.DIM_SPLIT.items()}
    return render_template(
        "rubric.html",
        grouped=config.scored_rubric_grouped(),
        numbers=numbers,
        split=split,
    )


# --- flagged-for-discussion agenda ------------------------------------------------

@app.route("/flags")
@login_required
def flags_page():
    """Workbench for everything either labeler flagged as not cut-and-dry, grouped
    by call. Both labelers can score, annotate and resolve ANY flag here (writes
    go to the flag owner's scorecard), so the joint session needs one screen."""
    dims_by_id = {d["id"]: d for d in config.scored_rubric()}
    dim_order = {d_id: i for i, d_id in enumerate(dims_by_id)}
    dim_order["overall"] = len(dim_order)
    by_item = {}
    for a in db.all_assignments_full():
        flagged = json.loads(a["flags_json"] or "[]")
        if not flagged:
            continue
        scores = json.loads(a["scores_json"] or "{}")
        notes = json.loads(a["notes_json"] or "{}")
        e = by_item.setdefault(a["item_id"], {
            "item_id": a["item_id"],
            "ceo_id": a["ceo_id"],
            "turns": parse_turns(a["transcript"]),
            "entries": [],
        })
        for dim in flagged:
            crit = dims_by_id.get(dim)
            e["entries"].append({
                "labeler": a["labeler_name"],
                "owner": a["labeler_name"].split()[0],
                "assignment_id": a["id"],
                "dim": dim,
                "dim_name": crit["name"] if crit else "Overall impression",
                "crit": crit,
                "score": a["would_recommend"] if dim == "overall" else scores.get(dim),
                "note": (a["overall_notes"] if dim == "overall" else notes.get(dim)) or "",
                "mine": a["labeler_id"] == g.user["id"],
            })
    for e in by_item.values():
        e["entries"].sort(key=lambda en: (dim_order.get(en["dim"], 99), en["labeler"]))
    items = sorted(by_item.values(), key=lambda e: e["ceo_id"] or "")
    n_flags = sum(len(e["entries"]) for e in items)
    return render_template(
        "flags.html", items=items, n_flags=n_flags,
        score_choices=config.SCORE_CHOICES, score_labels=config.SCORE_LABELS,
    )


@app.route("/flags/<int:assignment_id>/<dim>", methods=["POST"])
@login_required
def resolve_flag(assignment_id, dim):
    """Save a verdict for one flagged dimension — usable by EITHER labeler.
    Writes to the assignment that owns the flag (not necessarily the logged-in
    user's), so Maya and Grader B can work the whole agenda from one login."""
    a = db.assignment_by_id(assignment_id)
    if not a:
        abort(404)
    if dim != "overall" and dim not in {d["id"] for d in config.scored_rubric()}:
        abort(404)

    scores = json.loads(a["scores_json"] or "{}")
    notes = json.loads(a["notes_json"] or "{}")
    flags = set(json.loads(a["flags_json"] or "[]"))
    recommend = a["would_recommend"]
    overall_notes = a["overall_notes"]

    score = request.form.get("score", "").strip()
    note = request.form.get("note", "").strip()
    if dim == "overall":
        if score in ("pass", "fail"):
            recommend = score
        overall_notes = note or None
    else:
        if score in config.SCORE_CHOICES:
            scores[dim] = score
        if note:
            notes[dim] = note
        else:
            notes.pop(dim, None)

    resolved = request.form.get("action") == "resolve"
    if resolved:
        flags.discard(dim)
    db.save_flag_resolution(assignment_id, scores, notes, flags, recommend, overall_notes)

    owner = a["labeler_name"].split()[0]
    if resolved:
        flash(f"Resolved — flag cleared on {owner}'s scorecard.", "ok")
    else:
        flash(f"Saved to {owner}'s scorecard — still flagged.", "ok")
    return redirect(url_for("flags_page") + f"#item-{a['item_id']}")


# --- compare + export ------------------------------------------------------------

@app.route("/compare")
@login_required
def compare():
    """Coverage matrix: who has scored what (dims are split, so per-dimension
    columns show coverage; Overall is scored by both and highlights disagreement)."""
    criteria = config.scored_rubric()
    assignments = db.all_assignments_full()
    by_item = {}
    for a in assignments:
        e = by_item.setdefault(a["item_id"], {"ceo_id": a["ceo_id"], "labelers": {}})
        e["labelers"][a["labeler_name"]] = {
            "status": a["status"],
            "scores": json.loads(a["scores_json"] or "{}"),
            "recommend": a["would_recommend"],
            "assignment_id": a["id"],
        }
    names = [l["name"] for l in db.all_labelers()]
    items = sorted(by_item.values(), key=lambda e: e["ceo_id"] or "")
    return render_template("compare.html", items=items, names=names, criteria=criteria)


@app.route("/export.csv")
@login_required
def export_csv():
    rows, cols = export_rows()
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=live_round3_labels.csv"},
    )


def export_rows():
    """One row per (labeler, call). call_id + arm are included here (only here)
    so the export joins straight back to the judge verdicts in
    labeling_set_live.tsv / Supabase."""
    criteria = config.scored_rubric()
    cols = ["labeler", "ceo_id", "call_id", "arm", "status", "submitted_at", "would_recommend"]
    cols += [c["id"] for c in criteria]
    cols += [f"note_{c['id']}" for c in criteria]
    cols += ["flagged_for_discussion", "overall_notes"]
    out = []
    for a in db.all_assignments_full():
        scores = json.loads(a["scores_json"] or "{}")
        notes = json.loads(a["notes_json"] or "{}")
        row = {
            "flagged_for_discussion": ", ".join(json.loads(a["flags_json"] or "[]")),
            "labeler": a["labeler_name"],
            "ceo_id": a["ceo_id"],
            "call_id": a["source_row"],
            "arm": a["arm"],
            "status": a["status"],
            "submitted_at": a["submitted_at"] or "",
            "would_recommend": a["would_recommend"] or "",
            "overall_notes": a["overall_notes"] or "",
        }
        for c in criteria:
            row[c["id"]] = scores.get(c["id"], "")
            row[f"note_{c['id']}"] = notes.get(c["id"], "")
        out.append(row)
    return out, cols


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5003"))
    app.run(debug=True, host="127.0.0.1", port=port)
