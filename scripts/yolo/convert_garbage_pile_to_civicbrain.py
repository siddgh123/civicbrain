from pathlib import Path
import shutil


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(
    r"C:\Users\Siddhesh\OneDrive\Desktop\CivicBrain"
)

SOURCE_ROOT = (
    PROJECT_ROOT
    / "data"
    / "yolo"
    / "raw"
    / "garbage_pile_source"
)

OUTPUT_ROOT = (
    PROJECT_ROOT
    / "data"
    / "yolo"
    / "raw"
    / "garbage_pile_converted"
)


# ============================================================
# CIVICBRAIN CLASS
# ============================================================

# CivicBrain final class:
# 0 = Pothole
# 1 = Garbage Accumulation
# 2 = Waterlogging
# 3 = Road Damage

CIVICBRAIN_GARBAGE_CLASS_ID = 1


# ============================================================
# IMAGE EXTENSIONS
# ============================================================

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp"
}


# ============================================================
# CONVERT SEGMENTATION POLYGON TO BOUNDING BOX
# ============================================================

def polygon_to_bbox(coordinates):

    xs = coordinates[0::2]
    ys = coordinates[1::2]

    x_min = min(xs)
    x_max = max(xs)

    y_min = min(ys)
    y_max = max(ys)

    x_center = (x_min + x_max) / 2
    y_center = (y_min + y_max) / 2

    width = x_max - x_min
    height = y_max - y_min

    return (
        x_center,
        y_center,
        width,
        height
    )


# ============================================================
# CLAMP BOUNDING BOX
# ============================================================

def clamp_bbox(
    x_center,
    y_center,
    width,
    height
):

    # Calculate corners
    x_min = x_center - width / 2
    x_max = x_center + width / 2

    y_min = y_center - height / 2
    y_max = y_center + height / 2

    # Clamp corners to image boundary
    x_min = max(0.0, min(1.0, x_min))
    x_max = max(0.0, min(1.0, x_max))

    y_min = max(0.0, min(1.0, y_min))
    y_max = max(0.0, min(1.0, y_max))

    # Recalculate bbox
    width = x_max - x_min
    height = y_max - y_min

    x_center = (x_min + x_max) / 2
    y_center = (y_min + y_max) / 2

    return (
        x_center,
        y_center,
        width,
        height
    )


# ============================================================
# CONVERT ONE LABEL FILE
# ============================================================

def convert_label(
    source_label_path,
    output_label_path
):

    converted_lines = []

    detection_lines = 0
    segmentation_lines = 0
    invalid_lines = 0

    with open(
        source_label_path,
        "r",
        encoding="utf-8"
    ) as file:

        for line_number, line in enumerate(
            file,
            start=1
        ):

            line = line.strip()

            if not line:
                continue

            parts = line.split()

            try:

                source_class = int(parts[0])

                values = [
                    float(value)
                    for value in parts[1:]
                ]

            except ValueError:

                invalid_lines += 1
                continue


            # ------------------------------------------------
            # Only source class 0 is expected
            # ------------------------------------------------

            if source_class != 0:

                invalid_lines += 1
                continue


            # =================================================
            # FORMAT 1: YOLO DETECTION
            #
            # class x_center y_center width height
            #
            # Total tokens = 5
            # =================================================

            if len(values) == 4:

                x_center = values[0]
                y_center = values[1]
                width = values[2]
                height = values[3]

                detection_lines += 1


            # =================================================
            # FORMAT 2: YOLO SEGMENTATION
            #
            # class x1 y1 x2 y2 x3 y3 ...
            #
            # Must have at least 3 points
            # =================================================

            elif (
                len(values) >= 6
                and len(values) % 2 == 0
            ):

                (
                    x_center,
                    y_center,
                    width,
                    height
                ) = polygon_to_bbox(values)

                segmentation_lines += 1


            # =================================================
            # INVALID FORMAT
            # =================================================

            else:

                invalid_lines += 1
                continue


            # =================================================
            # CLAMP BOUNDING BOX
            # =================================================

            (
                x_center,
                y_center,
                width,
                height
            ) = clamp_bbox(
                x_center,
                y_center,
                width,
                height
            )


            # =================================================
            # FINAL VALIDITY CHECK
            # =================================================

            if (
                width <= 0
                or height <= 0
            ):

                invalid_lines += 1
                continue


            if not (
                0 <= x_center <= 1
                and
                0 <= y_center <= 1
                and
                0 < width <= 1
                and
                0 < height <= 1
            ):

                invalid_lines += 1
                continue


            # =================================================
            # CIVICBRAIN LABEL
            # =================================================

            converted_lines.append(
                f"{CIVICBRAIN_GARBAGE_CLASS_ID} "
                f"{x_center:.6f} "
                f"{y_center:.6f} "
                f"{width:.6f} "
                f"{height:.6f}"
            )


    # ========================================================
    # WRITE OUTPUT
    # ========================================================

    with open(
        output_label_path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "\n".join(converted_lines)
        )


    return (
        len(converted_lines),
        detection_lines,
        segmentation_lines,
        invalid_lines
    )


