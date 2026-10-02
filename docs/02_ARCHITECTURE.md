# 02 — Architecture

## 1. Components
```
 Phone / laptop browser (React SPA: citizen · officer · contractor portals)
        │  HTTPS (same origin)            dev: Vite :5173 proxies /api → :8080
        ▼
 Spring Boot API :8080  ── Flyway ──►  PostgreSQL 18 + PostGIS 3.6 :5432
   auth · complaints · workflow            ▲        ▲
   contractors · plans · exports           │        │ jobs table (SKIP LOCKED)
   notification dispatcher ─► SMTP / WhatsApp│        │
   photo storage (local disk)               │   Python AI worker + FastAPI :8001 (internal)
                                            │     analyze_complaint · optimize_plan · blur_image
                                            │        │
                                            └────────┴──► OSRM :5000 (Docker, road times)
```
- **One database, two writers.** Spring owns users, complaints (create/status), contractors, plans, notifications. The Python worker owns AI outputs (ai_classifications, yolo_detections, defect_measurements, priority_assessments, resource_estimates, authenticity_checks, duplicate_relation) and moves status only through the V2 rules with `civicbrain.actor_role = 'SYSTEM'`.
- **No service-to-service calls for heavy work.** Spring inserts a row (complaint / optimizer_run); a DB trigger enqueues a job (V4); the worker claims it with `fn_claim_jobs`, finishes with `fn_finish_job` (retries after 1 and 5 min; the 3rd failure → DEAD, `max_attempts = 3`). FastAPI only exposes `/health` (no auth, localhost), `/v1/models` and `/v1/jobs/{jobId}/requeue` (service JWT) — `04_API_CONTRACT.md` §10.
- **Photos** are stored under `STORAGE_ROOT` (outside the web root) as `photos/YYYY/MM/<uuid>.jpg`, re-encoded (EXIF removed, long side ≤ 1920 px, JPEG q85). Served only by `GET /api/v1/files/{imageId}` after an ownership check. The worker reads the same folder (read-only) and writes blurred copies to `photos-public/`.

## 2. Repository layout (monorepo)
```
civicbrain/                      <- C:\dev\civicbrain  (NOT inside OneDrive, NOT a drive root)
├── AGENTS.md  .agents/          <- agent rules + skills (Antigravity reads them; CLAUDE.md + .claude/ for Claude Code)
├── docs/                        <- this specification + PROGRESS.md
├── db/                          <- V1..V5 (psql/pgAdmin versions), tests, seed, schema reference
├── gis/                         <- cleaned 23 wards + QA report + build scripts
├── backend/                     <- Spring Boot (Maven wrapper)
│   └── src/main/resources/db/migration/  <- Flyway copies (from kit folder flyway/)
├── frontend/                    <- React + Vite
├── ai-service/                  <- FastAPI + worker (app/, worker/, models/ (git-ignored), tests/)
├── infra/osrm/                  <- docker-compose + OSRM data (git-ignored)
├── scripts/dev/                 <- PowerShell setup/start/check scripts (start-all.ps1 runs the stack; who runs what: 10 §4)
├── data/  scripts/ (existing research pipeline, Steps 1-13 — keep; large image folders git-ignored)
└── storage/                     <- photos (git-ignored)
```

## 3. Backend package structure (`com.civicbrain`)
`config` (security, web, jackson, clock) · `common` (error model, pagination, validation, audit) · `auth` (register, login, refresh, OTP, TOTP, lockout) · `users` · `officers` · `contractors` · `complaints` (create, query, timeline, votes, feedback) · `files` (upload pipeline, storage, download) · `workflow` (status transitions via DB rules, actor context) · `ai` (read AI results, re-analysis request) · `plans` (optimizer runs, action plans, versions, approve/assign, exports) · `field` (inspections, completions, verification) · `notifications` (outbox dispatcher, templates, channels, webhooks) · `privacy` (consents, requests, public map) · `admin` (settings, jobs monitor). Each module: `api` (controllers + DTOs), `service`, `repo`, `model`. Controllers never return entities.

**Actor context:** a `WorkflowActor` helper runs, inside the same transaction, `select set_config('civicbrain.actor_user_id', :id, true), set_config('civicbrain.actor_role', :role, true), set_config('civicbrain.status_remarks', :remarks, true)` before any complaint status update. Status is never changed with plain JPA dirty checking without this call (enforced by a unit test that scans for `setStatus(` outside `workflow`).

