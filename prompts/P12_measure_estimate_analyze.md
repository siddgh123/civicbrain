# P12 — Measurement, estimate, photo quality and the full ANALYZE_COMPLAINT job
**Day 4 (Sun 4 Oct) · agent ≈ 3 h · human 0 min · Needs: P08, P09, P10 · Model: strongest**

## Goal
The worker analyses every new complaint end to end in the order of 06 §2 (authenticity → classify → YOLO →
mismatch check → quality → measure → estimate → duplicates → priority → status) idempotently, and moves it to
VERIFIED or MERGED as SYSTEM. Smoke stage `analysis` passes (A VERIFIED, B MERGED into A, C VERIFIED).

## Read first
`docs/06_AI_PIPELINE.md` §1, §2 (table), §2.4, §2.5, §2.6 (best photo), §5 · `docs/03_DATABASE.md` §3 ·
`docs/INVENTORY.md` (Step 10 resource models present?) · `scripts/resources/predict_resource_estimate.py` and
`data/resources/models/*.json` if present · `tests/smoke/smoke_flow.py` (`stage_analysis`)

## Build
1. `pipeline/measure.py`: shape from the primary box (ellipse π/4·w·h for Pothole/Waterlogging/Garbage, long side for Road
   Damage); **Tier B** when pitch is known and camera depression θ = 90° − β ≥ 30° (f_px from f35 = 26 mm, h = 1.4 m,
   ground projection of the box polygon with shapely, area / length / width, 200 Monte-Carlo samples with a FIXED seed →
   P10–P90 band); **Tier C** class priors otherwise; Tier A is Phase 2 (the `a4_in_frame` flag is noted in `assumptions`);
   depth from `complaints.depth_answer` (06 §2.4 step 3); writes `defect_measurements` (source AI, method, confidence by tier,
   `error_band_pct`, `assumptions` incl. `"tier"`).
2. `pipeline/estimate.py`: 06 §2.5 (pothole cut area + hot mix + tack coat + equipment; road damage; garbage cone + trips;
   other categories labour/equipment defaults); workers & duration from the Step 10 models through the logic of
   `predict_resource_estimate.py` (if missing: category defaults as ASSUMPTION constants in `app/config.py`, flagged in
   `assumptions`); cost rules (any rate NULL → Step 10 model cost, `rate_reference` "Step 10 synthetic model; SSR rates not
   configured"; min/max = expected × (1 ∓ error band)); `estimate_source` RULE_BASED / AI_MODEL; `is_current` switch; an
   OFFICER_OVERRIDE estimate stays current.
3. Quality score (06 §2.6 "best photo") → `complaint_images.quality_score`.
4. `pipeline/analyze.py` orchestrator: exactly the step order and failure behaviour of the 06 §2 table, one transaction
   for the writes, delete-then-insert per complaint and model version, status change SUBMITTED → VERIFIED or MERGED with
   `set_system_actor`; re-analysis on other statuses rewrites AI rows only (DUPLICATE stored as UNCERTAIN); `ai_status`
   COMPLETED. Wire it as the `ANALYZE_COMPLAINT` handler (replacing the P02 placeholder). Log the time per step.
5. `REQUIRE_MODELS=true` now: the worker refuses to start without the YOLO, classifier and MiniLM files (06 §5).

## Tests (write first)
estimate worked example: 0.6 × 0.4 m medium pothole → cut area 0.63 m², ≈ 78 kg hot mix, ≈ 0.16 kg tack · Tier B maths with a
synthetic camera geometry (known answer) · Tier C when no pitch or θ < 30° · depth mapping per category · quality: a sharp
fixture outranks its blurred copy · integration (`civicbrain_test`): analyse a fixture complaint twice → identical rows
(idempotent), status VERIFIED, `ai_status` COMPLETED; a near duplicate → MERGED with `master_complaint_id`; DEAD job → FAILED.

## Verify (agent)
1. ruff + pytest in `ai-service`.
2. E2E smoke: `start-all.ps1 -Stop` → `seed-e2e.ps1 -MinAccounts 3` → `start-all.ps1 -E2E` →
   `ai-service\.venv\Scripts\python.exe tests\smoke\smoke_flow.py --stage analysis` → `SMOKE ANALYSIS PASSED` →
   from `logs\worker.log`: seconds per complaint (target < 60 s on this laptop) → `start-all.ps1 -Restart`.

## Ask the human (yes/no)
- Q1. The worker needed <n> s per complaint on this laptop (target < 60 s). Acceptable?

## Done when
verify green · `SMOKE ANALYSIS PASSED` · timing recorded · committed + pushed.

## Next
`/run-prompt P13` — first real phone test over the HTTPS tunnel (≈ 45 min, needs 1–2 phones and someone inside TDMC)
