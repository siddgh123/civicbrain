# Test fixtures - images (shared by backend, AI and Playwright tests)

Made by `ai-service/training/make_test_fixtures.py` (P03) from the project dataset `data/yolo` (TEST split, never
used for training). The dataset files were copied, not changed. Do not edit these files by hand: the recorded label
lines are the reference for a later golden test (docs/08_TEST_PLAN.md: IoU ≥ 0.5, Phase 2).

**P08 (MVP) YOLO smoke test** (`ai-service/tests/unit/test_detect.py`, `@pytest.mark.models`): `pothole_1.jpg` gives at
least one Pothole box with conf ≥ 0.25, and all four class fixtures run without error. Measured on 2026-10-03 with
`yolov8s_civicbrain.onnx` (sha256 `93af36422072…`, CPU, imgsz 640, conf 0.25, iou 0.5) - the real model numbers are
`docs/reports/yolo_metrics.json`, this is only a smoke test:

| Fixture | Boxes found | Best box of the own class vs the recorded box |
|---|---|---|
| `pothole_1.jpg` | Pothole 0.51, Pothole 0.43, Road Damage 0.26 | IoU 0.02: both Pothole boxes are small boxes **inside** the one large labelled patch (422, 506)-(715, 699); the Road Damage box covers that patch |
| `garbage_1.jpg` | Garbage Accumulation 0.66 | IoU 0.77 |
| `waterlogging_1.jpg` | Waterlogging 0.88 | IoU 0.96 |
| `road_damage_1.jpg` | Road Damage 0.53 | IoU 0.73 |

No fixture had to be replaced (the model detects its class on every one). For the Phase 2 golden test (IoU ≥ 0.5)
`pothole_1.jpg` would need a test image with a single, tightly labelled pothole.

| Fixture | Split | Original file | Source | Size (px) | Recorded box (`<name>.txt`, YOLO: class cx cy w h) | Box in px (x1, y1) - (x2, y2) |
|---|---|---|---|---|---|---|
| `pothole_1.jpg` | test | `India_002154_jpg.rf.b26b8c5792b894ab09bfe83b1734c073.jpg` | S1 | 720x720 | `0 0.7895833333333333 0.8368055555555556 0.40694444444444444 0.26805555555555555` | (422, 506) - (715, 699) |
| `garbage_1.jpg` | test | `IMG_5472_JPG.rf.4a4fd60e36d31b2014d3b2de28aef47e.jpg` | S3 | 640x640 | `1 0.460938 0.541667 0.921875 0.911458` | (0, 55) - (590, 638) |
| `waterlogging_1.jpg` | test | `image_101.jpg` | S2 | 512x384 | `2 0.500000 0.765625 1.000000 0.468750` | (0, 204) - (512, 384) |
| `road_damage_1.jpg` | test | `India_000130_jpg.rf.1858fd1e7e87a3bff9396d16f6889c47.jpg` | S1 | 720x720 | `3 0.41597222222222224 0.7479166666666667 0.5958333333333333 0.26805555555555555` | (85, 442) - (514, 635) |
| `tiny_200px.jpg` | - | centre crop (4:3) of `pothole_1.jpg`, resized to 200x150 | S1 | 200x150 | - | must be rejected: `IMAGE_TOO_SMALL` (< 320 px) |
| `not_an_image.jpg` | - | plain text with a `.jpg` name | kit | - | - | must be rejected by the magic-byte check |

Not here yet (docs/08_TEST_PLAN.md §2): `no_defect.jpg`, `a4_pothole.jpg` + `a4_pothole.json` (real photos, later
prompts), `huge_50mp.png` (generated inside its test, never committed), `camera.y4m` (generated, git-ignored).

## Licence
From the project dataset (`data/yolo`, sources and licences in `data/yolo/dataset_sources.csv`). Used here only as
test data; the photos are not Talegaon field photos. CC BY 4.0 attribution: the source links below.

| Source (`data/yolo/dataset_sources.csv`) | Licence |
|---|---|
| S1 RDD2022-India (https://universe.roboflow.com/prakhar-kpb1v/rdd2022-india-il8ju/dataset/5) | CC BY 4.0 |
| S2 Waterlogging Dataset (https://universe.roboflow.com/yolo-and-car-accident-detection-xaltb/waterlogging) | CC BY 4.0 |
| S3 GarbagePile (https://universe.roboflow.com/objectdetectiondemo-irh54/garbagepile/dataset/1) | CC BY 4.0 |

Attribution for `waterlogging_1.jpg`: "Waterlogging Dataset" by yolo and car accident detection (https://universe.roboflow.com/yolo-and-car-accident-detection-xaltb/waterlogging), licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Converted, not an unchanged copy: the project re-saved the downloaded `image_101.jpg` as JPEG (same 512x384 size, not cropped or resized; `scripts/yolo/convert_waterlogging_masks.py`) and made the box in `waterlogging_1.txt` from the dataset's segmentation mask.
