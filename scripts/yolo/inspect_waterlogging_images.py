from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import random

# --------------------------------------------------
# PATHS
# --------------------------------------------------

IMAGE_DIR = Path(
    r"data/yolo/raw/waterlogging_converted/images"
)

LABEL_DIR = Path(
    r"data/yolo/raw/waterlogging_converted/labels"
)

OUTPUT_DIR = Path(
    r"data/yolo/raw/waterlogging_visual_validation"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CLASS_NAME = "Waterlogging"
CLASS_ID = 2

SAMPLE_COUNT = 20


# --------------------------------------------------
# GET IMAGES
# --------------------------------------------------

images = sorted([
    p for p in IMAGE_DIR.iterdir()
    if p.suffix.lower() in [".jpg", ".jpeg", ".png"]
])

random.seed(42)

if len(images) > SAMPLE_COUNT:
    selected_images = random.sample(images, SAMPLE_COUNT)
else:
    selected_images = images


# --------------------------------------------------
# PROCESS
# --------------------------------------------------

processed = 0
missing_labels = 0

for image_path in selected_images:

    label_path = LABEL_DIR / f"{image_path.stem}.txt"

    if not label_path.exists():
        print(f"Missing label: {image_path.name}")
        missing_labels += 1
        continue

    with Image.open(image_path).convert("RGB") as img:

        width, height = img.size
        draw = ImageDraw.Draw(img)

        lines = label_path.read_text(
            encoding="utf-8"
        ).splitlines()

        for line in lines:

            parts = line.split()

            if len(parts) != 5:
                continue

            class_id = int(parts[0])

            x_center = float(parts[1])
            y_center = float(parts[2])
            box_width = float(parts[3])
            box_height = float(parts[4])

            # YOLO normalized -> pixel coordinates

            x1 = int(
                (x_center - box_width / 2) * width
            )

            y1 = int(
                (y_center - box_height / 2) * height
            )

            x2 = int(
                (x_center + box_width / 2) * width
            )

            y2 = int(
                (y_center + box_height / 2) * height
            )

            # Keep coordinates inside image

            x1 = max(0, min(x1, width - 1))
            y1 = max(0, min(y1, height - 1))
            x2 = max(0, min(x2, width - 1))
            y2 = max(0, min(y2, height - 1))

            # Draw bounding box

            draw.rectangle(
                [x1, y1, x2, y2],
                outline="red",
                width=4
            )

            label_text = f"{CLASS_NAME} ({class_id})"

            draw.text(
                (x1 + 5, max(0, y1 - 20)),
                label_text,
                fill="red"
            )

        output_path = OUTPUT_DIR / image_path.name
        img.save(output_path)

        processed += 1


# --------------------------------------------------
# RESULT
# --------------------------------------------------

print("=" * 60)
print("WATERLOGGING VISUAL VALIDATION")
print("=" * 60)

print(f"Total converted images : {len(images)}")
print(f"Images inspected       : {processed}")
print(f"Missing labels         : {missing_labels}")

print()
print("Validation images saved to:")
print(OUTPUT_DIR)

print("=" * 60)