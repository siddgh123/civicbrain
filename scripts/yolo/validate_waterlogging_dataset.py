from pathlib import Path

IMAGE_DIR = Path(r"data/yolo/raw/waterlogging_converted/images")
LABEL_DIR = Path(r"data/yolo/raw/waterlogging_converted/labels")

EXPECTED_COUNT = 441
EXPECTED_CLASS_ID = 2

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def main():

    images = sorted(
        p for p in IMAGE_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )

    labels = sorted(
        p for p in LABEL_DIR.iterdir()
        if p.is_file() and p.suffix.lower() == ".txt"
    )

    image_stems = {p.stem for p in images}
    label_stems = {p.stem for p in labels}

    missing_labels = sorted(image_stems - label_stems)
    extra_labels = sorted(label_stems - image_stems)

    invalid_labels = []
    wrong_class = []
    empty_labels = []

    # Validate every matching label
    for image_stem in sorted(image_stems & label_stems):

        label_path = LABEL_DIR / f"{image_stem}.txt"

        try:
            lines = [
                line.strip()
                for line in label_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except Exception as e:
            invalid_labels.append(
                f"{label_path.name} -> cannot read: {e}"
            )
            continue

        if not lines:
            empty_labels.append(label_path.name)
            continue

        for line_no, line in enumerate(lines, start=1):

            parts = line.split()

            # YOLO detection format:
            # class x_center y_center width height
            if len(parts) != 5:
                invalid_labels.append(
                    f"{label_path.name}: line {line_no} -> expected 5 values"
                )
                continue

            try:
                class_id = int(parts[0])
                x_center = float(parts[1])
                y_center = float(parts[2])
                width = float(parts[3])
                height = float(parts[4])
            except ValueError:
                invalid_labels.append(
                    f"{label_path.name}: line {line_no} -> non-numeric value"
                )
                continue

            # Class ID must be exactly 2
            if class_id != EXPECTED_CLASS_ID:
                wrong_class.append(
                    f"{label_path.name}: line {line_no} -> class {class_id}"
                )

            # YOLO normalized values must be 0..1
            values = [
                ("x_center", x_center),
                ("y_center", y_center),
                ("width", width),
                ("height", height),
            ]

            for name, value in values:
                if not 0.0 <= value <= 1.0:
                    invalid_labels.append(
                        f"{label_path.name}: line {line_no} -> "
                        f"{name}={value} outside 0..1"
                    )

    # --------------------------------------------------
    # SUMMARY
    # --------------------------------------------------

    passed = (
        len(images) == EXPECTED_COUNT
        and len(labels) == EXPECTED_COUNT
        and not missing_labels
        and not extra_labels
        and not invalid_labels
        and not wrong_class
        and not empty_labels
    )

    print("=" * 60)
    print("WATERLOGGING DATASET BATCH VALIDATION")
    print("=" * 60)

    print(f"Images found        : {len(images)}")
    print(f"Labels found        : {len(labels)}")
    print(f"Expected images     : {EXPECTED_COUNT}")
    print(f"Expected class ID   : {EXPECTED_CLASS_ID}")
    print()

    print(f"Missing labels      : {len(missing_labels)}")
    print(f"Extra labels        : {len(extra_labels)}")
    print(f"Invalid YOLO labels : {len(invalid_labels)}")
    print(f"Wrong class IDs     : {len(wrong_class)}")
    print(f"Empty labels        : {len(empty_labels)}")

    print()
    print("-" * 60)

    if passed:
        print("VALIDATION PASSED")
        print("441 images have matching labels.")
        print("All labels use valid YOLO values.")
        print("All class IDs are 2 (Waterlogging).")
    else:
        print("VALIDATION FAILED")

        if missing_labels:
            print("\nMissing labels:")
            for name in missing_labels:
                print(f"  {name}")

        if extra_labels:
            print("\nExtra labels:")
            for name in extra_labels:
                print(f"  {name}")

        if invalid_labels:
            print("\nInvalid labels:")
            for item in invalid_labels:
                print(f"  {item}")

        if wrong_class:
            print("\nWrong class IDs:")
            for item in wrong_class:
                print(f"  {item}")

        if empty_labels:
            print("\nEmpty labels:")
            for name in empty_labels:
                print(f"  {name}")

    print("=" * 60)


if __name__ == "__main__":
    main()