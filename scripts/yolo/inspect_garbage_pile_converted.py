from pathlib import Path
import random
import cv2


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

OUTPUT_ROOT = (
    PROJECT_ROOT
    / "data"
    / "yolo"
    / "raw"
    / "garbage_pile_visual_validation"
)

SAMPLES_PER_SPLIT = 10


def draw_labels(image_path, label_path):

    image = cv2.imread(str(image_path))

    if image is None:
        return None

    height, width = image.shape[:2]

    if not label_path.exists():
        return image

    lines = label_path.read_text(
        encoding="utf-8"
    ).splitlines()

    for line in lines:

        parts = line.strip().split()

        if len(parts) != 5:
            continue

        class_id = int(parts[0])

        x_center = float(parts[1])
        y_center = float(parts[2])
        box_width = float(parts[3])
        box_height = float(parts[4])

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

        x1 = max(0, min(x1, width - 1))
        y1 = max(0, min(y1, height - 1))
        x2 = max(0, min(x2, width - 1))
        y2 = max(0, min(y2, height - 1))

        cv2.rectangle(
            image,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            2
        )

        cv2.putText(
            image,
            f"Garbage Accumulation ({class_id})",
            (x1, max(20, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 0),
            2
        )

    return image


def process_split(split):

    image_dir = DATASET_ROOT / split / "images"
    label_dir = DATASET_ROOT / split / "labels"

    output_dir = OUTPUT_ROOT / split
    output_dir.mkdir(parents=True, exist_ok=True)

    extensions = {".jpg", ".jpeg", ".png", ".webp"}

    images = [
        p for p in image_dir.iterdir()
        if p.suffix.lower() in extensions
    ]

    random.seed(42)

    samples = random.sample(
        images,
        min(SAMPLES_PER_SPLIT, len(images))
    )

    for image_path in samples:

        label_path = (
            label_dir / f"{image_path.stem}.txt"
        )

        result = draw_labels(
            image_path,
            label_path
        )

        if result is not None:

            output_path = (
                output_dir / image_path.name
            )

            cv2.imwrite(
                str(output_path),
                result
            )

    print(
        f"{split}: {len(samples)} images saved"
    )


def main():

    print("=" * 60)
    print("Garbage Accumulation Visual Validation")
    print("=" * 60)

    OUTPUT_ROOT.mkdir(
        parents=True,
        exist_ok=True
    )

    for split in ["train", "valid", "test"]:
        process_split(split)

    print()
    print("Visual validation complete.")
    print()
    print("Output:")
    print(OUTPUT_ROOT)


if __name__ == "__main__":
    main()