## 4. AI service structure (`ai-service/`)
`app/main.py` (FastAPI) · `app/config.py` (pydantic-settings) · `app/db.py` (SQLAlchemy 2 + psycopg3) · `worker/run.py` (loop: claim → dispatch by job_type → finish; graceful stop; stale requeue every 5 min) · `pipeline/` (`authenticity.py`, `classify.py`, `detect.py`, `measure.py`, `estimate.py`, `duplicates.py`, `priority.py`, `analyze.py` orchestrator) · `optimizer/` (`cluster.py` → `fn_cluster_jobs`, `osrm.py`, `routing.py` OR-Tools, `plan_writer.py`) · `privacy/blur.py` · `models/` (weights, git-ignored) · `tests/`.

## 5. Key flows
**Submit complaint:** SPA `POST /capture-sessions` → camera → `POST /complaints` (multipart) → Spring validates session, GPS accuracy, boundary (`fn_locate_point`), rate limit, file → one transaction: insert complaint (trigger: history + outbox SUBMITTED + job ANALYZE_COMPLAINT) + insert complaint_images + mark session used → 201 with `publicRef`.
**Analyse:** worker claims ANALYZE_COMPLAINT → authenticity → classify → YOLO → measure → estimate → duplicates → priority → status VERIFIED or MERGED (SYSTEM) → finish job. Any step failure: the job fails and retries; partial results are written idempotently (delete-then-insert per complaint and model version inside one transaction).
**Plan:** officer `POST /officer/plans/generate` → optimizer_runs QUEUED (trigger → job) → worker: `fn_cluster_jobs` → OSRM table → OR-Tools → writes DRAFT action_plans + items + revision 1 → run SUCCEEDED → SPA polls `GET /officer/optimizer-runs/{id}` every 2 s (max 60 s).
**Notify:** Spring `@Scheduled` dispatcher every 10 s reads unprocessed `notification_outbox` rows (FOR UPDATE SKIP LOCKED, batch 50) → one `notifications` row per recipient × channel (`dedupe_key` = outbox_id:user_id:channel) → send → update status; provider webhooks update DELIVERED/READ. Rules:
1. **Status events** (`COMPLAINT_STATUS_CHANGED`, written by the V2 trigger): recipients = `fn_complaint_notification_recipients(complaint_id)` (owner + owners of merged children); template = `notification_templates` row with `event_status` = the outbox row's `event_status` and the channel. **No template for that status (e.g. VERIFIED) → mark the outbox row processed and create no rows.**
2. **ACTION_PLAN_ASSIGNED** (`complaint_id` NULL, `action_plan_id` set): recipient = `contractors.user_id` of the plan's contractor.
3. **COMPLETION_SUBMITTED**: inserted by the backend in the completion transaction; recipient = the plan's `assigned_by_user_id` (the officer).
4. **OTP mails never go through the outbox** (`07_SECURITY.md` §1).
5. Channels: e-mail if `users.email_opt_in` and an e-mail exists; WhatsApp only if `users.whatsapp_opt_in` (kept in sync with the WHATSAPP_MESSAGES consent — both endpoints update both in one transaction) and a phone exists.
6. Bodies: templates use `{{name}}` placeholders → a small HTML-escaping replacer (unknown placeholder = error, never a blank); Thymeleaf only for the e-mail layout around the body. Values (exactly the 16 placeholders used by the seeded templates): `citizen_name` (recipient's full name), `public_ref`, `category` (category name), `location_text` (landmark, else address text, else "Ward N"), `submitted_at` (Asia/Kolkata, `05_UI_SPEC.md` §2 format), `contractor_name` (firm name), `planned_date`, `inspection_notes` (inspection findings), `expected_completion` (inspection's expected completion date), `master_ref` (master's `public_ref`), `remarks` (the status change's `status_remarks`, else empty text), `track_url` (= `APP_BASE_URL` + `/c/<publicRef>`), `plan_code`, `job_count`, `plan_url`, `review_url`. A unit test renders every template with a full value map (no leftover `{{`).
7. `notifications.provider`: Gmail SMTP → GMAIL_SMTP, Brevo → BREVO, other SMTP (Mailpit) → INTERNAL, `log` → INTERNAL, meta → META_CLOUD_API, twilio → TWILIO_SANDBOX.
8. Photos (`include_photo`): e-mail = inline + attachment from storage; Meta = upload the bytes to `/{PHONE_ID}/media`, send the media id; Twilio = signed URL `/api/v1/public/media/{token}` valid 10 min. Never a permanent public URL of a private photo.
9. Meta outside the 24-hour window needs approved templates: store the approved name in `provider_template_name` (P5/P12) and send the placeholders as positional parameters in template order; until approved, the test number is used with registered recipients only.
10. Retries: 1 / 5 / 30 min, max 5 attempts (`next_attempt_at`); 4xx from a provider (bad number, template) → FAILED without retry.

