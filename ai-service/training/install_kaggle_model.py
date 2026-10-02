"""CivicBrain | ai-service/training/install_kaggle_model.py - installs the YOLO model trained on Kaggle

Input: civicbrain_yolo_outputs.zip (downloaded by the human from the Kaggle notebook's Output tab into
C:\\dev\\civicbrain\\kaggle_download\\). The agent may run this script (prompt P08):

    ai-service\\.venv\\Scripts\\python ai-service\\training\\install_kaggle_model.py --check

What it does (nothing is deleted):
  1. reads only these members of the zip: yolov8s_civicbrain.onnx, yolo_metrics.json, manifest_entry.json,
     dataset_report.json and plots/*.png|csv (any other name, absolute path or '..' is refused);
  2. checks the ONNX SHA-256 against manifest_entry.json and the classes against the FROZEN list;
  3. copies the ONNX to ai-service/models/ (an older different file is renamed *.previous-<sha12>.onnx);
  4. writes/updates ai-service/models/MANIFEST.json (entry for yolov8s_civicbrain.onnx);
  5. copies yolo_metrics.json, dataset_report.json and the plots to docs/reports/ (committed, used in the report);
  6. --check: loads the ONNX with onnxruntime on CPU and runs one dummy 640x640 image (output shape 1x8x8400).
Exit codes: 0 installed, 1 verification failed, 2 input missing / wrong arguments.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from model_manifest import FROZEN_CLASSES, MODELS_DIR, REPO_ROOT, now_iso, sha256_file, upsert_entry  # noqa: E402

ONNX_NAME = "yolov8s_civicbrain.onnx"
WANTED = {ONNX_NAME, "yolo_metrics.json", "manifest_entry.json", "dataset_report.json"}
PLOT_RE = re.compile(r"^plots/[A-Za-z0-9_./-]+\.(png|csv)$")


def newest_zip(folder: Path) -> Path | None:
    zips = sorted(folder.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    return zips[0] if zips else None


def safe_members(z: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    out: dict[str, zipfile.ZipInfo] = {}
    for info in z.infolist():
        name = info.filename
        if info.is_dir():
            continue
        if name.startswith(("/", "\\")) or ".." in Path(name).parts or ":" in name:
            raise ValueError(f"unsafe path in zip: {name}")
        if name in WANTED or PLOT_RE.match(name):
            out[name] = info
    return out


def check_onnx(path: Path) -> str:
    import numpy as np
    import onnxruntime as ort

    sess = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    inp = sess.get_inputs()[0]
    x = np.zeros((1, 3, 640, 640), dtype=np.float32)
    out = sess.run(None, {inp.name: x})[0]
    if tuple(out.shape) != (1, 4 + len(FROZEN_CLASSES), 8400):
        raise ValueError(f"unexpected ONNX output shape {out.shape} (expected 1x8x8400 for 4 classes at 640)")
    return f"input {inp.name} {inp.shape}, output {tuple(out.shape)}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zip", type=Path, help="default: newest *.zip in kaggle_download/")
    ap.add_argument("--models-dir", type=Path, default=MODELS_DIR)
    ap.add_argument("--reports-dir", type=Path, default=REPO_ROOT / "docs" / "reports")
    ap.add_argument("--check", action="store_true", help="load the ONNX with onnxruntime and run one dummy image")
    args = ap.parse_args(argv)

    zpath = args.zip or newest_zip(REPO_ROOT / "kaggle_download")
    if not zpath or not zpath.is_file():
        print("ERROR: no zip found. Download civicbrain_yolo_outputs.zip from Kaggle into kaggle_download/ first.", file=sys.stderr)
        return 2

    with zipfile.ZipFile(zpath) as z:
        try:
            members = safe_members(z)
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1
        missing = sorted(WANTED - members.keys())
        if missing:
            print(f"ERROR: {zpath.name} lacks {missing} - was the Kaggle run finished (cell 6 printed DONE)?", file=sys.stderr)
            return 1
        entry = json.loads(z.read(members["manifest_entry.json"]).decode("utf-8"))
        metrics = json.loads(z.read(members["yolo_metrics.json"]).decode("utf-8"))
        if entry.get("classes") != FROZEN_CLASSES:
            print(f"ERROR: classes {entry.get('classes')} differ from the FROZEN list {FROZEN_CLASSES}", file=sys.stderr)
            return 1
        if entry.get("path") != ONNX_NAME:
            print(f"ERROR: manifest_entry path is {entry.get('path')!r}, expected {ONNX_NAME}", file=sys.stderr)
            return 1

        args.models_dir.mkdir(parents=True, exist_ok=True)
        staged = args.models_dir / (ONNX_NAME + ".incoming")
        with z.open(members[ONNX_NAME]) as src, staged.open("wb") as dst:
            shutil.copyfileobj(src, dst)
        digest = sha256_file(staged)
        if digest != entry.get("sha256"):
            print(f"ERROR: SHA-256 mismatch: file {digest[:12]}..., manifest_entry {str(entry.get('sha256'))[:12]}...", file=sys.stderr)
            print(f"       (left as {staged.name}; download the zip again)", file=sys.stderr)
            return 1
        target = args.models_dir / ONNX_NAME
        if target.is_file():
            old = sha256_file(target)
            if old != digest:
                keep = args.models_dir / f"yolov8s_civicbrain.previous-{old[:12]}.onnx"
                target.replace(keep)
                print(f"older model kept as {keep.name}")
        staged.replace(target)

        args.reports_dir.mkdir(parents=True, exist_ok=True)
        for name in ("yolo_metrics.json", "dataset_report.json"):
            (args.reports_dir / name).write_bytes(z.read(members[name]))
        (args.models_dir / "yolo_metrics.json").write_bytes(z.read(members["yolo_metrics.json"]))
        plots = 0
        for name, info in members.items():
            if name.startswith("plots/"):
                dest = args.reports_dir / "yolo_plots" / Path(name).relative_to("plots")
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(z.read(info))
                plots += 1

    entry["installed_at"] = now_iso()
    entry["source_zip"] = zpath.name
    manifest = upsert_entry(entry, args.models_dir)

    check_text = "not run (add --check)"
    if args.check:
        try:
            check_text = check_onnx(target)
        except Exception as e:  # noqa: BLE001 - report any loader problem clearly
            print(f"ERROR: ONNX check failed: {e}", file=sys.stderr)
            return 1

    print(f"INSTALLED {target} (sha256 {digest[:12]}...)")
    print(f"MANIFEST  {manifest}")
    print(f"REPORTS   {args.reports_dir} (yolo_metrics.json, dataset_report.json, {plots} plot files)")
    print(f"ONNX CHECK {check_text}")
    print("TEST-SPLIT METRICS (existing test split, not a Talegaon field test):")
    o = metrics.get("overall", {})
    print(f"  overall   P={o.get('precision')} R={o.get('recall')} mAP50={o.get('mAP50')} mAP50-95={o.get('mAP50_95')}")
    for cls in FROZEN_CLASSES:
        m = (metrics.get("per_class") or {}).get(cls)
        print(f"  {cls:21s} " + (f"P={m['precision']} R={m['recall']} mAP50={m['mAP50']}" if m else "no test images for this class"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
