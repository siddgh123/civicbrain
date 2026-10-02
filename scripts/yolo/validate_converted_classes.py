from pathlib import Path
from collections import Counter

# ============================================================
# CivicBrain - Converted YOLO Class Validation
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

LABEL_DIR = (
    PROJECT_ROOT
    / "data"
    / "yolo"
    / "labels"
    / "train"
)

ALLOWED_CLASSES = {
    0: "Pothole",
    3: "Road Damage"
}

label_files = list(LABEL_DIR.glob("*.txt"))

print("=" * 60)
print("CIVICBRAIN - CONVERTED CLASS VALIDATION")
print("=" * 60)

print("\nLabel directory:")
print(LABEL_DIR)

print("\nTotal label files:", len(label_files))

class_counter = Counter()
invalid_classes = set()
invalid_lines = []

# ------------------------------------------------------------
# Read every converted label
# ------------------------------------------------------------

for label_file in label_files:

    with open(label_file, "r", encoding="utf-8") as file:

        for line_number, line in enumerate(file, start=1):

            line = line.strip()

            if not line:
                continue

            parts = line.split()

            if len(parts) != 5:

                invalid_lines.append(
                    f"{label_file.name}: line {line_number}"
                )

                continue

            try:
                class_id = int(parts[0])

            except ValueError:

                invalid_lines.append(
                    f"{label_file.name}: line {line_number}"
                )

                continue

            class_counter[class_id] += 1

            if class_id not in ALLOWED_CLASSES:
                invalid_classes.add(class_id)

# ------------------------------------------------------------
# Results
# ------------------------------------------------------------

print("\n" + "=" * 60)
print("CLASS DISTRIBUTION")
print("=" * 60)

for class_id in sorted(class_counter):

    class_name = ALLOWED_CLASSES.get(
        class_id,
        "INVALID CLASS"
    )

    print(
        f"Class {class_id} | "
        f"{class_name:<15} | "
        f"{class_counter[class_id]} objects"
    )

# ------------------------------------------------------------
# Validation
# ------------------------------------------------------------

print("\n" + "=" * 60)
print("VALIDATION")
print("=" * 60)

if invalid_classes:
    print("FAILED")
    print(
        "Invalid class IDs found:",
        sorted(invalid_classes)
    )

else:
    print("Class ID validation: PASSED")
    print("Only classes 0 and 3 are present.")

if invalid_lines:

    print("\nInvalid label lines:", len(invalid_lines))

    for item in invalid_lines[:20]:
        print(item)

else:

    print("YOLO label format validation: PASSED")

# ------------------------------------------------------------
# Final status
# ------------------------------------------------------------

if not invalid_classes and not invalid_lines:

    print("\n" + "=" * 60)
    print("9.5.7 VALIDATION PASSED")
    print("=" * 60)

else:

    print("\n" + "=" * 60)
    print("9.5.7 VALIDATION FAILED")
    print("=" * 60)