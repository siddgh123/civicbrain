# 07 — Security, Authentication and Privacy

Target: **OWASP ASVS 5.0 Level 2** for the areas below, OWASP API Security Top 10 (2023), India's DPDP Act 2023 + DPDP Rules 2025 (substantive duties apply from about May 2027; we build them now), CERT-In directions (6-hour incident reporting, 180-day logs, NTP sync) for a government deployment.

## 1. Authentication
- **Passwords:** 12–128 characters, any characters, no composition rules, checked against a local blocklist (top 100k common passwords file in `backend/src/main/resources/security/`) and against the user's name/e-mail; no forced rotation. Hash: `DelegatingPasswordEncoder` with default `new Argon2PasswordEncoder(16, 32, 1, 19456, 2)` (Argon2id, 19 MiB, 2 iterations), bcrypt(12) accepted for upgrade.
- **Login:** generic error "E-mail/phone or password is incorrect"; same timing for unknown accounts (hash a dummy password); lockout 15 min after 10 failures (`users.failed_login_count`, `locked_until`), `auth_events` row for every attempt. While locked, a wrong password still answers 401 `INVALID_CREDENTIALS` (no hint that the account exists); only the correct password answers 423 `ACCOUNT_LOCKED`. The login rate limit (30 / 15 min per identifier) sits above the lockout so both are testable.
- **E-mail OTP:** 6 digits from `SecureRandom`, 10-minute expiry, single use, 5 attempts per code, stored as `HMAC-SHA256(OTP_HMAC_KEY, otpId || code)` (hex) in `auth_otp_codes.code_hmac`, constant-time comparison. Resend ≥ 60 s apart. OTP e-mails are sent **synchronously by the auth service**, never through `notification_outbox`/`notifications` (so the plain code is never stored or logged); on SMTP failure → 503 `DEPENDENCY_UNAVAILABLE` and that OTP row is marked used.
- **TOTP (RFC 6238, SHA-1, 30 s, 6 digits, ±1 step):** mandatory for OFFICER and ADMIN, optional for CONTRACTOR/STAFF. Implemented in-house (~60 lines) and unit-tested with the RFC 6238 test vectors. Secret: 20 random bytes, stored AES-256-GCM encrypted (`TOTP_ENC_KEY`) in `users.totp_secret_enc`; `totp_last_used_step` blocks replay. ADMIN can reset a user's MFA (audited). `auth_events` types (V5): TOTP_ENABLED, TOTP_VERIFIED, TOTP_FAILED, TOTP_RESET, LOGOUT_ALL.
- **Access token:** JWT HS256 signed with `JWT_SECRET` (≥ 256 bits random), 15 min, claims `sub` (user id), `roles`, `iat`, `exp`, `iss=civicbrain`, `aud=civicbrain-web`, `typ=at+jwt` header; no PII. Validate alg (HS256 only), `iss`, `aud`, `typ`, `exp` (60 s skew) and `iat ≥ users.token_valid_after` (revocation: logout-all, password change/reset, role change, disable).
- **Refresh token:** 256-bit random opaque value in cookie `__Host-cb_rt` (`Secure; HttpOnly; SameSite=Strict; Path=/`), stored as SHA-256 hex in `auth_refresh_tokens` with `family_id`. Rotated on every refresh; presenting a rotated/revoked token revokes the whole family, writes `REFRESH_REUSE_DETECTED`, returns 401. Lifetime: citizen 30 days absolute / 7 days idle; officer/admin 24 h absolute / 1 h idle; contractor 7 days / 3 days.
- **CSRF:** only `/auth/refresh` and `/auth/logout` use the cookie → POST only, require header `X-CB-CSRF: 1`, check `Origin` against `APP_BASE_URL` (plus `APP_EXTRA_ORIGINS` in dev only; empty on the demo machine), SameSite=Strict. All other endpoints use the bearer header (not CSRF-able).
- **Sensitive changes** (e-mail, phone, password, disabling MFA) require the current password (re-authentication).

## 2. Authorization (deny by default)
- `SecurityFilterChain`: first `POST /api/v1/auth/logout-all` and `POST /api/v1/auth/password/change` → authenticated; then permit `/api/v1/auth/**`, `/api/v1/public/**`, `/api/v1/webhooks/**`, `POST /api/v1/client-errors`, `/actuator/health`, `/v3/api-docs/**` (profiles dev/test only), and every GET outside `/api/**`, `/actuator/**`, `/v3/**` (the SPA; unknown SPA routes forward to `/index.html` so deep links work in the demo build); `/api/v1/citizen/**` → CITIZEN; `/api/v1/officer/**` → OFFICER or ADMIN; `/api/v1/contractor/**` → CONTRACTOR or CONTRACTOR_STAFF; `/api/v1/admin/**` → ADMIN; `/api/v1/me/**`, `/api/v1/files/**` → authenticated; **`anyRequest().denyAll()`**.
- `@EnableMethodSecurity` + object checks **inside queries** (e.g. `findByIdAndUserId`, officer scope join on `officer_scopes`, contractor join on `action_plans.contractor_id`). Not found or not allowed → 404.
- Separate request/response DTOs per role (API3: a contractor never sees citizen phone/e-mail; a citizen never sees authenticity details or other users).
- Function-level (API5): ADMIN creates officers; OFFICER creates contractors and their staff; CONTRACTOR can manage nothing else.
- **Authorization matrix test** (`08_TEST_PLAN.md` §3) covers every endpoint × role × ownership case and fails if a new endpoint is missing from the matrix.

