import csv
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "resources"
    / "processed"
    / "resource_dataset.csv"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "resources"
    / "processed"
    / "split"
)

SEED = 42


def write_csv(path, rows, fieldnames):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():

    with open(INPUT_FILE, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    random.seed(SEED)
    random.shuffle(rows)

    train_end = 350
    val_end = 450

    train_rows = rows[:train_end]
    val_rows = rows[train_end:val_end]
    test_rows = rows[val_end:]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = list(rows[0].keys())

    write_csv(
        OUTPUT_DIR / "train.csv",
        train_rows,
        fieldnames
    )

    write_csv(
        OUTPUT_DIR / "validation.csv",
        val_rows,
        fieldnames
    )

    write_csv(
        OUTPUT_DIR / "test.csv",
        test_rows,
        fieldnames
    )

    print("RESOURCE DATASET SPLIT COMPLETE")
    print(f"Train: {len(train_rows)}")
    print(f"Validation: {len(val_rows)}")
    print(f"Test: {len(test_rows)}")
    print(f"Total: {len(rows)}")
    print(f"Random seed: {SEED}")


if __name__ == "__main__":
    main()