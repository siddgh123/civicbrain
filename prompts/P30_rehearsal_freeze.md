# P30 — Rehearsal, freeze and tag `mvp-v1`
**Day 7 evening · agent ≈ 30 min · humans ≈ 1 h · Needs: P28, P29 · Model: any**

## Goal
The demo script runs twice without error on the demo laptop, the code is frozen and tagged, and everything needed on demo day
is written down.

## Read first
`docs/13_DEMO_AND_DEPLOY.md` §3, §4, §5 · `docs/DEMO_RUNBOOK.md` · `docs/09_BUILD_PLAN_7DAY.md` §5 Gate D7

## Before the rehearsal (agent)
1. Final checks on the E2E stack (dev/demo stack stopped first, as 13 §3 says): `start-all.ps1 -Stop` → `verify-all.ps1 -SkipE2E` →
   `seed-e2e.ps1` → `start-all.ps1 -E2E` → smoke `--stage all` → `start-all.ps1 -Stop`. All PASS.
2. `docs/REHEARSAL.md`: the 7 steps of 13 §4 as a table (who, device, what to say, expected screen, time budget) + a fallback per
   step (e.g. WhatsApp slow → show the Mailpit/Gmail mail; tunnel down → phone hotspot + restart the tunnel; AI slow → show an
   already analysed complaint).

## Human step (≈ 1 h)
1. `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Demo -Tunnel`.
2. Run the demo script twice with a timer (≈ 12 min each); the agent records times and problems from what you tell it.
3. `pwsh -NoProfile -File scripts\dev\backup-db.ps1 -CopyTo <USB folder>` once more after the rehearsal.

## After the rehearsal (agent)
- Blockers only: fix with a test (same rules as P27); otherwise add to Known limitations.
- `/phase-gate D7` → on "yes": `git tag mvp-v1` → `git push` + `git push origin mvp-v1`.
- Final Autopilot log entry: what works, what was cut, where the report notes are.

## Ask the human (yes/no)
- Q1. Did both rehearsal runs finish without an error?
- Q2. Approve gate D7 and tag `mvp-v1`?

## Done when
two clean rehearsals · backup on USB · `mvp-v1` tag pushed · PROGRESS final.

## Next
Demo day. After the deadline: Phase 2 with `docs/09_BUILD_PLAN.md` (`/start-phase P<n>`).
