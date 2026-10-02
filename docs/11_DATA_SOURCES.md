# 11 — Data: what is needed, where it comes from, how to prepare it

Checked on 2026-09-30. Licences matter: record every source in `data/yolo/DATASET_CARD.md` and in the final report.

## 0. 7-DAY MVP MODE (1–7 Oct 2026): existing images only
There is no time to collect or label new photos, so the MVP uses **only the data already in the repo**. Sections 1–6 below describe the full (Phase 2) plan.
- **YOLO:** the existing dataset `data/yolo` — `images/{train,val,test}` + `labels/…` (2,708 / 351 / 339 = 3,398 images, 4 FROZEN classes; garbage 135 and waterlogging 441 images are the weak classes). Do not re-split, relabel or add images.
  1. On the laptop: `ai-service\.venv\Scripts\python ai-service\training\prepare_mvp_dataset.py --root data\yolo --out-dir data\yolo\mvp` → checks every label (class 0–3, box inside the image), reports identical images shared by train and val/test (those train copies are left out) and writes `train_mvp.txt` (garbage images ×3, waterlogging ×2) + `data_mvp.yaml` + `dataset_report.json`. Fix any label problem it prints (exit code 1) before training.
  2. Kaggle (prompt P03): `scripts\dev\make-kaggle-package.ps1` builds `kaggle_upload\civicbrain-yolo.zip` (`yolo/images`, `yolo/labels`, `yolo/data.yaml` + the training scripts and `kaggle_train_mvp.ipynb`; never `raw/` or `backup_*`). Human: upload it as a private Kaggle dataset, import the notebook, add the dataset, GPU + Internet on (phone-verified account), run cells 1–4 (setup, dataset search, `prepare_mvp_dataset.py`, 3-epoch timing), then "Save Version → Save & Run All (Commit)": the committed run trains YOLOv8s (640 px, up to 120 epochs, early stop 25, `cls_pw=0.5`, seed 42), evaluates on the test split, exports ONNX and writes `civicbrain_yolo_outputs.zip`.
  3. Human downloads `civicbrain_yolo_outputs.zip` into `kaggle_download\`; the agent runs `ai-service\training\install_kaggle_model.py --check` (prompt P08): SHA-256 check → `ai-service/models/yolov8s_civicbrain.onnx` + `MANIFEST.json` entry, metrics + dataset report + plots → `docs/reports/`. If time is short, train `--model yolov8n.pt` (faster, less accurate).
  4. Report the metrics honestly: "measured on the existing test split (339 images), not on a Talegaon field test set". Expect weaker garbage/waterlogging numbers; YOLO is supporting evidence — the citizen's category and the text classifier stay primary, and the officer reviews.
- **Text classifier:** train on `data/complaints/synthetic_complaints_500.csv` + `kit_authored_train.csv` (160 kit-written English/Hinglish/Roman-Marathi sentences); sanity check on `sanity_test_mvp.csv` (40 other kit-written sentences). Labels and limits: `data/complaints/README.md`. Members may add real sentences in `real_test_team.csv` (same columns).
- **Demo photos (not training):** on Day 3 take 20–30 photos of real potholes/garbage near the college with the app itself, only for testing and the live demo.
- **Models to download once:** `all-MiniLM-L6-v2` (duplicates, FROZEN) - `ai-service\training\download_models.py` (agent, P09). Not needed in the MVP: YuNet (no blur), OSRM map (`ROUTING_MODE=haversine`).
- **Rates:** PWD SSR rates stay empty → estimates show "rate not configured" and use the Step 10 model cost (honest).

## 1. What the project needs (checklist)
| # | Data | Status | Source | Phase |
|---|---|---|---|---|
| 1 | TDMC boundary, 23 wards, 1,113 roads, 25 POIs | ✅ have (cleaned wards: `gis/tdmc_wards_clean_v2.geojson`) | Team GIS work (QGIS/OSM) | P1 review of 4 large disputed areas |
| 2 | 500 synthetic complaints + Step 10/11/12 outputs | ✅ have (DB + CSVs) — re-run Steps 10/11/13 on DB data | Team | P1 |
| 3 | YOLO images (4 classes) | ⚠ have 3,398; garbage (135 img) and waterlogging (441 img) weak; 0 local photos | §2 | P2 |
| 4 | Real complaint texts (multilingual) | ❌ need 240–400 | §3 | P2 |
| 5 | Maharashtra PWD SSR 2022-23 rates for patch mix, tack coat, labour, equipment | ❌ need (rates blank in DB) | pwd.maharashtra.gov.in → State Schedule of Rates 2022-2023 | P6/P11 (admin rates page) |
| 6 | Ward population (for Step 11 Ipop) | ✅ have `data/priority/official_ward_population.csv` | Team | — |
| 7 | OSM road network for routing | ❌ download | §4 | P8 |
| 8 | Field measurements (tape) for 20–30 potholes, 5–10 garbage piles | ❌ collect | §5 | P11 |
| 9 | Test fixtures (images, fake camera video) | ❌ create | §6 | P3–P6 |
| 10 | Face detector for blurring | ❌ download | opencv_zoo `face_detection_yunet_2023mar.onnx` (github.com/opencv/opencv_zoo) | P7 |
| 11 | Sentence embedding model | ❌ download once | Hugging Face `sentence-transformers/all-MiniLM-L6-v2` (FROZEN Step 12) | P6 |

## 2. YOLO dataset v2 (4 frozen classes)
### 2.1 Sources
| Source | Use | Licence | Link |
|---|---|---|---|
| RDD2022 official — **India** subset (7,706 train images, PASCAL VOC XML) | Pothole (D40), Road Damage (D00, D10, D20); undamaged road images as 0–10 % backgrounds | **CC BY-SA 4.0** (the Roboflow copy says CC BY 4.0 — the upstream licence wins) | github.com/sekilab/RoadDamageDetector → figshare "RDD2022" (India zip ≈ 502 MB); cite Arya et al., Geoscience Data Journal 11(4), 2024 |
| Current Roboflow RDD2022-India copy (2,822 img) | already in `data/yolo` | treat as CC BY-SA 4.0 | universe.roboflow.com (project rdd2022-india) |
| Roboflow "garbagepile" (135 img) | Garbage Accumulation | CC BY 4.0 | already in `data/yolo` |
| GINI / SpotGarbage (~2,400 web images, boxes on ~1,496) | Garbage Accumulation (train only) | unclear (review says CC0, repo states none) → academic use with citation, **do not redistribute** | github.com/spotgarbage/spotgarbage-GINI |
| Roboflow "water-logging" (199 img) | Waterlogging | CC BY 4.0 | universe.roboflow.com/water-logging/water-logging |
| Current 441 waterlogging (from masks) | Waterlogging | probably "Image Dataset for Roadway Flooding" (Mendeley t395bwcvbw) — **confirm licence on the page and record it** | data.mendeley.com/datasets/t395bwcvbw/1 |
| TACO | not recommended (single litter items) | CC BY 4.0 (Zenodo) | zenodo.org/records/3354286 |
| BharatPotHole (>7,000 Indian dashcam frames) | optional extra potholes | licence not stated → only if the authors confirm | kaggle.com/datasets/surbhisaswatimohanty/bharatpothole |
| **Talegaon photos (team)** | all classes, especially garbage + waterlogging; the local test set | owned by the team; get consent if people are recognisable; blur faces/plates before publishing | collect (§2.2) |

### 2.2 Collecting Talegaon photos (the most important data)
- Targets: ≥ 150 garbage heaps, ≥ 150 waterlogging, ≥ 100 potholes, ≥ 100 road-damage (cracks), ≥ 100 no-defect street photos. Spread over ≥ 15 wards, different times of day, dry and wet days (waterlogging: monsoon/after rain), phone held 45–70° down from ~1.4 m (the app's capture protocol), plus ~30 photos with an A4 sheet next to the defect (Tier A validation).
- Use the CivicBrain capture page itself once P4 works (GPS + tilt saved) or the phone camera with location on.
- **No leakage:** run `imagededup` (Apache-2.0) to remove near-duplicates; split by street/session (never random frames from one walk into train and test); keep a **frozen Talegaon test set** (≥ 30 per class) that is never used for training or tuning.
- Labelling: **Label Studio** (Apache-2.0, local `pip install label-studio`) or **CVAT** (self-hosted, MIT). Export YOLO format. Two people label, a third reviews 10 % (write the class definitions from `data/yolo/class_definition.csv` on the labelling page). Ultralytics HUB closed on 31 Jul 2026; do not plan on it.

### 2.3 Building dataset v2
Script `ai-service/training/build_dataset_v2.py`: convert RDD VOC → YOLO with the class map; merge sources; drop images with no mapped class except the chosen backgrounds (≤ 10 %); dedupe; group-aware split 70/15/15; write the images/labels to git-ignored `data/yolo_v2/{images,labels}/{train,val,test}` and the two small files that ARE committed to `data/yolo/`: `data_v2.yaml` (`nc: 4`, names in FROZEN order, `path:` pointing at `../yolo_v2`) and `DATASET_CARD.md` (counts per class/source/split, licences, citations). Oversample garbage/waterlogging images in the **train list only** (e.g. ×2) — `copy_paste` augmentation does not apply to plain detection.

### 2.4 Training (Kaggle notebook, GPU T4/P100; ≈ 30 GPU-h/week — check your quota panel)
```python
from ultralytics import YOLO
model = YOLO("yolov8s.pt")                     # spec: YOLOv8. Optional ablation: yolo26s.pt
model.train(data="data_v2.yaml", epochs=200, patience=40, imgsz=640, batch=-1,
            seed=42, deterministic=True, optimizer="auto", cos_lr=True,
            mosaic=1.0, close_mosaic=10, mixup=0.1, cls_pw=0.0,   # ablation cls_pw=0.5/1.0
            save_period=10, project="/kaggle/working/runs", name="v8s_640_seed42", plots=True)
