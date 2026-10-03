# PROGRESS — CivicBrain build log

The agent updates this file in the same commit as every task. Humans approve each phase gate here.

## Current plan: 7-DAY MVP (`docs/09_BUILD_PLAN_7DAY.md`), 1–7 Oct 2026
| Day | Date | Gate (from §5) | Status | Evidence / bugs | Approved by |
|---|---|---|---|---|---|
| D1 | Thu 1 Oct | build laptop ready, backend + Flyway + seed, Vite layout, worker claims a job, YOLO training started, CI green | PASSED (human yes 2026-10-03 12:12; tag `d1-done`) | check-env all required PASS (8 WARN) · `verify-all.ps1 -SkipE2E` GREEN (SQL 7/7, 6/6, 11/11, 11/11 · backend 70 + 13 IT 0 failures incl. SchemaIT 74 tables + ward 1 · AI ruff clean, 82 passed · frontend lint/typecheck, 39 passed) · frontend build OK · Flyway v5 on `civicbrain`, 23 wards, seed 500 · dataset check exit 0 · Kaggle run committed · CI green incl. full-history gitleaks (human yes) · SCRIPT FIX `verify-all`/`start-backend`/`seed-e2e` `[NullString]::Value` (Task log "D1 gate") · commit b0a5f43 | human (yes 2026-10-03 12:12) |
| D2 | Fri 2 Oct | register → OTP → login, admin exists, priority 0 mismatches, duplicates test, YOLO ONNX detects | NOT STARTED | | |
| D3 | Sat 3 Oct | phone capture → submit → "Under review" < 60 s, SUBMITTED mail, duplicate → Linked | NOT STARTED | | |
| D4 | Sun 4 Oct | officer map/detail/actions, contractor created, WhatsApp sandbox, optimizer test | NOT STARTED | | |
| D5 | Mon 5 Oct | plan generate → reorder → approve → assign → "Contractor X assigned" to all owners, PDF; feature freeze | NOT STARTED | | |
| D6 | Tue 6 Oct | complete flow to CLOSED + rating on demo laptop with 2 phones, all mails | NOT STARTED | | |
| D7 | Wed 7 Oct | flow twice without error, `mvp-v1` tag, backup on USB | NOT STARTED | | |

## Autopilot log (single laptop, `/run-prompt P<nn>`)
Status values: NOT STARTED · IN PROGRESS · BLOCKED · DONE (human yes <date time>). The agent adds a detailed entry per prompt under "Task log".

| Prompt | What | Day | Status | Evidence (smoke / tests) |
|---|---|---|---|---|
| P01 | Repo, environment check, databases | D1 | DONE (human yes 2026-10-02) | check-env 0 FAIL (13 WARN) · SQL tests 4/4 (7/7, 6/6, 11/11, 11/11) · AGENT_CAN_START=yes · INVENTORY written · commit 6c2481e |
| P02 | AI service skeleton + venv + worker loop | D1 | DONE (human yes 2026-10-02 19:45) | ruff clean · pytest 82 passed ×5 (14 integration on civicbrain_test) · worker alive, waits for schema (dev DB empty until P04) · /health 503 "schema missing" · V4 claim over-claim found + handled (V6 fix = Phase 2) · commit f0575ee |
| P03 | Dataset check + fixtures + Kaggle package (YOLO training starts) | D1 | DONE (human yes 2026-10-02 20:29) | dataset check exit 0 (0 label problems, 0 leakage, 3,258 train lines) · 6 fixtures + README · zip 6,802 files / 174.6 MB · ruff clean · pytest 82 passed · Kaggle cells 1-4 OK, 0.9 min/epoch, committed run "Running" (finish ≈ 22:30 at the latest) · commit 8141812 |
| P03b | Fallback: auto-label (only if labels are missing) | D1 | NOT STARTED | |
| P04 | Backend skeleton + Flyway + demo seed | D2 | DONE (human yes 2026-10-03 10:24) | mvnw verify 83 tests 0 failures (70 unit + 13 IT on Testcontainers PostGIS) · Flyway "Successfully applied 6 migrations" on `civicbrain` · `DB check: 23 wards visible to civicbrain_app` · seed complaints=500, wards=23 · SQL tests 4/4 · AI /health 200 db ok |
| P05 | Frontend skeleton | D2 | DONE (human yes 2026-10-03 11:28) | lint 0 problems · typecheck 0 errors · vitest 39 passed (6 files, lines 87 %) · build OK · `start-all -Only frontend` healthy · walkthrough 6 passed (desktop + 390 px) · proxy `/api/v1/public/categories` → backend 404 problem+json · `package-lock.json` committed · commit 79d097b |
| P06 | Auth backend + E2E seed runner + smoke auth | D2 | IN PROGRESS (verified, awaiting human Q1) | mvnw verify 152 tests 0 failures (107 unit + 45 IT on Testcontainers PostGIS + Mailpit) · `SMOKE AUTH PASSED: 19 / 19` (twice) · seed-e2e 5 accounts (3 fixed) · log scan 0 hits · frontend lint/typecheck/39 tests green |
| P07 | Auth screens + CameraCapture | D2 | NOT STARTED | |
| P08 | Text classifier, YOLO detector (install Kaggle model), authenticity | D3 | NOT STARTED | |
| P09 | Priority + duplicates (FROZEN) + MiniLM | D3 | NOT STARTED | |
| P10 | Complaint intake API + e-mail outbox + smoke intake | D3 | NOT STARTED | |
| P11 | Citizen screens | D3 | NOT STARTED | |
| P12 | Measure, estimate, quality, analyze orchestrator + smoke analysis | D4 | NOT STARTED | |
| P13 | Phone test over the tunnel | D4 | NOT STARTED | |
| P14 | Officer/admin/contractor-management API + smoke officer | D4 | NOT STARTED | |
| P15 | Officer portal UI | D4 | NOT STARTED | |
| P16 | WhatsApp (Twilio sandbox / log) | D5 | NOT STARTED | |
| P17 | Planning engine (haversine + OR-Tools) | D5 | NOT STARTED | |
| P18 | Plan API + PDF + assignment notifications + smoke plan | D5 | NOT STARTED | |
| P19 | Plan builder UI | D5 | NOT STARTED | |
| P20 | Contractor API + smoke contractor | D6 | NOT STARTED | |
| P21 | AI polish + message bodies | D6 | NOT STARTED | |
| P22 | Contractor screens + citizen feedback UI | D6 | NOT STARTED | |
| P23 | Close/reopen + security pass + smoke all (FEATURE FREEZE) | D6 | NOT STARTED | |
| P24 | Full-flow test with 2 phones + demo accounts | D7 | NOT STARTED | |
| P25 | Officer TOTP (stretch, optional) | D6/D7 | NOT STARTED | |
| P26 | Playwright happy path (optional) | D7 | NOT STARTED | |
| P27 | Bug bash | D7 | NOT STARTED | |
| P28 | Demo build + Gmail + backup | D7 | NOT STARTED | |
| P29 | Report material (metrics, screenshots, limits) | D7 | NOT STARTED | |
| P30 | Rehearsal + freeze + tag mvp-v1 | D7 | NOT STARTED | |

**Open issues (carry into the named prompt)**
- **RESOLVED 2026-10-03 09:36 - P03 S2 licence (`tests/fixtures/images/waterlogging_1.jpg`):** CC BY 4.0, attribution added.
  S2 = "Waterlogging Dataset" by yolo and car accident detection,
  https://universe.roboflow.com/yolo-and-car-accident-detection-xaltb/waterlogging (licence confirmed by the human/team).
  `data/yolo/dataset_sources.csv` S2 row (URL + `CC BY 4.0`) and `tests/fixtures/images/README.md` (attribution) updated;
  the fixture stays, nothing to do in P13.

## Full plan (after the deadline)
- **App track:** P0 — Machines, repo, Antigravity (status: covered by the MVP days; re-check its gate)
- **ML track:** P2 — ML data and models (status: NOT STARTED — MVP used the existing images only)
- **Known issue (P02):** V4 `fn_claim_jobs` can claim more jobs than `p_limit` (LIMIT … FOR UPDATE SKIP LOCKED re-scanned in a
  nested-loop semi join). MVP: the worker processes / releases every claimed row. Phase 2: V6 migration with
  `WITH picked AS MATERIALIZED (SELECT … LIMIT p_limit FOR UPDATE SKIP LOCKED) UPDATE jobs … FROM picked` (Task log P02).

## Phase gates
| Phase | Status | Gate evidence (command → result) | Approved by / date |
|---|---|---|---|
| P0 Setup | NOT STARTED | | |
| P1 Database | NOT STARTED | | |
| P2 ML data & models | NOT STARTED | | |
| P3 Backend & security | NOT STARTED | | |
| P4 Citizen portal | NOT STARTED | | |
| P5 Notifications | NOT STARTED | | |
| P6 AI worker | NOT STARTED | | |
| P7 Officer dashboard | NOT STARTED | | |
| P8 Action plans | NOT STARTED | | |
| P9 Contractor & closure | NOT STARTED | | |
| P10 Privacy & hardening | NOT STARTED | | |
| P11 Measurement & evaluation | NOT STARTED | | |
| P12 Demo readiness | NOT STARTED | | |

## Task log (newest first)

### 2026-10-03 — P06 — Auth backend, E2E seed runner, smoke auth (IN PROGRESS, started about 12:40)
- Requirement(s): FR-01, FR-02, FR-04 (first admin), FR-60, NFR-01; docs/04 §1, §2, §3 (privacy notice), §11; docs/07 §1, §2,
  §6, §7; docs/12 §2; rule 10, rule 50; 09_7DAY §4 (register → OTP → login, generic 401, refresh rotation/reuse).
**Plan** (Claude Code, Auto mode):
1. Error code `PASSWORD_CHANGE_REQUIRED` (403) → docs/12 §2 first, then `ErrorCode` + `en.json`; RFC 9457 extension members
   (`otpId` on 403 EMAIL_NOT_VERIFIED).
2. Config: `RateLimitProperties` (`app.rate-limits.*`; `e2e` per-IP ×100, 100 complaints/24 h), `JwtConfig` (HS256 encoder/decoder;
   validators iss, aud, `typ=at+jwt`, exp ±60 s, `iat ≥ token_valid_after`), `SecurityConfig` role areas + resource server +
   filters (PASSWORD_CHANGE_REQUIRED, 300/min per user).
3. `auth`: AuthController + DTOs · AuthService (register/decoy, verify/resend OTP, login/lockout, logout-all, password change) ·
   OtpService (HMAC, synchronous mail) · RefreshTokenService (`__Host-cb_rt`, rotation, reuse → family revoked) · AccessTokens ·
   PasswordPolicy (+ small blocklist) · AuthEvents · RateLimiter (Bucket4j, in memory).
4. `users`: UserAccounts (create user + consents; used by register, seed, bootstrap) + MeController (GET/PUT /me, POST /me/consents);
   `privacy`: GET /public/privacy-notice; `common/AuditLog`.
5. Runners: AdminBootstrapRunner (`bootstrap-admin`, no TOTP while mfa-required=false), E2eSeedRunner (`e2e-seed`, `_e2e` guard).
Tests first: ITs on Testcontainers PostGIS + Mailpit (`axllent/mailpit:v1.31.3`) for the prompt's list; unit tests for policy,
rate limiter, JWT, OTP codes. Verify: `.\mvnw.cmd -q verify` → E2E smoke (stop → seed-e2e -MinAccounts 3 → -E2E → smoke auth →
-Restart) → log scan. Forgot/reset (FR-03) last, only inside the time box.


