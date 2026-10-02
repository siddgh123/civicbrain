from pathlib import Path
import random

from PIL import Image, ImageDraw, ImageFont


# ============================================================
# CivicBrain - Random YOLO Annotation Visual Inspection
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

IMAGE_DIR = (
    PROJECT_ROOT
    / "data"
    / "yolo"
    / "images"
    / "train"
)

LABEL_DIR = (
    PROJECT_ROOT
    / "data"
    / "yolo"
    / "labels"
    / "train"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "yolo"
    / "visual_validation"
)

# Number of random images to inspect
SAMPLE_COUNT = 20

CLASS_NAMES = {
    0: "Pothole",
    3: "Road Damage"
}

# Reproducible random selection
random.seed(42)


# ------------------------------------------------------------
# CHECK DIRECTORIES
# ------------------------------------------------------------

if not IMAGE_DIR.exists():
    print("ERROR: Image directory not found:")
    print(IMAGE_DIR)
    raise SystemExit(1)

if not LABEL_DIR.exists():
    print("ERROR: Label directory not found:")
    print(LABEL_DIR)
    raise SystemExit(1)


OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ------------------------------------------------------------
# FIND IMAGES
# ------------------------------------------------------------

image_extensions = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp"
}

images = [
    file
    for file in IMAGE_DIR.iterdir()
    if file.is_file()
    and file.suffix.lower() in image_extensions
]


if len(images) == 0:
    print("ERROR: No images found.")
    raise SystemExit(1)


# ------------------------------------------------------------
# RANDOM SAMPLE
# ------------------------------------------------------------

sample_count = min(
    SAMPLE_COUNT,
    len(images)
)

selected_images = random.sample(
    images,
    sample_count
)


print("=" * 60)
print("CIVICBRAIN - VISUAL ANNOTATION VALIDATION")
print("=" * 60)

print("\nTotal images:", len(images))
print("Images selected:", sample_count)

print("\nOutput folder:")
print(OUTPUT_DIR)


# ------------------------------------------------------------
# PROCESS IMAGES
# ------------------------------------------------------------

processed = 0
missing_labels = 0
invalid_boxes = 0
total_boxes = 0


for image_path in selected_images:

    label_path = LABEL_DIR / f"{image_path.stem}.txt"

    if not label_path.exists():

        print(
            f"WARNING: Label missing for {image_path.name}"
        )

        missing_labels += 1
        continue


    # --------------------------------------------------------
    # Open image
    # --------------------------------------------------------

    try:

        image = Image.open(image_path).convert("RGB")

    except Exception as error:

        print(
            f"WARNING: Could not open {image_path.name}"
        )

        print(error)

        continue


    image_width, image_height = image.size


    # --------------------------------------------------------
    # Drawing
    # --------------------------------------------------------

    draw = ImageDraw.Draw(image)


    # --------------------------------------------------------
    # Read YOLO labels
    # --------------------------------------------------------

    with open(
        label_path,
        "r",
        encoding="utf-8"
    ) as file:

        lines = file.readlines()


    for line_number, line in enumerate(
        lines,
        start=1
    ):

        line = line.strip()

        if not line:
            continue


        parts = line.split()

        if len(parts) != 5:

            print(
                f"WARNING: Invalid label format: "
                f"{label_path.name}, line {line_number}"
            )

            invalid_boxes += 1
            continue


        try:

            class_id = int(parts[0])

            x_center = float(parts[1])
            y_center = float(parts[2])
            width = float(parts[3])
            height = float(parts[4])

        except ValueError:

            invalid_boxes += 1
            continue


        # ----------------------------------------------------
        # Validate normalized coordinates
        # ----------------------------------------------------

        if not (
            0 <= x_center <= 1
            and 0 <= y_center <= 1
            and 0 < width <= 1
            and 0 < height <= 1
        ):

            invalid_boxes += 1

            continue


        # ----------------------------------------------------
        # Convert YOLO normalized coordinates
        # to pixel coordinates
        # ----------------------------------------------------

        x_center_pixel = x_center * image_width
        y_center_pixel = y_center * image_height

        box_width_pixel = width * image_width
        box_height_pixel = height * image_height


        x1 = int(
            x_center_pixel - box_width_pixel / 2
        )

        y1 = int(
            y_center_pixel - box_height_pixel / 2
        )

        x2 = int(
            x_center_pixel + box_width_pixel / 2
        )

        y2 = int(
            y_center_pixel + box_height_pixel / 2
        )


        # ----------------------------------------------------
        # Keep box inside image
        # ----------------------------------------------------

        x1 = max(0, min(x1, image_width - 1))
        y1 = max(0, min(y1, image_height - 1))

        x2 = max(0, min(x2, image_width - 1))
        y2 = max(0, min(y2, image_height - 1))


        # ----------------------------------------------------
        # Class name
        # ----------------------------------------------------

        class_name = CLASS_NAMES.get(
            class_id,
            f"Unknown-{class_id}"
        )


        # ----------------------------------------------------
        # Draw bounding box
        # ----------------------------------------------------

        draw.rectangle(
            [x1, y1, x2, y2],
            outline="red",
            width=4
        )


        # ----------------------------------------------------
        # Draw label background
        # ----------------------------------------------------

        label_text = (
            f"{class_id}: {class_name}"
        )

        try:

            text_bbox = draw.textbbox(
                (0, 0),
                label_text
            )

            text_width = (
                text_bbox[2] - text_bbox[0]
            )

            text_height = (
                text_bbox[3] - text_bbox[1]
            )

        except AttributeError:

            text_width = len(label_text) * 7
            text_height = 15


        label_y = max(
            0,
            y1 - text_height - 4
        )


        draw.rectangle(
            [
                x1,
                label_y,
                x1 + text_width + 8,
                label_y + text_height + 4
            ],
            fill="red"
        )


        draw.text(
            (
                x1 + 4,
                label_y + 2
            ),
            label_text,
            fill="white"
        )


        total_boxes += 1


    # --------------------------------------------------------
    # Save visualized image
    # --------------------------------------------------------

    output_path = (
        OUTPUT_DIR
        / image_path.name
    )

    image.save(
        output_path
    )

    processed += 1

    print(
        f"[{processed}/{sample_count}] "
        f"Created: {output_path.name}"
    )


# ------------------------------------------------------------
# FINAL REPORT
# ------------------------------------------------------------

print("\n" + "=" * 60)
print("VISUAL VALIDATION COMPLETE")
print("=" * 60)

print(
    "Images visualized:",
    processed
)

print(
    "Bounding boxes drawn:",
    total_boxes
)

print(
    "Missing labels:",
    missing_labels
)

print(
    "Invalid boxes:",
    invalid_boxes
)

print("\nOutput folder:")
print(OUTPUT_DIR)

print("\nOriginal images and labels were NOT modified.")