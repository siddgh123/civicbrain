# P26 — OPTIONAL: one Playwright run with a fake camera (citizen happy path)
**Day 7 · agent ≈ 1.5 h · human ≈ 5 min · Needs: P23 · Model: any** - first item of the cut list; skip when behind.

## Goal
`npx playwright test` runs E2E-01 in a real browser: register → OTP from Mailpit → login → report with the fake camera and fake
GPS → CB number → "Under review" (08 §4).

## Read first
`docs/08_TEST_PLAN.md` §4 (config, fake camera args, accounts via `process.loadEnvFile('../.env.test')`) · `docs/05_UI_SPEC.md` §8

## Build
1. `frontend/playwright.config.ts` exactly as 08 §4 (workers 1, projects desktop + mobile Pixel 7 with geolocation 18.7440/73.6760
   and the fake-camera args with an absolute path built from `import.meta.dirname`; `webServer` = Vite with `reuseExistingServer`).
2. `tests/fixtures/images/camera.y4m`: generate it WITHOUT ffmpeg - a small Python script (`tests/fixtures/make_camera_y4m.py`, venv
   python + Pillow/numpy) that writes ~30 frames of `pothole_1.jpg` scaled to 640×480 as YUV4MPEG2 (`C420jpeg`) - git-ignored output.
3. `frontend/e2e/citizen.spec.ts` (E2E-01) using roles/labels first, `data-testid` where needed.

## Human step (≈ 5 min)
Playwright's browser must be installed into your user profile (outside the project, so the agent may not): in PowerShell 7
`cd C:\dev\civicbrain\frontend` then `npx playwright install chromium`. Say "done".

## Verify (agent)
`start-all.ps1 -Stop` → `seed-e2e.ps1` → `start-all.ps1 -E2E` → in `frontend`: `npx playwright test` → green (attach the HTML report
path) → `start-all.ps1 -Restart`.

## Ask the human (yes/no)
- Q1. Keep this Playwright test in the project (it is in the report as the browser-level check)?

## Next
`/run-prompt P27` — bug bash
