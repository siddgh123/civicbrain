from pathlib import Path
import shutil
import random


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(
    r"C:\Users\Siddhesh\OneDrive\Desktop\CivicBrain"
)

SOURCE = (
    PROJECT_ROOT
    / "data"
    / "yolo"
    / "raw"
    / "waterlogging_converted"
)

OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "yolo"
    / "raw"
    / "waterlogging_split"
)


# ============================================================
# SETTINGS
# ============================================================

SEED = 42

TRAIN_RATIO = 0.80
VAL_RATIO = 0.10
TEST_RATIO = 0.10


IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp"
}


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("Waterlogging Dataset Split")
    print("=" * 70)

    source_images = SOURCE / "images"
    source_labels = SOURCE / "labels"

    if not source_images.exists():
        raise FileNotFoundError(
            f"Source images folder not found: {source_images}"
        )

    if not source_labels.exists():
        raise FileNotFoundError(
            f"Source labels folder not found: {source_labels}"
        )

    # --------------------------------------------------------
    # Collect paired images
    # --------------------------------------------------------

    images = sorted(
        [
            p
            for p in source_images.iterdir()
            if p.suffix.lower() in IMAGE_EXTENSIONS
        ],
        key=lambda p: p.name.lower()
    )

    label_map = {
        p.stem: p
        for p in source_labels.glob("*.txt")
    }

    paired = []

    for image in images:

        label = label_map.get(image.stem)

        if label is not None:
            paired.append(
                (image, label)
            )

    print()
    print(f"Total images found : {len(images)}")
    print(f"Paired images      : {len(paired)}")

    if len(paired) != 441:

        raise RuntimeError(
            f"Expected 441 paired images, found {len(paired)}"
        )

    # --------------------------------------------------------
    # Deterministic shuffle
    # --------------------------------------------------------

    random.seed(SEED)

    random.shuffle(paired)

    total = len(paired)

    train_count = int(
        total * TRAIN_RATIO
    )

    val_count = int(
        total * VAL_RATIO
    )

    test_count = (
        total
        - train_count
        - val_count
    )

    splits = {
        "train": paired[
            :train_count
        ],
        "val": paired[
            train_count:
            train_count + val_count
        ],
        "test": paired[
            train_count + val_count:
        ]
    }

    # --------------------------------------------------------
    # Create output directories
    # --------------------------------------------------------

    for split in [
        "train",
        "val",
        "test"
    ]:

        (
            OUTPUT
            / split
            / "images"
        ).mkdir(
            parents=True,
            exist_ok=True
        )

        (
            OUTPUT
            / split
            / "labels"
        ).mkdir(
            parents=True,
            exist_ok=True
        )

    # --------------------------------------------------------
    # Copy files
    # --------------------------------------------------------

    for split, items in splits.items():

        print()
        print(
            f"Processing: {split}"
        )

        for image, label in items:

            shutil.copy2(
                image,
                OUTPUT
                / split
                / "images"
                / image.name
            )

            shutil.copy2(
                label,
                OUTPUT
                / split
                / "labels"
                / label.name
            )

        print(
            f"Images copied : {len(items)}"
        )

        print(
            f"Labels copied : {len(items)}"
        )

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("SPLIT COMPLETE")
    print("=" * 70)

    print(
        f"Train : {len(splits['train'])}"
    )

    print(
        f"Val   : {len(splits['val'])}"
    )

    print(
        f"Test  : {len(splits['test'])}"
    )

    print(
        f"Total : {sum(len(v) for v in splits.values())}"
    )

    print()
    print("Output:")
    print(OUTPUT)


if __name__ == "__main__":
    main()