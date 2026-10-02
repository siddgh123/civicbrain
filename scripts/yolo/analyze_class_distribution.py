from pathlib import Path
from collections import Counter
import csv


# ============================================================
# CivicBrain - YOLO Class Distribution Analysis
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

LABEL_DIR = (
    PROJECT_ROOT
    / "data"
    / "yolo"
    / "labels"
    / "train"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "yolo"
    / "class_distribution.csv"
)


CLASS_NAMES = {
    0: "Pothole",
    1: "Garbage Accumulation",
    2: "Waterlogging",
    3: "Road Damage"
}


# ------------------------------------------------------------
# CHECK LABEL DIRECTORY
# ------------------------------------------------------------

if not LABEL_DIR.exists():

    print("ERROR: Label directory not found:")
    print(LABEL_DIR)

    raise SystemExit(1)


# ------------------------------------------------------------
# COUNTERS
# ------------------------------------------------------------

object_counts = Counter()

image_counts = Counter()

total_images = 0


# ------------------------------------------------------------
# PROCESS LABEL FILES
# ------------------------------------------------------------

label_files = list(
    LABEL_DIR.glob("*.txt")
)


for label_file in label_files:

    total_images += 1

    classes_in_image = set()

    with open(
        label_file,
        "r",
        encoding="utf-8"
    ) as file:

        for line in file:

            line = line.strip()

            if not line:
                continue

            parts = line.split()

            if len(parts) != 5:
                continue

            try:

                class_id = int(parts[0])

            except ValueError:

                continue


            object_counts[class_id] += 1

            classes_in_image.add(class_id)


    # Count image once per class
    for class_id in classes_in_image:

        image_counts[class_id] += 1


# ------------------------------------------------------------
# PRINT RESULTS
# ------------------------------------------------------------

print("=" * 70)
print("CIVICBRAIN - CLASS DISTRIBUTION ANALYSIS")
print("=" * 70)

print("\nTotal labeled images:")
print(total_images)

print("\n" + "-" * 70)
print("CLASS DISTRIBUTION")
print("-" * 70)

print(
    f"{'ID':<5}"
    f"{'Class Name':<25}"
    f"{'Images':<12}"
    f"{'Objects':<12}"
)


for class_id in range(4):

    class_name = CLASS_NAMES[class_id]

    images = image_counts.get(
        class_id,
        0
    )

    objects = object_counts.get(
        class_id,
        0
    )

    print(
        f"{class_id:<5}"
        f"{class_name:<25}"
        f"{images:<12}"
        f"{objects:<12}"
    )


# ------------------------------------------------------------
# CURRENT DATASET STATUS
# ------------------------------------------------------------

print("\n" + "-" * 70)
print("DATASET STATUS")
print("-" * 70)

print(
    "Pothole available:",
    object_counts.get(0, 0) > 0
)

print(
    "Garbage Accumulation available:",
    object_counts.get(1, 0) > 0
)

print(
    "Waterlogging available:",
    object_counts.get(2, 0) > 0
)

print(
    "Road Damage available:",
    object_counts.get(3, 0) > 0
)


# ------------------------------------------------------------
# SAVE CSV
# ------------------------------------------------------------

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)


with open(
    OUTPUT_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as csv_file:

    writer = csv.writer(csv_file)

    writer.writerow([
        "class_id",
        "class_name",
        "image_count",
        "object_count",
        "status"
    ])


    for class_id in range(4):

        class_name = CLASS_NAMES[class_id]

        images = image_counts.get(
            class_id,
            0
        )

        objects = object_counts.get(
            class_id,
            0
        )


        if objects > 0:

            status = "available"

        else:

            status = "not_yet_added"


        writer.writerow([
            class_id,
            class_name,
            images,
            objects,
            status
        ])


# ------------------------------------------------------------
# FINAL MESSAGE
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("CLASS DISTRIBUTION ANALYSIS COMPLETE")
print("=" * 70)

print("\nCSV created:")
print(OUTPUT_FILE)

print("\nOriginal images and labels were NOT modified.")