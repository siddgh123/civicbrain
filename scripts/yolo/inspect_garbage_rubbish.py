from pathlib import Path
from PIL import Image, ImageDraw
import random

SOURCE = Path(r"data/yolo/raw/garbage_source")

IMAGE_DIRS = [
    SOURCE / "train" / "images",
    SOURCE / "valid" / "images",
    SOURCE / "test" / "images",
]

LABEL_DIRS = [
    SOURCE / "train" / "labels",
    SOURCE / "valid" / "labels",
    SOURCE / "test" / "labels",
]

OUTPUT_DIR = Path(
    r"data/yolo/raw/garbage_rubbish_visual_validation"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_CLASS = 52
SAMPLE_COUNT = 20

# --------------------------------------------------
# FIND IMAGES CONTAINING CLASS 52
# --------------------------------------------------

candidates = []

for image_dir, label_dir in zip(IMAGE_DIRS, LABEL_DIRS):

    if not label_dir.exists():
        continue

    for label_path in label_dir.glob("*.txt"):

        contains_rubbish = False

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

            if class_id == TARGET_CLASS:
                contains_rubbish = True
                break

        if contains_rubbish:

            for ext in [".jpg", ".jpeg", ".png"]:

                image_path = image_dir / f"{label_path.stem}{ext}"

                if image_path.exists():
                    candidates.append(
                        (image_path, label_path)
                    )
                    break


# --------------------------------------------------
# SELECT RANDOM SAMPLE
# --------------------------------------------------

random.seed(42)

if len(candidates) > SAMPLE_COUNT:
    selected = random.sample(candidates, SAMPLE_COUNT)
else:
    selected = candidates


# --------------------------------------------------
# DRAW RUBBISH BOXES
# --------------------------------------------------

processed = 0

for image_path, label_path in selected:

    with Image.open(image_path).convert("RGB") as img:

        width, height = img.size
        draw = ImageDraw.Draw(img)

        for line in label_path.read_text(
            encoding="utf-8"
        ).splitlines():

            parts = line.split()

            if len(parts) < 5:
                continue

            class_id = int(parts[0])

            # Dataset is segmentation format.
            # Draw bounding box around all polygon points.
            if class_id != TARGET_CLASS:
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
                "rubbish (52)",
                fill="red"
            )

        output_path = OUTPUT_DIR / image_path.name
        img.save(output_path)

        processed += 1


# --------------------------------------------------
# SUMMARY
# --------------------------------------------------

print("=" * 65)
print("RUBBISH CLASS VISUAL INSPECTION")
print("=" * 65)

print(f"Class ID              : {TARGET_CLASS}")
print(f"Candidate images      : {len(candidates)}")
print(f"Images selected       : {processed}")

print()
print("Output folder:")
print(OUTPUT_DIR)

print("=" * 65)