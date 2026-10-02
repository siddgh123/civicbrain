# P25 — OPTIONAL stretch: officer/admin TOTP (two-factor login)
**Day 6/7 · agent ≈ 2 h · human ≈ 10 min · Needs: P24 with no open blocker · Model: strongest**
Run only if all gates so far are green and there are at least 4 hours left before the freeze. Otherwise skip (it is on the
MVP OUT list as "stretch") and say "skipped" in PROGRESS.

## Goal
Officers and admins must use a 6-digit authenticator code at login (FR-02); first login shows the setup with a manual key.

## Read first
`docs/04_API_CONTRACT.md` §1 (mfa/setup, mfa/confirm, mfa/verify) · `docs/07_SECURITY.md` §1 (TOTP, encrypted secret, replay) ·
`docs/05_UI_SPEC.md` §3 (TOTP screens) · `tests/smoke/smoke_flow.py` (`login` handles `mfaRequired`)

## Build
1. Backend: `app.security.mfa-required=true` for OFFICER/ADMIN; login returns `{mfaRequired, mfaToken}` or
   `{mfaSetupRequired, mfaToken}`; setup returns `otpauthUri` + `secretBase32` (secret encrypted with `TOTP_ENC_KEY`, AES-GCM);
   confirm/verify with ±1 step window, a used time step is rejected (422 TOTP_INVALID); auth_events TOTP_*; `POST /admin/users/{id}/reset-mfa`.
2. E2E seed: officers/admin get TOTP enabled with the `.env.test` secrets (the smoke computes the codes).
3. Frontend: TOTP code screen; setup screen with the manual key in groups of 4 and the otpauth link text (no QR library is
   pinned - adding one is an ASK-FIRST item; Google Authenticator / Microsoft Authenticator accept manual keys).

## Tests
setup → confirm → login needs a code · wrong code 422 · replayed code 422 · admin reset-mfa forces setup again · smoke `--stage officer`
still passes (with TOTP).

## Verify (agent)
`.\mvnw.cmd -q verify` · frontend checks · E2E smoke `--stage all` → PASSED.

## Human step (≈ 10 min)
Log in on the laptop as the demo officer and the admin (dev stack) → set up TOTP in an authenticator app on your phone.

## Ask the human (yes/no)
- Q1. Did the authenticator setup and the next login with a code work for the officer and the admin?

## Next
`/run-prompt P26` (optional Playwright) or `/run-prompt P27` — bug bash
