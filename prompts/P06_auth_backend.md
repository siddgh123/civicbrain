# P06 — Authentication backend + E2E seed runner
**Day 2 (Fri 2 Oct) · agent ≈ 3 h · human 0 min · Needs: P04, P05 · Model: strongest**

## Goal
Citizens can register (privacy notice + consents), verify the e-mail OTP, log in, refresh, log out; `/me` works;
lockout, generic errors, rate limits and the rotating refresh cookie behave as specified. The first admin can
be created by `bootstrap-admin.ps1`, and `seed-e2e.ps1` can build the E2E accounts that exist so far.
Smoke stage `auth` passes.

## Read first
`docs/04_API_CONTRACT.md` §1, §2, §3 (`/public/privacy-notice`), §11 · `docs/07_SECURITY.md` §1, §2, §6, §7 ·
`docs/12_ERROR_HANDLING.md` §2 · `docs/03_DATABASE.md` §3 (users, auth_otp_codes, refresh families, auth_events, consents) ·
`db/SCHEMA_REFERENCE_after_V5.sql` (those tables) · `.agents/rules/10-backend-spring.md`, `50-security.md` ·
`tests/smoke/smoke_flow.py` (`stage_auth`, `register_fresh`, `login`) · `scripts/dev/seed-e2e.ps1`, `bootstrap-admin.ps1`

## Build
1. `auth` module: register (always 202; existing e-mail/phone → decoy otpId + "someone tried to register" mail, nothing
   created), verify-otp (5 attempts, 10 min), resend-otp (1/60 s), login (identifier = e-mail or +91 phone; unverified →
   403 EMAIL_NOT_VERIFIED + new otpId), refresh (cookie `__Host-cb_rt`: Secure, HttpOnly, SameSite=Strict, Path=/;
   rotation, reuse of a rotated token revokes the family → 401 SESSION_REVOKED; header `X-CB-CSRF: 1` + Origin check →
   403 CSRF_CHECK_FAILED), logout (204, clears cookie), logout-all (`token_valid_after`), password change (clears
   `must_change_password`), forgot/reset (FR-03: build last, only if the time box allows).
2. OTP: 6 digits, stored as HMAC (`OTP_HMAC_KEY`), sent **synchronously** by e-mail (JavaMailSender; Mailpit in dev),
   never through the outbox, never logged. Mail text contains the code once.
3. Passwords: Argon2id (`Argon2PasswordEncoder` + BouncyCastle), policy 12–128 chars (+ small blocklist).
   Lockout: 10 failures → 423 ACCOUNT_LOCKED for 15 min; unknown account and wrong password → identical 401
   INVALID_CREDENTIALS. `auth_events` rows for every auth event (V5 types).
4. JWT access tokens (HS256 with `JWT_SECRET`, `typ`, `iss`, `aud`, `exp` 15 min, `iat`; resource-server decoder with
   validators incl. `iat >= users.token_valid_after`). MVP: `app.security.mfa-required=false` (TOTP is P25).
5. Users with `must_change_password = true` get 403 `PASSWORD_CHANGE_REQUIRED` on every endpoint except `/me`,
   `/auth/password/change`, `/auth/logout*` (add the code to `docs/12_ERROR_HANDLING.md` §2 first).
6. `GET /me`, `PUT /me` (name, language, opt-ins - WhatsApp opt-in kept in sync with the WHATSAPP_MESSAGES consent),
   `POST /me/consents`; `GET /public/privacy-notice` (current notice row); consents stored at registration (FR-60).
7. Rate limits (Bucket4j, in memory) exactly as 04 §11; profile `e2e` relaxes per-IP limits ×100 and allows 100 complaints /
   24 h per user (the smoke posts several complaints as one citizen).
8. `AdminBootstrapRunner` (profile `bootstrap-admin`, rule 10 - with `mfa-required=false` it must NOT force a TOTP set-up:
   the MVP has no TOTP screens before the optional P25, and P24 needs the admin to log in with password only) and `E2eSeedRunner` (profile `e2e-seed`, refuses unless
   the DB name ends with `_e2e`): creates now - through the real services, verified e-mail, no forced change -
   `E2E_ADMIN_*`, `E2E_CITIZEN1_*`, `E2E_CITIZEN2_*` (phones from `.env.test`) and, when the `E2E_UI_ADMIN_*` /
   `E2E_UI_CITIZEN_*` variables exist (set by `seed-e2e.ps1`), `ui.admin` and `ui.citizen`. Officers/contractors/staff: P14.
   Idempotent (existing e-mail → skip). Exits when done.

## Tests (write first)
Backend IT (Testcontainers + a Mailpit container): register → OTP mail → verify → login · decoy register (no second
account, owner mail) · wrong password and unknown account → same 401 body · 10 failures → 423, wrong one while locked → 401 ·
refresh rotation; reuse → 401 and the family is dead · refresh without CSRF header / wrong Origin → 403 · logout clears the
cookie · logout-all invalidates an existing access token · OTP code never appears in `notification_outbox`/`notifications` ·
`must_change_password` → 403 PASSWORD_CHANGE_REQUIRED · rate limit → 429 RATE_LIMITED with Retry-After ·
E2eSeedRunner refuses a non-`_e2e` database.

## Verify (agent)
1. in `backend`: `.\mvnw.cmd -q verify`.
2. E2E smoke (repo root, one command each):
   `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Stop` ·
   `pwsh -NoProfile -File scripts\dev\seed-e2e.ps1 -MinAccounts 3` ·
   `pwsh -NoProfile -File scripts\dev\start-all.ps1 -E2E` ·
   `ai-service\.venv\Scripts\python.exe tests\smoke\smoke_flow.py --stage auth` → `SMOKE AUTH PASSED` ·
   `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Restart` (dev stack back).
3. `Select-String -Path logs\backend.log -Pattern 'eyJ[A-Za-z0-9_-]{10,}|password=|otp.{0,20}\d{6}'` → no hits (no tokens/secrets/OTPs logged).

## Human step
None. (`bootstrap-admin.ps1` for the real demo admin is done in P24.)

## Ask the human (yes/no)
- Q1. Open http://localhost:8025 (Mailpit) - do you see "smoke-…@smoke.local" OTP mails from the smoke run?

## Done when
verify green · `SMOKE AUTH PASSED` · log scan clean · committed + pushed.

## Next
`/run-prompt P07` — auth screens + CameraCapture (≈ 2.5 h)
