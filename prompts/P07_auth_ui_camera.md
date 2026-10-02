# P07 — Auth screens + CameraCapture component
**Day 2 · agent ≈ 2.5 h · human ≈ 5 min · Needs: P05, P06 · Model: Flash is fine (strongest for CameraCapture)**

## Goal
Register (privacy notice + consents) → OTP → login → forced password change → logout work in the browser against
the real backend; the auth provider keeps the token in memory with silent refresh; `CameraCapture` (in-page
camera + GPS + tilt + fallback) exists and is unit-tested (the real phone test is P13).

## Read first
`docs/05_UI_SPEC.md` §2, §3, §4 step 2, §7, §8 · `docs/04_API_CONTRACT.md` §1–§3 · `docs/12_ERROR_HANDLING.md` §6 ·
`.agents/rules/20-frontend-react.md` · `docs/07_SECURITY.md` §1 (cookie/CSRF from the browser side)

## Build
1. `AuthProvider`: access token in memory only, silent refresh on page load (`POST /auth/refresh` with
   `credentials:'include'` + `X-CB-CSRF: 1`), ONE shared refresh promise for parallel 401s, `BroadcastChannel('cb-auth')`
   logout sync, redirect to `/login?next=…`, role → portal (`CITIZEN`→/citizen, `OFFICER`/`ADMIN`→/officer,
   `CONTRACTOR`/`CONTRACTOR_STAFF`→/contractor), `mustChangePassword` → `/change-password`.
2. Screens (react-hook-form + zod mirroring server rules): Register (name, e-mail, phone with fixed +91, password with
   show/hide + strength hint, privacy notice scroll box from `/public/privacy-notice`, required "I accept", optional
   WhatsApp / public photo / AI training checkboxes), OTP (6 boxes, paste, resend timer 60 s), Login, Change password,
   minimal Profile (opt-ins). Error codes → i18n messages (12 §6); server `fieldErrors` mapped to fields.
3. `CameraCapture` (05 §4 step 2 + §7): `getUserMedia({video:{facingMode:'environment', width:{ideal:1920}}})`, guide
   frame, tilt indicator from `deviceorientation` (green 45–70° down, roll < 5°; iOS `DeviceOrientationEvent.requestPermission`
   on the Capture tap), GPS chip (green ≤ 50 m, amber ≤ 150 m, red > 150 m) from `watchPosition`, shutter → canvas JPEG 0.9
   (verify `image/jpeg`), `getCurrentPosition({enableHighAccuracy:true, maximumAge:0, timeout:20000})`, preview + Retake,
   no gallery button; camera denied → explanation + `<input type="file" accept="image/*" capture="environment">`
   (method `FILE_CAPTURE`); location denied → explanation, cannot continue; accuracy > 150 m → "Move to open sky".
   Returns `{blob, lat, lon, accuracyM, capturedAt, pitchDeg, rollDeg, method}`. Stops the camera tracks on unmount.
4. `ProtectedImage` (fetch with bearer → blob URL, revoked on unmount) - used from P11.

## Tests (write first, Vitest + MSW)
login form validation (empty / bad e-mail / short password) · register requires the privacy checkbox · OTP screen
accepts a pasted 6-digit code · AuthProvider: two parallel 401s trigger ONE refresh · `CameraCapture` shows the fallback
when `getUserMedia` rejects with `NotAllowedError` · location denied blocks "Continue".

## Verify (agent)
1. in `frontend`: `npm run lint` · `npm run typecheck` · `npm test -- --run` · `npm run build`.
2. Browser walkthrough on the **E2E stack** (keeps the dev database clean): `start-all.ps1 -Stop` → `seed-e2e.ps1 -MinAccounts 3`
   → `start-all.ps1 -E2E`. In the browser tool at http://localhost:5173: register a new account
   `p07-<4 random chars>@smoke.local`, read the OTP at http://localhost:8025, verify, log in, open the citizen home,
   log out, log in as `ui.citizen` (password in `tests/e2e-ui-accounts.local.json`), open `/citizen/new` until the
   camera step (the agent browser has no camera → the fallback must appear). Screenshots:
   `docs/screenshots/P07_register.png`, `P07_otp.png`, `P07_citizen_home.png`, `P07_camera_fallback.png`.
3. `start-all.ps1 -Restart` (dev stack back).

## Human step (≈ 5 min, laptop only)
Open http://localhost:5173/register on the laptop, register with your own e-mail, open http://localhost:8025 to read
the code (all dev mails land in Mailpit), verify and log in. Then log out.

## Ask the human (yes/no)
- Q1. Did register → OTP (from Mailpit) → login → logout work for you on the laptop?
- Q2. Do the 4 screenshots in `docs/screenshots/P07_*.png` look right (readable, nothing overlapping)?

## Done when
4 frontend checks green · walkthrough screenshots committed · answers yes.

## Next
Day 3: `/run-prompt P08` — text classifier + YOLO detector + authenticity (needs the Kaggle result)