m = YOLO("/kaggle/working/runs/v8s_640_seed42/weights/best.pt")
m.val(data="data_v2.yaml", split="test")          # report these numbers
m.export(format="onnx", imgsz=640)                # used by the worker on CPU (OpenVINO optional)
```
Time a 3-epoch run first (rough expectation: 1–2 min/epoch for ~5k images). Use "Save & Run All" so training continues without the browser; copy `runs/` out at the end. Also train YOLOv8n for a speed comparison.
**Report:** P, R, mAP50, mAP50-95 overall and per class on (a) the mixed test split and (b) the Talegaon test set; confusion matrix; PR curves; CPU latency measured inside the worker. Lead with mAP50 for garbage/waterlogging (fuzzy edges). Never report validation-set numbers as final.

### 2.5 Licence note (AGPL-3.0)
Ultralytics code and weights trained with it are AGPL-3.0: fine for this academic project if the CivicBrain source is public (GitHub public repo). A real council deployment must either publish its full source or buy an Ultralytics Enterprise licence; Apache-2.0 alternative: RF-DETR. Mention this in the report.

## 3. Complaint text data (classifier)
- No open labelled Indian civic-complaint text dataset exists. Collect **240–400 real complaints**: team members, friends and family write what they would really type (English, Marathi, Hindi, Hinglish/Romanised Marathi), 30–50 per category; label with the 8 categories; two labellers, disagreements resolved. This is the **test set** (plus a small part for training if needed).
- Augment training (never testing) with the 500 synthetic complaints and seed phrases derived from NYC 311 category names (data.cityofnewyork.us, 311 Service Requests) mapped to the 8 categories.
- Models: baseline TF-IDF (word 1–2 + char 2–5) + LogisticRegression; compare with `intfloat/multilingual-e5-small` (MIT) or `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (Apache-2.0) embeddings + LogisticRegression; report macro-F1 on the real test set; ship the better one that runs < 50 ms on CPU.
- Duplicate detection stays on `all-MiniLM-L6-v2` (FROZEN); its weakness on Marathi text is a stated limitation (officer can merge manually).

