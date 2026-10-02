# P10 — Complaint intake API + e-mail outbox dispatcher
**Day 3 · agent ≈ 3 h · human 0 min · Needs: P02, P06 · Model: strongest**

## Goal
Citizens create complaints exactly as `04` §5 says (capture session, validation order, photo pipeline), see their
list/detail/timeline, and every citizen-facing status sends the e-mail from the seeded templates through the outbox.
Smoke stage `intake` passes.

## Read first
`docs/04_API_CONTRACT.md` §3, §4, §5 · `docs/02_ARCHITECTURE.md` §5 (Submit complaint, Notify rules 1–7 and 10) ·
`docs/07_SECURITY.md` §3 · `docs/12_ERROR_HANDLING.md` §2, §4, §5 · `docs/03_DATABASE.md` §3 (complaint insert trigger, outbox,
capture_sessions, `fn_locate_point`, `fn_complaint_notification_recipients`) · `db/V2__civicbrain_app_layer.sql` (templates rows) ·
`tests/smoke/smoke_flow.py` (`stage_intake`)

## Build
1. `GET /public/categories` (`{id, name, workTypeCode, citizenSelectable, needsDepthAnswer}`), `GET /public/wards` (GeoJSON,
   simplified 5 m, `wardNumber`; cached 60 s).
2. `POST /citizen/capture-sessions` → 201 `{captureSessionId, expiresAt}` (10 min).
3. `POST /citizen/complaints` (multipart `data` JSON + `photo`): validation order of 04 §5 (first failure wins, codes of 12 §2):
   auth & verified → rate limit 5/24 h → JSON schema (depthAnswer required for `needs_depth_answer` categories, forbidden
   otherwise → 400 VALIDATION_FAILED) → capture session (own, unused, not expired: 422 CAPTURE_SESSION_INVALID /
   410 CAPTURE_SESSION_EXPIRED) → accuracy ≤ 150 m → `locationCapturedAt` within 10 min → inside boundary
   (`fn_locate_point`) → file: magic bytes JPEG/PNG (415), ≤ 8 MB (413), ≥ 320 px (422 IMAGE_TOO_SMALL), ≤ 40 MP →
   read EXIF (metadata-extractor; keep only capture time/GPS facts for authenticity), **re-encode without EXIF**, store under
   `STORAGE_ROOT/photos/<yyyy>/<mm>/<uuid>.jpg`, SHA-256 → one DB transaction: complaint (trigger → history + outbox
   SUBMITTED + ANALYZE_COMPLAINT job), `complaint_images` (pitch/roll/accuracy, sha256), session used. Response 201
   `{complaintId, publicRef, status, wardNumber}`.
4. `GET /citizen/complaints` (paged), `GET /citizen/complaints/{id}` (04 §5 fields: images, timeline, `contractorName` =
   firm name, `plannedDate`, `mergedIntoPublicRef`, `canGiveFeedback`), `POST /citizen/complaints/{id}/feedback` (upsert,
   `isResolved=false` on COMPLETED/CLOSED → REOPENED through `WorkflowActor`; 422 FEEDBACK_NOT_ALLOWED otherwise).
   Ownership inside the query → 404.
5. `GET /files/{imageId}` (owner, officer in scope, assigned contractor, admin; else 404; `Cache-Control: private, max-age=300`).
6. **Outbox dispatcher** (`@Scheduled` every 10 s, `FOR UPDATE SKIP LOCKED`, batch 50; off in `e2e-seed`/`bootstrap-admin`/
   `test` unless a test enables it): rules 1–7 and 10 of 02 §5 for the EMAIL channel; `{{placeholder}}` replacer (HTML-escaping,
   unknown placeholder = error) for the 16 placeholders; Thymeleaf layout around the body; `dedupe_key`; retries 1/5/30 min,
   max 5; provider INTERNAL for Mailpit. WhatsApp: a `NotificationChannel` interface with a `log` implementation now
   (Twilio in P16). No template for a status (e.g. VERIFIED, SCHEDULED) → outbox row processed, no notifications.
7. `track_url` = `APP_BASE_URL` + `/c/<publicRef>`; `plan_url` = `APP_BASE_URL` + `/contractor/plans/<id>`; `review_url` =
   `APP_BASE_URL` + `/officer/complaints/<id>` (every placeholder of the seeded templates needs a value).

## Tests (write first)
Backend IT: intake happy path (201, publicRef `CB-\d{6}`, ward 1 for 18.7440/73.6760, history + outbox + job rows,
depth/a4 stored, stored file has no EXIF) · each error code above (incl. used session, accuracy 400, outside point
18.7700/73.7500, text file, depth missing for Pothole / present for Garbage) · other citizen's complaint and photo → 404 ·
feedback rules · dispatcher with a Mailpit container: SUBMITTED → exactly one e-mail per recipient; VERIFIED → none;
running the dispatcher twice → no duplicates · template unit test: every seeded template renders with a full value map
(no `{{` left).

## Verify (agent)
1. in `backend`: `.\mvnw.cmd -q verify`.
2. E2E smoke: `start-all.ps1 -Stop` → `seed-e2e.ps1 -MinAccounts 3` → `start-all.ps1 -E2E` →
   `ai-service\.venv\Scripts\python.exe tests\smoke\smoke_flow.py --stage intake` → `SMOKE INTAKE PASSED` → `start-all.ps1 -Restart`.
3. Log scan as in P06 (no tokens, no OTP, no full phone numbers).

## Ask the human (yes/no)
- Q1. In Mailpit (http://localhost:8025) is there a mail "CivicBrain: complaint CB-… received" for citizen1@test.local, and does it read well?

## Done when
verify green · `SMOKE INTAKE PASSED` · committed + pushed.

## Next
`/run-prompt P11` — citizen screens (≈ 2.5 h)
