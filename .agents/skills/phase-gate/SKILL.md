---
name: phase-gate
description: Check whether a CivicBrain phase (P0-P12) or 7-day MVP day (D1-D7) meets every gate item before it can be closed. Use when the user types /phase-gate P<n> or /phase-gate D<n>, or asks if a phase or day is finished.
---

# /phase-gate P<n>

1. Copy the gate list: for `D<n>` the row of the "Day gates" table in `prompts/README.md` (autopilot) plus the `docs/09_BUILD_PLAN_7DAY.md` §4 tests that exist so far; for `P<n>` the gate in `docs/09_BUILD_PLAN.md`.
2. For each item decide how it is proven: a command you run now (`/verify …`), a test name that must exist and pass, a file that must exist (metrics, reports, screenshots), or a manual check the human must confirm.
3. Run every command-based check now; do not reuse old results.
4. Run `scripts\dev\verify-all.ps1 -SkipE2E` yourself (DB tests, all components; log in `logs/verify-all_<timestamp>.txt`) and the smoke stage for the day on the freshly seeded E2E stack. Only phone/device checks and real WhatsApp delivery need the human: give numbered steps and ask yes/no. You never run psql directly.
5. Also check: `git status` clean (everything committed), no `TODO`/`FIXME` added in this phase without an issue link, `docs/PROGRESS.md` has an entry for every task, and the requirement IDs of the phase are all covered by at least one test (grep test names/comments for the IDs).
6. Output a table: gate item · evidence · PASS/FAIL. If anything fails: list the fix tasks and keep the phase IN PROGRESS.
7. If everything passes: update the row in `docs/PROGRESS.md` to "PASSED – awaiting approval" with the evidence, commit, and ask the human "Approve D<n>? (yes/no)". On yes: mark PASSED, commit, push, tag `d<n>-done` (`p<n>-done` for full phases).
