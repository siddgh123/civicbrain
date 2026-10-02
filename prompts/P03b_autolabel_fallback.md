# P03b — FALLBACK: auto-label the images (run ONLY if P03 said labels are missing)
**Day 1 · agent ≈ 1 h (+ 20–40 min CPU) · human ≈ 10 min · Needs: P02 · Model: strongest**
Skip this prompt when `data/yolo/labels/{train,val,test}` already hold label files for (almost) every image.

## Goal
Every image in `data/yolo/images/{train,val,test}` gets a YOLO label file made by an open-vocabulary detector
(YOLO-World), the human spot-checks a contact sheet, and P03 can run. The report states honestly:
"labels generated automatically with YOLO-World and spot-checked; not hand-labelled".

## Read first
`docs/11_DATA_SOURCES.md` §0 and §2 · `.agents/rules/02-frozen-rules.md` (class ids) · `docs/INVENTORY.md`

## Build
1. `ai-service/training/autolabel_yoloworld.py` (venv python):
   - `from ultralytics import YOLOWorld`; model `yolov8s-worldv2.pt` (Ultralytics downloads it once into the working
     folder; it may also install its CLIP package - allowed for this prompt only, record it in the log);
   - `model.set_classes(["pothole", "garbage pile", "flooded road", "road crack"])` → ids 0..3 in this FROZEN order
     (0 Pothole, 1 Garbage Accumulation, 2 Waterlogging, 3 Road Damage);
   - for each image WITHOUT a label file: `predict(imgsz=640, conf=0.25, iou=0.5, device="cpu")`, keep boxes,
     write `labels/<split>/<stem>.txt` (`cls cx cy w h`, normalised, 6 decimals); no box → empty file (background);
   - never overwrite an existing label file; log every written file into `data/yolo/autolabel_log.csv`
     (split, image, boxes, classes, max_conf);
   - if the image folder name or the old dataset folder tells the class (e.g. `waterlogging_split`), keep only boxes of
     that class for that image and record `folder_hint` in the log (reduces wrong classes);
   - `--limit N` and `--split` options for a quick trial.
2. `ai-service/training/contact_sheet.py`: picks 40 random auto-labelled images (fixed seed), draws the boxes with
   class names, writes 4 sheets of 10 images to `docs/screenshots/P03b_sheet_<n>.jpg`.
3. Trial: `--limit 20`, look at one sheet yourself (open the image), fix obvious bugs; then the full run.
4. Run `prepare_mvp_dataset.py` (as in P03 step 2) on the result.

## Tests
`ai-service/tests/unit/test_autolabel.py`: label line format, class-id mapping order, existing label never
overwritten (use a temp folder and a fake predictor).

## Verify (agent)
counts of written labels per split and per class · `prepare_mvp_dataset.py` exit code · the 4 contact sheets exist.

## Human step
Open the 4 files `docs/screenshots/P03b_sheet_1.jpg` … `_4.jpg`.

## Ask the human (yes/no)
- Q1. Are most boxes (≈ 7 of 10 or better) on the right object with the right class name?
- Q2. Continue with these labels (yes) - or stop and train only on the images that already had labels (no)?

## Done when
labels written · contact sheets checked · answers recorded (a "no" to Q1: write the problem classes into the
log and ask whether to raise `conf` to 0.35 and run again - once).

## Next
`/run-prompt P03` again (dataset check + Kaggle package).
