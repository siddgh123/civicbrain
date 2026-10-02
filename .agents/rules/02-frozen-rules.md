---
trigger: always_on
---

# Frozen research rules (from the validated Steps 9, 11, 12, 13 — do not change)

- **YOLO classes (Step 9):** 0 Pothole, 1 Garbage Accumulation, 2 Waterlogging, 3 Road Damage. Same order in `data.yaml`, code and DB (`complaint_categories.yolo_class_id`).
- **Work types:** ROAD, WATER, GARBAGE, ELECTRICITY (+ REVIEW_REQUIRED for "Other"). Category → work type mapping lives in `complaint_categories.work_type_code`.
- **Priority (Step 11):** P = 0.25 S + 0.15 Ipop + 0.15 Rloc + 0.10 F + 0.10 Twait + 0.15 Iinfra + 0.10 H; LOW < 25 ≤ MEDIUM < 50 ≤ HIGH < 75 ≤ CRITICAL. Port `scripts/priority/priority_engine.py` exactly; golden test = 0 mismatches.
- **Duplicates (Step 12):** 300 m radius, 7-day window, `sentence-transformers/all-MiniLM-L6-v2`, score 0.70 text + 0.20 distance + 0.10 recency, DUPLICATE ≥ 0.59, UNCERTAIN 0.55–0.59 (manual review, never auto-merge); earlier complaint is the master; two different masters → manual review.
- **Grouping (Step 13):** same work type, ≤ 2,000 m, ≤ 10 jobs per group — use `fn_cluster_jobs`. Shift 08:00–17:00; depot D001 (18.729411, 73.699489, prototype).
- **Scope:** no hotspot detection. Human officer makes every final decision (reject, merge, approve, assign, close).
- **Honesty:** synthetic data stays labelled (`is_synthetic`); prototype teams/depot/rates are labelled as prototype; AI size/cost always shown with confidence tier or range; never invent metrics, TDMC staff, departments, rates or inventory.
- **Wards:** 23 analytical GIS units (`wards`, cleaned by V3). Join on `ward_id`, display `ward_number`. They are not the 14 electoral wards.
- Changing any of these requires a written decision in `docs/PROGRESS.md` approved by the team, a new migration/version, and re-running the affected validation.