## 3. Input, files and output
- Jakarta Bean Validation on every DTO (sizes, patterns, ranges; lat 18.6–18.8, lon 73.6–73.8 for Talegaon payloads); unknown JSON properties rejected (`FAIL_ON_UNKNOWN_PROPERTIES`); request body limit 1 MB (JSON); multipart `max-file-size` 8 MB and `max-request-size` 25 MB (contractor forms send up to 3 photos); `MaxUploadSizeExceededException` → 413 `FILE_TOO_LARGE`.
- **Uploads:** allow JPEG/PNG only by magic bytes (not Content-Type), ≤ 8 MB, ≥ 320 px, ≤ 40 MP (decompression-bomb guard); read EXIF into `exif_extracted` (metadata-extractor), then re-encode (long side ≤ 1920 px, JPEG q85, no metadata) with a random UUID file name under `STORAGE_ROOT`; compute SHA-256 of the stored bytes. Never serve user files from a static folder. ASVS 5.2.x virus scanning: re-encoding removes active content; documented as the compensating control.
- SQL only via JPA/`JdbcClient` parameters (no string concatenation); PostGIS values via parameters.
- JSON output only; filenames in `Content-Disposition` sanitised; errors never contain stack traces, SQL or paths.

## 4. HTTP security headers (Spring + Nginx in demo)
`Content-Security-Policy: default-src 'self'; img-src 'self' blob: data: https://tile.openstreetmap.org; connect-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'` · `Strict-Transport-Security: max-age=31536000` (HTTPS only) · `X-Content-Type-Options: nosniff` · `Referrer-Policy: strict-origin-when-cross-origin` · `Permissions-Policy: camera=(self), geolocation=(self), microphone=(), payment=()` · `Cross-Origin-Opener-Policy: same-origin`. SPA and API on **one origin** (Vite proxy in dev, Spring static/Nginx in demo) → no CORS configuration.

## 5. Service-to-service and secrets
- AI service listens on `127.0.0.1:8001` only; admin endpoints require a 60-second JWT signed with `AI_SERVICE_JWT_SECRET`, `aud=civicbrain-ai`, verified with PyJWT (`algorithms=["HS256"]`, `require=["exp","iat","aud","iss"]`). The worker talks to PostgreSQL with the `civicbrain_ai` role.
- Secrets only in `.env` (git-ignored) and the Windows user environment; `.env.example` has dummies; gitleaks in CI and as a pre-commit hook; rotate any key that was ever committed. Antigravity must never be given real WhatsApp/SMTP credentials during the build (use `WHATSAPP_PROVIDER=log` and Mailpit).
- Database: app connects as `civicbrain_app`, worker as `civicbrain_ai` (roles: `db/tools/create_roles_template.sql`; rights: `R__civicbrain_grants.sql`), never `postgres`. Only Flyway (and the human scripts) use the owner account `PG_ADMIN_USER`.

## 6. Logging, audit, monitoring
- Log: auth events, OTP sent/verified/failed, token reuse, role/scope changes, status changes, assignments, uploads, plan edits/downloads, privacy requests, admin actions, rate-limit hits, 5xx errors.
- Never log: passwords, OTPs, TOTP secrets, tokens, cookies, full phone numbers (mask `+91******4321`), photo bytes, full request bodies. Strip CR/LF from logged user input (log injection).
- Retention: `audit_logs` and `auth_events` 365 days (covers CERT-In 180 days and DPDP one year); `fn_purge_expired()` daily. Server clock synced (Windows time service; NTP in production).

## 7. Privacy (DPDP)
- Versioned privacy notice shown and accepted at registration (`privacy_notices`, `user_consents`); separate optional consents: WhatsApp messages, public photo, AI training; withdrawal as easy as giving (profile page); withdrawn AI-training consent excludes the user's photos from future training exports.
- Data-principal requests (`data_subject_requests`): access (instant JSON export), correction, erasure (anonymise the user in one transaction: `full_name = 'Deleted user'`, `email = 'deleted-<user_id>@invalid.invalid'` (the DB requires e-mail or phone), `phone = NULL`, random `password_hash`, `is_active = false`, `whatsapp_opt_in = false`, `email_opt_in = false`, TOTP cleared, `token_valid_after = now()`, refresh tokens revoked; photos deleted unless the complaint is still open; complaints kept as municipal records), withdraw consent, grievance; due in 90 days; admin queue.
- Minimisation: public map = `v_public_complaint_map` (no personal data, ~220 m snapping); citizen contact details visible only to officers in scope; photos public only when blurred + approved.
- Breach runbook (`13_DEMO_AND_DEPLOY.md` §6): contain, preserve logs, inform the council within hours so it can report to CERT-In in 6 hours and to the Data Protection Board / affected users without delay (detailed report within 72 hours).

## 8. Abuse prevention
Rate limits (`04_API_CONTRACT.md` §11); registration/forgot-password protected by ALTCHA (self-hosted proof-of-work, MIT) once abuse is seen (feature flag, off in dev); account enumeration: identical responses for existing/non-existing accounts; capture sessions single-use with 10-minute TTL.

## 9. Security gates (must pass before the demo)
Authorization matrix green · ZAP baseline 0 high/medium unresolved · Trivy (pinned version) 0 critical/high in dependencies/images · `npm audit --omit=dev` 0 high · `pip-audit` 0 high · gitleaks 0 findings · headers checked by an automated test · manual check of the ASVS L2 checklist in `docs/PROGRESS.md` (tick each item with the test that proves it).
