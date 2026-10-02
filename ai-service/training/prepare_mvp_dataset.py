"""CivicBrain | ai-service/training/prepare_mvp_dataset.py   (7-day MVP: train YOLO on the EXISTING images)

Checks the team's existing YOLO dataset (data/yolo: images/{train,val,test} + labels/{train,val,test},
3,398 images, 4 FROZEN classes) and prepares an oversampled training list, WITHOUT changing any
image or label file.

What it does
  1. data.yaml must list exactly the frozen classes: 0 Pothole, 1 Garbage Accumulation,
     2 Waterlogging, 3 Road Damage (otherwise it stops - never retrain with other names/ids).
  2. Every label line is checked: 5 numbers, class id 0-3, box inside 0..1, width/height > 0.
  3. Leakage check: the same image (SHA-256) in train and val/test is reported; such train copies
     are left OUT of the training list (so test numbers stay honest).
  4. Writes <out-dir>/train_mvp.txt: absolute image paths, images with Garbage repeated x3 and
     images with Waterlogging repeated x2 (the two weak classes), everything else once.
  5. Writes <out-dir>/data_mvp.yaml (path = dataset root, train = train_mvp.txt, val/test = the
     existing folders) and <out-dir>/dataset_report.json (counts per split/class, problems found).

Run on the laptop first (quick sanity check), then again on Kaggle with Kaggle paths:
    ai-service\\.venv\\Scripts\\python ai-service\\training\\prepare_mvp_dataset.py --root data\\yolo --out-dir data\\yolo\\mvp
    python prepare_mvp_dataset.py --root /kaggle/input/civicbrain-yolo/yolo --out-dir /kaggle/working/mvp
Exit code 0 = ready to train; 1 = errors (read the report); 2 = wrong arguments/structure.
Needs only PyYAML and Pillow (both come with ultralytics; both are on Kaggle).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

FROZEN_NAMES = ["Pothole", "Garbage Accumulation", "Waterlogging", "Road Damage"]
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
SPLITS = ("train", "val", "test")


def names_from_yaml(data: dict) -> list[str]:
    names = data.get("names")
    if isinstance(names, dict):
        return [names[k] for k in sorted(names, key=int)]
    return list(names or [])


def split_dir(root: Path, data: dict, split: str) -> Path:
    """Image folder of a split: from data.yaml when it points to a folder, else images/<split>."""
    for key in ([split] + (["valid"] if split == "val" else [])):
        value = data.get(key)
        if isinstance(value, str) and not value.endswith(".txt"):
            p = Path(value)
            p = p if p.is_absolute() else (root / p)
            if p.is_dir():
                return p.resolve()
    return (root / "images" / split).resolve()


def label_path(img: Path) -> Path:
    parts = list(img.parts)
    idx = len(parts) - 1 - parts[::-1].index("images")  # last 'images' component (Ultralytics rule)
    parts[idx] = "labels"
    return Path(*parts).with_suffix(".txt")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_label(lbl: Path, problems: list[str]) -> list[int]:
    classes: list[int] = []
    for n, raw in enumerate(lbl.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 5:
            problems.append(f"{lbl}:{n} expected 5 values (detection box), got {len(parts)}")
            continue
        try:
            cls = int(float(parts[0]))
            x, y, w, h = (float(v) for v in parts[1:])
        except ValueError:
            problems.append(f"{lbl}:{n} not numbers")
            continue
        if float(parts[0]) != cls or not 0 <= cls <= 3:
            problems.append(f"{lbl}:{n} class id {parts[0]} not in 0..3")
            continue
        if not (0 <= x <= 1 and 0 <= y <= 1 and 0 < w <= 1 and 0 < h <= 1):
            problems.append(f"{lbl}:{n} box outside 0..1 or empty ({x} {y} {w} {h})")
            continue
        classes.append(cls)
    return classes


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, required=True, help="dataset root that contains data.yaml, images/, labels/")
    ap.add_argument("--out-dir", type=Path, required=True, help="where train_mvp.txt, data_mvp.yaml, dataset_report.json go")
    ap.add_argument("--garbage-factor", type=int, default=3)
    ap.add_argument("--waterlogging-factor", type=int, default=2)
    ap.add_argument("--check-images", action="store_true", help="also open every image with Pillow (slower)")
    args = ap.parse_args(argv)

    root = args.root.resolve()
    yaml_file = root / "data.yaml"
    if not yaml_file.is_file():
        print(f"ERROR: {yaml_file} not found", file=sys.stderr)
        return 2
    data = yaml.safe_load(yaml_file.read_text(encoding="utf-8")) or {}
    names = names_from_yaml(data)
    norm = [str(x).strip().lower().replace("_", " ") for x in names]
    if norm != [x.lower() for x in FROZEN_NAMES]:
        print(f"ERROR: data.yaml names are {names}; they must be {FROZEN_NAMES} in this order (FROZEN class ids "
              "0-3). Fix the names in data.yaml only if the label ids already mean these classes.", file=sys.stderr)
        return 2

    problems: list[str] = []
    report: dict = {"root": str(root), "splits": {}, "leakage": [], "problems": problems}
    hashes: dict[str, dict[str, list[Path]]] = {s: defaultdict(list) for s in SPLITS}
    train_items: list[tuple[Path, set[int]]] = []

    for split in SPLITS:
        img_dir = split_dir(root, data, split)
        if not img_dir.is_dir():
            print(f"ERROR: image folder for '{split}' not found: {img_dir}", file=sys.stderr)
            return 2
        images = sorted(p for p in img_dir.rglob("*") if p.suffix.lower() in IMG_EXT)
        inst = Counter()
        img_per_class = Counter()
        backgrounds = missing_labels = 0
        for img in images:
            lbl = label_path(img)
            if not lbl.is_file():
                missing_labels += 1
                classes: list[int] = []
            else:
                classes = check_label(lbl, problems)
            if not classes:
                backgrounds += 1
            inst.update(classes)
            img_per_class.update(set(classes))
            hashes[split][sha256(img)].append(img)
            if args.check_images:
                try:
                    from PIL import Image
                    with Image.open(img) as im:
                        im.verify()
                except Exception as exc:  # noqa: BLE001 - report every unreadable file
                    problems.append(f"{img} unreadable: {exc}")
            if split == "train":
                train_items.append((img, set(classes)))
        report["splits"][split] = {
            "folder": str(img_dir),
            "images": len(images),
            "background_or_empty": backgrounds,
            "missing_label_files": missing_labels,
            "instances": {FROZEN_NAMES[c]: inst.get(c, 0) for c in range(4)},
            "images_with_class": {FROZEN_NAMES[c]: img_per_class.get(c, 0) for c in range(4)},
        }

    # leakage: identical files across splits
    leaked_train: set[Path] = set()
    for other in ("val", "test"):
        for h, paths in hashes["train"].items():
            if h in hashes[other]:
                report["leakage"].append({"sha256": h, "train": [str(p) for p in paths],
                                          other: [str(p) for p in hashes[other][h]]})
                leaked_train.update(paths)
    for h, paths in hashes["val"].items():
        if h in hashes["test"]:
            report["leakage"].append({"sha256": h, "val": [str(p) for p in paths], "test": [str(p) for p in hashes["test"][h]]})

    # oversampled training list (absolute paths; leaked train copies left out)
    lines: list[str] = []
    for img, classes in train_items:
        if img in leaked_train:
            continue
        factor = 1
        if 1 in classes:
            factor = max(factor, args.garbage_factor)
        if 2 in classes:
            factor = max(factor, args.waterlogging_factor)
        lines.extend([img.as_posix()] * factor)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    train_txt = (args.out_dir / "train_mvp.txt").resolve()
    train_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    data_mvp = {
        "path": root.as_posix(),
        "train": train_txt.as_posix(),
        "val": split_dir(root, data, "val").as_posix(),
        "test": split_dir(root, data, "test").as_posix(),
        "nc": 4,
        "names": {i: n for i, n in enumerate(FROZEN_NAMES)},
    }
    (args.out_dir / "data_mvp.yaml").write_text(yaml.safe_dump(data_mvp, sort_keys=False, allow_unicode=True), encoding="utf-8")

    report["train_list"] = {
        "file": str(train_txt),
        "lines": len(lines),
        "unique_images": len({ln for ln in lines}),
        "left_out_because_of_leakage": len(leaked_train),
        "factors": {"Garbage Accumulation": args.garbage_factor, "Waterlogging": args.waterlogging_factor},
    }
    (args.out_dir / "dataset_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    for split in SPLITS:
        s = report["splits"][split]
        print(f"{split:5s} images={s['images']:5d} empty={s['background_or_empty']:4d} "
              + " ".join(f"{k}={v}" for k, v in s["instances"].items()))
    print(f"leakage groups: {len(report['leakage'])}  (train copies left out: {len(leaked_train)})")
    print(f"train_mvp.txt: {len(lines)} lines, {report['train_list']['unique_images']} unique images")
    print(f"label problems: {len(problems)}")
    for p in problems[:20]:
        print("  " + p)
    if report["splits"]["test"]["images"] == 0 or any(v == 0 for v in report["splits"]["test"]["instances"].values()):
        print("WARNING: the test split lacks at least one class - per-class test metrics will be missing for it")
    print(f"wrote {args.out_dir / 'data_mvp.yaml'} and dataset_report.json")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
