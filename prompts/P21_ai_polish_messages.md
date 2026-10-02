# P21 — AI polish and message details
**Day 6 · agent ≈ 1.5 h · human 0 min · Needs: P12, P20 · Model: any**

## Goal
The analysis is fast and robust on this laptop, re-analysis works from the officer screen, model checksums are enforced,
and the later-status messages carry the right details (inspection notes, expected completion, proof photo inline).

## Read first
`docs/06_AI_PIPELINE.md` §1 (re-analysis rules), §5 · `docs/02_ARCHITECTURE.md` §5 rules 6–8 · `docs/12_ERROR_HANDLING.md` §7 ·
`logs\worker.log` (timings from P12/P13) · `db/V2__civicbrain_app_layer.sql` (templates INSPECTED … REOPENED)

## Build
1. Performance: models load once per worker process; YOLO warm-up at start; measure per-step time; if one complaint takes > 60 s
   on this laptop, fix the slowest step (e.g. resize to 640 before pHash/quality, reuse the embedding model, lower Monte-Carlo
   samples to 100 only if needed - write the change as DECISION).
2. Re-analysis: officer "Re-run analysis" (P14 endpoint) → a second ANALYZE_COMPLAINT job → AI rows rewritten, status untouched on
   non-SUBMITTED complaints, DUPLICATE stored as UNCERTAIN, OFFICER_OVERRIDE estimate kept (06 §1) - integration test.
3. Worker start: `REQUIRE_MODELS=true` refuses missing/changed files with a message naming the file; `/health` `modelsLoaded`.
4. Messages: placeholders `inspection_notes`, `expected_completion`, `remarks`, `track_url` filled from the right rows;
   `include_photo` e-mails (INSPECTED, COMPLETED, COMPLETION_SUBMITTED) carry the photo inline (CID) + as attachment from storage
   (02 §5 rule 8); WhatsApp stays text + link. Dates in Asia/Kolkata format of 05 §2.
5. Officer detail "AI" tab: add "analysed in N s, model versions" (small, from the rows written).

## Tests (write first)
render each status template with real rows (no `{{`, no "null") · COMPLETED e-mail has an inline image part and an attachment ·
re-analysis rules (3 cases) · worker refuses a wrong-hash model file.

## Verify (agent)
ruff + pytest in `ai-service` · `.\mvnw.cmd -q verify` in `backend` · E2E smoke `--stage contractor` again → PASSED; open the
COMPLETED mail in Mailpit with the browser tool and screenshot `docs/screenshots/P21_completed_mail.png` · seconds per complaint
from `logs\worker.log`.

## Ask the human (yes/no)
- Q1. Does `P21_completed_mail.png` show the proof photo inside the e-mail?
- Q2. Analysis now takes <n> s per complaint. OK?

## Done when
all green · committed + pushed.

## Next
`/run-prompt P22` — contractor screens + citizen feedback (≈ 3 h)
