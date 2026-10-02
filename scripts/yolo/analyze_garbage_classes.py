from pathlib import Path
from collections import Counter
import yaml

SOURCE = Path(r"data/yolo/raw/garbage_source")
DATA_YAML = SOURCE / "data.yaml"

data = yaml.safe_load(
    DATA_YAML.read_text(encoding="utf-8")
)

names = data["names"]

image_counts = Counter()
object_counts = Counter()

splits = ["train", "valid", "test"]

for split in splits:

    label_dir = SOURCE / split / "labels"

    if not label_dir.exists():
        continue

    for label_file in label_dir.glob("*.txt"):

        classes_in_image = set()

        for line in label_file.read_text(
            encoding="utf-8"
        ).splitlines():

            parts = line.split()

            # YOLO segmentation:
            # class x1 y1 x2 y2 x3 y3 ...
            if len(parts) < 7:
                continue

            try:
                class_id = int(parts[0])
            except ValueError:
                continue

            if 0 <= class_id < len(names):

                object_counts[class_id] += 1
                classes_in_image.add(class_id)

        for class_id in classes_in_image:
            image_counts[class_id] += 1


print("=" * 75)
print("CIVICBRAIN - GARBAGE DATASET CLASS ANALYSIS")
print("=" * 75)

print(f"Total classes: {len(names)}")
print()

print("-" * 75)
print(
    f"{'ID':<5}"
    f"{'Class Name':<35}"
    f"{'Images':>10}"
    f"{'Objects':>12}"
)
print("-" * 75)

for class_id, class_name in enumerate(names):

    print(
        f"{class_id:<5}"
        f"{class_name:<35}"
        f"{image_counts[class_id]:>10}"
        f"{object_counts[class_id]:>12}"
    )


print()
print("=" * 75)
print("POTENTIAL GARBAGE ACCUMULATION CLASSES")
print("=" * 75)

candidate_keywords = [
    "garbage",
    "rubbish",
    "litter",
    "food waste",
]

candidates = []

for class_id, class_name in enumerate(names):

    name_lower = class_name.lower()

    if any(
        keyword in name_lower
        for keyword in candidate_keywords
    ):

        candidates.append(
            (
                class_id,
                class_name,
                image_counts[class_id],
                object_counts[class_id]
            )
        )

if candidates:

    for class_id, class_name, img_count, obj_count in candidates:

        print(
            f"ID {class_id:<2} | "
            f"{class_name:<25} | "
            f"Images: {img_count:<5} | "
            f"Objects: {obj_count}"
        )

else:

    print("No direct garbage/rubbish/litter classes found.")

print()
print("-" * 75)
print("NOTE")
print("-" * 75)
print(
    "These are candidate classes only. "
    "They are NOT automatically mapped to "
    "Garbage Accumulation."
)

print("=" * 75)