# P28 — Demo build: one jar with the web app, real e-mail, backup
**Day 7 · agent ≈ 1.5 h · human ≈ 20 min · Needs: P27 · Model: any**

## Goal
The demo runs from one command (`start-all.ps1 -Demo -Tunnel`): Spring Boot serves the built React app and the API on 8080,
real e-mails go out through the project Gmail account, WhatsApp through the sandbox, and a verified backup sits on a USB stick.

## Read first
`docs/13_DEMO_AND_DEPLOY.md` §1–§3, §7 · `docs/07_SECURITY.md` §4 (CSP for the served SPA) · `scripts/dev/start-all.ps1` header

## Build
1. SPA inside the jar: `frontend` `npm run build` → copy `frontend/dist/*` into `backend/src/main/resources/static/` (git-ignored;
   Copy-Item, never delete outside it - the agent may overwrite files there) → in the backend a forward of non-API, non-file
   routes to `index.html` (React Router deep links like `/c/CB-000123`, `/officer/plans/5`), long cache for hashed assets, no cache
   for `index.html`; CSP still strict (no inline scripts).
2. `scripts/dev/build-demo.ps1` (ASCII only, same style as the others): `npm run build` → copy dist → `.\mvnw.cmd -q -DskipTests package`
   → prints the jar path. The agent writes it and runs it once (Antigravity asks for approval because it is not on the allow list).
3. Profile `demo`: synthetic complaints hidden on maps (`includeSynthetic=false` default), log level INFO, the same security
   settings as `dev`; `start-all.ps1 -Demo` passes `APP_EXTRA_ORIGINS=http://localhost:8080` itself.
4. Checks the agent runs: `npm run build`, `build-demo.ps1`, and a backend IT that requests `/` and `/c/CB-000001` → 200 `text/html`
   with the CSP header, `/api/v1/unknown` → 401 JSON (not the SPA). The IT uses a tiny `src/test/resources/static/index.html`, so it
   also passes in CI where no built SPA exists. Starting the demo stack (`-Demo`) is the human's step below.

## Human step (≈ 20 min)
1. Gmail (project account): Google Account → Security → 2-Step Verification ON → App passwords → create "CivicBrain" → copy the 16 chars.
2. `.env` (Notepad): `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, `SMTP_STARTTLS=true`, `SMTP_USER=<gmail address>`,
   `SMTP_PASSWORD=<app password>`, `SMTP_FROM="CivicBrain TDMC <gmail address>"`, `SPRING_PROFILES_ACTIVE=demo`. Save.
   (The E2E stack ignores these and always uses Mailpit, so the agent's tests never send real mail.)
3. PowerShell 7: `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Stop` then `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Demo -Tunnel`
   → PHONE URL. On a phone: open it, log in as a demo citizen, check that a status mail reaches the real inbox (trigger one by an
   officer action on a test complaint, or register a new citizen - the OTP mail must arrive in Gmail).
4. Redo the Twilio sandbox `join <code>` on every demo phone (72-hour limit).
5. Plug in the USB stick and run `pwsh -NoProfile -File scripts\dev\backup-db.ps1 -CopyTo <USB folder>`.
6. Tell the agent the results.
(To go back to development later: `SPRING_PROFILES_ACTIVE=dev`, SMTP back to Mailpit `localhost`, `1025`, `SMTP_STARTTLS=false`.)

## Verify (agent)
backend + frontend checks green · `build-demo.ps1` output · `docs/DEMO_RUNBOOK.md` (one page: start, stop, URLs, accounts list
without passwords, what to do if the tunnel or Wi-Fi fails: phone hotspot, restart `start-all.ps1 -Demo -Tunnel`).

## Ask the human (yes/no)
- Q1. Did the phone open the demo URL and did a real e-mail arrive in Gmail?
- Q2. Is the backup on the USB stick (backup-db printed PASS)?

## Done when
demo stack runs from the jar · real mail works · backup on USB · runbook committed + pushed.

## Next
`/run-prompt P29` — report material (≈ 1 h)
