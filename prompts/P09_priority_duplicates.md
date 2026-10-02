# P09 — Priority (FROZEN Step 11) + duplicates (FROZEN Step 12) + MiniLM
**Day 3 · agent ≈ 2 h · human 0 min (unless research files are missing) · Needs: P02 · Model: strongest**

## Goal
`pipeline/priority.py` reproduces the validated Step 11 engine exactly (golden test 0 mismatches) and
`pipeline/duplicates.py` reproduces the Step 12 engine (3 pairs within 0.001), with the MiniLM model installed
offline with checksums.

## Read first
`.agents/rules/02-frozen-rules.md` · `docs/06_AI_PIPELINE.md` §2.6, §2.7 · `docs/INVENTORY.md` ·
`scripts/priority/priority_engine.py` (+ the CSVs it reads under `data/priority/`) · `data/duplicates/duplicate_engine_config.json`,
`duplicate_engine_results.csv`, `scripts/duplicates/run_duplicate_engine_and_load.py` · `ai-service/training/download_models.py`

## Build
1. `ai-service\.venv\Scripts\python.exe ai-service\training\download_models.py` → `models/all-MiniLM-L6-v2/` + MANIFEST
   (commit recorded) + the 384-dimension check. Worker settings: `TEXT_EMBEDDING_MODEL_DIR`, `HF_HUB_OFFLINE=1` at runtime.
2. **Priority:** port `priority_engine.py` and its rule CSVs into `pipeline/priority.py` **unchanged in behaviour**
   (copy the CSVs the engine needs to `ai-service/pipeline/data/priority/` or read them from `data/priority/` by a
   configured path - decide by what the engine does, note it as DECISION). Output: the 7 factors
   (`severity_score`=S, `impact_score`=Ipop, `location_score`=Rloc, `urgency_score`=Twait, `frequency_score`,
   `infrastructure_score`, `historical_risk_score`), total P, level (LOW < 25 ≤ MEDIUM < 50 ≤ HIGH < 75 ≤ CRITICAL) and an
   `explanation` JSON (each factor's input + rule). DB writer: `priority_assessments` with `is_current` switch and
   `complaints.current_priority_*`.
3. **Duplicates:** candidates `fn_duplicate_candidates(id)` (300 m, previous 7 days, masters only); text = title + " " +
   description; MiniLM cosine; `distance_score = 1 − d/300`; `recency_score = 1 − hours/168`;
   `score = 0.70·text + 0.20·distance + 0.10·recency`; ≥ 0.59 DUPLICATE, 0.55–0.59 UNCERTAIN, else NOT_DUPLICATE; best
   DUPLICATE → MERGED into the candidate's master (earlier complaint); two different masters → UNCERTAIN; master COMPLETED/
   CLOSED → UNCERTAIN; every scored pair upserted into `duplicate_relation`. Pure scoring function + DB part.
4. Daily 02:00 IST priority recompute for open non-synthetic complaints (06 §1) - a small scheduled step in the worker loop.

## Fallbacks (only if `docs/INVENTORY.md` says the files are missing)
- `priority_engine.py` or its CSVs missing → STOP and ask: "The Step 11 engine files are missing. (yes) implement the
  documented weights with factor rules written as ASSUMPTIONS in `app/config.py` and a hand-computed golden test, or (no) wait
  while you copy the files from the old folder?" Never invent rules silently.
- `duplicate_engine_results.csv` missing → test the formula with 3 hand-computed pairs (documented in the test) instead.

## Tests (write first)
- `test_priority_golden.py`: recompute every row of `data/priority/priority_factor_dataset.csv` → **0 mismatches** against
  `data/priority/priority_scores.csv` (score within 1e-6 and same level); print the row count.
- `test_duplicates_repro.py` (`@pytest.mark.models`): 3 pairs from `duplicate_engine_results.csv` (one DUPLICATE, one UNCERTAIN,
  one NOT_DUPLICATE if present) → same score within 0.001 and same label.
- unit: thresholds at the edges (0.55, 0.59), two masters → UNCERTAIN, closed master → UNCERTAIN, distance/recency clamps.
- integration (`civicbrain_test`): two complaints 40 m apart, same day, similar text → relation DUPLICATE and the later one
  would be MERGED (status change itself is done by the orchestrator in P12 - test the decision object here).

## Verify (agent)
ruff + pytest in `ai-service` (show golden row count and "0 mismatches"; `models` tests ran) ·
`start-all.ps1 -Only worker,ai-api -Restart` → `/health` lists MiniLM as loaded (the YOLO/classifier part depends on P08;
`REQUIRE_MODELS` stays false until P12).

## Ask the human (yes/no)
- Q1. The priority golden test checked <n> rows with 0 mismatches and the duplicate test reproduced 3 pairs. Continue?

## Done when
both FROZEN ports proven · MiniLM installed with MANIFEST · committed + pushed.

## Next
`/run-prompt P10` — complaint intake API + e-mail outbox (≈ 3 h, strongest model)
