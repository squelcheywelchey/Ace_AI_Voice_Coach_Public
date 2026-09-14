#!/usr/bin/env python3
"""
CEO Voice Coach Eval — Dimension-Level Split
Takes a consensus labels CSV for one dimension and splits into train/dev/test.

Usage:
    python3 split_dimension.py --consensus consensus_limits_the_load.csv --output-dir splits/limits_the_load

Produces:
    train_ids.csv  (~15% — examples you can quote in prompts)
    dev_ids.csv    (~43% — tune against, no verbatim quotes)
    test_ids.csv   (~42% — touch once at the end)

Split is stratified on pass/fail to maintain balance in each set.
"""

import argparse
import random
import pandas as pd
from pathlib import Path


def stratified_split(ids_by_class, train_pct=15, dev_pct=43, seed=42):
    """Split IDs stratified by class label."""
    random.seed(seed)

    train, dev, test = [], [], []

    for label, ids in ids_by_class.items():
        random.shuffle(ids)
        n = len(ids)
        n_train = max(1, round(n * train_pct / 100))
        n_dev = round(n * dev_pct / 100)
        n_test = n - n_train - n_dev

        # Ensure at least 1 in dev and test if possible
        if n_test < 1 and n > 2:
            n_test = 1
            n_dev = n - n_train - n_test

        train.extend(ids[:n_train])
        dev.extend(ids[n_train:n_train + n_dev])
        test.extend(ids[n_train + n_dev:])

    return train, dev, test


def main():
    parser = argparse.ArgumentParser(description="Split consensus labels into train/dev/test")
    parser.add_argument("--consensus", required=True, help="Path to consensus labels CSV")
    parser.add_argument("--output-dir", required=True, help="Directory to save split files")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--include-not-observed", action="store_true",
                        help="Treat not_observed as a third stratified class (for N/A-heavy dims like "
                             "adapts_when_stuck, where correct abstention IS the behavior under test). "
                             "Default off = legacy behavior (pass/fail only).")
    args = parser.parse_args()

    df = pd.read_csv(args.consensus)
    dimension = df['dimension'].iloc[0]

    # Classes to stratify on. Legacy default is pass/fail only (not_observed dropped);
    # --include-not-observed keeps N/A as a real class so the judge is tested on abstention too.
    keep_labels = ['pass', 'fail'] + (['not_observed'] if args.include_not_observed else [])
    kept = df[df['consensus_label'].isin(keep_labels)]
    dropped = df[~df['consensus_label'].isin(keep_labels)]

    ids_by_class = {}
    for label in keep_labels:
        ids = kept[kept['consensus_label'] == label]['source_row'].tolist()
        ids_by_class[label] = ids

    train_ids, dev_ids, test_ids = stratified_split(ids_by_class, seed=args.seed)

    # Create output directory
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Save split files
    for name, ids, comment in [
        ("train_ids.csv", train_ids, "Training set — can quote from these in prompts"),
        ("dev_ids.csv", dev_ids, "Dev set — tune against, no verbatim quotes"),
        ("test_ids.csv", test_ids, "Test set (HARD HOLDOUT) — touch once at the end"),
    ]:
        with open(out / name, "w") as f:
            f.write(f"# {comment}\n")
            for sid in sorted(ids):
                f.write(f"{sid}\n")

    # Print summary
    print(f"\n{'='*55}")
    print(f"  SPLIT — {dimension}")
    print(f"{'='*55}")
    print(f"  Total kept: {len(kept)}  (classes: {', '.join(keep_labels)})")
    print(f"  Dropped: {len(dropped)}")
    print(f"\n  {'Set':<10} {'Total':>6} {'Pass':>6} {'Fail':>6} {'NotObs':>7}")
    print(f"  {'-'*42}")

    for name, ids in [("Train", train_ids), ("Dev", dev_ids), ("Test", test_ids)]:
        subset = kept[kept['source_row'].isin(ids)]
        p = (subset['consensus_label'] == 'pass').sum()
        f_count = (subset['consensus_label'] == 'fail').sum()
        no = (subset['consensus_label'] == 'not_observed').sum()
        print(f"  {name:<10} {len(ids):>6} {p:>6} {f_count:>6} {no:>7}")

    print(f"\n  Files saved to: {out}/")
    print(f"{'='*55}")

    # Also save a combined reference file
    scoreable_with_split = kept.copy()
    split_map = {}
    for sid in train_ids:
        split_map[sid] = 'train'
    for sid in dev_ids:
        split_map[sid] = 'dev'
    for sid in test_ids:
        split_map[sid] = 'test'
    scoreable_with_split['split'] = scoreable_with_split['source_row'].map(split_map)
    scoreable_with_split.to_csv(out / "split_reference.csv", index=False)
    print(f"  Reference file with split assignments: {out}/split_reference.csv\n")


if __name__ == "__main__":
    main()
