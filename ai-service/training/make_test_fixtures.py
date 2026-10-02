"""CivicBrain | ai-service/training/make_test_fixtures.py   (P03: shared image fixtures, docs/08_TEST_PLAN.md §2)

Copies one TEST-split image per FROZEN class from data/yolo into tests/fixtures/images/ (repo root) and writes:
  pothole_1.jpg, garbage_1.jpg, waterlogging_1.jpg, road_damage_1.jpg   copies - the dataset is never changed
  <name>.txt           the image's YOLO label line = the "recorded box" for P08's golden test (±10 px)
  tiny_200px.jpg       200x150 photo (centre crop of pothole_1), must be rejected: IMAGE_TOO_SMALL (< 320 px)
  not_an_image.jpg     plain text with a .jpg name, must be rejected by the magic-byte check
  README.md            source split + original file name of every fixture, box in pixels, licence note

Pick rule (deterministic): data/yolo/images/test sorted by name; the label file has exactly ONE box and it is of the
class; shorter image side >= 320 px; no EXIF rotation (a re-encode would move the box). Preferred: the first one whose
box covers 5-60 % of the image (not a sliver, not the whole frame); if no box of the class is in that range (garbage:
the single-box test images are all close-ups), the one with the smallest box. JPEG sources are copied byte for byte,
other formats saved as JPEG.
Check the picks by eye; --exclude NAME skips an image (e.g. a readable face or number plate) and picks the next one.

    ai-service\\.venv\\Scripts\\python.exe ai-service\\training\\make_test_fixtures.py --dry-run   # show the candidates
    ai-service\\.venv\\Scripts\\python.exe ai-service\\training\\make_test_fixtures.py             # write the fixtures
Existing fixtures are only replaced with --force (P08's golden test depends on them).
Exit code 0 = written (or dry run), 1 = no candidate for a class / fixtures exist, 2 = dataset not found.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[2]
FROZEN_NAMES = ["Pothole", "Garbage Accumulation", "Waterlogging", "Road Damage"]
FIXTURE_NAMES = ["pothole_1", "garbage_1", "waterlogging_1", "road_damage_1"]
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
MIN_SIDE_PX = 320  # docs/12_ERROR_HANDLING.md: IMAGE_TOO_SMALL below 320 px
EXIF_ORIENTATION = 0x0112
NOT_AN_IMAGE_TEXT = (
    "CivicBrain test fixture: this is plain text, not a JPEG.\n"
    "The upload check must reject it by its magic bytes (docs/08_TEST_PLAN.md section 2).\n"
)
# file-name patterns of the merged dataset (checked against data/yolo/raw/{rdd_civicbrain_split,waterlogging_split,
# garbage_pile_source}); the ids are the rows of data/yolo/dataset_sources.csv
SOURCE_BY_PREFIX = {"India_": "S1", "image_": "S2", "IMG_": "S3"}
SOURCES = (
    "| Source (`data/yolo/dataset_sources.csv`) | Licence |\n"
    "|---|---|\n"
    "| S1 RDD2022-India (https://universe.roboflow.com/prakhar-kpb1v/rdd2022-india-il8ju/dataset/5) | CC BY 4.0 |\n"
    "| S2 Waterlogging Dataset (project download source) | to be documented (see `dataset_sources.csv`) |\n"
    "| S3 GarbagePile (https://universe.roboflow.com/objectdetectiondemo-irh54/garbagepile/dataset/1) | CC BY 4.0 |\n"
)


def read_boxes(lbl: Path) -> list[tuple[int, float, float, float, float]]:
    boxes = []
    for raw in lbl.read_text(encoding="utf-8").splitlines():
        parts = raw.split()
        if len(parts) == 5:
            boxes.append((int(float(parts[0])), *(float(v) for v in parts[1:])))
    return boxes


def candidates(root: Path, cls: int, min_area: float, max_area: float, exclude: set[str]) -> tuple[list[tuple[Path, Path, float]], bool]:
    """Single-box images of the class in pick order, and whether they are in the preferred box-area range."""
    found = []
    for img in sorted((root / "images" / "test").iterdir()):
        if img.suffix.lower() not in IMG_EXT or img.name in exclude:
            continue
        lbl = root / "labels" / "test" / (img.stem + ".txt")
        if not lbl.is_file():
            continue
        boxes = read_boxes(lbl)
        if len(boxes) != 1 or boxes[0][0] != cls:
            continue
        with Image.open(img) as im:
            if min(im.size) < MIN_SIDE_PX or im.getexif().get(EXIF_ORIENTATION, 1) != 1:
                continue
        found.append((img, lbl, boxes[0][3] * boxes[0][4]))
    preferred = [c for c in found if min_area <= c[2] <= max_area]
    if preferred:
        return preferred, True
    return sorted(found, key=lambda c: (c[2], c[0].name)), False


def source_of(file_name: str) -> str:
    return next((s for prefix, s in SOURCE_BY_PREFIX.items() if file_name.startswith(prefix)), "unknown")


def box_px(label_line: str, size: tuple[int, int]) -> str:
    _, x, y, w, h = (float(v) for v in label_line.split())
    width, height = size
    x1, y1 = round((x - w / 2) * width), round((y - h / 2) * height)
    x2, y2 = round((x + w / 2) * width), round((y + h / 2) * height)
    return f"({x1}, {y1}) - ({x2}, {y2})"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=REPO / "data" / "yolo", help="dataset root with images/test, labels/test")
    ap.add_argument("--out", type=Path, default=REPO / "tests" / "fixtures" / "images")
    ap.add_argument("--min-area", type=float, default=0.05, help="smallest box area as a share of the image")
    ap.add_argument("--max-area", type=float, default=0.60, help="largest box area as a share of the image")
    ap.add_argument("--exclude", action="append", default=[], help="test image file name to skip (repeatable)")
    ap.add_argument("--dry-run", action="store_true", help="only print the first candidates per class")
    ap.add_argument("--force", action="store_true", help="replace existing fixtures")
    args = ap.parse_args(argv)

    root = args.root.resolve()
    if not (root / "images" / "test").is_dir() or not (root / "labels" / "test").is_dir():
        print(f"ERROR: {root} has no images/test + labels/test", file=sys.stderr)
        return 2

    picks: list[tuple[str, Path, Path]] = []
    for cls, name in enumerate(FIXTURE_NAMES):
        found, in_range = candidates(root, cls, args.min_area, args.max_area, set(args.exclude))
        rule = "" if in_range or not found else f" (none with a box of {args.min_area:.0%}-{args.max_area:.0%}: smallest box first)"
        print(f"{FROZEN_NAMES[cls]}: {len(found)} candidates{rule}")
        if args.dry_run:
            for img, _, area in found[:5]:
                print(f"  {img.name}  box {area:.0%}")
            continue
        if not found:
            print(f"ERROR: no single-box test image for {FROZEN_NAMES[cls]}", file=sys.stderr)
            return 1
        picks.append((name, found[0][0], found[0][1]))
    if args.dry_run:
        return 0

    out = args.out.resolve()
    targets = [f"{n}{ext}" for n in FIXTURE_NAMES for ext in (".jpg", ".txt")] + ["tiny_200px.jpg", "not_an_image.jpg", "README.md"]
    existing = [t for t in targets if (out / t).exists()]
    if existing and not args.force:
        print(f"ERROR: fixtures exist ({', '.join(existing)}) - add --force to replace them", file=sys.stderr)
        return 1
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    for name, img, lbl in picks:
        dest = out / f"{name}.jpg"
        if img.suffix.lower() in {".jpg", ".jpeg"}:
            shutil.copyfile(img, dest)  # copy, never move
        else:
            with Image.open(img) as im:
                im.convert("RGB").save(dest, "JPEG", quality=95)
        label_line = lbl.read_text(encoding="utf-8").strip()
        (out / f"{name}.txt").write_text(label_line + "\n", encoding="utf-8")
        with Image.open(dest) as im:
            size = im.size
        rows.append(f"| `{name}.jpg` | test | `{img.name}` | {source_of(img.name)} | {size[0]}x{size[1]} | `{label_line}` "
                    f"| {box_px(label_line, size)} |")
        print(f"wrote {name}.jpg + {name}.txt  <- test/{img.name}")

    with Image.open(out / "pothole_1.jpg") as im:
        width, height = im.size
        crop_w = min(width, height * 4 // 3)
        crop_h = crop_w * 3 // 4
        left, top = (width - crop_w) // 2, (height - crop_h) // 2
        im.convert("RGB").crop((left, top, left + crop_w, top + crop_h)).resize((200, 150), Image.Resampling.LANCZOS).save(
            out / "tiny_200px.jpg", "JPEG", quality=90)
    (out / "not_an_image.jpg").write_text(NOT_AN_IMAGE_TEXT, encoding="utf-8")
    print("wrote tiny_200px.jpg (200x150) + not_an_image.jpg (text)")

    readme = (
        "# Test fixtures - images (shared by backend, AI and Playwright tests)\n\n"
        "Made by `ai-service/training/make_test_fixtures.py` (P03) from the project dataset `data/yolo` (TEST split, never\n"
        "used for training). The dataset files were copied, not changed. Do not edit these files by hand: P08's golden test\n"
        "compares the YOLO box with the recorded label line (±10 px).\n\n"
        "| Fixture | Split | Original file | Source | Size (px) | Recorded box (`<name>.txt`, YOLO: class cx cy w h) "
        "| Box in px (x1, y1) - (x2, y2) |\n"
        "|---|---|---|---|---|---|---|\n"
        + "\n".join(rows) + "\n"
        "| `tiny_200px.jpg` | - | centre crop (4:3) of `pothole_1.jpg`, resized to 200x150 | S1 | 200x150 | - "
        "| must be rejected: `IMAGE_TOO_SMALL` (< 320 px) |\n"
        "| `not_an_image.jpg` | - | plain text with a `.jpg` name | kit | - | - | must be rejected by the magic-byte check |\n\n"
        "Not here yet (docs/08_TEST_PLAN.md §2): `no_defect.jpg`, `a4_pothole.jpg` + `a4_pothole.json` (real photos, later\n"
        "prompts), `huge_50mp.png` (generated inside its test, never committed), `camera.y4m` (generated, git-ignored).\n\n"
        "## Licence\n"
        "From the project dataset (`data/yolo`, sources and licences in `data/yolo/dataset_sources.csv`). Used here only as\n"
        "test data; the photos are not Talegaon field photos. CC BY 4.0 attribution: the source links below.\n\n"
        + SOURCES
    )
    (out / "README.md").write_text(readme, encoding="utf-8")
    print(f"wrote {out / 'README.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
