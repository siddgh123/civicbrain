# P08 — Text classifier, YOLO detector (install the Kaggle model), authenticity checks
**Day 3 (Sat 3 Oct) · agent ≈ 2.5 h · human ≈ 5 min · Needs: P02, P03 · Model: strongest**

## Goal
The trained YOLO model is installed with its checksum and honest metrics; the complaint-text classifier is trained
and saved; `pipeline/classify.py`, `pipeline/detect.py`, `pipeline/authenticity.py` work and are tested.
(They are wired into the analysis job in P12.)

## Human step (FIRST, ≈ 5 min)
1. kaggle.com → your notebook → **Versions** → the committed version → status "Complete"? If it is still running,
   say "not ready" - the agent builds everything else first and asks again at the end.
2. Open the version → **Output** → download `civicbrain_yolo_outputs.zip`.
3. Put it into `C:\dev\civicbrain\kaggle_download\` (create the folder) and say "model downloaded".
If the committed run FAILED: open its log, paste the last 30 lines into the chat.

## Read first
`docs/06_AI_PIPELINE.md` §2.1, §2.2, §2.3, §5 · `ai-service/training/install_kaggle_model.py` (docstring) ·
`data/complaints/README.md` · `docs/03_DATABASE.md` §3–§4 (authenticity_checks, yolo_detections, ai_classifications,
`fn_similar_images`, boundary functions) · `.agents/rules/30-ai-service-python.md` · `docs/INVENTORY.md`

## Build
1. **Install the YOLO model:** `ai-service\.venv\Scripts\python.exe ai-service\training\install_kaggle_model.py --check`
   → `ai-service/models/yolov8s_civicbrain.onnx` + MANIFEST entry + `docs/reports/yolo_metrics.json`, plots.
2. **Text classifier:** `ai-service/training/train_text_clf.py`: train = `synthetic_complaints_500.csv` (title + ". " +
   description) + `kit_authored_train.csv`; TF-IDF union (word 1–2, `char_wb` 2–5, sublinear tf) → LogisticRegression
   (`class_weight='balanced'`, C from 5-fold stratified CV over [1, 2, 5, 10], `max_iter=2000`, `random_state=42`);
   report accuracy + macro-F1 + confusion matrix on `sanity_test_mvp.csv`; save `models/text_clf.joblib`,
   `models/text_clf_metrics.json`, copy to `docs/reports/text_clf_metrics.json`; MANIFEST entry through
   `ai-service/training/model_manifest.py` (`kind: text-classifier`, sha256, data files + row counts, C, metrics).
3. `pipeline/classify.py`: load once (checksum from MANIFEST), `predict(text) → top-3 [(category, p)]`, mismatch rule
   of 06 §2.2 (top-1 ≠ citizen category with p ≥ 0.70 → `is_accepted=false`), writes `ai_classifications` (TEXT).
4. `pipeline/detect.py`: Ultralytics `YOLO(path, task='detect')` on the ONNX file, `imgsz=640, conf=0.25, iou=0.5,
   device='cpu'`, loaded once; boxes in pixels; `model_version` = SHA-256[:12]; primary detection = highest confidence
   of the category's `yolo_class_id`; writes `yolo_detections` + `ai_classifications` (IMAGE). Measure the CPU time per image.
5. `pipeline/authenticity.py`: MVP checks of 06 §2.1 - CAPTURE_SESSION, GPS_ACCURACY, GPS_FRESHNESS, BOUNDARY
   (distance to the boundary edge with PostGIS), IMAGE_REUSE_SHA256, IMAGE_REUSE_PHASH (`fn_similar_images`; the
   nearby-and-recent rule), SUBMISSION_RATE, IMPOSSIBLE_TRAVEL, ACCOUNT_TRUST, CATEGORY_IMAGE_MISMATCH (after YOLO);
   score from 100 with the table's deltas, clamp 0–100, < 40 → FLAGGED else PASSED; pure scoring functions + small DB
   helpers; writes `authenticity_checks` and `complaints.authenticity_*` (idempotent: delete-then-insert per complaint).
   `phash` = `imagehash.phash` 64-bit → signed int64.

## Tests (write first)
- classifier: training is deterministic (same predictions twice); sanity accuracy recorded; regression guard
  accuracy ≥ 0.80 on `sanity_test_mvp.csv` (measured ≈ 0.90 with this recipe); mismatch rule cases.
- detector (`@pytest.mark.models`): `tests/fixtures/images/pothole_1.jpg` gives at least one Pothole box (conf ≥ 0.25);
  each of the 4 fixtures runs without error; `model_version` = first 12 hex of the file hash. If the trained model finds
  nothing on a fixture, replace that fixture with another TEST-split image of the same class on which it does detect,
  and say so in `tests/fixtures/images/README.md` (this is a smoke test; the real numbers are `yolo_metrics.json`).
- authenticity: one test per row of the 06 §2.1 table (PASS/WARN/FAIL + delta), clamp, FLAGGED threshold, nearby&recent
  pHash = duplicate hint PASS.
- model manifest: worker start fails with a clear message when a required file or hash is wrong (`REQUIRE_MODELS`).

## Verify (agent)
in `ai-service`: ruff + pytest (the `models` tests must RUN, not skip - show the count) · print the YOLO overall and
per-class metrics and the classifier sanity metrics · CPU ms per image · `start-all.ps1 -Only worker,ai-api -Restart` →
`/health` lists the YOLO model and the text classifier as loaded (MiniLM arrives in P09, so an overall
`modelsLoaded` flag may still be false here - expected, not a failure; `REQUIRE_MODELS` stays false until P12).

## Ask the human (yes/no)
- Q1. These are the YOLO numbers on the existing test split (table in the Done report). Use them as they are in the report (they are stated honestly as "not a Talegaon field test")?
- Q2. The text classifier scores <accuracy> on the 40 kit-written sanity sentences. OK to continue?

## Done when
model installed and checked · classifier saved with metrics · 3 pipeline modules tested · models tests ran · committed + pushed.
If the human said "not ready" at the start: everything except step 1 done, then ask again for the zip; the prompt is DONE
only after step 1 and the `models` tests ran.

## Next
`/run-prompt P09` — priority + duplicates (FROZEN) + MiniLM (≈ 2 h)
