#!/usr/bin/env python3
"""
CEO Voice Coach Eval — Split Labels
Takes consensus_labels.csv and produces train/dev/test ID files.

Usage:
    python split_labels.py --train-pct 15 --dev-pct 42 --test-pct 43 --prioritize drives_practice_uptake

Splits at transcript level (not dimension level) to avoid contamination.
Stratifies on pass/fail balance for the prioritized dimension.
"""

import csv
import random
import argparse
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).parent.parent


def main():
    parser = argparse.ArgumentParser(description="Split labels into train/dev/test")
    parser.add_argument("--train-pct", type=int, default=15, help="Percent for training")
    parser.add_argument("--dev-pct", type=int, default=42, help="Percent for dev")
    parser.add_argument("--test-pct", type=int, default=43, help="Percent for test")
    parser.add_argument("--prioritize", default=None, help="Dimension to prioritize for pass/fail balance")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    assert args.train_pct + args.dev_pct + args.test_pct == 100, "Percentages must sum to 100"

    random.seed(args.seed)

    # Load labels
    labels_file = BASE_DIR / "labels" / "consensus_labels.csv"
    rows = list(csv.DictReader(open(labels_file)))

    # Get unique transcript IDs
    all_ids = list(set(r["transcript_id"] for r in rows))
    random.shuffle(all_ids)

    n = len(all_ids)
    n_train = max(1, int(n * args.train_pct / 100))
    n_dev = max(1, int(n * args.dev_pct / 100))
    # Test gets the rest
    n_test = n - n_train - n_dev

    if args.prioritize:
        # Stratify: separate pass and fail IDs for the priority dimension
        pass_ids = [r["transcript_id"] for r in rows
                    if r["dimension"] == args.prioritize and r["consensus_label"].upper() == "PASS"]
        fail_ids = [r["transcript_id"] for r in rows
                    if r["dimension"] == args.prioritize and r["consensus_label"].upper() == "FAIL"]
        other_ids = [tid for tid in all_ids if tid not in pass_ids and tid not in fail_ids]

        random.shuffle(pass_ids)
        random.shuffle(fail_ids)
        random.shuffle(other_ids)

        # Proportional allocation from pass and fail
        pass_ratio = len(pass_ids) / (len(pass_ids) + len(fail_ids)) if (len(pass_ids) + len(fail_ids)) > 0 else 0.5

        train_pass = int(n_train * pass_ratio)
        train_fail = n_train - train_pass

        train_ids = pass_ids[:train_pass] + fail_ids[:train_fail]
        remaining_pass = pass_ids[train_pass:]
        remaining_fail = fail_ids[train_fail:]

        remaining = remaining_pass + remaining_fail + other_ids
        random.shuffle(remaining)

        dev_ids = remaining[:n_dev]
        test_ids = remaining[n_dev:n_dev + n_test]
    else:
        train_ids = all_ids[:n_train]
        dev_ids = all_ids[n_train:n_train + n_dev]
        test_ids = all_ids[n_train + n_dev:]

    # Save
    for name, ids in [("train", train_ids), ("dev", dev_ids), ("test", test_ids)]:
        path = BASE_DIR / "labels" / f"{name}_ids.csv"
        with open(path, "w") as f:
            if name == "train":
                f.write("# Training set — can quote from these in prompts\n")
            elif name == "dev":
                f.write("# Dev set — tune against, no verbatim quotes\n")
            else:
                f.write("# Test set (HARD HOLDOUT) — touch once at the end\n")
            for tid in ids:
                f.write(f"{tid}\n")

    print(f"Split {n} transcripts:")
    print(f"  Train: {len(train_ids)}")
    print(f"  Dev:   {len(dev_ids)}")
    print(f"  Test:  {len(test_ids)}")

    if args.prioritize:
        # Show balance
        for name, ids in [("Train", train_ids), ("Dev", dev_ids), ("Test", test_ids)]:
            p = sum(1 for r in rows if r["transcript_id"] in ids
                    and r["dimension"] == args.prioritize and r["consensus_label"].upper() == "PASS")
            fl = sum(1 for r in rows if r["transcript_id"] in ids
                     and r["dimension"] == args.prioritize and r["consensus_label"].upper() == "FAIL")
            print(f"  {name} — {args.prioritize}: {p} PASS, {fl} FAIL")


if __name__ == "__main__":
    main()
