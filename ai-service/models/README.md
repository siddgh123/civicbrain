# ai-service/models

Model files are **not** in git (see `.gitignore`); this README and `MANIFEST.json` are. The worker and the API refuse to start if a file listed in `MANIFEST.json` is missing or its SHA-256 differs (`docs/06_AI_PIPELINE.md` §5, rule `.agents/rules/30-ai-service-python.md`).

## Files expected (after P2)
| File | What | Made by |
|---|---|---|
| `yolov8s_civicbrain.onnx` | YOLOv8s detector, 4 classes (0 Pothole, 1 Garbage Accumulation, 2 Waterlogging, 3 Road Damage), imgsz 640 | P2 training on Kaggle → `yolo export format=onnx` |
| `yolov8n_civicbrain.onnx` | smaller fallback / latency comparison | P2 |
| `text_clf.joblib` | complaint-text classifier (TF-IDF + logistic regression) | P2 `ai-service/training/` |
| `all-MiniLM-L6-v2/` | sentence-transformers model folder (duplicate text similarity, Step 12) | downloaded once from Hugging Face, then `HF_HUB_OFFLINE=1` |
| `face_detection_yunet_2023mar.onnx` | YuNet face detector for photo blurring (BLUR_IMAGE) | OpenCV Zoo (Apache-2.0) |

## MANIFEST.json format
Create it in P2 with the real values (the script in `ai-service/training/` computes the hashes). Example shape — **do not copy these placeholder values**:
```json
{
  "manifest_version": 1,
  "created_at": "2026-10-20T10:00:00+05:30",
  "files": [
    {
      "path": "yolov8s_civicbrain.onnx",
      "sha256": "<64 hex chars>",
      "kind": "yolo",
      "classes": ["Pothole", "Garbage Accumulation", "Waterlogging", "Road Damage"],
      "imgsz": 640,
      "dataset_version": "data_v2 (see data/yolo/DATASET_CARD.md)",
      "training_run": "v8s_640_seed42",
      "metrics_file": "yolo_metrics.json",
      "licence": "AGPL-3.0 (Ultralytics); training data licences in DATASET_CARD.md"
    }
  ]
}
```
For a folder (MiniLM), list every file inside it with its own hash, or hash the sorted concatenation and say so in `kind`.

## Licences to remember
Ultralytics YOLOv8 = AGPL-3.0 (keep the repository public); RDD2022 images = CC BY-SA 4.0 (credit in `DATASET_CARD.md` and the report); all-MiniLM-L6-v2 = Apache-2.0; YuNet = Apache-2.0.
