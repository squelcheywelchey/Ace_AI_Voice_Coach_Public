"""
Wire the synthetic makes_it_a_dialogue transcripts into the judge-suite.

Reads the two generated TSVs and produces the data assets the harness needs:

  judge-suite/labels/consensus_makes_it_a_dialogue.csv
      one row per transcript: source_row, ceo_id, dimension, consensus_label,
      individual_labels, excerpt  (the harness reads `excerpt` directly).

  judge-suite/labels/dev_ids.csv  /  test_ids.csv   (APPENDED, idempotent)
      registers each source_row under dimension=makes_it_a_dialogue so
      eval_harness_v2.py --split dev/test picks them up.

  judge-suite/splits/makes_it_a_dialogue/{dev_ids,test_ids,split_reference}.csv
      reference copies, matching the layout of the other dimensions.

Source-row numbering is kept in a reserved synthetic range (9001+/9101+) so it
never collides with the real corpus rows. Re-running is safe: split rows for
this dimension are de-duped before writing.

Run AFTER make_dialogue_synth.py:
    python make_dialogue_synth.py && python wire_dialogue_into_suite.py
"""
import csv
from pathlib import Path

csv.field_size_limit(10 ** 7)

DIM = "makes_it_a_dialogue"
HERE = Path(__file__).parent
SUITE = HERE / "judge-suite"
LABELS = SUITE / "labels"
SPLITDIR = SUITE / "splits" / DIM

POS_TSV = HERE / "synthetic_makes_it_a_dialogue.tsv"
NEG_TSV = HERE / "synthetic_makes_it_a_dialogue_negatives.tsv"
TRICKY_TSV = HERE / "synthetic_makes_it_a_dialogue_tricky.tsv"
TRICKY_NEG_TSV = HERE / "synthetic_makes_it_a_dialogue_tricky_negatives.tsv"

# source_row assignment (reserved synthetic range) + split membership.
#   9001-9004  clean positives    (reflective Q + specifics)
#   9005-9009  TRICKY positives   (buried STT / one-Q-amid-templated / unusual
#                                  phrasing / wrap-up-only / deflected) -> all dev
#   9101-9104  matched near-miss negatives
#   9105-9109  TRICKY negatives   (comprehension-check / STT content follow-up /
#                                  reflective-Qs-but-no-engagement / content-add /
#                                  factual clarifier) -> all dev
# dev = tune against; test = holdout. Test stays a balanced 1 pass / 1 fail so the
# tricky rows (added to dev) don't skew the held-out metric.
POS_BASE, NEG_BASE, TRICKY_BASE, TRICKY_NEG_BASE = 9001, 9101, 9005, 9105
TEST_ROWS = {9004, 9104}  # everything else -> dev


def read_tsv(path):
    with open(path) as f:
        return list(csv.DictReader(f, delimiter="\t"))


def build_consensus_rows():
    rows = []
    for i, r in enumerate(read_tsv(POS_TSV)):
        rows.append(dict(source_row=POS_BASE + i, ceo_id=r["CEO ID"], label="pass",
                         excerpt=r["Transcript"]))
    for i, r in enumerate(read_tsv(NEG_TSV)):
        rows.append(dict(source_row=NEG_BASE + i, ceo_id=r["CEO ID"], label="fail",
                         excerpt=r["Transcript"]))
    for i, r in enumerate(read_tsv(TRICKY_TSV)):
        rows.append(dict(source_row=TRICKY_BASE + i, ceo_id=r["CEO ID"], label="pass",
                         excerpt=r["Transcript"]))
    for i, r in enumerate(read_tsv(TRICKY_NEG_TSV)):
        rows.append(dict(source_row=TRICKY_NEG_BASE + i, ceo_id=r["CEO ID"], label="fail",
                         excerpt=r["Transcript"]))
    return rows


def write_consensus(rows):
    out = LABELS / f"consensus_{DIM}.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source_row", "ceo_id", "dimension", "consensus_label",
                    "individual_labels", "excerpt"])
        for r in rows:
            w.writerow([r["source_row"], r["ceo_id"], DIM, r["label"],
                        f"{{'synthetic_seed': '{r['label']}'}}", r["excerpt"]])
    return out


def append_split(split_name, rows):
    """Append this dimension's rows to labels/<split>_ids.csv, de-duping any
    existing makes_it_a_dialogue rows first so re-runs stay idempotent."""
    path = LABELS / f"{split_name}_ids.csv"
    existing = []
    if path.exists():
        with open(path) as f:
            existing = [r for r in csv.DictReader(f) if r.get("dimension") != DIM]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source_row", "ceo_id", "dimension"])
        for r in existing:
            w.writerow([r["source_row"], r["ceo_id"], r["dimension"]])
        for r in rows:
            w.writerow([r["source_row"], r["ceo_id"], DIM])
    return path


def write_split_reference(rows):
    SPLITDIR.mkdir(parents=True, exist_ok=True)
    dev = [r for r in rows if r["source_row"] not in TEST_ROWS]
    test = [r for r in rows if r["source_row"] in TEST_ROWS]
    for name, subset in (("dev", dev), ("test", test)):
        with open(SPLITDIR / f"{name}_ids.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["source_row", "ceo_id", "dimension"])
            for r in subset:
                w.writerow([r["source_row"], r["ceo_id"], DIM])
    with open(SPLITDIR / "split_reference.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source_row", "ceo_id", "dimension", "consensus_label", "excerpt", "split"])
        for r in rows:
            split = "test" if r["source_row"] in TEST_ROWS else "dev"
            w.writerow([r["source_row"], r["ceo_id"], DIM, r["label"], r["excerpt"], split])
    return dev, test


def main():
    rows = build_consensus_rows()
    dev = [r for r in rows if r["source_row"] not in TEST_ROWS]
    test = [r for r in rows if r["source_row"] in TEST_ROWS]

    cons = write_consensus(rows)
    dev_path = append_split("dev", dev)
    test_path = append_split("test", test)
    write_split_reference(rows)

    print(f"Wrote {cons.relative_to(HERE)}  ({len(rows)} rows: "
          f"{sum(r['label'] == 'pass' for r in rows)} pass / "
          f"{sum(r['label'] == 'fail' for r in rows)} fail)")
    print(f"Registered dev split  -> {dev_path.relative_to(HERE)}  (+{len(dev)} rows for {DIM})")
    print(f"Registered test split -> {test_path.relative_to(HERE)}  (+{len(test)} rows for {DIM})")
    print(f"Reference copies      -> {SPLITDIR.relative_to(HERE)}/")
    print("\nDev  :", ", ".join(f"{r['source_row']}({r['label']})" for r in dev))
    print("Test :", ", ".join(f"{r['source_row']}({r['label']})" for r in test))


if __name__ == "__main__":
    main()
