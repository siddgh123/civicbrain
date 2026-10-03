# 12 — Error Handling (all layers)

## 1. API error format (RFC 9457 Problem Details)
```json
{ "type": "https://civicbrain.app/errors/GPS_ACCURACY_TOO_LOW", "title": "Location is not accurate enough",
  "status": 422, "code": "GPS_ACCURACY_TOO_LOW", "detail": "Accuracy was 240 m; 150 m or better is needed.",
  "requestId": "7f3a…", "fieldErrors": [ { "field": "locationAccuracyM", "code": "MAX", "message": "must be ≤ 150" } ] }
```
One `@RestControllerAdvice` maps exceptions → this body. `detail` never contains stack traces, SQL, file paths, other users' data or secrets. Every response carries `X-Request-Id`.

## 2. Error codes
| HTTP | code | When | UI message (i18n key `errors.<code>`) |
|---|---|---|---|
| 400 | `VALIDATION_FAILED` | Bean validation / unknown JSON field / bad enum | Show field errors |
| 400 | `MALFORMED_REQUEST` | Unreadable JSON, wrong content type | "Something went wrong. Please try again." |
| 401 | `UNAUTHENTICATED` | Missing/invalid/expired token | silent refresh, then login page |
| 401 | `INVALID_CREDENTIALS` | Login failed | "E-mail/phone or password is incorrect" |
| 401 | `SESSION_REVOKED` | Refresh reuse, logout-all, token before `token_valid_after` | "You were signed out. Please log in again." |
| 403 | `FORBIDDEN` | Role not allowed for the endpoint | 403 page |
| 403 | `ROLE_NOT_ALLOWED` | DB rejected the status change for this role (SQLSTATE 42501 from the V2 guard) | "You can't do this step." |
| 403 | `EMAIL_NOT_VERIFIED` | Citizen not verified | OTP screen |
| 403 | `MFA_REQUIRED` | Officer/admin without TOTP | TOTP setup |
| 403 | `CSRF_CHECK_FAILED` | Refresh/logout without header or bad Origin | force re-login |
| 403 | `PASSWORD_CHANGE_REQUIRED` | `users.must_change_password = true` (one-time password): every endpoint except `GET /me`, `/auth/password/change`, `/auth/logout`, `/auth/logout-all` | change-password screen |
| 404 | `NOT_FOUND` | Missing **or not yours** | "Not found" |
| 409 | `INVALID_TRANSITION` | V2 guard: "Invalid complaint status transition" (SQLSTATE 23514 with that message) | "This complaint has already moved on. Refresh." |
| 409 | `STALE_VERSION` | Plan edited by someone else | "Plan changed — reload" dialog |
| 409 | `ALREADY_EXISTS` | Unique violation (e-mail, phone, contractor phone) | field error |
| 409 | `COMPLAINT_NOT_PLANNABLE` | `fn_approve_action_plan` refused (status/other plan) | show which complaint |
| 409 | `PLAN_STATE_CONFLICT` | Plan action not allowed in the plan's current status (edit non-DRAFT, approve non-DRAFT, assign non-APPROVED, cancel with work started) | "This plan has already moved on. Reload." |
| 409 | `BLUR_NOT_READY` | Public approval before the blurred copy exists | "Blurring is still running — try again in a moment." |
| 410 | `CAPTURE_SESSION_EXPIRED` | Session older than 10 min | "Please take the photo again." |
| 413 | `FILE_TOO_LARGE` | a file > 8 MB or the request > 25 MB (`MaxUploadSizeExceededException`) | "Photo is too large." |
| 415 | `FILE_TYPE_NOT_ALLOWED` | Not JPEG/PNG by magic bytes | "Only photos (JPG/PNG) are allowed." |
| 422 | `CAPTURE_SESSION_INVALID` | Unknown, used or other user's session | "Please take the photo again." |
| 422 | `GPS_ACCURACY_TOO_LOW` | > 150 m | "Move to open sky and retry." |
| 422 | `LOCATION_STALE` | Captured > 10 min before submit | "Please capture again." |
| 422 | `OUTSIDE_BOUNDARY` | Not inside TDMC | "This location is outside Talegaon Dabhade Municipal Council." |
| 422 | `IMAGE_TOO_SMALL` / `IMAGE_TOO_LARGE_PIXELS` | < 320 px / > 40 MP | "Photo quality not accepted." |
| 422 | `OTP_INVALID` / `OTP_EXPIRED` / `OTP_ATTEMPTS_EXCEEDED` | OTP checks | matching message + resend |
| 422 | `TOTP_INVALID` | Wrong/replayed code | "Code is incorrect." |
| 422 | `PASSWORD_POLICY` | Length/blocklist | show rule |
| 422 | `CONTRACTOR_NOT_ELIGIBLE` | Inactive / wrong work type (DB function error) | "Choose a contractor registered for ROAD." |
| 422 | `FEEDBACK_NOT_ALLOWED` | Feedback when the complaint is not COMPLETED/CLOSED | hide button |
| 422 | `CONSENT_MISSING` | Public photo approval without the owner's current PUBLIC_PHOTO consent | "The citizen has not allowed public photos." |
| 423 | `ACCOUNT_LOCKED` | Lockout | "Too many attempts. Try again in 15 minutes." |
| 429 | `RATE_LIMITED` | Bucket4j | "Please wait N seconds." (`Retry-After`) |
| 500 | `INTERNAL_ERROR` | Anything unexpected (logged with stack trace server-side) | "Something went wrong. Reference: <requestId>" |
| 503 | `DEPENDENCY_UNAVAILABLE` | DB down, storage not writable | "Service temporarily unavailable." |

