from pathlib import Path
import shutil

# ============================================================
# CivicBrain - RDD2022 to CivicBrain YOLO Converter
# ============================================================
#
# Original RDD2022 dataset is READ ONLY.
# No files inside data/yolo/raw/ are modified or deleted.
#
# RDD2022 classes:
# 0  D00
# 1  D01
# 2  D0w0
# 3  D10
# 4  D11
# 5  D20
# 6  D40
# 7  D43
# 8  D44
# 9  D50
#
# CivicBrain classes:
# 0 = Pothole
# 1 = Garbage Accumulation
# 2 = Waterlogging
# 3 = Road Damage
#
# Mapping:
# D40                    -> CivicBrain 0 (Pothole)
# D00,D01,D10,D11,D20   -> CivicBrain 3 (Road Damage)
#
# Excluded:
# D0w0,D43,D44,D50
# ============================================================


# ------------------------------------------------------------
# PROJECT PATHS
# ------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SOURCE_IMAGE_DIR = (
    PROJECT_ROOT
    / "data"
    / "yolo"
    / "raw"
    / "train"
    / "images"
)

SOURCE_LABEL_DIR = (
    PROJECT_ROOT
    / "data"
    / "yolo"
    / "raw"
    / "train"
    / "labels"
)

DEST_IMAGE_DIR = (
    PROJECT_ROOT
    / "data"
    / "yolo"
    / "images"
    / "train"
)

DEST_LABEL_DIR = (
    PROJECT_ROOT
    / "data"
    / "yolo"
    / "labels"
    / "train"
)


# ------------------------------------------------------------
# RDD2022 -> CIVICBRAIN CLASS MAPPING
# ------------------------------------------------------------

POTHOLE_CLASS = 6

ROAD_DAMAGE_CLASSES = {
    0,  # D00
    1,  # D01
    3,  # D10
    4,  # D11
    5,  # D20
}

EXCLUDED_CLASSES = {
    2,  # D0w0
    7,  # D43
    8,  # D44
    9,  # D50
}


# ------------------------------------------------------------
# IMAGE EXTENSIONS
# ------------------------------------------------------------

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp",
}


# ------------------------------------------------------------
# CHECK SOURCE DATASET
# ------------------------------------------------------------

if not SOURCE_IMAGE_DIR.exists():
    print("ERROR: Source image folder not found:")
    print(SOURCE_IMAGE_DIR)
    raise SystemExit(1)

if not SOURCE_LABEL_DIR.exists():
    print("ERROR: Source label folder not found:")
    print(SOURCE_LABEL_DIR)
    raise SystemExit(1)


# ------------------------------------------------------------
# CREATE DESTINATION FOLDERS
# ------------------------------------------------------------

DEST_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
DEST_LABEL_DIR.mkdir(parents=True, exist_ok=True)


print("=" * 70)
print("CIVICBRAIN - RDD2022 DATASET CONVERSION")
print("=" * 70)

print("\nSource images:")
print(SOURCE_IMAGE_DIR)

print("\nSource labels:")
print(SOURCE_LABEL_DIR)

print("\nDestination images:")
print(DEST_IMAGE_DIR)

print("\nDestination labels:")
print(DEST_LABEL_DIR)


# ------------------------------------------------------------
# FIND SOURCE IMAGES
# ------------------------------------------------------------

source_images = {}

for image_file in SOURCE_IMAGE_DIR.iterdir():

    if not image_file.is_file():
        continue

    if image_file.suffix.lower() not in IMAGE_EXTENSIONS:
        continue

    source_images[image_file.stem] = image_file


print("\nTotal source images found:", len(source_images))


# ------------------------------------------------------------
# COUNTERS
# ------------------------------------------------------------

processed_images = 0
copied_images = 0
created_labels = 0

pothole_images = set()
road_damage_images = set()
both_images = set()

excluded_only_images = 0
missing_image_count = 0
empty_label_count = 0

total_pothole_boxes = 0
total_road_damage_boxes = 0
total_excluded_boxes = 0


# ------------------------------------------------------------
# PROCESS EACH LABEL FILE
# ------------------------------------------------------------

