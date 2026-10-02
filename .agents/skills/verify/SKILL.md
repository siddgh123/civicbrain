---
name: verify
description: Run the CivicBrain test and quality checks for one component or all components and report the exact results. Use after every change, before committing, or when the user types /verify [backend|frontend|ai|smoke|db|all].
---

# /verify [component]

Run each command on its own (one terminal call per command, working directory set as shown, no `&&` chains,
no `cd`). Stop at the first failing command, show its last 40 lines, and fix it (max 2 attempts per error,
then report and ask).

| Component | Working dir | Commands (in this order) |
|---|---|---|
| backend | `backend` | `.\mvnw.cmd -q verify` (Docker Desktop must be running for Testcontainers) |
| frontend | `frontend` | `npm run lint` · `npm run typecheck` · `npm test -- --run` |
| ai | `ai-service` | `.\.venv\Scripts\python.exe -m ruff check .` · `.\.venv\Scripts\python.exe -m pytest -q` |
| db | repo root | `pwsh -NoProfile -File scripts\dev\db-rebuild-test.ps1 -Force` (expects V2 6/6, V4 11/11, V5 11/11, roles 7/7) |
| smoke | repo root | `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Stop` · `pwsh -NoProfile -File scripts\dev\seed-e2e.ps1` · `pwsh -NoProfile -File scripts\dev\start-all.ps1 -E2E` · `ai-service\.venv\Scripts\python.exe tests\smoke\smoke_flow.py --stage <latest built stage>` · `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Restart` |
| all | repo root | `pwsh -NoProfile -File scripts\dev\verify-all.ps1 -SkipE2E` (DB + backend + AI + frontend), then smoke |

Report as a table: component · command · result line (e.g. `Tests run: 214, Failures: 0`, `SMOKE PLAN PASSED: 41 / 41`) · PASS/FAIL.
Copy the table into the current entry of `docs/PROGRESS.md`. Never report PASS for a command you did not run in this session.