# ============================================================
# PROCESS ONE SPLIT
# ============================================================

def process_split(split_name):

    source_images = (
        SOURCE_ROOT
        / split_name
        / "images"
    )

    source_labels = (
        SOURCE_ROOT
        / split_name
        / "labels"
    )

    output_images = (
        OUTPUT_ROOT
        / split_name
        / "images"
    )

    output_labels = (
        OUTPUT_ROOT
        / split_name
        / "labels"
    )


    output_images.mkdir(
        parents=True,
        exist_ok=True
    )

    output_labels.mkdir(
        parents=True,
        exist_ok=True
    )


    images = [
        path
        for path in source_images.iterdir()
        if path.suffix.lower()
        in IMAGE_EXTENSIONS
    ]


    total_images = 0
    total_objects = 0
    total_detection = 0
    total_segmentation = 0
    total_invalid = 0


    for image_path in images:

        source_label = (
            source_labels
            / f"{image_path.stem}.txt"
        )

        output_label = (
            output_labels
            / f"{image_path.stem}.txt"
        )


        # ----------------------------------------------------
        # Missing source label
        # ----------------------------------------------------

        if not source_label.exists():

            print(
                f"WARNING: Missing label: "
                f"{image_path.name}"
            )

            continue


        # ----------------------------------------------------
        # Copy image
        # ----------------------------------------------------

        shutil.copy2(
            image_path,
            output_images / image_path.name
        )


        # ----------------------------------------------------
        # Convert label
        # ----------------------------------------------------

        (
            objects,
            detection_count,
            segmentation_count,
            invalid_count
        ) = convert_label(
            source_label,
            output_label
        )


        total_images += 1
        total_objects += objects

        total_detection += detection_count
        total_segmentation += segmentation_count
        total_invalid += invalid_count


    return (
        total_images,
        total_objects,
        total_detection,
        total_segmentation,
        total_invalid
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("GarbagePile → CivicBrain Corrected Conversion")
    print("=" * 70)

    print()
    print(f"Source:")
    print(SOURCE_ROOT)

    print()
    print(f"Output:")
    print(OUTPUT_ROOT)

    print()


    if not SOURCE_ROOT.exists():

        print(
            "ERROR: Source folder does not exist."
        )

        return


    # --------------------------------------------------------
    # IMPORTANT:
    # Remove previous converted dataset
    # --------------------------------------------------------

    if OUTPUT_ROOT.exists():

        print(
            "Removing previous converted dataset..."
        )

        shutil.rmtree(OUTPUT_ROOT)


    # --------------------------------------------------------
    # Totals
    # --------------------------------------------------------

    grand_images = 0
    grand_objects = 0
    grand_detection = 0
    grand_segmentation = 0
    grand_invalid = 0


    # --------------------------------------------------------
    # Process train / valid / test
    # --------------------------------------------------------

    for split in [
        "train",
        "valid",
        "test"
    ]:

        print()
        print("-" * 70)
        print(
            f"Processing: {split}"
        )
        print("-" * 70)


        (
            images,
            objects,
            detection_count,
            segmentation_count,
            invalid_count
        ) = process_split(split)


        print(
            f"Images processed       : {images}"
        )

        print(
            f"Objects converted      : {objects}"
        )

        print(
            f"Detection annotations  : "
            f"{detection_count}"
        )

        print(
            f"Segmentation objects   : "
            f"{segmentation_count}"
        )

        print(
            f"Invalid source lines   : "
            f"{invalid_count}"
        )


        grand_images += images
        grand_objects += objects
        grand_detection += detection_count
        grand_segmentation += segmentation_count
        grand_invalid += invalid_count


    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("CONVERSION COMPLETE")
    print("=" * 70)

    print(
        f"Total images           : "
        f"{grand_images}"
    )

    print(
        f"Total objects          : "
        f"{grand_objects}"
    )

    print(
        f"Detection annotations  : "
        f"{grand_detection}"
    )

    print(
        f"Segmentation objects   : "
        f"{grand_segmentation}"
    )

    print(
        f"Invalid source lines   : "
        f"{grand_invalid}"
    )

    print()
    print(
        "CivicBrain class mapping:"
    )

    print(
        "1 = Garbage Accumulation"
    )

    print()
    print(
        "Output:"
    )

    print(OUTPUT_ROOT)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()