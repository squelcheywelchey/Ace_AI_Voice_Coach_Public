"""Flask app: round-2 calibration labeling (Maya + Grader B).

Both labelers re-score the 50 round-1 calibration transcripts. On every
dimension they can see all 12 round-1 labels, each tagged with its labeler's
group (G1 hawks / G2 middle / G3 lenient / G4 noisy) plus that labeler's
evidence quotes and notes — so disagreements read as bar disputes.

Run locally:
    cd calibration && /usr/bin/python3 seed.py && /usr/bin/python3 app.py
    # then open http://127.0.0.1:5002

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

import calibration_notes
import config
import db
import groups
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
    return {"user": g.user, "GROUPS": groups.GROUPS}


@app.template_filter("fromjson")
def fromjson(s):
    try:
        return json.loads(s or "[]")
    except (ValueError, TypeError):
        return []


@app.template_filter("speaker_rows")
def speaker_rows(text):
    if not text:
        return text
    return re.sub(r"[ \t]+(AI:|User:|Coach:|Participant:)", r"\n\1", text)


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


# --- prior-label helpers -------------------------------------------------------

def prior_by_dimension(item_id):
    """For one transcript: {dim_id: [{labeler, grp, label, note, good, bad}, ...]}
    plus the overall-recommend list. Ordered G1 -> G4 within each dimension."""
    priors = db.prior_labels_for_item(item_id)
    dims = {d["id"]: [] for d in config.scored_rubric()}
    # A dimension may pull its round-1 labels from a retired dimension it was
    # split from (e.g. the four feedback brackets all map to feedback_is_correct).
    source = {d["id"]: d.get("prior_source", d["id"]) for d in config.scored_rubric()}
    overall = []
    for p in priors:
        scores = json.loads(p["scores_json"] or "{}")
        notes = json.loads(p["notes_json"] or "{}")
        evidence = json.loads(p["evidence_json"] or "{}")
        overall.append({
            "labeler": p["labeler_name"], "grp": p["grp"],
            "label": p["would_recommend"], "note": p["overall_notes"] or "",
        })
        for new_id, entries in dims.items():
            dim_id = source[new_id]
            label = scores.get(dim_id)
            if not label:
                continue
            ev = evidence.get(dim_id, {})
            entries.append({
                "labeler": p["labeler_name"],
                "grp": p["grp"],
                "label": label,
                "note": notes.get(dim_id, ""),
                "good": ev.get("good", []),
                "bad": ev.get("bad", []),
            })
    for entries in dims.values():
        entries.sort(key=lambda e: (e["grp"], e["labeler"]))
    overall.sort(key=lambda e: (e["grp"], e["labeler"]))
    return dims, overall


def tally(entries):
    """{'pass': n, 'fail': n, 'not_observed': n} for a list of prior entries."""
    t = {"pass": 0, "fail": 0, "not_observed": 0}
    for e in entries:
        if e["label"] in t:
            t[e["label"]] += 1
    return t


def my_grouped_dims(labeler_name):
    """This labeler's half of the rubric, grouped by section, keeping each
    dimension's GLOBAL number (1-10) so numbering matches the rubric page:
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
    """Human-readable '1–5, 12' style label for this labeler's dimensions:
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
    rec_counts = db.prior_recommend_counts()
    # the other labeler's status per item, for the shared-progress column
    others = {}
    for l in db.all_labelers():
        if l["id"] == g.user["id"]:
            continue
        for a in db.assignments_for_labeler(l["id"]):
            others[a["item_id"]] = {"name": l["name"].split()[0], "status": a["status"]}
    return render_template(
        "dashboard.html", rows=rows, done=done, total=len(rows),
        rec_counts=rec_counts, others=others, dim_range=my_dim_range(g.user["name"]),
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
    prior_dims, prior_overall = prior_by_dimension(a["item_id"])
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
        prior_dims=prior_dims,
        prior_overall=prior_overall,
        prior_tally={dim: tally(entries) for dim, entries in prior_dims.items()},
        overall_tally=tally(prior_overall),
        notes=calibration_notes.NOTES,
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


# --- rubric-rework reference -----------------------------------------------------

@app.route("/rubric")
@login_required
def rubric_page():
    import rubric as rubric_mod
    # Retired dims (e.g. feedback_is_correct) stay on this history page even
    # though they're no longer scored.
    all_dims = config.scored_rubric() + list(getattr(rubric_mod, "RETIRED_DIMENSIONS", []))
    rubric_by_id = {d["id"]: d for d in all_dims}
    ordered = [d["id"] for d in all_dims]
    return render_template(
        "rubric.html",
        bars=calibration_notes.BARS,
        global_rules=calibration_notes.GLOBAL_RULES,
        notes=calibration_notes.NOTES,
        rubric_by_id=rubric_by_id,
        ordered=ordered,
        decisions=calibration_notes.DECISIONS,
    )


# --- flagged-for-discussion agenda ------------------------------------------------

@app.route("/flags")
@login_required
def flags_page():
    """Workbench for everything either labeler flagged as not cut-and-dry, grouped
    by transcript. Both labelers can score, annotate and resolve ANY flag here
    (writes go to the flag owner's scorecard), so the joint session needs one screen."""
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
    # round-1 context per flagged dimension, same panels as the scoring page
    for item_id, e in by_item.items():
        prior_dims, prior_overall = prior_by_dimension(item_id)
        for entry in e["entries"]:
            prior = prior_overall if entry["dim"] == "overall" else prior_dims.get(entry["dim"], [])
            entry["prior"] = prior
            entry["prior_tally"] = tally(prior)
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
    """Maya-vs-Grader B agreement per transcript per dimension (round 2 only)."""
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
        headers={"Content-Disposition": "attachment; filename=round2_labels.csv"},
    )


def export_rows():
    criteria = config.scored_rubric()
    cols = ["labeler", "ceo_id", "source_row", "status", "submitted_at", "would_recommend"]
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
            "source_row": a["source_row"],
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
    port = int(os.environ.get("PORT", "5002"))
    app.run(debug=True, host="127.0.0.1", port=port)
