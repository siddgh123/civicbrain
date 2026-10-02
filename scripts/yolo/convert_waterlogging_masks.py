from pathlib import Path
from PIL import Image

# --------------------------------------------------
# PATHS
# --------------------------------------------------

SOURCE_IMAGES = Path(
    r"data/yolo/raw/waterlogging_source/Dataset/images"
)

SOURCE_MASKS = Path(
    r"data/yolo/raw/waterlogging_source/Dataset/labels"
)

OUTPUT_IMAGES = Path(
    r"data/yolo/raw/waterlogging_converted/images"
)

OUTPUT_LABELS = Path(
    r"data/yolo/raw/waterlogging_converted/labels"
)

CLASS_ID = 2


# --------------------------------------------------
# CREATE OUTPUT FOLDERS
# --------------------------------------------------

OUTPUT_IMAGES.mkdir(parents=True, exist_ok=True)
OUTPUT_LABELS.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# CONVERSION
# --------------------------------------------------

converted = 0
skipped = 0

for image_path in sorted(SOURCE_IMAGES.glob("*")):

    if image_path.suffix.lower() not in [".jpg", ".jpeg", ".png"]:
        continue

    # image_1.jpg -> label_1.png
    mask_number = image_path.stem.split("_")[-1]
    mask_name = f"label_{mask_number}.png"
    mask_path = SOURCE_MASKS / mask_name

    if not mask_path.exists():
        print(f"Missing mask: {mask_name}")
        skipped += 1
        continue

    # Read image size
    with Image.open(image_path) as img:
        width, height = img.size

    # Read binary mask
    with Image.open(mask_path).convert("L") as mask:

        pixels = mask.load()

        min_x = width
        min_y = height
        max_x = -1
        max_y = -1

        for y in range(height):
            for x in range(width):

                if pixels[x, y] > 0:

                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)

    # Empty mask
    if max_x == -1:
        print(f"Empty mask: {mask_name}")
        skipped += 1
        continue

    # Bounding box
    box_width = max_x - min_x + 1
    box_height = max_y - min_y + 1

    center_x = min_x + box_width / 2
    center_y = min_y + box_height / 2

    # Normalize for YOLO
    x_center = center_x / width
    y_center = center_y / height
    norm_width = box_width / width
    norm_height = box_height / height

    # Copy image
    output_image = OUTPUT_IMAGES / image_path.name

    with Image.open(image_path) as img:
        img.save(output_image)

    # Create YOLO label
    output_label = OUTPUT_LABELS / f"{image_path.stem}.txt"

    output_label.write_text(
        f"{CLASS_ID} "
        f"{x_center:.6f} "
        f"{y_center:.6f} "
        f"{norm_width:.6f} "
        f"{norm_height:.6f}\n",
        encoding="utf-8"
    )

    converted += 1


# --------------------------------------------------
# RESULT
# --------------------------------------------------

print("=" * 60)
print("WATERLOGGING MASK → YOLO CONVERSION")
print("=" * 60)

print(f"Images converted : {converted}")
print(f"Images skipped   : {skipped}")

print()
print("Class ID: 2 = Waterlogging")

print()
print("Output:")
print(OUTPUT_IMAGES)
print(OUTPUT_LABELS)

print("=" * 60)