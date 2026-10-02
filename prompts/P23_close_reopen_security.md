# P23 — Close / reopen loop, plan lifecycle checks, security pass  (FEATURE FREEZE after this)
**Day 6 · agent ≈ 2.5 h · human 0 min · Needs: P20, P22 · Model: strongest**

## Goal
The loop closes: officer verifies → CLOSED (citizen rates) or rejects → REOPENED → plannable again; citizen "Not fixed"
reopens; plan states stay right. Then a focused security pass over every MVP endpoint. Smoke `close` and `all` pass.
After this prompt: no new features - only fixes (P27).

## Read first
`docs/04_API_CONTRACT.md` §5 feedback, §6 verify-completion + plan lifecycle · `docs/03_DATABASE.md` §3 (V5 release trigger) ·
`docs/07_SECURITY.md` §2, §3, §4, §6, §9 · `docs/09_BUILD_PLAN_7DAY.md` §1 (Security minimum) · `tests/smoke/smoke_flow.py` (`stage_close`)

## Build
1. Close/reopen: re-check P14's verify-completion and P10's feedback against 04 (CLOSED, REOPENED, feedback upsert with audit of
   the old values, 422 FEEDBACK_NOT_ALLOWED on other statuses incl. MERGED); after REOPENED the V5 trigger frees the complaint →
   a new GENERATE includes it; plan lifecycle helper (P18) re-evaluates after every item status change (COMPLETED plan keeps its
   items; all items REMOVED → CANCELLED).
2. Security pass (fix what fails, each with a test):
   - **Deny-all proof:** a test lists every `@RequestMapping` (reflection) and calls it anonymously → 401, except the documented
     public ones (`/auth/*` minus logout-all/password change, `/public/*`, `/actuator/health`, `/client-errors`).
   - **Ownership/scope 404:** one "other user → 404" test for every endpoint that returns someone's data (citizen, officer scope,
     contractor firm, files).
   - **Headers:** CSP, nosniff, frame-ancestors, Referrer-Policy, Permissions-Policy on `/` and `/api/v1/public/categories`.
   - **Input/files:** oversized JSON, unknown fields, path traversal in file ids, non-image upload, > 8 MB upload.
   - **Logs:** run the smoke `all` stage, then scan `logs\backend.log` and `logs\worker.log` for JWTs (`eyJ…`), refresh cookies,
     6-digit OTPs next to "otp", passwords, full +91 phone numbers → none.
   - **Rate limits:** login, register, complaint create return 429 with `Retry-After` at the documented limits.
   - Frontend: no `dangerouslySetInnerHTML`, no tokens in `localStorage`/`sessionStorage` (grep test).
3. `docs/SECURITY_CHECK.md`: table check · how tested · result (for the report).

## Tests
the ones above + backend IT for COMPLETED → REOPENED → generate → approve succeeds.

## Verify (agent)
1. `pwsh -NoProfile -File scripts\dev\verify-all.ps1 -SkipE2E` → all PASS (DB, backend, AI, frontend).
2. E2E smoke: `start-all.ps1 -Stop` → `seed-e2e.ps1` → `start-all.ps1 -E2E` →
   `ai-service\.venv\Scripts\python.exe tests\smoke\smoke_flow.py --stage all` → `SMOKE ALL PASSED` → log scan → `start-all.ps1 -Restart`.
3. Gate D6 itself is checked in P24 (with the phones).

## Ask the human (yes/no)
- Q1. `docs/SECURITY_CHECK.md` lists every check as PASS - agree to freeze features now (only bug fixes from here)?

## Done when
verify-all green · `SMOKE ALL PASSED` · security table complete · committed + pushed.

## Next
`/run-prompt P24` — full-flow test with 2 phones + demo accounts (≈ 1 h with the team)
