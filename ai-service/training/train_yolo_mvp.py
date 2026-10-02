"""CivicBrain | ai-service/training/train_yolo_mvp.py   (7-day MVP - run on Kaggle, GPU T4/P100)

Trains YOLOv8 on the EXISTING dataset (prepared by prepare_mvp_dataset.py), evaluates on the untouched
test split, exports ONNX for the CPU worker and writes everything the kit expects:
    <out>/yolov8s_civicbrain.onnx      -> copy to ai-service/models/
    <out>/yolo_metrics.json            -> P, R, mAP50, mAP50-95 overall + per class (test split)
    <out>/manifest_entry.json          -> paste into ai-service/models/MANIFEST.json
    <out>/runs/...                     -> Ultralytics plots (confusion matrix, PR curves)

Kaggle notebook (Settings: Accelerator = GPU, Internet = On; dataset "civicbrain-yolo" = your data/yolo folder):
    !pip install -q ultralytics==8.4.168
    !python prepare_mvp_dataset.py --root /kaggle/input/civicbrain-yolo/yolo --out-dir /kaggle/working/mvp
    !python train_yolo_mvp.py --data /kaggle/working/mvp/data_mvp.yaml --out /kaggle/working/out --timing
    !python train_yolo_mvp.py --data /kaggle/working/mvp/data_mvp.yaml --out /kaggle/working/out
Then "Save Version -> Save & Run All" so training continues when the browser is closed, and download
/kaggle/working/out when it finishes. Settings follow docs/11_DATA_SOURCES.md sec. 0 (MVP mode).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

FROZEN_NAMES = ["Pothole", "Garbage Accumulation", "Waterlogging", "Road Damage"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, required=True, help="data_mvp.yaml from prepare_mvp_dataset.py")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--model", default="yolov8s.pt", help="yolov8s.pt (default) or yolov8n.pt (faster, less accurate)")
    ap.add_argument("--epochs", type=int, default=120)
    ap.add_argument("--patience", type=int, default=25)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--timing", action="store_true", help="3-epoch run only, prints minutes per epoch, no export")
    args = ap.parse_args(argv)

    try:
        from ultralytics import YOLO
    except ImportError:
        print("ERROR: run  pip install ultralytics==8.4.168  first", file=sys.stderr)
        return 2
    if not args.data.is_file():
        print(f"ERROR: {args.data} not found - run prepare_mvp_dataset.py first", file=sys.stderr)
        return 2

    args.out.mkdir(parents=True, exist_ok=True)
    run_name = "timing" if args.timing else f"{Path(args.model).stem}_{args.imgsz}_mvp_seed42"
    epochs = 3 if args.timing else args.epochs

    model = YOLO(args.model)
    t0 = time.time()
    model.train(
        data=str(args.data), epochs=epochs, patience=args.patience, imgsz=args.imgsz, batch=-1,
        seed=42, deterministic=True, optimizer="auto", cos_lr=True,
        mosaic=1.0, close_mosaic=10, mixup=0.1,
        cls_pw=0.5,                     # class-imbalance weighting (garbage/waterlogging are rare)
        save_period=10, project=str(args.out / "runs"), name=run_name, exist_ok=True, plots=True,
    )
    minutes = (time.time() - t0) / 60
    if args.timing:
        print(f"TIMING: {minutes / epochs:.1f} min per epoch -> {args.epochs} epochs ~ {minutes / epochs * args.epochs / 60:.1f} h "
              "(early stopping usually ends sooner). Kaggle GPU quota is ~30 h/week.")
        return 0

    best = args.out / "runs" / run_name / "weights" / "best.pt"
    if not best.is_file():
        print(f"ERROR: {best} missing - training did not finish", file=sys.stderr)
        return 1

    trained = YOLO(str(best))
    m = trained.val(data=str(args.data), split="test", imgsz=args.imgsz, plots=True,
                    project=str(args.out / "runs"), name=f"{run_name}_test", exist_ok=True)
    per_class = {}
    for i, c in enumerate(m.ap_class_index):
        p, r, ap50, ap = m.class_result(i)
        per_class[FROZEN_NAMES[int(c)]] = {"precision": round(float(p), 4), "recall": round(float(r), 4),
                                           "mAP50": round(float(ap50), 4), "mAP50_95": round(float(ap), 4)}
    for name in FROZEN_NAMES:
        per_class.setdefault(name, None)   # class absent from the test split -> no number (say so in the report)
    mp, mr, map50, map5095 = (float(x) for x in m.mean_results())
    metrics = {
        "model": args.model, "run": run_name, "epochs_requested": epochs, "train_minutes": round(minutes, 1),
        "evaluated_on": "existing test split (data/yolo/images/test) - NOT a Talegaon field test set",
        "overall": {"precision": round(mp, 4), "recall": round(mr, 4), "mAP50": round(map50, 4), "mAP50_95": round(map5095, 4)},
        "per_class": per_class,
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
    }
    (args.out / "yolo_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    onnx_path = Path(trained.export(format="onnx", imgsz=args.imgsz))
    final = args.out / "yolov8s_civicbrain.onnx" if "8s" in args.model else args.out / f"{Path(args.model).stem}_civicbrain.onnx"
    shutil.copy2(onnx_path, final)
    entry = {
        "path": final.name, "sha256": sha256(final), "kind": "yolo", "classes": FROZEN_NAMES, "imgsz": args.imgsz,
        "dataset_version": "existing data/yolo (3,398 images, MVP) - see dataset_report.json",
        "training_run": run_name, "metrics_file": "yolo_metrics.json",
        "licence": "AGPL-3.0 (Ultralytics); training data licences in data/yolo/dataset_sources.csv",
    }
    (args.out / "manifest_entry.json").write_text(json.dumps(entry, indent=2), encoding="utf-8")
    print(json.dumps(metrics["overall"], indent=2))
    print(f"DONE: {final} (sha256 {entry['sha256'][:12]}...), yolo_metrics.json, manifest_entry.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
