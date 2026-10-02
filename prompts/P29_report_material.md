# P29 — Report and presentation material (honest numbers only)
**Day 7 · agent ≈ 1 h · human ≈ 15 min · Needs: P27 · Model: strongest**

## Goal
One document `docs/REPORT_NOTES.md` the team can paste into the SPPU report and slides: what was built, how, measured
results with their real meaning, screenshots, security, limitations and the Phase-2 list. No invented numbers.

## Read first
`docs/01_REQUIREMENTS.md` §1–§4 · `docs/02_ARCHITECTURE.md` §1, §5 · `docs/reports/` (yolo_metrics.json, dataset_report*.json,
text_clf_metrics.json, yolo_plots/) · `docs/PROGRESS.md` · `docs/SECURITY_CHECK.md` · `docs/TEST_RUN_P24.md` ·
`docs/09_BUILD_PLAN_7DAY.md` §1 OUT · `.agents/rules/02-frozen-rules.md` · `docs/screenshots/`

## Build
`docs/REPORT_NOTES.md` with these sections (tables where possible):
1. Problem and users (citizen, officer, contractor), the end-to-end flow (status chain of 05 §1).
2. Architecture: a Mermaid diagram (SPA ↔ Spring Boot ↔ PostgreSQL/PostGIS ↔ Python worker; outbox → Mailpit/Gmail, Twilio) +
   stack table with versions from `pom.xml`, `package.json`, `requirements.txt`.
3. Data: YOLO dataset counts per split/class (dataset_report), sources/licences (`data/yolo/dataset_sources.csv` if present),
   text data (`data/complaints/README.md`: synthetic + kit-written, NOT real complaints), 23 analytical wards (not electoral).
4. Results (copy the numbers exactly, with their scope): YOLO P/R/mAP50/mAP50-95 overall + per class "on the existing test split,
   not a Talegaon field test"; text classifier "sanity check on 40 kit-written sentences"; priority golden test rows/mismatches;
   duplicate reproduction; analysis seconds per complaint on the laptop; test counts (backend tests, pytest, vitest, smoke checks)
   from the last runs in PROGRESS; P24 full-flow result.
5. Measurement and estimate method (Tier B/C, assumptions table with sources/ASSUMPTION labels), planning method (FROZEN grouping,
   OR-Tools, straight-line × 1.3 at 20 km/h).
6. Security and privacy measures (from SECURITY_CHECK.md), authenticity checks list.
7. Screenshots index (file → what it shows) for slides.
8. Limitations (honest) and Phase 2 (the OUT list + field validation, Talegaon dataset, OSRM, Meta WhatsApp, TOTP if skipped).
9. A 10-slide outline (title per slide + which section/screenshot feeds it).

## Verify (agent)
every number in the document is traceable: add a "source" column (file + key) to each results table; grep that no "TBD"/"TODO" remains.

## Human step (≈ 15 min)
Read `docs/REPORT_NOTES.md`; tell the agent names/roll numbers/guide name to put on the title part (or say "leave blank").

## Ask the human (yes/no)
- Q1. Are all numbers in the results tables shown with their source and scope (nothing looks invented)?
- Q2. Is the slide outline OK for the presentation length you have?

## Done when
REPORT_NOTES.md committed + pushed.

## Next
`/run-prompt P30` — rehearsal, freeze, tag (≈ 1 h with the team)
