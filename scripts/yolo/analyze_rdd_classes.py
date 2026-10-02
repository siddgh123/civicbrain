from pathlib import Path
from collections import defaultdict

# --------------------------------------------------
# CivicBrain - RDD2022 Class Image Analysis
# This script ONLY READS the dataset.
# It does NOT modify images or labels.
# --------------------------------------------------

# Project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# RDD2022 train labels
LABEL_DIR = PROJECT_ROOT / "data" / "yolo" / "raw" / "train" / "labels"

# RDD2022 class IDs from data.yaml
CLASS_NAMES = {
    0: "D00",
    1: "D01",
    2: "D0w0",
    3: "D10",
    4: "D11",
    5: "D20",
    6: "D40",
    7: "D43",
    8: "D44",
    9: "D50",
}

# Classes we want to investigate
POTHOLE_ID = 6

ROAD_DAMAGE_IDS = {
    0, 1, 3, 4, 5
}

# Store image names for each class
class_images = defaultdict(set)

# Check folder
if not LABEL_DIR.exists():
    print("ERROR: Labels folder not found:")
    print(LABEL_DIR)
    raise SystemExit(1)

label_files = list(LABEL_DIR.glob("*.txt"))

print("=" * 60)
print("CivicBrain - RDD2022 Unique Image Analysis")
print("=" * 60)

print(f"\nLabels folder:")
print(LABEL_DIR)

print(f"\nTotal label files: {len(label_files)}")

# --------------------------------------------------
# Read every label file
# --------------------------------------------------

for label_file in label_files:

    image_name = label_file.stem

    try:
        with open(label_file, "r", encoding="utf-8") as file:
            lines = file.readlines()

    except Exception as e:
        print(f"Could not read: {label_file.name}")
        print(e)
        continue

    for line in lines:

        line = line.strip()

        if not line:
            continue

        parts = line.split()

        try:
            class_id = int(parts[0])
        except (ValueError, IndexError):
            continue

        if class_id in CLASS_NAMES:
            class_images[class_id].add(image_name)

# --------------------------------------------------
# Print all class counts
# --------------------------------------------------

print("\n" + "=" * 60)
print("UNIQUE IMAGES BY ORIGINAL CLASS")
print("=" * 60)

for class_id in sorted(CLASS_NAMES):

    count = len(class_images[class_id])

    print(
        f"ID {class_id:<2} | "
        f"{CLASS_NAMES[class_id]:<5} | "
        f"{count} unique images"
    )

# --------------------------------------------------
# Pothole
# --------------------------------------------------

pothole_images = class_images[POTHOLE_ID]

# --------------------------------------------------
# Road Damage
# --------------------------------------------------

road_damage_images = set()

for class_id in ROAD_DAMAGE_IDS:
    road_damage_images.update(class_images[class_id])

# --------------------------------------------------
# Combined relevant images
# --------------------------------------------------

relevant_images = pothole_images | road_damage_images

print("\n" + "=" * 60)
print("CIVICBRAIN RELEVANT IMAGE COUNTS")
print("=" * 60)

print(f"Pothole images       : {len(pothole_images)}")
print(f"Road Damage images   : {len(road_damage_images)}")
print(f"Combined unique      : {len(relevant_images)}")

# --------------------------------------------------
# Extra information
# --------------------------------------------------

print("\n" + "=" * 60)
print("SOURCE CLASS MAPPING")
print("=" * 60)

print("Pothole:")
print("  D40")

print("\nRoad Damage:")
print("  D00")
print("  D01")
print("  D10")
print("  D11")
print("  D20")

print("\nExcluded from current mapping:")
print("  D0w0")
print("  D43")
print("  D44")
print("  D50")

print("\nAnalysis completed.")
print("No images or labels were modified.")