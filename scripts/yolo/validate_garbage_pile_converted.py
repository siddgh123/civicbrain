from pathlib import Path
import csv


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(
    r"C:\Users\Siddhesh\OneDrive\Desktop\CivicBrain"
)

DATASET_ROOT = (
    PROJECT_ROOT
    / "data"
    / "yolo"
    / "raw"
    / "garbage_pile_converted"
)

REPORT_PATH = (
    PROJECT_ROOT
    / "data"
    / "yolo"
    / "garbage_pile_validation_report.csv"
)

STATS_PATH = (
    PROJECT_ROOT
    / "data"
    / "yolo"
    / "garbage_pile_statistics.csv"
)


# ============================================================
# SETTINGS
# ============================================================

EXPECTED_CLASS_ID = 1

# Small tolerance for floating-point rounding
EPSILON = 0.000001

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp"
}


# ============================================================
# VALIDATE ONE LABEL
# ============================================================

def validate_label(label_path):

    errors = []
    valid_objects = 0

    content = label_path.read_text(
        encoding="utf-8"
    )

    lines = [
        line.strip()
        for line in content.splitlines()
        if line.strip()
    ]

    if len(lines) == 0:
        errors.append("EMPTY_LABEL")
        return valid_objects, errors

    for line_number, line in enumerate(
        lines,
        start=1
    ):

        parts = line.split()

        # YOLO detection:
        # class x_center y_center width height
        if len(parts) != 5:
            errors.append(
                f"INVALID_TOKEN_COUNT_LINE_{line_number}"
            )
            continue

        try:
            class_id = int(parts[0])

            x_center = float(parts[1])
            y_center = float(parts[2])
            width = float(parts[3])
            height = float(parts[4])

        except ValueError:

            errors.append(
                f"NON_NUMERIC_VALUE_LINE_{line_number}"
            )
            continue

        # ----------------------------------------------------
        # Class ID
        # ----------------------------------------------------

        if class_id != EXPECTED_CLASS_ID:

            errors.append(
                f"WRONG_CLASS_ID_LINE_{line_number}"
            )

            continue

        # ----------------------------------------------------
        # Basic YOLO value checks
        # ----------------------------------------------------

        if not (
            -EPSILON <= x_center <= 1 + EPSILON
        ):

            errors.append(
                f"X_CENTER_OUT_OF_RANGE_LINE_{line_number}"
            )

            continue

        if not (
            -EPSILON <= y_center <= 1 + EPSILON
        ):

            errors.append(
                f"Y_CENTER_OUT_OF_RANGE_LINE_{line_number}"
            )

            continue

        if not (
            0 < width <= 1 + EPSILON
        ):

            errors.append(
                f"WIDTH_INVALID_LINE_{line_number}"
            )

            continue

        if not (
            0 < height <= 1 + EPSILON
        ):

            errors.append(
                f"HEIGHT_INVALID_LINE_{line_number}"
            )

            continue

        # ----------------------------------------------------
        # Bounding box corners
        # ----------------------------------------------------

        x_min = x_center - width / 2
        x_max = x_center + width / 2

        y_min = y_center - height / 2
        y_max = y_center + height / 2

        # Allow tiny floating-point rounding error
        if x_min < -EPSILON:

            errors.append(
                f"BBOX_OUTSIDE_LEFT_LINE_{line_number}"
            )

            continue

        if x_max > 1 + EPSILON:

            errors.append(
                f"BBOX_OUTSIDE_RIGHT_LINE_{line_number}"
            )

            continue

        if y_min < -EPSILON:

            errors.append(
                f"BBOX_OUTSIDE_TOP_LINE_{line_number}"
            )

            continue

        if y_max > 1 + EPSILON:

            errors.append(
                f"BBOX_OUTSIDE_BOTTOM_LINE_{line_number}"
            )

            continue

        # ----------------------------------------------------
        # Valid object
        # ----------------------------------------------------

        valid_objects += 1

    return valid_objects, errors


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("GarbagePile Converted Dataset Validation + Statistics")
    print("=" * 70)

    print()
    print(f"Dataset: {DATASET_ROOT}")
    print()

    if not DATASET_ROOT.exists():

        print(
            "ERROR: Dataset folder does not exist."
        )

        return

    report_rows = []
    statistics_rows = []

    total_images = 0
    total_labels = 0
    total_objects = 0

    total_valid_objects = 0
    total_invalid_objects = 0

    total_missing_labels = 0
    total_extra_labels = 0
    total_empty_labels = 0

    for split in [
        "train",
        "valid",
        "test"
    ]:

        image_dir = DATASET_ROOT / split / "images"
        label_dir = DATASET_ROOT / split / "labels"

        images = {
            p.stem: p
            for p in image_dir.iterdir()
            if p.suffix.lower()
            in IMAGE_EXTENSIONS
        }

        labels = {
            p.stem: p
            for p in label_dir.glob("*.txt")
        }

        image_stems = set(images.keys())
        label_stems = set(labels.keys())

        missing_labels = image_stems - label_stems
        extra_labels = label_stems - image_stems

        split_images = len(images)
        split_labels = len(labels)

        split_objects = 0
        split_valid_objects = 0
        split_invalid_objects = 0
        split_empty_labels = 0

        # ----------------------------------------------------
        # Validate labels
        # ----------------------------------------------------

        for stem, label_path in labels.items():

            valid_objects, errors = validate_label(
                label_path
            )

            content = label_path.read_text(
                encoding="utf-8"
            )

            lines = [
                line.strip()
                for line in content.splitlines()
                if line.strip()
            ]

            object_count = len(lines)

            split_objects += object_count
            split_valid_objects += valid_objects

            split_invalid_objects += (
                object_count - valid_objects
            )

            if "EMPTY_LABEL" in errors:

                split_empty_labels += 1

            if errors:

                report_rows.append({
                    "split": split,
                    "label_file": label_path.name,
                    "errors": ";".join(errors)
                })

        # ----------------------------------------------------
        # Missing / extra
        # ----------------------------------------------------

        if missing_labels:

            total_missing_labels += len(
                missing_labels
            )

        if extra_labels:

            total_extra_labels += len(
                extra_labels
            )

        total_empty_labels += (
            split_empty_labels
        )

        # ----------------------------------------------------
        # Totals
        # ----------------------------------------------------

        total_images += split_images
        total_labels += split_labels
        total_objects += split_objects
        total_valid_objects += split_valid_objects
        total_invalid_objects += (
            split_invalid_objects
        )

        # ----------------------------------------------------
        # Statistics row
        # ----------------------------------------------------

        statistics_rows.append({
            "split": split,
            "images": split_images,
            "labels": split_labels,
            "objects": split_objects,
            "valid_objects": split_valid_objects,
            "invalid_objects": split_invalid_objects,
            "missing_labels": len(missing_labels),
            "extra_labels": len(extra_labels),
            "empty_labels": split_empty_labels
        })

        # ----------------------------------------------------
        # Print split result
        # ----------------------------------------------------

        print(
            f"--- {split.upper()} ---"
        )

        print(
            f"Images          : {split_images}"
        )

        print(
            f"Labels          : {split_labels}"
        )

        print(
            f"Objects         : {split_objects}"
        )

        print(
            f"Valid objects   : {split_valid_objects}"
        )

        print(
            f"Invalid objects : {split_invalid_objects}"
        )

        print(
            f"Missing labels  : {len(missing_labels)}"
        )

        print(
            f"Extra labels    : {len(extra_labels)}"
        )

        print(
            f"Empty labels    : {split_empty_labels}"
        )

        print()

    # ========================================================
    # FINAL RESULT
    # ========================================================

    print("=" * 70)
    print("TOTAL DATASET")
    print("=" * 70)

    print(
        f"Total images          : {total_images}"
    )

    print(
        f"Total label files     : {total_labels}"
    )

    print(
        f"Total objects         : {total_objects}"
    )

    print(
        f"Valid objects         : {total_valid_objects}"
    )

    print(
        f"Invalid objects       : {total_invalid_objects}"
    )

    print(
        f"Missing labels        : {total_missing_labels}"
    )

    print(
        f"Extra labels          : {total_extra_labels}"
    )

    print(
        f"Empty labels          : {total_empty_labels}"
    )

    # ========================================================
    # PASS / FAIL
    # ========================================================

    validation_passed = (
        total_missing_labels == 0
        and total_extra_labels == 0
        and total_invalid_objects == 0
        and total_empty_labels == 0
    )

    print()

    if validation_passed:

        print("VALIDATION PASSED")
        print(
            "All image-label pairs are valid."
        )
        print(
            "All objects use class ID 1."
        )
        print(
            "All YOLO bounding boxes are valid."
        )

    else:

        print("VALIDATION FAILED")
        print(
            "See validation report for details."
        )

    # ========================================================
    # SAVE VALIDATION REPORT
    # ========================================================

    REPORT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        REPORT_PATH,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "split",
                "label_file",
                "errors"
            ]
        )

        writer.writeheader()
        writer.writerows(report_rows)

    # ========================================================
    # SAVE STATISTICS
    # ========================================================

    with open(
        STATS_PATH,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "split",
                "images",
                "labels",
                "objects",
                "valid_objects",
                "invalid_objects",
                "missing_labels",
                "extra_labels",
                "empty_labels"
            ]
        )

        writer.writeheader()
        writer.writerows(statistics_rows)

    print()
    print("Reports created:")
    print(REPORT_PATH)
    print(STATS_PATH)


if __name__ == "__main__":
    main()