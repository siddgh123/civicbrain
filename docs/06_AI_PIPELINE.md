# 06 — AI Pipeline (Python worker in `ai-service/`)

All numbers marked **FROZEN** come from the validated research Steps 9/11/12 and must not change. Numbers marked **ASSUMPTION** are project defaults: keep them in `ai-service/app/config.py`, show them in the UI as assumptions, and replace them when field data exists.

**7-day MVP (until 7 Oct 2026, `docs/09_BUILD_PLAN_7DAY.md`):** YOLO weights are trained on the existing images only (`11_DATA_SOURCES.md` §0); measurement uses Tier B/C (Tier A later — the `a4_in_frame` flag is stored); OPTIMIZE_PLAN uses `ROUTING_MODE=haversine` (travel minutes = straight-line km × 1.3 / 20 km/h × 60, straight route segments) instead of OSRM tables/routes; BLUR_IMAGE and ANALYZE_IMAGE are not built; authenticity uses the checks listed in the MVP scope. Everything else below applies unchanged.

## 1. Worker loop
- `python -m worker.run` (one process per laptop is enough). Every 2 s: `SELECT * FROM fn_claim_jobs(:worker_id, ARRAY['ANALYZE_COMPLAINT','ANALYZE_IMAGE','OPTIMIZE_PLAN','BLUR_IMAGE'], 1)`. Dispatch by `job_type`; on success `fn_finish_job(id, true)`; on exception `fn_finish_job(id, false, '<ExceptionType>: <message>')` (retries after 1 and 5 min; the 3rd failure → DEAD because `max_attempts = 3` — visible on the admin jobs page). When an ANALYZE_COMPLAINT job ends DEAD the worker sets `complaints.ai_status = 'FAILED'` (the complaint stays SUBMITTED and appears in the officer's "Needs review" tab with "Re-run analysis" and "Accept"). Every 5 min: `fn_requeue_stale_jobs('15 minutes')`. Daily 02:00 IST: recompute priority (wait-time factor changes) for all open non-synthetic complaints.
- Graceful shutdown on Ctrl+C: finish the current job, then exit. Each job has a hard timeout (analyze 120 s, optimize 60 s, blur 60 s).
- Each job writes its results in **one DB transaction** and is **idempotent**: before inserting AI rows for a complaint it deletes that complaint's rows from the same `model_name`/`model_version` (or sets `is_current=false`). Running a job twice gives the same end state.
- Status changes by the worker: `set_config('civicbrain.actor_role','SYSTEM', true)` then UPDATE. Only SUBMITTED → VERIFIED and SUBMITTED → MERGED. Never REJECTED (officer decides).
- **Job inputs:** jobs made by DB triggers have `payload = {}` — the worker reads the complaint (`ref_id` = complaint_id) or the run's `optimizer_runs.request` (`ref_id` = run_id; `{mode:'GENERATE'|'RETIME', plannedDate, workTypeCode, wardNumbers?, complaintIds?, actionPlanId?, items?, requestId}`). Only BLUR_IMAGE (rectangles) and ANALYZE_IMAGE use `jobs.payload`; the backend inserts those rows itself.
- **Re-analysis** (officer "Re-run analysis" → backend inserts an ANALYZE_COMPLAINT job with `ON CONFLICT DO NOTHING`): on a SUBMITTED complaint it runs normally; on any other status it rewrites the AI rows only and never changes the status — a DUPLICATE result is stored as UNCERTAIN (`duplicate_review_required = true`) for the officer. An estimate with `estimate_source = OFFICER_OVERRIDE` stays current.

## 2. ANALYZE_COMPLAINT (order matters)
| Step | Output tables | Failure behaviour |
|---|---|---|
| 1 Load complaint + image, compute `phash` (imagehash.phash, 64-bit → signed int64), `width_px/height_px` | complaint_images | image missing/corrupt → mark image FAILED, continue with text-only steps, authenticity WARN |
| 2 Authenticity checks (all except CATEGORY_IMAGE_MISMATCH) | authenticity_checks | never fails the job; each check independent |
| 3 Text classification | ai_classifications (model_type TEXT) | model missing → job fails (config error) |
| 4 YOLO detection (only if category has `yolo_class_id`) | yolo_detections, ai_classifications (IMAGE) | no detection → note, measurement Tier C |
| 4b CATEGORY_IMAGE_MISMATCH check, then final authenticity score/status | authenticity_checks, complaints.authenticity_* | — |
| 4c Image quality score (§2.6) | complaint_images.quality_score | image missing → NULL |
| 5 Measurement | defect_measurements (source AI) | never fails: falls back to Tier C |
| 6 Estimate | resource_estimates (+materials, +equipment), is_current | missing rates → amounts NULL, cost from Step 10 model |
| 7 Duplicates | duplicate_relation, complaints.duplicate_* | embedding model missing → job fails |
| 8 Priority | priority_assessments (is_current), complaints.current_priority_* | factor data missing → job fails |
| 9 Status | complaints.status VERIFIED or MERGED, ai_status COMPLETED | — |

### 2.1 Authenticity score (start 100, clamp 0–100; < 40 → FLAGGED, else PASSED)
| Check code | PASS | WARN | FAIL |
|---|---|---|---|
| CAPTURE_SESSION | valid, used once | — | (API already rejects) |
| GPS_ACCURACY | ≤ 50 m | 50–150 m: −10 | (API rejects > 150 m) |
| GPS_FRESHNESS | captured ≤ 2 min before submit | 2–10 min: −10 | (API rejects > 10 min) |
| BOUNDARY | inside, > 50 m from edge | within 50 m of edge: −5 | (API rejects outside) |
| IMAGE_REUSE_SHA256 | no other image with same hash | — | same hash on another complaint: −50 |
| IMAGE_REUSE_PHASH | nothing ≤ 10 bits | 5–10 bits, other complaint > 300 m away or > 7 days apart: −15 | ≤ 4 bits, other complaint > 300 m away or > 7 days apart: −40 (≤ 4 bits nearby & recent = duplicate hint, PASS) |
| SUBMISSION_RATE | ≤ 3 in 24 h | 4–5 in 24 h: −10 | — |
| IMPOSSIBLE_TRAVEL | ≤ 150 km/h since user's previous complaint | > 150 km/h: −20 | — |
| ACCOUNT_TRUST | users.trust_score 30–100 (> 70: +5) | < 30: −15 | — |
| CATEGORY_IMAGE_MISMATCH | detection of the category's class ≥ 0.4 conf, or category has no YOLO class | YOLO finds only other classes ≥ 0.5: −10 | — |
Trust score updates (by the backend): officer rejects as fake −20; citizen confirms fixed +5; clamp 0–100.

### 2.2 Text classification
TF-IDF word 1–2-grams + char 2–5-grams (`char_wb`, sublinear tf) → LogisticRegression (class_weight=balanced, C tuned by 5-fold CV, `random_state=42`) over the 8 categories. **MVP data:** train on `data/complaints/synthetic_complaints_500.csv` (title + ". " + description) + `data/complaints/kit_authored_train.csv`; report accuracy and macro-F1 on `data/complaints/sanity_test_mvp.csv` (≈ 0.90 accuracy measured with C = 5; label it "sanity check on 40 kit-written sentences"). Phase 2: the real multilingual set (`11_DATA_SOURCES.md` §3). Save `models/text_clf.joblib` (+ SHA-256 in MANIFEST) + `models/text_clf_metrics.json` and a committed copy `docs/reports/text_clf_metrics.json`. Inference: top-3 with probabilities; if top-1 ≠ citizen's category with p ≥ 0.70 → `is_accepted=false` and a "possible wrong category" badge for the officer. The citizen's category is never changed automatically.

### 2.3 YOLO
Model `models/yolov8s_civicbrain.onnx` (trained in P2, classes FROZEN 0 Pothole, 1 Garbage Accumulation, 2 Waterlogging, 3 Road Damage), loaded once at worker start with Ultralytics `YOLO(path, task='detect')`; `imgsz=640, conf=0.25, iou=0.5, device='cpu'`. Store all boxes (pixels, `model_version` = file SHA-256 first 12 chars). Primary detection = highest confidence box of the category's class.

### 2.4 Measurement (FR-23)
1. **Shape in pixels:** if a segmentation model exists (`yolov8n_seg_civicbrain.onnx`, P11) use its mask; else approximate from the box: ellipse area π/4·w·h (Pothole, Waterlogging, Garbage), long side as length (Road Damage).
2. **Scale tier:**
   - **Tier A (HIGH, ±10 % ASSUMPTION):** A4 sheet found (OpenCV: Canny → contours → 4-vertex convex polygon, area ≥ 1 % of image, rectified aspect 1.414 ± 0.15) → homography to 210 × 297 mm → project shape → metres.
   - **Tier B (MEDIUM):** pitch known and camera depression θ = 90° − β ≥ 30°. Focal length f_px = f35 × √(W² + H²) / 43.27 with f35 = 26 mm, the typical phone main camera (ASSUMPTION; browsers do not reliably expose the phone model, so there is no per-device table); camera height h = 1.4 m (ASSUMPTION). Ray below horizon φ(v) = θ + atan((v − cy)/f_px); ground distance Z = h / tan φ; slant R = h / sin φ; lateral X = (u − cx)·R/f_px. Project the shape polygon → shapely polygon → area, min-rotated-rectangle length/width. Error band from 200 Monte-Carlo samples (h ~ N(1.4, 0.15), θ ~ N(θ, 2°), f35 ~ N(26, 2)) → P10–P90.
   - **Tier C (LOW, ±60 %):** class priors (ASSUMPTION): Pothole 0.6 × 0.4 m, Road Damage 2.0 m crack, Garbage base 1.5 × 1.0 m, Waterlogging 4 × 3 m.
   - Tier A is tried only when `complaints.a4_in_frame = true` (V5); if no sheet is found, fall back to B/C and note it in `assumptions`.
3. **Depth (never from the photo):** from `complaints.depth_answer` (V5). Pothole SHALLOW → 25 mm (IRC:82 small), FINGER → 50 mm (medium), DEEP → 75 mm (large, ASSUMPTION); Waterlogging SHALLOW (below ankle) 0.08 m, FINGER (below knee) 0.30 m, DEEP 0.50 m (ASSUMPTION). NULL answer → the class prior's depth (Tier C). `depth_source = ASSUMED_FROM_SEVERITY_CLASS`; `severity_class`: SHALLOW → SMALL, FINGER → MEDIUM, DEEP → LARGE.
4. Save `defect_measurements` (source `AI`) with `method` and `confidence` by tier — A: `REFERENCE_OBJECT`, 0.9 · B: `GROUND_PLANE_HOMOGRAPHY`, 0.6 · C: `CATEGORY_DEFAULT`, 0.3 — plus `error_band_pct` and every assumption in `assumptions` JSON (including `"tier": "A"|"B"|"C"`, shown in the UI). Contractor tape values are saved as source `CONTRACTOR`, method `MANUAL_TAPE`, `depth_source = MEASURED_ON_SITE`.

### 2.5 Estimate (FR-24)
- **Pothole:** cut area A = (L + 2·0.15)(W + 2·0.15) m²; V = A × depth; hot mix t = V × 2.35 × 1.05 (density secondary source, confirm); tack coat kg = 0.25 × A (IRC:82: 2.5 kg/10 m²); equipment: plate_compactor 1 day, joint_cutting_machine 1 day.
- **Road damage:** crack length L; sealant litres = L × rate (rate not sourced → NULL, officer fills); wide cracking (area > 2 m²) → premix per IRC:82 (6.8 kg binder + 0.06 m³ sand per 10 m²).
- **Garbage:** V = cone on base ellipse (a, b = half dims), h = min(a,b)·tan 35° (ASSUMPTION); mass t = V × 0.45 (CPHEEO 0.37–0.54 range midpoint); trips = ceil(V / 5.5) on `truck_5_5_cum_per_10_mt`.
- **Waterlogging / Water leakage / Blocked drain / Streetlight:** labour + equipment from category defaults (drain_cleaning_tools, water_leakage_repair_tools, electrical_maintenance_tools) — no material takeoff.
- **Workers & duration:** Step 10 XGBoost models (`data/resources/models/*.json`, via the logic in `scripts/resources/predict_resource_estimate.py`).
- **Cost:** material Σ qty × rate + equipment Σ qty × rate + labour workers × hours × `LABOUR_RATE_PER_HOUR` (config, NULL until set). If any rate is NULL, `total_cost_expected` = Step 10 model cost and `rate_reference` says "Step 10 synthetic model; SSR rates not configured". Min/max = expected × (1 ∓ error band).
- **`estimate_source`:** worker `RULE_BASED` when every rate is set, else `AI_MODEL` (Step 10 model cost); contractor inspection → `CONTRACTOR_INSPECTION`; officer override → `OFFICER_OVERRIDE` (stays current until the officer changes it).

### 2.6 Duplicates (FROZEN Step 12)
Candidates: `fn_duplicate_candidates(id)` (300 m, previous 7 days, masters only). Text = title + " " + description, embedding `sentence-transformers/all-MiniLM-L6-v2` (cosine). distance_score = 1 − d/300; recency_score = 1 − hours/168; score = 0.70·text + 0.20·distance + 0.10·recency. ≥ 0.59 DUPLICATE, 0.55–0.59 UNCERTAIN (review, never auto-merge), else NOT_DUPLICATE. Best DUPLICATE candidate → the new complaint becomes MERGED with `master_complaint_id` = candidate's master (the earlier complaint). If two different masters qualify → UNCERTAIN (manual). If the master is COMPLETED or CLOSED (maybe a new defect at the same place) → UNCERTAIN, the officer decides. Write every scored pair to `duplicate_relation` (unique pair index; upsert).
**Best photo ("keep the better one", FR-22):** `complaint_images.quality_score` (V5) = 0.5 × sharpness + 0.3 × primary detection confidence (0 if none) + 0.2 × min(1, pixels / 2 MP), where sharpness = min(1, variance of the Laplacian of the 640-px grey copy / 300) (ASSUMPTION scale). The display photo of a master = the CITIZEN_EVIDENCE image with the highest `quality_score` among the master and its MERGED children (ties → earliest); APIs return it as `displayImageId`. Test: a sharp fixture outranks its blurred copy.

### 2.7 Priority (FROZEN Step 11)
Port `scripts/priority/priority_engine.py` and its rule CSVs (`data/priority/*.csv`) into `pipeline/priority.py` unchanged in behaviour. P = 0.25 S + 0.15 Ipop + 0.15 Rloc + 0.10 F + 0.10 Twait + 0.15 Iinfra + 0.10 H; levels LOW < 25 ≤ MEDIUM < 50 ≤ HIGH < 75 ≤ CRITICAL. Store all 7 factors (`severity_score`=S, `impact_score`=Ipop, `location_score`=Rloc, `urgency_score`=Twait, `frequency_score`, `infrastructure_score`, `historical_risk_score`) + `explanation` JSON (each factor's input and rule). **Golden test:** recompute `data/priority/priority_factor_dataset.csv` → 0 mismatches against `priority_scores.csv`.

### 2.8 ANALYZE_IMAGE (contractor photos, FR-42)
The backend inserts `jobs('ANALYZE_IMAGE', ref_id = image_id)` for every INSPECTION or COMPLETION_PROOF image it stores. The worker computes SHA-256 + pHash as in step 1, runs `fn_similar_images(image_id, 10)` and writes `authenticity_checks` rows with `image_id` set: `IMAGE_REUSE_SHA256` FAIL if any earlier image has the same SHA-256; `IMAGE_REUSE_PHASH` FAIL if ≤ 4 bits, WARN if 5–10 bits, against any earlier image — the same complaint's citizen photo included (a "proof" that is the before-photo). It never changes a status; the officer sees a reuse badge on the completion.

## 3. OPTIMIZE_PLAN (FR-33)
1. Read the run request (`optimizer_runs.request`). Select complaints: status VERIFIED or REOPENED, requested work type, requested wards or IDs, `current_action_plan_id IS NULL` (the V5 trigger clears it when a complaint is reopened or pulled out of a plan). Exclude any without a current resource estimate (→ dropped "no estimate"). The synthetic demo complaints are SUBMITTED and never analysed, so they are never selected.
2. Group: `fn_cluster_jobs(ids, 2000, 10)` (FROZEN rule: same work type, ≤ 2 km, ≤ 10 jobs; deterministic).
3. Per group: OSRM `table` for depot D001 + jobs (`annotations=duration,distance`, `fallback_speed=20`), timeout 10 s, 2 retries; OSRM down → run FAILED with "Routing service unavailable".
4. OR-Tools RoutingModel, one vehicle (one crew-day), time dimension horizon 540 min (08:00–17:00), service time = estimate hours × 60, each job `AddDisjunction([node], 100000 + priority_score × 1000)`, first solution PATH_CHEAPEST_ARC, metaheuristic GUIDED_LOCAL_SEARCH, `time_limit.seconds = 10`. Job > 540 min alone → dropped "Work longer than one shift".
5. Route geometry: OSRM `route` depot → stops → depot, `geometries=geojson&overview=full`.
6. Write one DRAFT `action_plans` per group with ≥ 1 job (plan_code `AP-YYYYMMDD-<WT>-NNN`), items with planned start/end and travel, totals (workers = max item workers), revision 1 snapshot (includes matrix hash, OSRM data date, solver params). Dropped jobs + reasons → `optimizer_runs.dropped_jobs`. Run SUCCEEDED.
7. **RETIME** (`optimizer_runs.request.mode = 'RETIME'` with `actionPlanId` and the officer's `items` order, after `PUT /officer/plans/{id}`): keep the officer's order, recompute times/travel/route/totals, new revision.
8. `action_plan_items.planned_start/end` are `timestamp without time zone` holding Asia/Kolkata local time (map to `LocalDateTime`); every `timestamptz` column is UTC.

## 4. BLUR_IMAGE (FR-37)
Enqueued by the backend (`jobs('BLUR_IMAGE', ref_id = image_id, payload = {rects:[…]})`): automatically (faces only, empty `rects`) when a CITIZEN_EVIDENCE image is stored and the owner has a current PUBLIC_PHOTO consent, and again when the officer sends rectangles (`POST /officer/images/{id}/blur`). Faces: OpenCV YuNet (`face_detection_yunet_2023mar.onnx`) → Gaussian blur; rectangles from the payload (number plates, anything else) → blur. Output JPEG to `photos-public/`, set `blurred_storage_key`. Approval (`public_approved = true`) is done by the officer through the API only after previewing the blurred copy (409 `BLUR_NOT_READY` before that).

## 5. Model files (`ai-service/models/`, git-ignored, SHA-256 listed in `models/MANIFEST.json`)
`yolov8s_civicbrain.onnx` (P2) · `text_clf.joblib` (P2) · `all-MiniLM-L6-v2/` (download once from Hugging Face, then offline) · `face_detection_yunet_2023mar.onnx` (opencv_zoo) · optional `yolov8n_seg_civicbrain.onnx` (P11). Worker refuses to start if a required file or its checksum is missing (clear message naming the file). "Required" = the YOLO weights, the text classifier and MiniLM from P6; the YuNet file only once BLUR_IMAGE is enabled (P7, setting `BLUR_ENABLED=true`).