for label_file in SOURCE_LABEL_DIR.glob("*.txt"):

    image_stem = label_file.stem

    processed_images += 1

    # --------------------------------------------------------
    # Find corresponding image
    # --------------------------------------------------------

    source_image = source_images.get(image_stem)

    if source_image is None:
        missing_image_count += 1
        print(
            f"WARNING: Image not found for label: "
            f"{label_file.name}"
        )
        continue


    # --------------------------------------------------------
    # Read original label
    # --------------------------------------------------------

    converted_lines = []

    has_pothole = False
    has_road_damage = False

    with open(
        label_file,
        "r",
        encoding="utf-8"
    ) as file:

        for line_number, line in enumerate(file, start=1):

            line = line.strip()

            if not line:
                continue

            parts = line.split()

            # YOLO format should contain:
            # class_id x_center y_center width height

            if len(parts) != 5:
                print(
                    f"WARNING: Invalid label format: "
                    f"{label_file.name}, line {line_number}"
                )
                continue

            try:
                source_class_id = int(parts[0])

            except ValueError:

                print(
                    f"WARNING: Invalid class ID: "
                    f"{label_file.name}, line {line_number}"
                )

                continue


            # ------------------------------------------------
            # D40 -> CivicBrain Pothole = 0
            # ------------------------------------------------

            if source_class_id == POTHOLE_CLASS:

                converted_class_id = 0

                has_pothole = True

                total_pothole_boxes += 1

                converted_lines.append(
                    f"{converted_class_id} "
                    f"{parts[1]} "
                    f"{parts[2]} "
                    f"{parts[3]} "
                    f"{parts[4]}"
                )

                continue


            # ------------------------------------------------
            # D00/D01/D10/D11/D20
            # -> CivicBrain Road Damage = 3
            # ------------------------------------------------

            if source_class_id in ROAD_DAMAGE_CLASSES:

                converted_class_id = 3

                has_road_damage = True

                total_road_damage_boxes += 1

                converted_lines.append(
                    f"{converted_class_id} "
                    f"{parts[1]} "
                    f"{parts[2]} "
                    f"{parts[3]} "
                    f"{parts[4]}"
                )

                continue


            # ------------------------------------------------
            # Excluded classes
            # ------------------------------------------------

            if source_class_id in EXCLUDED_CLASSES:

                total_excluded_boxes += 1

                continue


            # ------------------------------------------------
            # Unknown class
            # ------------------------------------------------

            print(
                f"WARNING: Unknown class ID "
                f"{source_class_id} in {label_file.name}"
            )


    # --------------------------------------------------------
    # If no relevant annotation remains, skip image
    # --------------------------------------------------------

    if not converted_lines:

        empty_label_count += 1
        excluded_only_images += 1

        continue


    # --------------------------------------------------------
    # Record class presence
    # --------------------------------------------------------

    if has_pothole:
        pothole_images.add(image_stem)

    if has_road_damage:
        road_damage_images.add(image_stem)

    if has_pothole and has_road_damage:
        both_images.add(image_stem)


    # --------------------------------------------------------
    # Copy image
    # --------------------------------------------------------

    destination_image = DEST_IMAGE_DIR / source_image.name

    shutil.copy2(
        source_image,
        destination_image
    )

    copied_images += 1


    # --------------------------------------------------------
    # Write converted label
    # --------------------------------------------------------

    destination_label = DEST_LABEL_DIR / f"{image_stem}.txt"

    with open(
        destination_label,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "\n".join(converted_lines)
        )

        file.write("\n")

    created_labels += 1


# ------------------------------------------------------------
# FINAL COUNTS
# ------------------------------------------------------------

combined_images = (
    pothole_images
    | road_damage_images
)


# ------------------------------------------------------------
# VERIFY IMAGE/LABEL PAIRING
# ------------------------------------------------------------

destination_images = {
    file.stem
    for file in DEST_IMAGE_DIR.iterdir()
    if file.is_file()
    and file.suffix.lower() in IMAGE_EXTENSIONS
}

destination_labels = {
    file.stem
    for file in DEST_LABEL_DIR.glob("*.txt")
}


missing_labels = destination_images - destination_labels
missing_images = destination_labels - destination_images


# ------------------------------------------------------------
# FINAL REPORT
# ------------------------------------------------------------

print("\n")
print("=" * 70)
print("CONVERSION COMPLETE")
print("=" * 70)

print("\nSource label files processed:")
print(processed_images)

print("\nImages copied:")
print(copied_images)

print("Labels created:")
print(created_labels)

print("\nCIVICBRAIN CLASS DISTRIBUTION")
print("-" * 70)

print(
    "Pothole images       :",
    len(pothole_images)
)

print(
    "Road Damage images   :",
    len(road_damage_images)
)

print(
    "Both classes         :",
    len(both_images)
)

print(
    "Combined unique      :",
    len(combined_images)
)

print("\nANNOTATION OBJECT COUNTS")
print("-" * 70)

print(
    "Pothole boxes        :",
    total_pothole_boxes
)

print(
    "Road Damage boxes    :",
    total_road_damage_boxes
)

print(
    "Excluded boxes       :",
    total_excluded_boxes
)

print("\nEXCLUDED-ONLY IMAGES:")
print(excluded_only_images)

print("\nMISSING SOURCE IMAGES:")
print(missing_image_count)

print("\nEMPTY CONVERTED LABELS:")
print(empty_label_count)

print("\nPAIRING VALIDATION")
print("-" * 70)

print(
    "Destination images   :",
    len(destination_images)
)

print(
    "Destination labels   :",
    len(destination_labels)
)

print(
    "Missing labels       :",
    len(missing_labels)
)

print(
    "Missing images       :",
    len(missing_images)
)


# ------------------------------------------------------------
# SAFETY CHECK
# ------------------------------------------------------------

if len(missing_labels) == 0 and len(missing_images) == 0:

    print("\n" + "=" * 70)
    print("PAIRING VALIDATION PASSED")
    print("=" * 70)

else:

    print("\n" + "=" * 70)
    print("PAIRING VALIDATION FAILED")
    print("=" * 70)


print("\nIMPORTANT:")
print("Original RDD2022 raw dataset was NOT modified.")
print("Conversion created a separate CivicBrain dataset.")
print("\nConversion finished.")