**Results** (2026-10-03, verified 13:18 - well inside the 3 h estimate)
1. Files (`backend/`): `auth/` (`api/AuthController`, `AuthDtos`, `RefreshCookie`, `CurrentUser`; `service/AuthService`, `OtpService`,
   `AuthMailer`, `AccessTokens`, `RefreshTokens`, `TokenRevocationValidator`, `PasswordPolicy`, `AuthEvents`; `repo/OtpRepository`,
   `RefreshTokenRepository`) · `users/` (`model/Role`, `UserAccount`; `repo/UserRepository`; `service/UserAccounts`, `MeService`;
   `api/MeController`; `setup/AdminBootstrapRunner`, `E2eSeedRunner`) · `privacy/` (`PrivacyNoticeController`, `PrivacyRepository`,
   `ConsentType`) · `common/` (`RateLimiter`, `RateLimitedException`, `AuditLog`, `Db`, `Masking`, `Times`; `ApiException`/`ApiProblem`
   RFC 9457 extension members; Retry-After in the advice and `ProblemWriter`) · `config/` (`JwtConfig`, `PasswordConfig`,
   `RateLimitProperties`, `PasswordChangeRequiredFilter`, `UserRateLimitFilter`, `SecurityConfig` role areas + resource server,
   `SecurityProblemHandler` → SESSION_REVOKED) · `CivicbrainApplication` (exits after the one-shot profiles) · `application.yml`
   (`app.rate-limits.*`, `server.forward-headers-strategy: native`), `application-e2e.yml` (per-IP ×100, 100 complaints/24 h) ·
   `resources/security/common-passwords.txt`. Docs: `docs/12_ERROR_HANDLING.md` §2 + `PASSWORD_CHANGE_REQUIRED` (403), also in
   `ErrorCode` and `frontend/src/i18n/en.json`.
2. Endpoints: POST `/auth/register` (202; decoy otpId + owner mail for an existing e-mail/phone), `/auth/verify-otp`, `/auth/resend-otp`,
   `/auth/login` (+ `__Host-cb_rt`), `/auth/refresh`, `/auth/logout`, `/auth/logout-all` (bearer), `/auth/password/change` (bearer),
   `/auth/password/forgot` + `/auth/password/reset` (FR-03, built last, inside the time box); GET/PUT `/me`, POST `/me/consents`;
   GET `/public/privacy-notice` (Cache-Control 60 s).
3. Tests (all new): ITs `AuthRegistrationIT` 8 (register → OTP mail in the Mailpit container → verify → login → /me; decoy for e-mail and
   phone with owner mail; OTP code absent from `notification_outbox`/`notifications`/`auth_events`; OTP_EXPIRED; 5 attempts →
   OTP_ATTEMPTS_EXCEEDED; resend 1/60 s → 429 + Retry-After; PASSWORD_POLICY; validation; register 5/h per IP → 429; privacy notice) ·
   `AuthLoginIT` 9 (same 401 body for wrong password/unknown account; 10 failures → 423, wrong while locked → 401, unlock; phone login
   forms; JWT header/claims; tampered/typ JWT/other audience → 401; role areas; must_change_password → 403 PASSWORD_CHANGE_REQUIRED
   then change → old token SESSION_REVOKED, refresh works; logout-all kills existing token + every family; login 30/identifier → 429) ·
   `AuthSessionIT` 5 (rotation + reuse → family dead + REFRESH_REUSE_DETECTED; no CSRF header/wrong/missing Origin → 403; logout
   clears cookie; missing/unknown/expired → 401; officer 1 h vs citizen 7 d idle) · `MeIT` 3 · `PasswordResetIT` 4 ·
   `SetupRunnersIT` 3 (E2eSeedRunner refuses DB `test`; bootstrap refuses when an ADMIN exists; creates a verified Argon2id ADMIN
   without TOTP/forced change, rolled back). Unit: `AccessTokensTest` 7, `PasswordPolicyTest` 12, `RateLimiterTest` 3, `MaskingTest` 10,
   `ProblemExtensionsTest` 5. Honest note: the test classes were written after most of the main code (not one-by-one test-first);
   PasswordResetIT was written before its code. Test infra: `MailpitContainerConfig` + `MailpitClient` (in `@IntegrationTest`),
   `AuthItSupport`; `WebSliceTest` imports `RateLimiter` + a rejecting JwtDecoder (slice has no user table); 2 endpoints added to
   `TestController`. No existing test assertion changed.
4. Runs (in `backend` unless noted):

   | Check | Command | Result | |
   |---|---|---|---|
   | backend run 1 | `.\mvnw.cmd -q verify` | 1 error in my new `AccessTokensTest` (`Jwt.getIssuer()` converts "civicbrain" to a URL) → test reads the claim as a string | FAIL→fixed |
   | backend run 2 | same | unit all green; IT 1 failure: owner "someone tried to register" mail skipped - it shared the 1/60 s OTP bucket with the owner's own code mail → own bucket key (`registration-attempt:<e-mail>`, same limits) | FAIL→fixed |
   | backend run 3 | same | exit 0, 148 tests 0 failures | PASS |
   | seed run 1-2 (repo root) | `pwsh -NoProfile -File scripts\dev\seed-e2e.ps1 -MinAccounts 3` | `e2e-seed run failed (exit 1)`: non-web profile has no `HttpSecurity` bean → `SecurityConfig` `@ConditionalOnWebApplication(SERVLET)` | FAIL→fixed |
   | backend run 4 (after FR-03) | `.\mvnw.cmd -q verify` | exit 0, **`TOTAL tests=152 failures=0 errors=0 skipped=0`** (surefire 107 + failsafe 45); test log scanned: 0 tokens/passwords/OTPs | PASS |
   | seed (final jar) | `pwsh -NoProfile -File scripts\dev\seed-e2e.ps1 -MinAccounts 3` | `E2E RESET DONE: 48 tables emptied, 27 reference tables kept` · `E2E seed on civicbrain_e2e: 5 accounts created, 0 already present` · `PASS E2E database civicbrain_e2e ready with 3 fixed accounts` | PASS |
   | E2E stack | `pwsh -NoProfile -File scripts\dev\start-all.ps1 -E2E` | `PASS stack 'e2e' is up`; backend log `Started CivicbrainApplication`, `DB check: 23 wards visible to civicbrain_app` | PASS |
   | smoke | `ai-service\.venv\Scripts\python.exe tests\smoke\smoke_flow.py --stage auth` | **`SMOKE AUTH PASSED: 19 / 19`** (run before and again after FR-03) | PASS |
   | log scan | `Select-String -Path logs\backend.log -Pattern 'eyJ[A-Za-z0-9_-]{10,}\|password=\|otp.{0,20}\d{6}'` | no output (0 hits); frontend/worker/ai-api/seed logs 0 hits; 0 ERROR lines | PASS |
   | Mailpit | API search `to:@smoke.local` | `smoke-0a093976@smoke.local \| Your CivicBrain verification code` (first run) | PASS |
   | dev stack back | `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Restart` | 5 services healthy; GET `:5173/api/v1/public/privacy-notice` → `200 2026-10-v1 …+05:30 max-age=60, public` | PASS |
   | frontend (en.json) | in `frontend`: `npm run lint` · `npm run typecheck` · `npm test -- --run` | exit 0 · exit 0 · `Tests 39 passed (39)` | PASS |
- DECISION: auth tables through `JdbcClient` (explicit SQL, `CAST(:ip AS inet)`), no JPA entities yet: avoids `ddl-auto=validate`
  type pitfalls (`char(64)`, `inet`) and JPA/JDBC flush ordering. Timestamps are bound as UTC `OffsetDateTime` from the app `Clock`.
- DECISION: `must_change_password` travels as the JWT claim `mcp=true`; the filter allows only GET `/me`, POST `/auth/password/change`,
  `/auth/logout`, `/auth/logout-all`, `/auth/refresh` (PUT `/me` is blocked too - stricter reading of "except /me").
- DECISION: `token_valid_after` arithmetic in whole seconds (JWT `iat` has no fraction): revocation sets
  `greatest(now, trunc(old)+1 s) + 1 s`; tokens get `iat = max(trunc(now), ceil(token_valid_after))` (≤ 2 s in the future right after a
  revocation). The validator compares `iat >= ceil(token_valid_after)` and also rejects inactive users → 401 SESSION_REVOKED.
