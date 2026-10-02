# P03 — Dataset check, test fixtures, Kaggle package (YOLO training starts)
**Day 1 (Thu 1 Oct, evening) · agent ≈ 30 min · human ≈ 30 min + upload time · Needs: P02 · Model: any**
Start this as early as possible: the Kaggle run trains for 2–4 h while P04–P07 are built.

## Goal
The existing images + labels are checked (labels valid, no train/test leakage), test fixtures for the AI tests are
copied, one zip is ready for Kaggle, and the human has started the committed training run on Kaggle.

## Read first
`docs/11_DATA_SOURCES.md` §0 · `ai-service/training/prepare_mvp_dataset.py` (docstring) · `ai-service/training/kaggle_train_mvp.ipynb`
(markdown cell) · `scripts/dev/make-kaggle-package.ps1` (header) · `docs/INVENTORY.md` (from P01) · `.agents/rules/02-frozen-rules.md`

## Build / do
1. **Labels present?** From `docs/INVENTORY.md`: if `data/yolo/labels/*` has (almost) no `.txt` files, STOP this prompt
   and tell the human: "Labels are missing - run `/run-prompt P03b` (auto-label fallback) first." Otherwise continue.
2. **Check:** `ai-service\.venv\Scripts\python.exe ai-service\training\prepare_mvp_dataset.py --root data\yolo --out-dir data\yolo\mvp`
   (exit 0 = ready, 1 = label problems, 2 = structure). Paste its summary into the log.
   - Exit 2 because of class names: if `data.yaml` lists the 4 classes with different spelling only, the script already
     accepts case/underscore differences. If the ids mean other classes: STOP and ask (FROZEN rule).
   - Exit 1 (label problems): if there are fewer than 30 bad lines, fix them in `data/yolo/labels` with a small Python
     script you write in `ai-service/training/fix_labels.py` that only removes invalid lines (first copies each file it
     changes to `data/yolo/backup_labels_P03/<split>/` - git-ignored - and prints what it removed); run it, then the check again. More than 30 → ask the human yes/no
     "train anyway (YOLO skips bad lines)?".
   - Copy `data/yolo/mvp/dataset_report.json` to `docs/reports/dataset_report_local.json` (commit it).
3. **Fixtures for the AI tests** (`docs/08_TEST_PLAN.md` §2): copy (Copy-Item, never move) one TEST-split image per class
   into `tests/fixtures/images/` as `pothole_1.jpg`, `garbage_1.jpg`, `waterlogging_1.jpg`, `road_damage_1.jpg`
   (pick images whose label file has exactly one box of that class; convert PNG to JPG with Pillow if needed), and save
   their label lines as `tests/fixtures/images/<name>.txt` (the "recorded box" for P08's golden test). Make `tiny_200px.jpg`
   (200×150) and `not_an_image.jpg` (text) with a short Pillow script. Write `tests/fixtures/images/README.md` (source split
   + original file name of each fixture; licence note: from the project dataset).
4. **Package:** `pwsh -NoProfile -File scripts\dev\make-kaggle-package.ps1` (add `-Force` if a zip exists).
5. Commit: fixtures, reports, `fix_labels.py` if made, log.

## Tests
`prepare_mvp_dataset.py` exit 0 (or the human said yes to "train anyway").

## Verify (agent)
- the check summary (images per split, boxes per class, leakage count, oversampled list size);
- `kaggle_upload\civicbrain-yolo.zip` exists, size in MB, file count;
- the 6 fixture files exist (`Get-ChildItem tests\fixtures\images`).

## Human step (≈ 30 min, browser)
1. kaggle.com → (Settings: phone number verified - needed for GPU) → **Create → New Dataset** → drop
   `C:\dev\civicbrain\kaggle_upload\civicbrain-yolo.zip` → title `civicbrain-yolo` → **Private** → Create. Wait until "Processing" ends.
2. **Create → New Notebook** → **File → Import Notebook** → choose `C:\dev\civicbrain\ai-service\training\kaggle_train_mvp.ipynb`.
3. Right panel: **Add Input** → Your Datasets → `civicbrain-yolo`. **Settings**: Accelerator **GPU T4 x2** (or P100), **Internet on**.
4. Run cells 1, 2, 3, 4 one after another (each ends with `OK`; cell 4 takes ≈ 10 min and prints minutes per epoch).
5. **Save Version** → **Save & Run All (Commit)** → Save. You may close the browser; training runs 2–4 h.
6. Tell the agent: the minutes per epoch from cell 4 and "committed".
If a cell fails: paste its last 20 lines into the chat; the agent tells you what to change.

## Ask the human (yes/no)
- Q1. Did cells 1–4 all end with `OK`?
- Q2. Does Kaggle show the new version as "Running" (Notebook → Versions)?

## Done when
dataset check passed · fixtures committed · zip built · Kaggle committed run running · answers yes.
Record the expected finish time (start + epochs × minutes, max 120 epochs) in the log - P08 needs the result.

## Next
`/run-prompt P04` — backend skeleton + Flyway + demo seed (≈ 2 h)
