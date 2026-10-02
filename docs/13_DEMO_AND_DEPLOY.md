# 13 — Demo, Deployment and Runbooks

## 1. Demo machine setup (MVP: prompt P28 on the build laptop; full plan: P12)
- Laptop with 16 GB RAM, charger, phone hotspot as backup internet.
- Database: the dev database `civicbrain` (Flyway V1–V5 + `db-setup-main.ps1 -Seed`) with the complaints the team captured during the phone tests.
- Build (agent, P28): `cd frontend; npm run build` → copy `dist/` to `backend/src/main/resources/static` → `.\mvnw.cmd -q -DskipTests package`.
- Start (human): `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Demo -Tunnel` → starts the tunnel first, then backend (`-Prod`, jar with the SPA) with `-BaseUrl <tunnel URL>`, AI API, worker (+ Mailpit only while SMTP is Mailpit) and prints the PHONE URL. `.env` is not edited; the laptop itself keeps working on http://localhost:8080. Stop: `start-all.ps1 -Stop`.
- MVP: routing `haversine` (no OSRM), WhatsApp through the Twilio sandbox (every phone sends `join <code>` within 72 h of the demo) or `log`. Phase 2: OSRM (`start-osrm.ps1`) and the Meta test number with approved templates.
- E-mail: Gmail app password (`SMTP_*` in `.env`, typed in by a human); test one mail the day before.

## 2. Demo accounts
`admin@…` (created with `scripts/dev/bootstrap-admin.ps1 -Email …` on the demo database; TOTP on the admin's phone at first login), `officer.road@…` (created by the admin; TOTP on the officer's phone), `contractor.patil@…` (created by the officer; one-time password changed at first login), two citizen accounts on two phones (self-registered with e-mail OTP). Passwords only in the team's password manager.

## 3. Pre-demo checklist (day before and 1 hour before)
- [ ] Day before: `start-all.ps1 -Stop` → `verify-all.ps1 -SkipE2E` → `seed-e2e.ps1` → `start-all.ps1 -E2E` → `tests\smoke\smoke_flow.py --stage all` green → `start-all.ps1 -Stop` → demo stack again. One hour before: health checks and one test complaint only (never run `verify-all`/`seed-e2e` while the demo stack is up — they rebuild the jar).
- [ ] `/actuator/health` UP; AI `/health` shows db and modelsLoaded = true (osrm is not used in the MVP).
- [ ] Tunnel URL opens on both phones; camera and location permission granted in Chrome/Safari.
- [ ] One test complaint end-to-end (then delete or keep as example).
- [ ] Mail + WhatsApp received on a phone.
- [ ] Backup taken: `scripts/dev/backup-db.ps1 -CopyTo <USB stick folder>`.
- [ ] Manual iPhone check: in-page camera opens (iOS asks for motion permission), GPS accuracy chip appears, photo submits.

## 4. Demo script (≈ 12 minutes; run twice in rehearsal)
1. Citizen phone: register (OTP e-mail) → report a pothole outside the venue (or a prepared spot) → CB number → e-mail + WhatsApp "received".
2. Officer laptop: New tab → the complaint appears within a minute → open detail: YOLO box, size with confidence tier, material + cost range, priority factors, authenticity checks.
3. Second citizen reports the same spot → MERGED → message "linked".
4. Officer: generate plan for ROAD today → route on map, dropped jobs explained → reorder one stop → approve → assign contractor → both citizens get "contractor assigned".
5. Contractor phone: worklist → inspection with tape values → start → completion proof → citizens get the proof photo.
6. Officer verifies → CLOSED → citizen rates.
7. Show: notification log, audit log, PDF export, public map (snapped, no personal data), evaluation report slide (YOLO per-class metrics, classifier macro-F1, measurement error per tier, FIFO vs optimised), limitations slide.

## 5. Known limitations to state honestly
Size from one photo is an estimate with a confidence tier; depth is never measured from the photo. Fake-report protection detects and deters, it cannot prove a photo is genuine. Wards are analytical units (not the 2025 electoral wards). Rates/teams/depot are prototype values until TDMC provides official ones. WhatsApp demo uses a test number (5 recipients). Ultralytics AGPL-3.0 applies to the model.

## 6. Incident / breach runbook (also required by CERT-In/DPDP in production)
1. Contain: disable affected accounts (`/admin/users/{id}/disable`), rotate `JWT_SECRET` (logs everyone out), rotate provider keys.
2. Preserve: copy logs and a DB dump; do not delete anything.
3. Report: tell the guide/council contact immediately (production: CERT-In within 6 hours; Data Protection Board and affected users without delay, detailed report within 72 hours).
4. Fix the cause, add a regression test, document in `docs/INCIDENTS.md`.

## 7. Backup & restore
Daily `scripts/dev/backup-db.ps1` (keeps 14 days). Restore drill once per phase into `civicbrain_restore_test` and run `db/tests/test_V4.sql` against it.
