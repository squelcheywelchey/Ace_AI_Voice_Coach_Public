"""Bootstrap the labeling app from the terminal (quick alternative to the admin UI).

Examples:
    # one-time: create the admin login
    python seed.py admin

    # add labelers (prints their private passcode + magic link)
    python seed.py add-labeler "CEO program lead" "Grader C"

    # pull transcripts into the review pool
    python seed.py import pcpt_mock_interview_v2.tsv --first 30
    python seed.py import pcpt_mock_interview_v2.tsv --random 30
    python seed.py import pcpt_mock_interview_v2.tsv --rows 2,5,9

    # assign every unassigned transcript to a labeler (by name)
    python seed.py assign "CEO program lead"

    # show current state
    python seed.py status
"""

import argparse
import sys

import config
import db
from app import import_rows  # reuse the same import logic the web UI uses


def cmd_admin(args):
    db.init_db()
    if any(l["is_admin"] for l in db.all_labelers()):
        print("Admin already exists.")
        return
    _, code = db.add_labeler("Admin", is_admin=True, passcode=config.ADMIN_PASSCODE)
    print(f"Created admin. Passcode: {code}")


def cmd_add_labeler(args):
    db.init_db()
    for name in args.names:
        lid, code = db.add_labeler(name)
        print(f"{name}: passcode={code}  link=/l/{code}")


def cmd_import(args):
    db.init_db()
    path = config.PROJECT_ROOT / args.file
    if not path.exists():
        sys.exit(f"No such file: {path}")
    if args.rows:
        mode, value = "rows", args.rows
    elif args.random:
        mode, value = "random", str(args.random)
    else:
        mode, value = "first", str(args.first or 25)
    n = import_rows(path, mode, value)
    print(f"Imported {n} transcript(s) from {args.file}.")


def cmd_assign(args):
    db.init_db()
    labeler = next(
        (l for l in db.all_labelers() if l["name"].lower() == args.name.lower()), None
    )
    if not labeler:
        sys.exit(f"No labeler named '{args.name}'. Add them first.")
    assignments = db.all_assignments_full()
    assigned = {a["item_id"] for a in assignments}
    todo = [i for i in db.all_items() if i["id"] not in assigned]
    for i in todo:
        db.assign(i["id"], labeler["id"])
    print(f"Assigned {len(todo)} transcript(s) to {labeler['name']}.")


def cmd_status(args):
    db.init_db()
    print(f"Items in pool: {len(db.all_items())}")
    print("Labelers:")
    assignments = db.all_assignments_full()
    for l in db.all_labelers():
        mine = [a for a in assignments if a["labeler_id"] == l["id"]]
        done = sum(1 for a in mine if a["status"] == "done")
        tag = " (admin)" if l["is_admin"] else ""
        print(f"  - {l['name']}{tag}: {done}/{len(mine)} done · passcode={l['passcode']}")


def main():
    p = argparse.ArgumentParser(description="Labeling app bootstrap CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("admin").set_defaults(func=cmd_admin)

    a = sub.add_parser("add-labeler")
    a.add_argument("names", nargs="+")
    a.set_defaults(func=cmd_add_labeler)

    im = sub.add_parser("import")
    im.add_argument("file")
    im.add_argument("--first", type=int)
    im.add_argument("--random", type=int)
    im.add_argument("--rows", type=str)
    im.set_defaults(func=cmd_import)

    asg = sub.add_parser("assign")
    asg.add_argument("name")
    asg.set_defaults(func=cmd_assign)

    sub.add_parser("status").set_defaults(func=cmd_status)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
