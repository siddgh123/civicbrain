from pathlib import Path
from PIL import Image, ImageDraw
import yaml

SOURCE = Path(r"data/yolo/raw/garbage_source")
OUTPUT_DIR = Path(
    r"data/yolo/raw/garbage_candidate_visual_validation"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_CLASSES = {
    17: "Food waste",
    18: "Garbage bag",
    51: "Unlabeled litter",
}

IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png"]

# --------------------------------------------------
# FIND CANDIDATE IMAGES
# --------------------------------------------------

candidates = []

for split in ["train", "valid", "test"]:

    image_dir = SOURCE / split / "images"
    label_dir = SOURCE / split / "labels"

    if not label_dir.exists():
        continue

    for label_path in label_dir.glob("*.txt"):

        found_classes = set()

        for line in label_path.read_text(
            encoding="utf-8"
        ).splitlines():

            parts = line.split()

            if not parts:
                continue

            try:
                class_id = int(parts[0])
            except ValueError:
                continue

            if class_id in TARGET_CLASSES:
                found_classes.add(class_id)

        if not found_classes:
            continue

        image_path = None

        for ext in IMAGE_EXTENSIONS:
            candidate = image_dir / f"{label_path.stem}{ext}"

            if candidate.exists():
                image_path = candidate
                break

        if image_path:
            candidates.append(
                (image_path, label_path, found_classes)
            )


# --------------------------------------------------
# DRAW ALL CANDIDATES
# --------------------------------------------------

processed = 0

for image_path, label_path, found_classes in candidates:

    with Image.open(image_path).convert("RGB") as img:

        width, height = img.size
        draw = ImageDraw.Draw(img)

        for line in label_path.read_text(
            encoding="utf-8"
        ).splitlines():

            parts = line.split()

            if len(parts) < 7:
                continue

            class_id = int(parts[0])

            if class_id not in TARGET_CLASSES:
                continue

            coords = list(map(float, parts[1:]))

            xs = coords[0::2]
            ys = coords[1::2]

            if not xs or not ys:
                continue

            min_x = int(min(xs) * width)
            max_x = int(max(xs) * width)
            min_y = int(min(ys) * height)
            max_y = int(max(ys) * height)

            draw.rectangle(
                [min_x, min_y, max_x, max_y],
                outline="red",
                width=4
            )

            draw.text(
                (min_x + 5, max(0, min_y - 20)),
                f"{TARGET_CLASSES[class_id]} ({class_id})",
                fill="red"
            )

        # Add candidate class information
        class_text = ", ".join(
            TARGET_CLASSES[c]
            for c in sorted(found_classes)
        )

        draw.text(
            (10, 10),
            f"Candidate: {class_text}",
            fill="red"
        )

        output_path = OUTPUT_DIR / image_path.name
        img.save(output_path)

        processed += 1


# --------------------------------------------------
# SUMMARY
# --------------------------------------------------

print("=" * 65)
print("GARBAGE CANDIDATE VISUAL INSPECTION")
print("=" * 65)

print(f"Candidate images found : {len(candidates)}")
print(f"Images processed       : {processed}")

print()
print("Classes reviewed:")
print("17 = Food waste")
print("18 = Garbage bag")
print("51 = Unlabeled litter")

print()
print("Output folder:")
print(OUTPUT_DIR)

print("=" * 65)