- DECISION: wrong current password on `/auth/password/change` → 400 VALIDATION_FAILED (field `currentPassword`), not 401 (a 401 would
  trigger the client's silent refresh); it counts towards the 10-failure lockout. `POST /me/consents` → 200 with the `/me` body.
- DECISION: 403 EMAIL_NOT_VERIFIED carries `otpId` (+ `expiresInSec`) as RFC 9457 extension members; inside the 60-s resend limit it
  returns the newest code already sent. Decoy register writes `auth_events` OTP_SENT with `details.decoy=true` (no better V5 type).
- DECISION: `server.forward-headers-strategy: native` - behind the Vite proxy / Cloudflare tunnel every client is 127.0.0.1, so
  per-IP limits (5 registrations/h) would be global in the demo; Tomcat trusts X-Forwarded-For only from internal-proxy addresses.
- DECISION: forgot-password has its own 5/h per-IP bucket (`forgot:<ip>`), the owner notice its own per-destination bucket.
  Rate-limit buckets are in memory with a 100,000-bucket safety reset. `mfa-required=true` without TOTP flows fails closed (403
  MFA_REQUIRED for OFFICER/ADMIN) until P25. E2eSeedRunner/AdminBootstrapRunner never set TOTP while `mfa-required=false`.
- Open / hand-offs: **P07** login/register/OTP/forced-change screens use `otpId` from the 403 body and refresh after a password
  change (old access token is revoked). **P14** E2eSeedRunner adds officers/contractors/staff (`SPECS` list). **P28** SPA GET permit
  (07 §2) is not added yet (the P04 test expects `GET /` → 401). Known limit: forgot-password timing differs by the SMTP send time
  for known vs unknown e-mails (real code mail is synchronous). Blocklist is a small local list (07 §1's 100k file = Phase 2).

### 2026-10-03 — D1 follow-up — SCRIPT FIX `Import-DotEnv` empty values (DONE 2026-10-03 12:16, human request)
- **SCRIPT FIX:** same root cause as the D1 gate fix (PowerShell turns `$null` into `""`; since .NET 9
  `SetEnvironmentVariable(name, "")` keeps an empty variable). `scripts/dev/_common.ps1` `Import-DotEnv`: a `.env` line
  `KEY=` (empty value) now calls `SetEnvironmentVariable($key, [NullString]::Value, 'Process')` → the variable is removed (as
  before .NET 9), so Spring defaults like `${KEY:x}` apply again; non-empty values are set as before. The returned dictionary
  is unchanged (`$vars[$key] = $val`, empty string kept), so callers that read it (e.g. verify-all's `.env` hiding) work as before.
- Checks (repo root):

  | Check | Command | Result |
  |---|---|---|
  | env | `pwsh -NoProfile -File scripts\dev\check-env.ps1` | `RESULT: all required checks PASS (8 WARN)` (same 8 WARN as the D1 gate) |
  | restart | `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Restart` | stopped backend/frontend/worker/ai-api; `PASS mailpit healthy` · `PASS ai-api healthy` · `PASS worker healthy` · `PASS frontend healthy` · `PASS backend healthy` · `PASS stack 'dev' is up: http://localhost:5173   (Mailpit http://localhost:8025)` |
  | status | `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Status` | mailpit, ai-api, worker, frontend, backend: Healthy `yes` (all 5) |
  | backend log (start 06:45 UTC) | `logs/backend.log` | `Successfully validated 6 migrations` · `Started CivicbrainApplication in 5.184 seconds` · `DB check: 23 wards visible to civicbrain_app`; only WARN = Thymeleaf "Cannot find template location" (also in the 10:13 start, not related) |
  | worker log (since restart) | `logs/worker.log` | `worker started: database civicbrain, polling every 2 s …`; WARNING "model files not ready, REQUIRE_MODELS=false" (expected until P08); no ERROR |
- Note: Mailpit is now healthy too (it was not running at the D1 gate; P06 needs it for OTP mails).

### 2026-10-03 — D1 gate (`/phase-gate D1`, "after P05") — PASSED (human yes 2026-10-03 12:12, tag `d1-done`)
- Gate items: `prompts/README.md` "Day gates" D1 row + the 09_BUILD_PLAN_7DAY §4 tests that exist so far (DB SQL tests,
  backend IT "context + Flyway V1-V5 (74 tables, fn_locate_point ward 1)"); 09_7DAY §5 Gate D1 extras (worker claims and
  finishes a job, Flyway history on `civicbrain`). No smoke stage exists yet (`auth` comes with P06).
- **Run 1 (11:37-11:44) - FAIL:** `pwsh -NoProfile -File scripts\dev\verify-all.ps1 -SkipE2E` → `VERIFY-ALL: FAILED`: DB PASS,
  Backend FAIL, AI/frontend NOT RUN (log `logs/verify-all_20261003_113731.txt`). All 13 ITs: `BindValidationException … field
  'baseUrl': rejected value []; … origin System Environment Property "APP_BASE_URL"`. A direct `.\mvnw.cmd -q verify` (in
  `backend`) was green (70 + 13, 0 failures) → the backend code is fine, the wrapper script was wrong. All other items passed.
  CI was not yet confirmed. The commit of the run-1 record was refused by the auto-mode check (red verify-all), so it was left
  staged and goes into this commit.
- **SCRIPT FIX (human yes 2026-10-03, Q1):** root cause (human): PowerShell turns `$null` into `""` for .NET `string`
  parameters, and since .NET 9 `[Environment]::SetEnvironmentVariable(name, "")` sets an empty value instead of deleting the
  variable. `verify-all.ps1` hid the `.env` keys from the test runs with `SetEnvironmentVariable($k, $null)` → the JVM saw
  `APP_BASE_URL=""`, the environment beats `application-test.yml` (`app.base-url: http://localhost:5173`) → `@NotBlank` failed.
  CI never defines the variable → green there. Changes (pass `[NullString]::Value`, the real null):
  1. `scripts/dev/verify-all.ps1` `Invoke-WithEnv`: set loop and restore loop (`$null` value → `[NullString]::Value`, else the value).
  2. `scripts/dev/start-backend.ps1` line 34 (E2E profile: `SMTP_USER`/`SMTP_PASSWORD` unset → no SMTP login to Mailpit).
  3. `scripts/dev/seed-e2e.ps1` line 86 (same two keys for the `e2e-seed` run).
  `scripts/` grep: no other `SetEnvironmentVariable(…, $null)` / `$env:X = $null`. Verified by run 2 (verify-all backend step
  green). Items 2-3 are verified when the E2E stack first runs (P06: `seed-e2e.ps1`, `start-all.ps1 -E2E`); `start-backend.ps1`
  is human-only, so it was edited, not run.
  Observation (not changed): `_common.ps1` `Import-DotEnv` line 55 sets every `.env` key into the process; with .NET 9 a key
  with an empty value (`KEY=`) is now an empty variable instead of an absent one, so a Spring default `${KEY:x}` would no longer
  apply for it. The dev stack starts healthy with the current `.env`.
- **Run 2 (11:57-11:59) - all PASS:**

  | Gate item | Evidence (command → result) | Result |
  |---|---|---|
  | check-env 0 FAIL | `pwsh -NoProfile -File scripts\dev\check-env.ps1` → `RESULT: all required checks PASS (8 WARN)` (long paths, `civicbrain_e2e` not yet (P06), OSRM (Phase 2), mailpit exe (Docker fallback), ffmpeg, k6, 7z, YOLO weights (P08)) | PASS |
  | `verify-all.ps1 -SkipE2E` | `VERIFY-ALL: GREEN (SKIP = component not built yet)` - DB PASS 1 s · Backend PASS 49 s · AI PASS 6 s · Frontend PASS 15 s · E2E SKIP; log `logs/verify-all_20261003_115728.txt` | PASS |
  | SQL tests 4/4 | (verify-all DB step) `ROLE TESTS PASSED: 7 / 7` · `NEGATIVE TESTS PASSED: 6 / 6` · `V4 TESTS PASSED: 11 / 11` · `V5 TESTS PASSED: 11 / 11` | PASS |
  | backend verify green | (verify-all backend step, `mvnw -q -B verify` without `.env` values) reports 11:57/11:58: surefire `tests=70 failures=0 errors=0 skipped=0`, failsafe `tests=13 failures=0 errors=0 skipped=0` | PASS |
  | §4 IT context + Flyway V1-V5, 74 tables, `fn_locate_point` ward 1 | `SchemaIT` `Tests run: 5, Failures: 0, Errors: 0` (`flywayAppliedV1ToV5AndTheGrantsMigration`, `theApplicationTablesOfTheSchemaReferenceExist` (74), `locatePointFindsWardOneInsideTheBoundary`, 23 wards, job enqueue) | PASS |
  | Flyway built `civicbrain` | `logs/backend.log`: `Successfully applied 6 migrations to schema "public", now at version v5` · `DB check: 23 wards visible to civicbrain_app`; `start-all.ps1 -Status` → backend/frontend/ai-api/worker healthy (backend runs with `ddl-auto=validate`) | PASS |
  | seed 500 complaints | `pwsh -NoProfile -File scripts\dev\db-setup-main.ps1 -Seed` (read-only when data exists; checks V5 in `flyway_schema_history` first) → `PASS complaints already has 500 rows - seed skipped` | PASS |
  | AI pytest green (worker claims + finishes a job on `civicbrain_test`) | (verify-all AI step) `All checks passed!` · `82 passed, 1 warning in 4.36s` (0 skipped; `tests/it/test_worker_it.py::test_successful_job_is_succeeded`, retry/dead/stale/timeout/stop cases) | PASS |
  | dataset check passed | `…python.exe ai-service\training\prepare_mvp_dataset.py --root data\yolo --out-dir data\yolo\mvp` → `leakage groups: 0`, `train_mvp.txt: 3258 lines`, `label problems: 0`, exit 0 (same as P03) | PASS |
  | Kaggle run committed | P03 human yes 2026-10-02 20:29 (committed version "Running"); `kaggle_download/civicbrain_yolo_outputs.zip` present (git-ignored, installed in P08) | PASS |
  | frontend lint/typecheck/test/build green | (verify-all frontend step) lint + typecheck exit 0 · `Test Files 6 passed (6)` `Tests 39 passed (39)`; in `frontend`: `npm run build` → `✓ 224 modules transformed` `✓ built in 402ms` | PASS |
  | CI green (GitHub) | human yes 2026-10-03 (Q2): latest CI run on `main` all green; "Run workflow" on `main` (full-history gitleaks, open since P01) → every job green | PASS |
  | `git status` clean | before this commit only this gate's files changed (`docs/PROGRESS.md` + the 3 SCRIPT FIX scripts); clean after commit | PASS |
  | no new TODO/FIXME without issue link | `git grep -n -I -E "TODO\|FIXME"` (code, no docs/lock) → 0 hits | PASS |
  | PROGRESS entry per task | Task log has P01 (+ follow-up), P02, P03, P04, P05; P03b not needed (labels present) | PASS |
  | requirement IDs covered | D1 IDs: NFR-03 → `ai-service/tests/it/test_worker_it.py` (stale jobs requeued); others are doc sections, each with its tests in the P01-P05 entries | PASS |
- Notes: the D1 gate's wording "seed 500 complaints" and "Flyway built `civicbrain`" are proven on the dev DB without psql
  (script + backend log). One read-only Bash listing of mine used `cd backend/target` in run 1, which moved the PowerShell
  location; the next `npm run build` failed with `ENOENT … backend\target\package.json` (nothing written), re-run in
  `frontend` → green. A diagnostic probe of the `$null` behaviour was denied by the auto-mode check and not retried.
- Commit: the auto-mode check refused my commit of the fix + run-2 record (its message named a human-only script); the human
  committed and pushed it as `b0a5f43` "fix(infra): really unset env vars in dev scripts; D1 gate passed - awaiting approval".
  Rule from the human: commit messages never name a human-only script.
- Human answer (2026-10-03 12:12): **Approve D1: yes** → D1 PASSED, commit, push, tag `d1-done`.
- Next: `/run-prompt P06` (auth backend + E2E seed runner + smoke auth; first real run of the fixed `seed-e2e.ps1` and the
  E2E start path).

### 2026-10-03 — P05 — Frontend skeleton (DONE, human yes 2026-10-03 11:28)
- Requirement(s): docs/05_UI_SPEC.md §1, §2, §3 (landing), §7, §8; docs/12_ERROR_HANDLING.md §2, §6; rule 20; docs/09_BUILD_PLAN.md
  P0 step 5 (frontend); 09_BUILD_PLAN_7DAY §1 (Vite layout).
**Plan** (Claude Code, Auto mode):
1. In `frontend`: `npm install` (package.json unchanged) → commit `package-lock.json`; peer conflict → stop and ask.
2. Config by hand: `index.html`, `vite.config.ts` (react + tailwind plugins, 5173 strictPort, `/api` → :8080 `changeOrigin:false`,
   `allowedHosts ['.trycloudflare.com']`), `vitest.config.ts` (jsdom, setup = jest-dom + MSW server, include/exclude per prompt),
   `tsconfig.json`/`.app`/`.node` (strict), `eslint.config.js` (flat), `playwright.walkthrough.config.ts` (CLAUDE.md).
3. Tests first: `StatusBadge.test.tsx` (11 statuses: label + icon), `App.test.tsx` (landing heading, 404, `/officer` → `/login`),
   `api.test.ts` (MSW 422 problem+json → `ApiError{code, fieldErrors}`).
4. `src/lib/api.ts` + `queryClient.ts` (GET 2 retries, not 4xx; mutations 0) · `src/auth/AuthProvider.tsx` placeholder + `RequireAuth`/
   `RequireRole` · `src/i18n` (`en.json`, `errors.<CODE>` for all 38 codes) · router (`/`, `/login`, `/register`, `/citizen/*`,
   `/officer/*`, `/contractor/*`, `/c/:publicRef`, 404) · layouts (Citizen/Contractor bottom nav, Officer left nav) · components
   (`StatusBadge`, `icons/`, `EmptyState`, `ErrorState`, `PageSkeleton`, `Toast`) · landing page (05 §3).
5. Verify: `npm run lint` · `npm run typecheck` · `npm test -- --run` · `npm run build` · `start-all.ps1 -Only frontend` ·
   walkthrough `walkthrough/P05_landing.spec.ts` → `P05_landing_desktop.png` / `P05_landing_mobile.png` · GET
   `:5173/api/v1/public/categories` → backend 401/404 JSON. Record, commit, push; Q1-Q2.

**Results**
1. `npm install` (in `frontend`, Node 24.19.0 / npm 11.17.0) → `added 345 packages … found 0 vulnerabilities`, no peer conflict;
   `package.json` unchanged (0 diff lines); `package-lock.json` (lockfileVersion 3) created, contains the linux-x64 native bindings
   (`@rolldown/binding-linux-x64-gnu`, `@tailwindcss/oxide-linux-x64-gnu`, `lightningcss-linux-x64-gnu`) so CI `npm ci` works.
   `npm ls`: msw **3.0.1** top level as pinned; vitest's `@vitest/mocker` pulls a nested `msw@2.15.0` (optional peer, browser mode
   only, unused). npm 11 "allow-scripts" warning: msw's postinstall not run (it only copies the browser worker file - not needed).
2. Tests first: 5 test files written before the code → first run `Test Files 5 failed (5)` (modules missing) = red.
3. Files (`frontend/`): `index.html`, `public/favicon.svg`, `vite.config.ts`, `vitest.config.ts`, `tsconfig.json`/`.app`/`.node`,
   `eslint.config.js`, `playwright.walkthrough.config.ts`, `walkthrough/P05_landing.spec.ts`; `src/`: `main.tsx`, `App.tsx`,
   `index.css` (Tailwind 4 `@theme`: brand + `--color-status-{neutral,info,warning,success,danger}-{bg,fg,border}`, AA pairs),
   `app/` (`routes.tsx`, `TranslatedPlaceholder`), `lib/` (`api.ts`, `queryClient.ts`, `errorMessage.ts`, `complaintStatus.ts`),
   `auth/` (`authContext`, `AuthProvider` placeholder, `useAuth`, `tokenStore`, `RequireAuth`, `RequireRole`), `i18n/` (`en.json`,
   `index.ts`, typed keys `i18next.d.ts`), `components/` (`StatusBadge`, `icons/` 24 inline SVGs, `EmptyState`, `ErrorState`,
   `PageSkeleton`, `toast/` (`ToastProvider` aria-live, `useToast`), `OfflineBanner`, `PlaceholderPage`, `MobileLayout`, `Brand`,
   `SkipLink`), `features/public` (Landing, PublicShell/Layout, NotFound, Forbidden, RouteError, TrackLink, MessageCard),
   `features/citizen` (CitizenLayout, CitizenComplaintRefPage), `features/contractor/ContractorLayout`, `features/officer/OfficerLayout`,
   `test/` (`setup.ts`, MSW `server.ts`, `handlers.ts`).
   Tests (39): `StatusBadge.test.tsx` 13 (11 statuses: label + `data-icon` per 05 §1 + tone; MERGED fallback; list = DB CHECK) ·
   `App.test.tsx` 9 (landing heading + 3 links, 404, `/officer` → `/login?returnTo=%2Fofficer`, `/c/CB-000123` → login keeps ref,
   citizen at `/officer` → "No access", officer at `/officer/admin` → "No access" inside the layout, officer nav without Admin,
   admin nav with Admin, citizen bottom nav) · `api.test.ts` 8 (MSW: 422 problem → `ApiError{status, code, message=detail,
   fieldErrors, requestId}`, bearer from memory, query params, JSON vs multipart content type, 502 text → DEPENDENCY_UNAVAILABLE +
   `X-Request-Id`, 429 `Retry-After`, network → NETWORK_ERROR, schema mismatch → UNEXPECTED_RESPONSE) · `queryClient.test.ts` 3
   (2 retries, never on 4xx, mutations 0) · `ErrorState.test.tsx` 5 (en.json has all 38 codes of 12 §2, message by code + requestId +
   Try again, INTERNAL_ERROR reference once, unknown code / plain Error → generic text, RATE_LIMITED seconds) · `Toast.test.tsx` 1.
4. First green run: 37/38 - my new test `getByRole('link', 'Go to my start page')` found the header link and the card link →
   scoped to `<main>` (test never passed before). `tsc -b` then failed on `document`/`window` in the walkthrough's `page.evaluate`
   → `tsconfig.node.json` `lib: ["ES2023","DOM"]`.
5. `/verify frontend` (in `frontend`) + build + CI command:

   | Component | Command | Result line | Result |
   |---|---|---|---|
   | frontend | `npm run lint` | `eslint .` - no problems (exit 0) | PASS |
   | frontend | `npm run typecheck` | `tsc -b --noEmit` - no errors (exit 0; 50 `src` files + 3 configs + walkthrough checked) | PASS |
   | frontend | `npm test -- --run` | `Test Files 6 passed (6)` · `Tests 39 passed (39)` | PASS |
   | frontend | `npm run build` | `✓ 224 modules transformed` · `dist/assets/index-*.js 492.49 kB │ gzip: 152.15 kB` · `✓ built` | PASS |
   | frontend | `npm run test:coverage` (CI) | `39 passed` · Lines 87.25 % · Statements 83.8 % · Branches 78.91 % | PASS |
   | stack | `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Only frontend` | `PASS frontend healthy` · `PASS stack 'dev' is up: http://localhost:5173`; log `VITE v8.3.1 ready in 390 ms` | PASS |
   | browser | `npx playwright test --config playwright.walkthrough.config.ts walkthrough/P05` | `6 passed (6.9s)` (desktop 1280 + phone 390: landing, Report → `/login?returnTo=%2Fcitizen%2Fnew`, proxy) | PASS |
   | proxy | (same spec) GET `http://localhost:5173/api/v1/public/categories` | `404 {"type":"https://civicbrain.app/errors/NOT_FOUND",…,"code":"NOT_FOUND","detail":"Not found.","requestId":"8c4d00cd-…"}` from the backend | PASS |
6. Screenshots (opened and checked: readable, nothing cut off or overlapping, no horizontal scroll at 390 px, all badges text + icon):
   `docs/screenshots/P05_landing_desktop.png` (1280×800, full page), `docs/screenshots/P05_landing_mobile.png` (390 wide, full page).
- DECISION: client in `src/lib/api.ts` + `src/lib/queryClient.ts` as the prompt says; rule 20's `src/api/` will hold the per-resource
  typed hooks (from P07). Every 2xx body goes through a zod schema (`api.get(path, schema)`), `null` schema = no body.
- DECISION: non-problem error bodies (Vite proxy error, empty) get a code by HTTP status (401 UNAUTHENTICATED, 403 FORBIDDEN, 404
  NOT_FOUND, 413 FILE_TOO_LARGE, 429 RATE_LIMITED, 502-504 DEPENDENCY_UNAVAILABLE, other 5xx INTERNAL_ERROR, other 4xx
  MALFORMED_REQUEST) and the `X-Request-Id` header. Client-only codes: `NETWORK_ERROR` (status 0), `UNEXPECTED_RESPONSE`,
  `UNKNOWN` (in `en.json`). The UI never shows the server `detail` (ErrorState/toasts use `errors.<code>`).
- DECISION: access token in module memory (`auth/tokenStore.ts`), written synchronously by AuthProvider, read by the API client
  (no effect lag); `AuthProvider initialState` is for tests only. P07 adds login, silent refresh, shared refresh promise, 401 retry,
  BroadcastChannel logout.
- DECISION: data router (`createBrowserRouter`/`RouterProvider`), one `errorElement` per portal (12 §6 "error boundary per portal":
  friendly page + Reload); reporting to `POST /client-errors` waits for that endpoint. Track link `/c/:publicRef` (must match
  `CB-\d{6,}`, else 404) → login with `returnTo` → citizen `/citizen/complaints/ref/:publicRef` (placeholder, P11), other roles → their
  start page. Wrong role → "No access" page with "Go to my start page".
- DECISION (MVP OUT): officer nav = Dashboard, Complaints, Action plans, Contractors, Admin (ADMIN only) - no Duplicates queue or
  Notifications log (09_7DAY §1 OUT). Landing has no public-map link (public map OUT); footer: privacy link (`/privacy` placeholder,
  P07 fills it from `GET /public/privacy-notice`), the limits sentence (AI estimates preliminary; wards are analytical units) and
  "Prototype · SPPU final-year project" (honesty rule). Contractor bottom nav has one item (Today) until P22.
- DECISION: i18n keys are typed (`i18n/i18next.d.ts` = `typeof en`), so a missing key fails `tsc`. ESLint also bans
  `dangerouslySetInnerHTML`, `eval`, `any`. MSW 3 renamed `onUnhandledRequest` → `onUnhandledFrame`; setup uses `'error'`.
- Note: `start-all.ps1 -Status` shows Mailpit not healthy (not used in P05; P06 needs it for OTP mails - start-all brings it up).
  Two read-only Bash listings of mine used `cd`, which moved the shell into `frontend\node_modules`; npm still found the project;
  fixed with `Set-Location`, no effect on results.
- Open / hand-offs: **P07** auth screens, `src/api/` hooks, refresh/401 flow, `/privacy` content. **P11** citizen screens incl. the
  track target. **Later** `client-errors` reporting from `RouteErrorPage`; bundle is one 492 kB chunk (route-level `lazy` when the
  portals grow).
- Human answers (2026-10-03 11:28): **Q1 yes** - landing page with "Report a problem" seen at http://localhost:5173 ·
  **Q2 yes** - both screenshots look clean (desktop and phone width).
- DoD: [x] traces (05 §1-§3/§7/§8, 12 §2/§6, rule 20, 09_7DAY §1) [x] tests written first (red run), green [x] loading/empty/error
  components + error codes in `en.json` [x] lint/type clean, no secrets [x] committed `79d097b`, pushed (`2e2f779..79d097b  main -> main`)

### 2026-10-03 — P04 — Backend skeleton, Flyway, demo seed (DONE, human yes 2026-10-03 10:24)
- Requirement(s): docs/02_ARCHITECTURE.md §3, §6; docs/03_DATABASE.md §1, §3, §5; docs/07_SECURITY.md §2, §4;
  docs/12_ERROR_HANDLING.md §1-§3; rule 10; 09_BUILD_PLAN_7DAY §4 "context + Flyway V1-V5 (74 tables, fn_locate_point ward 1)".
**Plan** (Claude Code, Auto mode):
0. Human step: Spring Initializr zip (Boot 4.1.1, Java 25) → `backend\` (`pom.xml`, `mvnw.cmd`).
1. `pom.xml`: + flyway-database-postgresql, hibernate-spatial, spring-boot-testcontainers, testcontainers-postgresql,
   spring-security-test; springdoc 3.x, bucket4j_jdk17-core 8.x, metadata-extractor 2.19.x, openpdf 3.x, bcprov-jdk18on,
   wiremock-standalone 3.x (newest per `versions:display-dependency-updates`); JaCoCo report; Failsafe for `*IT`.
2. Copy-Item `flyway\V1…V5` + `R__civicbrain_grants.sql` → `backend\src\main\resources\db\migration\` (unchanged).
3. `application.yml` + `-dev/-demo/-e2e/-e2e-seed/-bootstrap-admin` skeletons; `src/test/resources/application-test.yml` (fake).
4. `config`: `@Validated @ConfigurationProperties` records, `Clock`, Jackson, `SecurityConfig` (deny-all, 07 §4 headers).
5. `common`: `ApiException`, `ErrorCode` (12 §2), `GlobalExceptionHandler` (RFC 9457 + SQLSTATE 12 §3), `RequestIdFilter`, page record.
6. `workflow.WorkflowActor` + source-scan test for `setStatus(`. 7. `DbStartupCheck` (dev/demo/e2e) logs the ward count.
Tests first: `SchemaIT`, `ErrorAdviceTest`, `SecurityConfigTest`, `ConfigValidationTest`, SQLSTATE mapping test, setStatus scan.
Verify: `.\mvnw.cmd -q verify` · `start-all.ps1 -Only backend` (Flyway 6 migrations, `DB check: 23 wards …`) ·
`db-setup-main.ps1 -Seed` (complaints=500, wards=23) · `db-rebuild-test.ps1 -Force` · P02 hand-off: `-Only ai-api,worker`
→ `/health` 200 `db: ok`. Record, commit, push; Q1-Q2.

**Results**
1. Human step done (2026-10-03): Spring Initializr → Boot **4.1.1**, Java 25, Maven wrapper 3.3.4 / Maven 3.9.16 (`only-script`),
   10 starters + `flyway-database-postgresql` + `thymeleaf-extras-springsecurity6` (both added by Initializr). JDK: Temurin 25.0.4.1.
2. Versions (`.\mvnw.cmd versions:display-dependency-updates -DprocessDependencyManagement=false`, again with
   `-DallowMajorUpdates=false` and `-DallowMinorUpdates=false` to stay inside each named line; JaCoCo via
   `versions:display-plugin-updates`) - newest release of each line, pinned as properties in `pom.xml`:
   springdoc-openapi-starter-webmvc-ui **3.1.1** · bucket4j_jdk17-core **8.21.0** · metadata-extractor **2.19.0** (newest 2.19.x;
   2.21.0 exists, not taken) · openpdf **3.0.5** · bcprov-jdk18on **1.86** · wiremock-standalone **3.13.2** (4.0 is beta) ·
   jacoco-maven-plugin **0.8.15**. Boot-managed (no version in the pom): Flyway 12.4.0 (+ flyway-database-postgresql),
   hibernate-spatial 7.4.5.Final, Testcontainers 2.0.x (`testcontainers-postgresql`), spring-boot-testcontainers,
   spring-security-test. No Excel library (MVP OUT). Failsafe runs `*IT` in `verify`; JaCoCo report → `target/site/jacoco/`.
3. Migrations: `Copy-Item flyway\*.sql backend\src\main\resources\db\migration\` → `Get-FileHash` identical for all 6;
   `bash scripts/ci/check-migrations.sh` → `MIGRATION COPIES: CONSISTENT (6 files)`.
4. Files (`backend/`): `pom.xml`; `application.yml` + `-dev/-demo/-e2e/-e2e-seed/-bootstrap-admin.yml`; test `application-test.yml`;
   `config/` (`AppProperties`, `AuthProperties`, `WhatsAppProperties`, `Secret`, `Base64Key(+Validator)`, `ClockConfig`,
   `SchedulingConfig`, `SecurityConfig`, `SecurityProblemHandler`, `DatabaseStartupCheck`); `common/` (`ErrorCode` 38 codes,
   `ApiException`, `ApiProblem`, `FieldErrorItem`, `GlobalExceptionHandler`, `DbErrorTranslator`, `RequestIdFilter`, `ProblemWriter`,
   `PageResponse`); `workflow/` (`WorkflowActor`, `Actor`, `ActorRole`, `ComplaintStatus`). Tests: `unit/` (ConfigValidationTest 18,
   ErrorAdviceTest 11, SecurityConfigTest 7, DbErrorTranslatorTest 28, ErrorCodeTest 2, PageResponseTest 2,
   StatusChangesOnlyInWorkflowTest 2) + `it/` (SchemaIT 5, WorkflowActorIT 4, ApplicationIT 4; one shared
   `postgis/postgis:18-3.6` container via `@ServiceConnection`).
5. First runs: unit 2 failures → fixed in the code/scanner (never-passed tests): (a) the filter-level 401 sent
   `application/problem+json;charset=UTF-8`, the advice plain `application/problem+json` → `ProblemWriter` no longer adds a charset;
   (b) the `setStatus(` scan flagged `response.setStatus(...)` (servlet HTTP status, not a complaint) → scan skips `response.setStatus(`,
   self-test added for both cases. ITs: all 13 errored with `FATAL: invalid value for parameter "TimeZone": "Asia/Calcutta"` →
   DECISION below. Then 1 failure: Boot 4 health showed `"groups"` (probes on by default) → `management.endpoint.health.probes.enabled=false`.
6. `/verify backend` (in `backend`): `.\mvnw.cmd -q verify` → exit 0, **`Tests run: 83, Failures: 0, Errors: 0, Skipped: 0`**
   (surefire 70 + failsafe 13), JaCoCo report written. Log: Flyway on the container "Successfully applied 6 migrations … now at
   version v5", R__ NOTICE "roles not found - grants skipped" (expected); the weak test secret appears 0 times in the whole log.
7. `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Only backend` → `PASS backend healthy`. `logs\backend.log`: profile `dev`,
   `Migrating schema "public" to version "1 - baseline"` … `"5 - capture answers plan release"`, `with repeatable migration
   "civicbrain grants"`, **`Successfully applied 6 migrations to schema "public", now at version v5`** (no baseline row: database was
   empty), `Started CivicbrainApplication in 10.2 s`, **`DB check: 23 wards visible to civicbrain_app`**. Only WARN: Thymeleaf
   "Cannot find template location: classpath:/templates/" (the e-mail layout template comes with the outbox, P10).
   Local GET (python urllib): `/actuator/health` → `200 {"status":"UP"}` with CSP, nosniff, `X-Frame-Options: DENY`,
   Referrer-Policy, Permissions-Policy, COOP, `X-Request-Id`; `/api/v1/x` → `401 application/problem+json`
   `{"type":"https://civicbrain.app/errors/UNAUTHENTICATED",…,"code":"UNAUTHENTICATED","requestId":"…"}`.
8. `pwsh -NoProfile -File scripts\dev\db-setup-main.ps1 -Seed` → **`PASS seed loaded: complaints=500 (synthetic, SUBMITTED, never
   analysed), wards=23, roads=1113`** (seed runs with triggers off → no jobs/outbox rows for demo data).
9. `pwsh -NoProfile -File scripts\dev\db-rebuild-test.ps1 -Force` → V1-V5 + R__ + seed PASS, `application tables: 74 | wards: 23 |
   … 1/21`, `ROLE 7/7`, `NEGATIVE 6/6`, `V4 11/11`, `V5 11/11`, **`DB TESTS: ALL PASSED`**.
10. P02 hand-off: `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Only ai-api,worker` → `PASS ai-api healthy`, `PASS worker healthy`;
    AI `/health` → `200 {"status":"ok","db":"ok","osrm":"not used (haversine)","modelsLoaded":false}` (models = P08);
    `logs\worker.log` since the restart: `worker started: database civicbrain, polling every 2 s …`, 0 "no CivicBrain schema" lines.
    Backend, ai-api and worker left running (dev stack).

   | Component | Command | Result line | Result |
   |---|---|---|---|
   | backend | `.\mvnw.cmd -q verify` | `Tests run: 83, Failures: 0, Errors: 0, Skipped: 0` (exit 0) | PASS |
   | migrations | `bash scripts/ci/check-migrations.sh` | `MIGRATION COPIES: CONSISTENT (6 files)` | PASS |
   | stack | `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Only backend` | `PASS backend healthy`; log `Successfully applied 6 migrations`, `DB check: 23 wards visible to civicbrain_app` | PASS |
   | seed | `pwsh -NoProfile -File scripts\dev\db-setup-main.ps1 -Seed` | `complaints=500 …, wards=23, roads=1113` | PASS |
   | db | `pwsh -NoProfile -File scripts\dev\db-rebuild-test.ps1 -Force` | `DB TESTS: ALL PASSED` (7/7, 6/6, 11/11, 11/11) | PASS |
   | ai hand-off | `start-all.ps1 -Only ai-api,worker` + GET `/health` | `200 … "db":"ok"` | PASS |
- DECISION: every backend JVM runs in UTC - `TimeZone.setDefault(UTC)` first thing in `main()` (dev `spring-boot:run` and the demo
  jar) and `<argLine>-Duser.timezone=UTC</argLine>` in the pom (surefire + failsafe; JaCoCo prepends its agent). Cause: Windows
  "India Standard Time" → JVM zone `Asia/Calcutta`, which pgjdbc sends as the `TimeZone` startup parameter; the Debian-based
  `postgis/postgis:18-3.6` image no longer knows that legacy name (FATAL at connect). Matches rule 10 (UTC inside, Asia/Kolkata
  only when formatting); JSON log timestamps are now UTC.
- DECISION: secrets are bound as `config.Secret` (toString `[hidden]`) and checked by `@Base64Key` (present, base64, ≥ 32 bytes;
  `TOTP_ENC_KEY` exactly 32), so a failed start says e.g. "JWT_SECRET is missing or not base64 of at least 32 random bytes" without
  echoing the value (ConfigValidationTest proves it). Spring's own keys (`DB_URL`, `DB_USER`, `DB_PASSWORD`, `SMTP_HOST`,
  `SMTP_PORT`, `PG_ADMIN_*` in the real-DB profiles) are required placeholders - Spring names the missing variable.
  `WHATSAPP_PROVIDER=twilio|meta` also requires that provider's keys.
- DECISION: `postgresql` driver moved from `runtime` to compile scope: `DbErrorTranslator` reads `PSQLException.getServerErrorMessage()`
  (SQLSTATE, primary message, constraint name) instead of parsing `getMessage()`.
- DECISION (12 §3 details): 42501 is `ROLE_NOT_ALLOWED` only for the V2 guard text "Role … may not move complaint"; any other
  42501 (missing grant) → 500 (our bug, logged). 23503 "insert or update…" → 404 NOT_FOUND, otherwise 400 VALIDATION_FAILED.
  57014 (statement timeout), class 08/53/57P → 503. `COMPLAINT_NOT_PLANNABLE` detail names the complaint as `CB-000042`.
  Spring MVC 4xx without own handler (405 …) keep their status with code MALFORMED_REQUEST. The 40001/40P01 retry (3×) belongs to the
  service transactions (P06+); the translator gives the final 503.
- DECISION: 10-s statement limit = Hikari `connection-init-sql: SET statement_timeout = '10s'` (every API connection); Flyway on the
  dev/demo/e2e databases uses its own owner connection (no limit). `server.error.include-*=never`, whitelabel off;
  `/v3/api-docs` only in dev/test (springdoc on, Swagger UI off everywhere).
- DECISION: test layout per 08 §1: unit tests in `com.civicbrain.unit.*` (MVC slice `@WebSliceTest` = real `SecurityConfig` +
  filter + advice + a `@TestComponent` test controller, no DB), integration tests in `com.civicbrain.it.*` (`@IntegrationTest`).
  The generated `CivicbrainApplicationTests` (contextLoads, never run) was moved to `it/ApplicationIT.java` (needs a DB).
  `application.properties` (only `spring.application.name`) renamed to `application.yml`.
- Human answers (2026-10-03 10:24): **Q1 yes** - Chrome shows `{"status":"UP"}` at http://localhost:8080/actuator/health ·
  **Q2 yes** - CI job "Backend (mvnw verify, Testcontainers, JaCoCo)" green for `712de71`.
- BLOCKED (not retried): one combined `git add -A; git status --short | Select-String -Pattern '<forbidden-path regex>'` -
  permission-denied (the regex contained the text `.env`, which the deny rules match, as in P01). Replaced by `git add -A` and a
  plain `git status --short` read by eye: 58 source files, no env/secret/storage/logs/target/HELP.md. `gh` is not installed,
  so the CI result (Q2) is checked by the human.
- Open / hand-offs: **P06** - JWT resource server + role areas in `SecurityConfig`, `/auth/refresh`+`/logout` Origin/CSRF check
  (`AppProperties.baseUrl/extraOrigins`), e2e rate limits, `@Retryable` for 40001/40P01. **P10** - Thymeleaf template folder
  (removes the WARN). Mockito prints "self-attaching" (JDK 25 warning only). `backend/HELP.md` (Initializr help) is git-ignored by
  `backend/.gitignore`; the human may delete it.
- DoD: [x] traces (02 §3/§6, 03 §1/§3/§5, 07 §2/§4, 12 §1-§3, 09_7DAY §4) [x] tests written first, green [x] error states
  (Problem Details for 400/401/403/404/409/413/422/500/503) [x] no secrets in yml/logs [x] committed `712de71`, pushed
  (`48dbbb8..712de71  main -> main`)

### 2026-10-02 — P03 — Dataset check, test fixtures, Kaggle package (DONE, human yes 2026-10-02 20:29)
- Requirement(s): docs/11_DATA_SOURCES.md §0, §6; docs/08_TEST_PLAN.md §2 (fixtures); frozen rule "YOLO classes (Step 9)".
**Plan** (Claude Code, Auto mode):
1. Labels present? `docs/INVENTORY.md`: 2,708/351/339 label files, classes 0-3 only → continue (P03b not needed).
2. `ai-service\.venv\Scripts\python.exe ai-service\training\prepare_mvp_dataset.py --root data\yolo --out-dir data\yolo\mvp`
   → exit 0 (exit 1 with < 30 bad lines → `ai-service/training/fix_labels.py`, backups in `data/yolo/backup_labels_P03/`;
   more → ask). Copy `data/yolo/mvp/dataset_report.json` → `docs/reports/dataset_report_local.json`.
3. `ai-service/training/make_test_fixtures.py` (Pillow, deterministic): per class the first TEST image (by name) whose label
   file has exactly one box, of that class, image ≥ 320 px (12 `IMAGE_TOO_SMALL`), box 5-60 % of the image → copy (never move)
   to `tests/fixtures/images/{pothole,garbage,waterlogging,road_damage}_1.jpg` + `<name>.txt` (recorded box); make
   `tiny_200px.jpg` (200×150) + `not_an_image.jpg` (text); write `README.md` (split, original name, licence). Look at each
   picked photo (no readable face / number plate).
4. `pwsh -NoProfile -File scripts\dev\make-kaggle-package.ps1` → zip size + file count.
5. Checks (new Python under `ai-service/`): ruff + pytest. Record, commit, push. Human step: Kaggle upload + committed run; Q1-Q2.
Test: `prepare_mvp_dataset.py` exit 0.

**Results**
1. Labels present (INVENTORY + the check below: 0 missing label files) → P03b not needed.
2. `ai-service\.venv\Scripts\python.exe ai-service\training\prepare_mvp_dataset.py --root data\yolo --out-dir data\yolo\mvp`
   → **exit 0**; again with `--check-images` (Pillow opens every image) → exit 0, same summary:
   ```
   train images= 2708 empty=   0 Pothole=2135 Garbage Accumulation=488 Waterlogging=352 Road Damage=2616
   val   images=  351 empty=   0 Pothole=246 Garbage Accumulation=105 Waterlogging=44 Road Damage=342
   test  images=  339 empty=   0 Pothole=299 Garbage Accumulation=38 Waterlogging=45 Road Damage=321
   leakage groups: 0  (train copies left out: 0)
   train_mvp.txt: 3258 lines, 2708 unique images
   label problems: 0
   ```
   Images per class (train/val/test): Pothole 1044/119/133 · Garbage 99/25/11 · Waterlogging 352/44/45 · Road Damage
   1743/219/218. Oversampled list: 2,708 + 99×2 (garbage ×3) + 352×1 (waterlogging ×2) = 3,258 lines. No `fix_labels.py`
   needed. Report → `docs/reports/dataset_report_local.json` (copy of `data/yolo/mvp/dataset_report.json`; local paths only).
   Weak classes in test: garbage 11 images / 38 boxes, waterlogging 45 - per-class test metrics for garbage will be noisy (P29).
3. Fixtures: `ai-service/training/make_test_fixtures.py` (dry run, then write) → `tests/fixtures/images/`:
   `pothole_1.jpg` ← `India_002154_jpg.rf.b26b…` (S1 RDD2022-India, 720x720, box 11 %) · `garbage_1.jpg` ←
   `IMG_5472_JPG.rf.4a46…` (S3 GarbagePile, 640x640, box 84 %) · `waterlogging_1.jpg` ← `image_101.jpg` (S2, 512x384, box 47 %) ·
   `road_damage_1.jpg` ← `India_000130_jpg.rf.1858…` (S1, 720x720, box 16 %), each + `<name>.txt` (label line) ·
   `tiny_200px.jpg` (200x150 crop of pothole_1, JPEG magic `FF D8 FF`) · `not_an_image.jpg` (text, starts `Civi`) · `README.md`.
   Check: `Get-FileHash` fixture = dataset original for all 4 images, label files identical, originals still in place
   (copy, not move). The 4 photos looked at by eye: no readable face or number plate (distant riders/pedestrians only).
   `git check-ignore` → not ignored (will be committed).
4. `pwsh -NoProfile -File scripts\dev\make-kaggle-package.ps1` → `PASS  kaggle_upload\civicbrain-yolo.zip: 6802 files,
   174.6 MB (3398 images, 3398 label files)`. Zip listing: `yolo/images` 3398 · `yolo/labels` 3398 · `yolo/data.yaml`,
   `class_definition.csv`, `dataset_sources.csv` · `training/{prepare_mvp_dataset.py, train_yolo_mvp.py, kaggle_train_mvp.ipynb}`;
   0 entries from `raw/`, `backup_*`, `archive/`, `mvp/`.
5. In `ai-service`: `.\.venv\Scripts\python.exe -m ruff check .` → `All checks passed!` (covers `training/*.py`) ·
   `.\.venv\Scripts\python.exe -m pytest -q` → `82 passed, 1 warning in 3.38s` (unchanged from P02).

   | Component | Command | Result line | Result |
   |---|---|---|---|
   | data | `…python.exe ai-service\training\prepare_mvp_dataset.py --root data\yolo --out-dir data\yolo\mvp [--check-images]` | `label problems: 0`, `leakage groups: 0`, exit 0 | PASS |
   | package | `pwsh -NoProfile -File scripts\dev\make-kaggle-package.ps1` | `6802 files, 174.6 MB (3398 images, 3398 label files)` | PASS |
   | ai | `.\.venv\Scripts\python.exe -m ruff check .` | `All checks passed!` | PASS |
   | ai | `.\.venv\Scripts\python.exe -m pytest -q` | `82 passed, 1 warning` | PASS |
- DECISION: fixture pick rule = first TEST image by name whose label file has exactly one box of the class, shorter side
  ≥ 320 px (12 `IMAGE_TOO_SMALL`), no EXIF rotation, box 5-60 % of the image preferred. Garbage has no such image (the 4
  single-box garbage test images are close-ups, box 84-100 %) → fallback to the smallest box (84 %). JPEGs copied byte for
  byte, so P08's golden box needs no rescaling. The script refuses to overwrite fixtures without `--force`.
- Licence finding: `waterlogging_1.jpg` comes from S2 "Waterlogging Dataset", whose licence was "To be documented" in
  `data/yolo/dataset_sources.csv` (no licence file in `data/yolo/raw/waterlogging*`); all 45 waterlogging test images are S2
  (`image_<n>`), so `--exclude` cannot avoid it. S1/S3 are CC BY 4.0 (attribution in the fixture README).
  DECISION (human, 2026-10-02 20:29): keep the file for now, repo stays public; an interim "not yet confirmed - replace in P13"
  note went into the fixture README and the log (never committed). The CSV edit was blocked - Excel had the file open - and
  never made.
  RESOLVED (human, 2026-10-03 09:36): S2 licence confirmed - **CC BY 4.0** (https://creativecommons.org/licenses/by/4.0/),
  "Waterlogging Dataset" by yolo and car accident detection,
  https://universe.roboflow.com/yolo-and-car-accident-detection-xaltb/waterlogging. Changes: `data/yolo/dataset_sources.csv`
  S2 row only (source URL + `CC BY 4.0`; UTF-8 BOM, delimiter, quoting and line endings kept); `make_test_fixtures.py`
  writes the S2 table row + an attribution line per S2 fixture → `--force` re-run: 10 fixture files byte-identical
  (`Get-FileHash` before/after), only `README.md` changed. Attribution says "converted, not an unchanged copy": the
  downloaded `raw/waterlogging_source/Dataset/images/image_101.jpg` (28,670 B) differs from the dataset/fixture file
  (28,663 B, same 512x384) because `scripts/yolo/convert_waterlogging_masks.py` re-saves every image with Pillow and makes
  the box from the segmentation mask. P13 replacement cancelled.
- Human answers (2026-10-02 20:29): **Q1 yes** - cells 1-4 ended with `OK`, cell 4 `TIMING`: **0.9 min per epoch** ·
  **Q2 yes** - committed version shows "Running".
- Expected Kaggle finish (P08 needs it): committed ≈ 20:29 + 120 epochs × 0.9 min = 108 min + ≈ 10 min (setup, dataset check,
  test-split evaluation, ONNX export) → **≈ 22:30 on 2026-10-02 at the latest**; earlier if early stopping (patience 25)
  ends training. Then: Output tab → `civicbrain_yolo_outputs.zip` → `C:\dev\civicbrain\kaggle_download\` (P08).

### 2026-10-02 — P02 — AI service skeleton, venv and worker loop (DONE, human yes 2026-10-02 19:45)
- Requirement(s): NFR-03 (stale jobs requeued); docs/06_AI_PIPELINE.md §1, §5; docs/02_ARCHITECTURE.md §4, §6;
  docs/04_API_CONTRACT.md §10; docs/07_SECURITY.md §5; docs/12_ERROR_HANDLING.md §7; rule 30.
**Plan** (Claude Code, Auto mode):
1. Venv: `py -3.13 -m venv ai-service\.venv` + `… -m pip install -r ai-service\requirements-dev-win-py313.lock`.
2. `ai-service/pyproject.toml` (pytest markers `models`/`integration`, `testpaths`, ruff 140/py313/E,F,W,I,B,UP).
3. `app/errors.py` (ConfigError, ModelError, DataError, DependencyError), `app/logging_setup.py` (JSON lines),
   `app/config.py` (19 rule-30 keys + `REQUIRE_MODELS=false`, lazy `get_settings()`, ASSUMPTION constants 06 §2.1/§2.4).
4. `app/db.py` (SQLAlchemy 2 + psycopg3 as `civicbrain_ai`, `session_scope()`, `set_system_actor()`).
5. `app/models_check.py` (MANIFEST.json file + folder entries, SHA-256), `app/security.py` (service JWT, PyJWT HS256).
6. `app/main.py`: `GET /health` (no auth), `GET /v1/models` + `POST /v1/jobs/{id}/requeue` (service JWT).
7. `worker/jobs.py` (claim / finish / stale requeue / own-RUNNING requeue / DEAD → `ai_status=FAILED`),
   `worker/handlers.py` (dispatcher), `worker/run.py` (loop, per-job timeout, graceful stop).
8. Tests first: `tests/unit` (settings, JWT, dispatcher, manifest, API) + `tests/it` (`@pytest.mark.integration`,
   `civicbrain_test`: fail → retry, success, stale requeue, own requeue at start, stop flag, DEAD → FAILED).
9. Verify: ruff + pytest; `start-all.ps1 -Only ai-api,worker`; `/health` → `docs/screenshots/P02_health.json`
   (CLAUDE.md: P02 has no frontend); `logs\worker.log`; `start-all.ps1 -Stop -Only worker,ai-api`. Record, commit, push.

**Results**
1. `py -3.13 -m venv ai-service\.venv` → created. The agent's
   `ai-service\.venv\Scripts\python.exe -m pip install -r ai-service\requirements-dev-win-py313.lock` was permission-denied
   (not retried): `.claude/settings.json` lines 126-128 put `…python.exe -m pip install *` on the **ask** list, which wins over
   the allow rule `… -m pip install -r *` (line 63). Human ran the same line in their own window → "done";
   `ai-service\.venv\Scripts\python.exe -m pytest --version` → `pytest 9.1.1`.
2. Files: `ai-service/pyproject.toml`; `app/` (`errors`, `logging_setup`, `config`, `db`, `models_check`, `security`,
   `problems`, `main`); `worker/` (`jobs`, `handlers`, `run`); `tests/conftest.py`; `tests/unit/` (test_config,
   test_security, test_handlers, test_models_check, test_api, test_worker_loop); `tests/it/` (test_worker_it, test_api_it).
3. First pytest run: `database "civicbrain_test" does not exist` (built in P01, gone since) →
   `pwsh -NoProfile -File scripts\dev\db-rebuild-test.ps1 -Force` → V1-V5 + R__ + seed PASS, `ROLE 7/7`, `NEGATIVE 6/6`,
   `V4 11/11`, `V5 11/11`, `DB TESTS: ALL PASSED`. Second run: a test-helper bug (`ItData._sql` read rows from UPDATE/DELETE)
   broke set-up and cleanup and left rows behind → helper fixed, `db-rebuild-test.ps1 -Force` again (same PASS lines).
4. In `ai-service`: `.\.venv\Scripts\python.exe -m ruff check .` → `All checks passed!` ·
   `.\.venv\Scripts\python.exe -m pytest -q` → `79 passed, 1 warning in 3.01s` (twice in a row: cleanup leaves nothing) ·
   `… -m pytest -q -m integration` (before the last 3 unit tests were added) → `11 passed, 65 deselected`.
   The warning is Starlette's own deprecation notice for `httpx` in its TestClient (no action; not a new dependency).
5. `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Only ai-api,worker` (1st try) → `PASS ai-api healthy`,
   `FAIL worker exited during start-up`: `relation "jobs" does not exist` - the dev database `civicbrain` is EMPTY until P04
   (P01 decision), and `/health` had said `db: ok` (only `SELECT 1`). Fixed (DECISION below), `start-all -Stop`, 2nd try →
   `PASS worker healthy`; `FAIL ai-api not healthy after 120 s` = `/health` now honestly answers 503 on the empty database.
   `/health` (local GET, body saved as `docs/screenshots/P02_health.json`) → `HTTP 503`
   `{"status":"degraded","db":"schema missing","osrm":"not used (haversine)","modelsLoaded":false}`.
   `logs\worker.log`: JSON lines - `model files not ready, REQUIRE_MODELS=false so the worker still runs: MANIFEST.json: not
   found in MODELS_DIR; …` · `worker started: database civicbrain, polling every 2 s, job types ANALYZE_COMPLAINT,…` ·
   every 10 s `database civicbrain has no CivicBrain schema yet (no jobs table) - the backend's Flyway migrations create it
   (P04) - retrying in 10 s`. `logs\ai-api.log`: JSON lines, `AI API ready (database civicbrain, routing haversine)`.
   `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Stop -Only worker,ai-api` → `PASS stopped worker` · `PASS stopped ai-api`.
   Claim → handler → finish / retry / DEAD / stale / own-requeue / graceful stop are proven by the integration tests on
   `civicbrain_test`; live polling on the dev stack can only be seen after P04 creates the schema.
6. `/verify ai` before the commit: `test_stop_flag_ends_the_loop_after_the_current_job` failed once
   (`('RUNNING', 1) == ('QUEUED', 0)`: the 2nd job was claimed but never run), then passed 4×. Root cause found and
   reproduced: V4 `fn_claim_jobs` = `UPDATE jobs … WHERE job_id IN (SELECT … LIMIT n FOR UPDATE SKIP LOCKED)`. With a
   nested-loop semi join the LIMIT subquery is re-scanned per outer row, rows already updated by the statement are skipped
   (self-modified), so LIMIT takes the next queued job - forced plan → `fn_claim_jobs(…, 1)` returned **3 rows**; the default
   plan (Hash Semi Join) returned 1. The plan depends on table statistics → intermittent. The worker processed only
   `claimed[0]` and left the extra job RUNNING (recovered only by the 15-min stale requeue).
   Fix in the worker (V1-V5 are frozen): claim rows sorted in queue order (priority, run_after, job_id), all processed;
   after a stop request the not-started ones are released with `fn_finish_job(false, 'Released: …')`; a WARNING logs the
   over-claim. Regression tests `tests/it/test_zz_probe_claim_plan.py` force the plan with planner settings (deterministic):
   V4 over-claim documented, both jobs processed in order, stop releases the second. The stop test now accepts its two
   correct outcomes (2nd job never claimed, or claimed + released) - its earlier `attempts == 0` was wrong for V4.
   Final: `.\.venv\Scripts\python.exe -m ruff check .` → `All checks passed!` · `.\.venv\Scripts\python.exe -m pytest -q`
   → `82 passed, 1 warning` **5 runs in a row** · `start-all.ps1 -Only worker` (new code) → `PASS worker healthy`, then
   `start-all.ps1 -Stop -Only worker,ai-api` → `PASS stopped worker`.

   | Component | Command | Result line | Result |
   |---|---|---|---|
   | ai | `.\.venv\Scripts\python.exe -m ruff check .` | `All checks passed!` | PASS |
   | ai | `.\.venv\Scripts\python.exe -m pytest -q` | `82 passed, 1 warning` (5× in a row; 14 integration on civicbrain_test) | PASS |
   | db | `pwsh -NoProfile -File scripts\dev\db-rebuild-test.ps1 -Force` | `DB TESTS: ALL PASSED` (7/7, 6/6, 11/11, 11/11) | PASS |
- DECISION (human, Q2 = no, 2026-10-02 19:45): no migration in the MVP - the worker-side handling stays. KNOWN ISSUE for
  Phase 2: fix `fn_claim_jobs` in a V6 migration with a MATERIALIZED CTE -
  `WITH picked AS MATERIALIZED (SELECT … LIMIT p_limit FOR UPDATE SKIP LOCKED) UPDATE jobs … FROM picked` (+ db test,
  three identical copies); then update `test_v4_claim_can_return_more_rows_than_the_limit` (it will fail on purpose).
- Human answers (2026-10-02 19:45): **Q1 yes** - "schema missing" is expected until P04 runs the migrations ·
  **Q2 no** - keep the worker-side handling, V6 fix in Phase 2 (above) · password shown in the terminal: the human decides
  themselves, nothing for the agent to do.
- DECISION: a missing schema is a dependency problem, not a crash: `/health` checks `jobs` + `fn_claim_jobs` exist
  (`db: ok | schema missing | unavailable`, 503 unless ok); the worker raises `DependencyError` at start-up, logs it and
  retries every 10 s, so it starts polling by itself once Flyway has run (start order does not matter).
- SECURITY NOTE: in the first pytest run (test DB missing) pytest's default long traceback printed the arguments of
  psycopg's `connect()`, i.e. the `PG_ADMIN_PASSWORD` value, to the agent's terminal (not to a file, not committed; it is in
  the Claude Code session transcript). Fix: `--tb=short` in `pyproject.toml` (never prints frame arguments; matters for
  `verify-all.ps1`, which writes pytest output to `logs/`). Human decides whether to change the local `postgres` password
  (pgAdmin + `.env` - human-only).
- DECISION: own RUNNING jobs at worker start (locked_by = WORKER_ID) are finished with `fn_finish_job(id, false,
  'Interrupted: …')` - only V4 functions touch `jobs` (03 §3.8): retry after 1 min (5 min after the 2nd attempt), the 3rd
  attempt → DEAD (same attempt counting as `fn_requeue_stale_jobs`). No direct UPDATE of `jobs`, no new migration.
- DECISION: per-job time limit = handler in a daemon thread, the main thread waits in 0.5-s steps (Windows has no
  SIGALRM; Ctrl+C stays responsive). On timeout the job fails as `JobTimeoutError` and `ctx.cancelled` is set; handlers
  (P12/P17) call `ctx.check_cancelled()` right before their commit, so a late handler never writes results.
- DECISION: service-JWT HMAC key = base64-decoded `AI_SERVICE_JWT_SECRET` (same convention as `JWT_SECRET`; check-env
  already enforces ≥ 32 bytes base64). PyJWT checks signature/HS256-only/aud/iss/required claims; exp/iat/lifetime ≤ 60 s
  are checked in our code against an injectable clock (fixed-clock tests).
- DECISION: `POST /v1/jobs/{id}/requeue` copies a finished job (SUCCEEDED/FAILED/DEAD) into a new QUEUED row
  (`INSERT … SELECT … ON CONFLICT DO NOTHING`, like the V4 triggers) → 202 `{jobId, requeuedFrom, status}`; job still active
  or another active job for the same item → 409 `ALREADY_EXISTS`; unknown → 404 `NOT_FOUND`; errors as RFC 9457 Problem
  Details with `X-Request-Id`. No OpenAPI/docs pages on the internal API.
- DECISION: `GET /health` answers 503 with `status: degraded` when the database is down or has no schema (so start-all
  reports the AI API as unhealthy); `modelsLoaded` = every required file present with the MANIFEST SHA-256.
- DECISION: after `fn_requeue_stale_jobs` (and at start) the worker also sets `ai_status = FAILED` for complaints whose
  latest ANALYZE_COMPLAINT job is DEAD but still look PENDING/PROCESSING (a stale job at max attempts becomes DEAD inside
  the DB function, which returns only a count).
- NOTE for P12: 06 §2.4 says "NULL depth answer → the class prior's depth (Tier C)" but gives no number; `config.py` does
  not invent one - P12 decides and records it.
- Open / hand-offs: **P04** - after Flyway builds `civicbrain`, start `ai-api,worker` once and check `/health` → 200
  `db: ok` and `logs\worker.log` without the "no schema" line. **P12** - set `REQUIRE_MODELS=true`; handlers call
  `ctx.check_cancelled()` before commit. `.claude/settings.json` ask rule vs `pip install -r` allow rule: human's choice.
- DoD: [x] traces (06 §1/§5, 04 §10, 07 §5, 12 §7, NFR-03) [x] tests green [x] states/errors (Problem Details, 401/404/409/503)
  [x] ruff clean [x] committed (see git log: `feat(ai): …`)

### 2026-10-02 — P01 follow-up — Full-history secret scan, `.env` example files readable
- Requirement(s): docs/07_SECURITY.md §5 (secrets only in `.env`, gitleaks 0 findings); D1 gate "CI green".
- Changed: `.claude/settings.json` (human edit, commit `579b14f`): the deny list matched `.env.*` and its `!` exceptions had
  no effect (Claude Code permission rules have no negation; deny wins), so the Read tool refused `.env.example` and
  `.env.test.example`. It now denies the real env files by name (`.env`, `.env.test`, `.env.local`, `.env.*.local`,
  prod/dev/staging/demo/e2e/backup copies, `.env.txt`); `ask`/`allow` unchanged.
- Verified: `pwsh -NoProfile -File scripts\dev\sync-claude.ps1 -Check` → `PASS  .claude/settings.json is valid JSON (430 deny rules)` ·
  `PASS  sync-claude: .claude/ is current (10 files)`.
- Secret scan of the whole history (gitleaks/trufflehog not installed → `git grep -I -E` over `git rev-list --all` = 5 commits;
  `main` = `origin/main`, so this is what GitHub has):
  1. Tracked files: env files = only the two examples; no `*.local.json`, key/cert files, logs, `storage/`, weights, backups.
  2. Token formats (private key, AWS, GitHub, Google, Slack, Twilio SK/AC, Stripe, `sk-`, Hugging Face, SendGrid, JWT,
     URL with `user:password@`) → 0 real hits (only the P01 scan-pattern text in this file and `docs/INVENTORY.md`).
  3. `password|secret|token|api_key … = <8+ chars>` → only the CI throw-away DB passwords in `ci.yml` (`postgres`,
     `ci-*-password`), the allowlisted `dGVzdC1vbmx5…` (base64 "test-only-…") and env/`getpass` lookups in scripts.
  4. Personal data: all 24 e-mail addresses are `.local`/`example.com`/`.example`; phone-like numbers are fake
     (`+91900000000x`, `+919111100001`, `9999999999`), OpenStreetMap node IDs (POI GeoJSON) or hex WKB geometry (V1, seed).
  5. `.env.example` + `.env.test.example` (Read tool): placeholders only - `change-me-*`, `REPLACE_WITH_BASE64_32_BYTES`,
     `REPLACE_ME`/`REPLACE_ME_BASE32` (all on the `.gitleaks.toml` allowlist), empty SMTP/Meta/Twilio secrets, Twilio's public
     sandbox sender number, fake `+91900000000x` phones, `@test.local` accounts.
  Result: **0 secrets, 0 real personal data in git history.**
- Still open (D1 "CI green"): gitleaks in CI over the full history → human: Actions → CI → "Run workflow" on `main`.

### 2026-10-02 — P01 — Repo, environment check, databases (DONE, human yes 2026-10-02)
**Plan** (Claude Code, Auto mode):
1. Rules check from memory → log; `sync-claude.ps1 -Check` must end `PASS  sync-claude`.
2. `check-env.ps1` → 0 FAIL (kit-script bugs fixed with a small edit + `SCRIPT FIX:` line; install/PATH = human step).
3. `git init -b main` (no `.git` yet) + `core.autocrlf true`; check `user.name`/`user.email`.
4. Inventory (read-only) → `docs/INVENTORY.md`: research files, counts, format peek, OK / NEEDS ADAPTING / UNKNOWN + prompt;
   stray root files and non-ignored files > 20 MB → `.gitignore` under `# P01: not part of the project`.
5. Secret scan of every `.py/.sql/.json/.ipynb/.md` under `scripts/` and `data/`; literal → `os.environ[...]` (never printed).
6. First commit `chore: kit + existing research files` (`git status --short`: no `.env`, images, `storage/`).
7. `db-setup-main.ps1`, then `db-rebuild-test.ps1 -Force` → V2 6/6, V4 11/11, V5 11/11, roles 7/7.
8. `start-all.ps1 -SelfTest` twice (5 s apart) → `AGENT_CAN_START=yes|no`. 9. `docker version`.
10. Human step: GitHub repo URL → `git remote add origin` + `git push -u origin main`; then Q1–Q3.
Files: `docs/INVENTORY.md`, `docs/PROGRESS.md`, `.gitignore` (if needed), kit scripts only on a real bug. Tests: the SQL tests of step 7.

**Results**
1. Rules loaded (from memory, no file opened): Human-only = `install-all.ps1`, `new-env.ps1`, `new-secret.ps1`, `bootstrap-admin.ps1`,
   `start-all.ps1 -Tunnel`/`-Demo`, every single `start-*.ps1` (`start-e2e`, `start-tunnel`, `start-osrm` …), `prepare-osrm.ps1`, `cloudflared`,
   editing `.env`/`.env.test`, Kaggle/GitHub/Twilio/Gmail web consoles, anything on a phone. Skills: `/run-prompt`, `/start-phase`,
   `/verify`, `/phase-gate`, `/commit-step`.
   `pwsh -NoProfile -File scripts\dev\sync-claude.ps1 -Check` → `PASS  sync-claude: .claude/ is current (10 files)`.
2. `pwsh -NoProfile -File scripts\dev\check-env.ps1` → `RESULT: all required checks PASS (13 WARN)` (0 FAIL; no SCRIPT FIX needed).
   WARNs, all expected for later prompts / optional: long paths off (optional), `.venv` (P02), `uv` (only to change deps),
   `civicbrain_test`/`civicbrain_e2e`/login roles (step 7, P06), OSRM data (Phase 2), mailpit binary (Docker fallback), ffmpeg, k6, 7z,
   `storage/` folder, YOLO weights (P08). Note: database `civicbrain` already exists.
3. Inventory → `docs/INVENTORY.md`: every research file the prompts use is present (YOLO 2708/351/339 images + labels, classes 0-3 only;
   priority 500/500 rows; duplicates 109 pairs; Step 10 XGBoost 3.4.1 models; Step 13 routing). No fallback prompt needed (P03b not needed).
   NEEDS ADAPTING: P09 research `ward_id` = ward **number**; P09 duplicate loader uses psycopg2; P17 routing scripts call the public OSRM server.
4. Git: no `.git` existed → `git init -b main`; `git config core.autocrlf true`; identity set (user.name `siddgh123`).
   DECISION: `.gitignore` section `# P01: not part of the project` ignores `data/yolo/archive/backup_before_final_merge/` (2,822 images, 147 MB)
   and `data/yolo/visual_validation/` (20 dataset photos). GIS sources (PDF 5.1 MB, tif, reference png, gpkg) stay committed (≤ 5.1 MB, map
   sources, kit keeps the tif tracked). `KIT_FIXES.md` (human note) committed. No file > 20 MB exists.
5. Secret scan of 126 `.py/.sql/.json/.ipynb/.md/.yaml/.txt` files under `scripts/` + `data/` (password literal, `PGPASSWORD`,
   `postgres://u:p@`, key/token literal) → 0 hits; no edits needed. The 3 DB scripts use env `CIVICBRAIN_DB_PASSWORD` or `getpass`.
   BLOCKED: a read-only `git ls-files --others` filter that contained the text `.env` (to list would-be-committed env files) - denied by the
   `.env` deny rule; not retried. Covered instead by check-env `PASS .gitignore protects .env` and the `git status` check of step 6.
6. First commit: `git add -A` → 427 files staged; root level only `.env.example`/`.env.test.example` of the env files; no images
   (except the GIS reference map png), weights, `storage/`, `logs/`; largest 4.9 MB → `git commit` → `6c2481e chore: kit + existing research files`.
   `git ls-files --eol`: `scripts/ci/*.sh` and `flyway/*.sql` stored + checked out LF (`.gitattributes`), so CI is unaffected by `autocrlf`.
7. `pwsh -NoProfile -File scripts\dev\db-setup-main.ps1` → `PASS roles civicbrain_app and civicbrain_ai ready` ·
   `PASS database civicbrain already exists (left unchanged)`.
   `pwsh -NoProfile -File scripts\dev\db-rebuild-test.ps1 -Force` → V1-V5 + R__ + seed PASS; `application tables: 74 | wards: 23 |
   fn_locate_point(18.7440,73.6760) ward_number/ward_id: 1/21`; `ROLE TESTS PASSED: 7 / 7` · `NEGATIVE TESTS PASSED: 6 / 6` ·
   `V4 TESTS PASSED: 11 / 11` · `V5 TESTS PASSED: 11 / 11` · `DB TESTS: ALL PASSED`.
8. `pwsh -NoProfile -File scripts\dev\start-all.ps1 -SelfTest` → `selftest window started`; 5 s later the same command →
   `SELFTEST PASS: the window started by the previous command is still alive` · `PASS stopped selftest`. **AGENT_CAN_START=yes**
9. `docker version` → Server: Docker Desktop 4.93.0, Engine 29.8.1 (running) - Testcontainers can run.

**Open issues / hand-offs**
- **P04:** database `civicbrain` existed BEFORE P01 (Step 0 does not create it; `db-setup-main.ps1` left it unchanged).
  Human answer (2026-10-02): it is EMPTY (0 tables), `civicbrain_backup` was NOT restored.
  DECISION: P04 uses the normal empty-database path - Flyway builds V1-V5 + R__ from scratch (no `baseline-version` override).
- GitHub: remote `origin` = `https://github.com/siddgh123/civicbrain.git` (public). First `git push -u origin main` by the agent →
  `fatal: could not read Username for 'https://github.com': terminal prompts disabled` (Git Credential Manager cannot open its
  sign-in window from the agent's non-interactive terminal) → human step: one push from the human's own PowerShell window.
  After the human's push: `git status -sb` → `## main...origin/main`; `git log -1` → `d666bde (HEAD -> main, origin/main)`;
  agent retry `git push` → `Everything up-to-date` (stored credential works - the agent can push in later prompts).
- **CI security job, first push only (open for the D1 gate "CI green"):** the human's push (`6c2481e..d666bde`) failed the
  gitleaks step: `fatal: ambiguous argument '6c2481e…^..d666bde…': unknown revision` → `scanned ~0 bytes` → exit code 1. Cause:
  on a push, gitleaks-action scans `<first pushed commit>^..<last>`, and the root commit `6c2481e` has no parent. Not a leak
  ("no leaks found", 0 bytes scanned); happens only on a new repository's first push, so `ci.yml` stays unchanged. Later pushes
  scan normally, but the full history (incl. the 427-file root commit) has not been scanned by gitleaks yet → human: Actions →
  CI → "Run workflow" on `main` (`workflow_dispatch` makes gitleaks scan the whole history) and confirm the Security job is green.
  Local full-history scan 2026-10-02: 0 findings (entry "P01 follow-up" above); the CI run is still needed for the gate.
- Human answers: Q1 yes (files on GitHub, no `.env`) · Q2 yes (Database job green) · Q3 yes (INVENTORY complete; agent re-checked it:
  fixed 2 rounded label samples, OSRM server count 6 → 8 files, size units note - no count changed).
- P09: research `ward_id` columns are ward numbers; duplicate loader uses psycopg2 → port the scoring only (docs/INVENTORY.md).
- P17: Step 13 routing scripts call `router.project-osrm.org` → reuse solver settings only (MVP haversine).
- Optional (human): check-env WARN "Windows long paths disabled" - only if a path error ever appears:
  `git config --global core.longpaths true` (the agent never changes global git config).

<!-- Copy this block for every task -->
<!--
### YYYY-MM-DD — P<n>.<task> — <short title>
- Requirement(s): FR-xx / NFR-xx; doc: docs/<file> §<n>
- Changed: <files>
- Tests added/updated: <files>
- Verified: `<command>` → `<summary line>`
- DoD: [ ] traces  [ ] tests green  [ ] states/errors  [ ] lint/type/security clean  [ ] committed <hash>
- Notes / follow-ups:
-->

## Decisions log
| Date | Decision | Why | Who |
|---|---|---|---|
| 2026-09-30 | Requirements frozen v1.0 (docs/01) | Single source of truth before building | Team |
| 2026-09-30 | DB grants moved to repeatable migration `R__civicbrain_grants.sql`; roles template only creates the roles | Grants stay correct on every database Flyway builds (dev, e2e, Testcontainers) and after future migrations | Kit |
| 2026-09-30 | Three databases: `civicbrain` (Flyway), `civicbrain_test` (psql build, SQL + AI tests), `civicbrain_e2e` (Flyway + fixed accounts) | A psql-built DB has no Flyway history, so the backend must never use it; E2E needs resettable data | Kit |
| 2026-09-30 | OSRM image `v26.8.0-debian` pinned in `infra/osrm/docker-compose.yml` | Newest published image; the v26.9.0 release has no image | Kit |
| 2026-09-30 | CI actions pinned by commit SHA; Trivy action v0.35.0 + binary v0.69.3 | March 2026 Trivy supply-chain compromise (GHSA-69fq-xp46-6x23) | Kit |
| 2026-09-30 | `V5__capture_answers_plan_release.sql`: depth answer + A4 flag columns, image quality score, plan release trigger, TOTP/LOGOUT_ALL auth events, `audit_logs.entity_key` | Independent kit review found no storage for FR-10 answers and that reopened complaints could never be planned again | Kit |
| 2026-10-01 | 7-day MVP mode (`09_BUILD_PLAN_7DAY.md`): existing YOLO images only, haversine routing, Twilio sandbox, reduced test list | Deadline 7 Oct 2026; no time for new photos | Team |
| 2026-09-30 | Requirements v1.1: ADMIN bootstrap script, officer tabs Needs review / Rejected with accept / restore | "Officers see everything" and first-admin creation were not buildable | Kit |
| 2026-10-02 | `fn_claim_jobs` over-claim (V4): handled in the worker for the MVP; V6 migration with a MATERIALIZED CTE in Phase 2 | Reproduced in P02 tests; V1-V5 frozen, no new migration during the 7-day MVP | Human (P02 Q2) |
| 2026-10-03 | S2 "Waterlogging Dataset" (yolo and car accident detection, Roboflow) licence = CC BY 4.0: fixture `waterlogging_1.jpg` stays in the public repo with attribution; the interim plan of 2026-10-02 (replace it in P13 if unconfirmed) is cancelled | Licence confirmed by the team; CC BY 4.0 allows redistribution with attribution and a note of changes | Human (P03 follow-up) |

## ASVS L2 checklist evidence (fill in P10)
| Area | Item | Test / evidence |
|---|---|---|
| Authentication | Argon2id, lockout, OTP rules, TOTP for staff | |
| Session | refresh rotation + reuse detection, token_valid_after | |
| Access control | deny-all + matrix test complete | |
| Validation & files | magic bytes, re-encode, size/pixel limits | |
| Headers | CSP, HSTS, nosniff, frame-ancestors, Permissions-Policy | |
| Logging | no secrets/OTP/tokens/full phones in logs | |
| Privacy | notice, consents, requests, public map anonymised | |
