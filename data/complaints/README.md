# data/complaints - text data for the complaint-text classifier (docs/06_AI_PIPELINE.md sec. 2.2)

| File | Rows | What | Honest label |
|---|---|---|---|
| `synthetic_complaints_500.csv` | 500 | title + description + category of the 500 synthetic Step 8 complaints (extracted from `db/seed/seed_synthetic_demo_data.sql`; only 24 distinct texts) | synthetic (`is_synthetic = true`) |
| `kit_authored_train.csv` | 160 | 20 short complaint sentences per category (8 English, 5 Hinglish, 6 Marathi in Roman script, 1 English) | written for the kit as bootstrap data - **not real citizen reports** |
| `sanity_test_mvp.csv` | 40 | 5 different sentences per category, never used for training | written for the kit - a sanity check, **not** an evaluation on real data |

Rules: train on the first two files only; report the accuracy on `sanity_test_mvp.csv` as "sanity check on 40 kit-written sentences".
Devanagari text is not covered yet (Phase 2: collect real complaints with consent). The citizen's chosen category stays primary; the classifier only flags a mismatch (FR-21).
Team members may add their own real sentences to a new file `real_test_team.csv` (same columns, `source = team`).