## 4. Road network for OSRM
- Easiest small file: **BBBike custom extract** (extract.bbbike.org, free) for the box **73.60 E – 73.77 E, 18.65 N – 18.80 N** (the TDMC boundary is 73.654–73.716 E, 18.698–18.752 N, plus about 5 km margin), format "Protocolbuffer (PBF)"; small, preprocesses in seconds on an 8 GB laptop.
- Alternative: Geofabrik `asia/india/western-zone-latest.osm.pbf` (≈ 210 MB; confirm Talegaon is inside via the `.poly` file) — preprocess once on a 16 GB laptop and share the `.osrm*` files.
- Steps (`infra/osrm/README.md`): `osrm-extract -p /opt/car.lua` → `osrm-partition` → `osrm-customize` → `osrm-routed --algorithm mld`. Check: route from depot D001 (18.729411, 73.699489) to 18.7440, 73.6760 returns `"code":"Ok"`. Record the OSM data date in the plan revisions.

## 5. Field validation data (P11)
For each measured defect: photo through the app (with and without A4), tape length/width/depth (cm), GPS, date, who measured. Store in `data/field_validation/measurements.csv` + photos; the evaluation script compares AI vs tape per tier (MAPE, bias) and updates per-class correction factors.

## 6. Test fixtures
`tests/fixtures/images/` at the **repo root** (shared by backend, AI and Playwright tests): one clear photo per class (from the Talegaon test set, faces/plates blurred), `no_defect.jpg`, `a4_pothole.jpg` with its tape values in `a4_pothole.json`, `tiny_200px.jpg`, `not_an_image.jpg`, `huge_50mp.png` (generate with a script, do not commit if > 20 MB — generate in the test), and `camera.y4m` for the Playwright fake camera (git-ignored because it is large; each laptop and the nightly CI job generate it): `ffmpeg -y -loop 1 -i pothole_1.jpg -t 2 -r 5 -pix_fmt yuv420p -vf scale=1280:720 camera.y4m` (≈ 14 MB; Chrome loops it).
