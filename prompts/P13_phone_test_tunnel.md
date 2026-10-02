# P13 — First real phone test over the HTTPS tunnel
**Day 4 · agent ≈ 30 min (+ fixes) · human ≈ 30 min · Needs: P11, P12 · Model: any**
Phones need HTTPS for the camera, GPS and tilt sensor - the Cloudflare quick tunnel gives it. A real report only
passes the boundary check when the phone is **inside Talegaon Dabhade Municipal Council** (near the college is fine).

## Goal
A citizen on a real Android phone (and an iPhone if available) registers, captures a real photo with GPS and tilt,
submits, gets the CB number and sees "Under review" within about a minute; the agent finds and fixes what breaks.

## Read first
`docs/05_UI_SPEC.md` §4 · `docs/10_SETUP_WINDOWS.md` §4 (`start-all.ps1 -Tunnel`) · `logs\backend.log`, `logs\worker.log` after the test

## Before the human step (agent)
1. `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Restart` (dev stack) and `-Status` → all healthy.
2. Write `docs/TEST_RUN_P13.md`: a checklist table (step · expected · result · note) for the steps below.

## Human step (≈ 30 min)
1. In your own PowerShell 7 window: `cd C:\dev\civicbrain` then `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Tunnel`
   → it prints `PHONE URL: https://<name>.trycloudflare.com` (the backend restarts with that URL - nothing to edit).
2. Phone (Chrome on Android / Safari on iPhone): open the URL → Register (use a real e-mail; read the code at
   http://localhost:8025 on the laptop) → tick "WhatsApp updates" → verify → log in.
3. Report a problem: category Pothole or Garbage → Capture → allow camera, motion (iPhone) and location → hold the phone
   45–70° down until the tilt indicator is green → shutter → fill title/description (and the depth question) → Submit.
4. Note the CB number; open "My complaints" → after ≤ 1 min the status should be "Under review".
5. Also try once: deny the camera permission (the fallback "Take photo" button must appear) - then allow it again.
6. Stop the tunnel when done: `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Stop -Only tunnel`
   (then the agent restarts the backend so links point to localhost again).
Tell the agent what you saw at each step (short notes are enough), plus the phone model and browser.

## After the human step (agent)
- Read `logs\backend.log` / `logs\worker.log` for that complaint (status, timings, authenticity result, errors) - never paste
  personal data into the chat or the log, only ids and codes.
- Fix every problem found (most likely: iOS motion permission, camera constraints, GPS timeout, HEIC/large images, layout on
  small screens) with a regression test where possible; rerun the frontend checks; `start-all.ps1 -Only backend -Restart`.
- Fill `docs/TEST_RUN_P13.md` and commit.

## Ask the human (yes/no)
- Q1. Did the phone capture → submit → CB number work?
- Q2. Did the status become "Under review" within about a minute?
- Q3. (if fixes were made) Re-test once with the tunnel: does it work now?

## Done when
one real complaint went through end to end from a phone inside TDMC (or, if nobody is inside TDMC today: the phone got the
documented OUTSIDE_BOUNDARY message - record it and repeat Q1/Q2 in P24) · fixes committed.

## Next
`/run-prompt P14` — officer / admin / contractor-management API (≈ 3 h, strongest model)