## 3. Database errors → API
Map by SQLSTATE and message prefix (never parse free text elsewhere): 23505 unique → `ALREADY_EXISTS` (field from constraint name map); 23503 FK → `NOT_FOUND` or `VALIDATION_FAILED`; 23514 with "Invalid complaint status transition" → `INVALID_TRANSITION`, other 23514 → `VALIDATION_FAILED`; 42501 from the guard → `ROLE_NOT_ALLOWED`; P0001 (plain `RAISE EXCEPTION`) from `fn_approve_action_plan` / `fn_assign_action_plan` by message prefix: `Action plan % not found` → 404 `NOT_FOUND`; `Only DRAFT plans` / `Plan % must be APPROVED` → 409 `PLAN_STATE_CONFLICT`; `Complaint % is not free for planning` → 409 `COMPLAINT_NOT_PLANNABLE`; `Contractor % is not active` / `Contractor % is not registered for work type` → 422 `CONTRACTOR_NOT_ELIGIBLE`; any other P0001 → 500 (unit-test every prefix); 40001/40P01 (serialization/deadlock) → retry the transaction up to 3 times, then 503. Transactions: one per request (`@Transactional` on services), read-only for queries, 10-s statement timeout (`SET LOCAL statement_timeout`), HikariCP connection timeout 5 s.

## 4. External calls: timeouts and retries
| Call | Timeout | Retry | On final failure |
|---|---|---|---|
| SMTP send | 10 s connect/read | dispatcher retry 1/5/30 min, max 5 | notification FAILED, visible in log page |
| Meta / Twilio API | 10 s | same; 4xx (bad number/template) → no retry | FAILED with provider error code |
| OSRM table/route (worker) | 10 s | 2 retries, 1 s backoff | optimizer run FAILED "Routing service unavailable" |
| YOLO/classifier inference | job timeout 120 s | job retries after 1 and 5 min; the 3rd failure (`max_attempts = 3`) → DEAD | job DEAD, worker sets complaint `ai_status=FAILED`, officer sees it in "Needs review" with "Re-run analysis" and "Accept" |
| File storage write | — | none | 503 `DEPENDENCY_UNAVAILABLE`, no DB row committed (see §5 file + DB) |

## 5. Idempotency and consistency
- Complaint submit: capture session is single-use → a double-tap cannot create two complaints (second gets `CAPTURE_SESSION_INVALID`, UI shows the first result).
- Notifications: `dedupe_key` unique; dispatcher uses `FOR UPDATE SKIP LOCKED`.
- Jobs: one active job per (type, ref) (unique index); worker writes are delete-then-insert per model version inside one transaction.
- Plans: optimistic locking via `version`; approve/assign inside DB functions with `FOR UPDATE`.
- File + DB (one strategy everywhere): write the re-encoded file to its final random path (`photos/YYYY/MM/<uuid>.jpg`) → insert the DB rows → commit; if the transaction rolls back, delete the file in a `TransactionSynchronization.afterCompletion` hook; a nightly job (P10) deletes files under its own `STORAGE_ROOT` that no `complaint_images` row of its own database references and that are older than 1 day. The E2E stack always uses `STORAGE_ROOT\e2e` (set by the `scripts/dev` start scripts), so an E2E cleanup can never touch dev/demo photos.

## 6. Frontend handling
- `apiClient` converts every non-2xx into `ApiError {status, code, message, fieldErrors, requestId}`.
- 401 → one shared refresh attempt → retry original once → login page with return URL.
- Query errors → `ErrorState` component (message by code + "Try again" + requestId); mutation errors → toast + field errors; never lose form input.
- React error boundary per portal: friendly page + "Reload"; errors reported to `POST /api/v1/client-errors` (rate-limited, no PII; server log only).
- Camera/GPS errors: permission denied, no camera, insecure context (http) → specific explanations with steps; unsupported browser → fallback file input.

## 7. Worker handling (Python)
Each step raises a typed exception (`ConfigError`, `ModelError`, `DataError`, `DependencyError`); the orchestrator logs `{job_id, complaint_id, step, error_type}` and calls `fn_finish_job(false, ...)`. `ConfigError` (missing model/checksum) stops the worker at startup instead of failing jobs one by one. Never swallow exceptions silently; never mark a complaint VERIFIED if a required step failed.