## 6. Configuration (`.env`, never committed; `.env.example` lists every key with comments)
- **Database:** `DB_HOST, DB_PORT, DB_NAME` (Python + scripts) and `DB_URL` (JDBC, Spring) · `DB_USER, DB_PASSWORD` (API role `civicbrain_app`) · `DB_AI_USER, DB_AI_PASSWORD` (worker role `civicbrain_ai`) · `PG_ADMIN_USER, PG_ADMIN_PASSWORD` (database owner: **only** Flyway via `spring.flyway.user/password` and the human scripts) · `PG_BIN` (folder of psql.exe/pg_dump.exe) · `DB_TEST_NAME=civicbrain_test`, `DB_E2E_NAME=civicbrain_e2e`.
- **Auth/crypto:** `JWT_SECRET` (≥ 32 random bytes, base64) · `JWT_ISSUER=civicbrain` · `JWT_AUDIENCE=civicbrain-web` · `OTP_HMAC_KEY` · `TOTP_ENC_KEY` (exactly 32 bytes base64, AES-256-GCM) · `AI_SERVICE_JWT_SECRET`. A different random value for each (`scripts/dev/new-secret.ps1`).
- **Web:** `APP_BASE_URL` (links in messages + Origin check) · `APP_EXTRA_ORIGINS` (dev only, comma list) · `STORAGE_ROOT` (absolute) · `SPRING_PROFILES_ACTIVE=dev|demo` (`e2e`, `e2e-seed` set by scripts) · `LABOUR_RATE_PER_HOUR` (empty until TDMC gives a rate).
- **Mail:** `SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_STARTTLS, SMTP_FROM`.
- **WhatsApp:** `WHATSAPP_PROVIDER=log|meta|twilio` · `META_WA_TOKEN, META_WA_PHONE_ID, META_WA_APP_SECRET, META_WA_VERIFY_TOKEN, META_WA_API_VERSION=v26.0` · `TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM`.
- **AI:** `AI_API_HOST=127.0.0.1, AI_API_PORT=8001, AI_SERVICE_URL` · `ROUTING_MODE=haversine|osrm` (MVP: haversine) · `OSRM_URL=http://127.0.0.1:5000` (IPv4: Docker publishes on 127.0.0.1) · `YOLO_WEIGHTS, MODELS_DIR, TEXT_EMBEDDING_MODEL_DIR` (absolute paths) · `HF_HUB_OFFLINE=1` · `WORKER_ID` (unique per worker process) · `WORKER_POLL_SECONDS` · `BLUR_ENABLED` (P7) · `LOG_LEVEL`.
- Spring reads them through `application.yml` placeholders; the app fails fast at startup if a required one is missing (`@Validated @ConfigurationProperties`). Python: pydantic-settings with the same names. `.env.test` (from `.env.test.example`) holds the fixed E2E accounts only.
- Spring Boot does not read `.env` by itself: the `scripts/dev/start-*.ps1` scripts load it into the process environment. The Vite dev server needs no secrets.

## 7. Environments
| | Dev (each laptop) | Demo (one laptop) |
|---|---|---|
| Frontend | `npm run dev` :5173 (proxy) | `npm run build` served by Spring static or Nginx |
| HTTPS for phones | Cloudflare quick tunnel to :5173 (`start-all.ps1 -Tunnel`; Vite `server.allowedHosts: ['.trycloudflare.com']`; the backend gets the URL as `APP_BASE_URL` for that run) | quick tunnel to :8080 (`start-all.ps1 -Demo -Tunnel`) or Nginx :443 |
| Mail | Mailpit | Gmail SMTP app password or Brevo |
| WhatsApp | `log` provider | Meta test number (5 phones) / Twilio sandbox |
| Data | `civicbrain`: restored backup (or empty) → Flyway V2–V5/V1–V5 + R__ grants; `civicbrain_test` (psql build + seed, SQL + AI integration tests); `civicbrain_e2e` (Flyway + fixed accounts, Playwright) | restored backup + V2–V5 (Flyway) + demo accounts |

## 8. Observability
Structured JSON logs (Spring: logstash encoder or Boot 4 structured logging; Python: `logging` JSON) with `requestId` (header `X-Request-Id`, generated if absent, propagated to jobs via payload). Never log secrets, OTPs, tokens, full phone numbers, passwords or photo bytes. `/actuator/health` (public: status only), `/actuator/info`; job monitor page for ADMIN (counts by status, DEAD jobs with last_error, requeue button).
