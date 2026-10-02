# 01 — Requirements (FROZEN v1.1, 2026-09-30)

This is the single source of truth for WHAT CivicBrain does. Every feature, test and screen must trace to an ID below (FR-xx, NFR-xx). Changing anything here needs team + guide approval and a new version number at the top.

*v1.1 (kit review, same day): ADMIN bootstrap defined; officer tabs Rejected + Needs review and actions accept/restore; FR-25 bands written as ranges; Decision 1 phase corrected; FR-22 best-photo rule points to `06_AI_PIPELINE.md` §2.6.*

## 1. Scope
- **Client:** Talegaon Dabhade Municipal Council (TDMC), Maval taluka, Pune district, Maharashtra.
- **Area:** municipal boundary 25.26 km², divided into **23 wards** (CivicBrain analytical GIS units, cleaned file `gis/tdmc_wards_clean_v2.geojson`; UI label "Ward 1" … "Ward 23"). These are not the 2025 electoral wards (14 wards / 28 seats); the About page says so in one line.
- **Complaint categories (8):** Pothole, Road Damage, Garbage Accumulation, Waterlogging, Water Leakage, Blocked Drain, Streetlight, Other.
- **Work types (4 + review):** ROAD (Pothole, Road Damage), WATER (Waterlogging, Water Leakage, Blocked Drain), GARBAGE (Garbage Accumulation), ELECTRICITY (Streetlight), REVIEW_REQUIRED (Other → officer must reclassify).
- **YOLO classes (4, frozen):** 0 Pothole, 1 Garbage Accumulation, 2 Waterlogging, 3 Road Damage. Categories without a YOLO class keep the photo as evidence only.

## 2. Roles
| Role | Who | Created by | Login | Second factor |
|---|---|---|---|---|
| CITIZEN | Resident | Self-registration | e-mail or phone + password | E-mail OTP at registration and password reset |
| OFFICER | Municipal officer | ADMIN | e-mail + password | TOTP authenticator app (mandatory) |
| ADMIN | System administrator | Created once per database by `scripts/dev/bootstrap-admin.ps1` (P3; refuses if an ADMIN exists) | e-mail + password | TOTP (mandatory, set up at first login) |
| CONTRACTOR | Contractor firm owner/manager | OFFICER | e-mail/phone + password (must change on first login) | TOTP optional |
| CONTRACTOR_STAFF | Contractor employee (optional login) | OFFICER | same as contractor | TOTP optional |

Officers see only complaints inside their scope (wards and/or work types in `officer_scopes`; no row = nothing). ADMIN sees everything.

## 3. End-to-end flow (the product)
Statuses and who moves them are enforced by the database (`complaint_status_transitions`, V2 — the 20 allowed moves are listed in `03_DATABASE.md` §3). Citizen-facing labels: `05_UI_SPEC.md` §1. A complaint that leaves its plan (reopened, or returned to VERIFIED) is freed for the next plan by the database (V5).

| # | Step | Actor | Status after | Citizen message |
|---|---|---|---|---|
| 1 | Register, verify e-mail OTP, accept privacy notice | Citizen | — | OTP e-mail |
| 2 | Submit complaint: category, text, in-app photo, GPS at shutter | Citizen | SUBMITTED | "Received CB-000123" |
| 3 | AI analysis job: authenticity, classification, YOLO, size, cost, duplicates, priority | System | VERIFIED / MERGED / REJECTED(only by officer) | none for VERIFIED; MERGED gets a message |
| 4 | Officer reviews in "New" tab; can reject, merge, reclassify, edit estimate | Officer | VERIFIED / REJECTED / MERGED | REJECTED/MERGED get a message |
| 5 | Officer generates an action plan (2 km grouping, route, schedule), edits, approves | Officer | SCHEDULED | none |
| 6 | Officer assigns the plan to a contractor | Officer | ASSIGNED | "Contractor X assigned, date D" to every owner incl. merged duplicates |
| 7 | Contractor inspects on site (blind tape measurement, notes, photo, GPS) | Contractor | INSPECTED | notes + expected date |
| 8 | Contractor starts work | Contractor | IN_PROGRESS | "Work started" |
| 9 | Contractor uploads completion proof | Contractor | COMPLETED | message + proof photo |
| 10 | Officer verifies proof | Officer | CLOSED | "Closed, rate the work" |
| 11 | Citizen says "not fixed" (from COMPLETED or CLOSED) | Citizen/Officer | REOPENED | "Reopened" |

## 4. Functional requirements
### Accounts and access
- **FR-01** Citizen self-registration with name, e-mail, phone (+91), password (12–128 chars, blocklist check, no composition rules); e-mail OTP verification before first complaint.
- **FR-02** Login with password; OFFICER/ADMIN must complete TOTP; lockout 15 min after 10 failures; same response whether account exists or not.
- **FR-03** Password reset by e-mail OTP; all sessions revoked on reset.
- **FR-04** ADMIN creates/disables officers and sets their scopes.
- **FR-05** OFFICER creates/edits/disables contractors (firm, contact, work types, crew capacity, shift, equipment) and contractor employees (name, phone, skill, optional login).
- **FR-06** Every user can view/edit own profile, change password, see consents, request data export or deletion (DPDP).

### Complaint intake (citizen)
- **FR-10** Create complaint: category (8), title (5–120 chars), description (10–1000 chars), optional landmark; photo from the in-app camera (no gallery); GPS + accuracy + timestamp + phone tilt recorded at the shutter; optional "A4 sheet in frame" tick; for Pothole/Waterlogging a one-tap depth answer with category-specific labels — Pothole: shallower than a finger / about a finger deep / deeper; Waterlogging: below the ankle / below the knee / above the knee — stored as SHALLOW / FINGER / DEEP.
- **FR-11** Server rejects the submission if: no valid single-use capture session; GPS accuracy > 150 m; location outside the TDMC boundary; image not JPEG/PNG or > 8 MB; > 5 complaints by the same user in 24 h. Each rejection has a clear message (§ `12_ERROR_HANDLING.md`).
- **FR-12** Complaint gets a public number `CB-000123`, ward/road/nearest POI automatically (`fn_locate_point`).
- **FR-13** Citizen sees own complaints, a timeline of every status with date/time and remarks, photos, and the assigned contractor name.
- **FR-14** Citizen can support ("me too") a nearby complaint on the public map (one vote per user).
- **FR-15** Citizen confirms "fixed / not fixed" and rates 1–5 after COMPLETED/CLOSED.

### AI analysis (system, background job per complaint)
- **FR-20** Authenticity score 0–100 from explainable checks (capture session, GPS accuracy, GPS freshness, boundary, photo reuse by SHA-256 and perceptual hash, submission rate, impossible travel, account trust). Score < 40 → FLAGGED for officer review; never auto-reject on one signal.
- **FR-21** Text classification suggests a category; YOLO detects the 4 classes; mismatches are flagged, never silently changed.
- **FR-22** Duplicate detection with the frozen Step 12 method (300 m, 7 days, all-MiniLM-L6-v2, 0.70/0.20/0.10, DUPLICATE ≥ 0.59, UNCERTAIN 0.55–0.59 → officer review). DUPLICATE → MERGED into the existing master; the master keeps the earlier complaint (frozen rule) and shows the best-quality photo of the group (quality score in `06_AI_PIPELINE.md` §2.6).
- **FR-23** Size estimate in metres (length, width, area) with a confidence tier (A: A4 sheet, B: phone tilt + camera geometry, C: class size prior) and an error band; depth from the citizen's depth answer mapped to IRC:82 classes.
- **FR-24** Material quantities, workers, hours and cost range (min / expected / max) from rule-based takeoff + Step 10 models; Maharashtra PWD SSR 2022-23 rates configured by the team (blank rate = shown as "rate not configured").
- **FR-25** Priority with the frozen Step 11 formula (7 factors, weights 0.25/0.15/0.15/0.10/0.10/0.15/0.10; LOW P < 25, MEDIUM 25 ≤ P < 50, HIGH 50 ≤ P < 75, CRITICAL P ≥ 75) and a per-factor explanation.

### Officer
- **FR-30** Dashboard tabs New / Needs review (analysis failed or flagged) / In Progress / Completed / Rejected with counts, filters (ward, category, work type, priority, date, authenticity), sort by priority, table + map (23 ward polygons, markers).
- **FR-31** Complaint detail: photos with YOLO box, AI measurements vs contractor measurements, estimate, priority factors, authenticity checks, duplicates, timeline.
- **FR-32** Actions: reject (reason required), merge into another complaint, un-merge, reclassify category, override estimate, request re-analysis, accept a complaint whose analysis failed (SUBMITTED → VERIFIED), restore a rejected complaint (REJECTED → VERIFIED).
- **FR-33** Generate action plan: choose date + work type + wards or selected complaints → background optimisation (live 2 km grouping ≤ 10 jobs, OSRM road times, OR-Tools routing within 08:00–17:00 from depot D001) → DRAFT plan with ordered stops, times, route, workers, equipment, materials, cost; jobs that do not fit are listed with a reason.
- **FR-34** Edit plan (reorder, add/remove complaints, change date/times) — every save is a new version; approve (→ SCHEDULED); assign to an ACTIVE contractor registered for the work type (→ ASSIGNED); cancel.
- **FR-35** Download plan as PDF and Excel (officer/admin only), rendered from a specific version.
- **FR-36** Verify completion (approve → CLOSED; reject → REOPENED with reason).
- **FR-37** Approve a photo for the public map only after automatic face/plate blurring.
- **FR-38** Notification log page (who got what, channel, status).

### Contractor
- **FR-40** Worklist of assigned plans (today first) with map, stop order and navigation link.
- **FR-41** Inspection form: issue confirmed yes/no, tape measurements (not pre-filled with AI values), findings, expected completion date, ≥ 1 photo; GPS distance to the complaint is recorded; > 100 m flags the officer.
- **FR-42** Start work; completion form with proof photo(s), actual workers/hours/cost/materials; proof photos are checked against earlier photos (reuse flag).

### Notifications
- **FR-50** E-mail + WhatsApp to the complaint owner and to owners of complaints merged into it, for: SUBMITTED, MERGED, REJECTED, ASSIGNED, INSPECTED, IN_PROGRESS, COMPLETED (with photo), CLOSED, REOPENED. Contractor gets ACTION_PLAN_ASSIGNED; officer gets COMPLETION_SUBMITTED.
- **FR-51** Delivered through the transactional outbox; each (event, recipient, channel) sent at most once; retries 1/5/30 min, max 5; status SENT/DELIVERED/READ/FAILED logged.
- **FR-52** Channels respect opt-in (e-mail default on; WhatsApp only after consent).

### Privacy
- **FR-60** Privacy notice accepted at registration (versioned); separate optional consents: public photo, AI training, WhatsApp messages; withdrawable any time.
- **FR-61** Data-principal requests (access, correction, erasure, withdraw consent, grievance) tracked with a 90-day due date.
- **FR-62** Public map shows no personal data, location snapped to ~220 m, and only blurred + approved photos.

## 5. Non-functional requirements
- **NFR-01 Security:** OWASP ASVS 5.0 Level 2 for authentication, session, access control, validation, files, logging (`07_SECURITY.md`).
- **NFR-02 Performance (demo scale: 5,000 complaints, 20 concurrent users):** API p95 < 500 ms for list/detail; complaint submit < 2 s (excl. upload time); AI job < 60 s on a CPU laptop; plan optimisation ≤ 10 s solver limit for ≤ 50 jobs.
- **NFR-03 Reliability:** no lost notifications or jobs after a crash (outbox + job table); every external call has a timeout and a documented retry policy.
- **NFR-04 Usability:** citizen and contractor screens work at 360 px width, touch targets ≥ 44 px, English UI with Marathi-ready i18n keys; every screen has loading, empty, error states.
- **NFR-05 Accessibility:** no serious/critical axe violations on main pages.
- **NFR-06 Maintainability:** tests at every layer (`08_TEST_PLAN.md`), backend line coverage ≥ 70 %, CI green before merge.
- **NFR-07 Honesty:** AI numbers always shown with their confidence tier/range; synthetic data always labelled; README states limits.
- **NFR-08 Data retention:** audit/auth logs 365 days; OTPs 30 days; photos and complaints kept while the project runs; erasure requests honoured except where municipal records must be kept (then anonymised).

## 6. Decisions taken (change only with team + guide approval)
1. The PostgreSQL database is the complaint source of truth; Steps 10/11/13 are re-run on it (P1 step 4).
2. Duplicate master stays "earlier complaint" (frozen); the best photo is displayed.
3. Contractor employees are data by default; login optional (CONTRACTOR_STAFF).
4. Spring Boot 4.1 on Java 25 LTS (Boot 3.x is out of open-source support).
5. A4 sheet is optional (raises confidence to Tier A).
6. English message templates first; Marathi templates optional later (locale column exists).
7. No Redis, no MinIO: PostgreSQL job table + local disk storage.
8. OTP by e-mail (+ WhatsApp OTP for the 5 demo phones); no SMS (TRAI DLT registration needed).

## 7. Out of scope
Hotspot detection; native Android/iOS apps; SMS; payments; exact pothole depth from a photo; official TDMC staff/inventory/rates (prototype values are labelled); integration with TDMC's existing systems.

## 8. Acceptance (project level)
The system is accepted when the demo script in `13_DEMO_AND_DEPLOY.md` runs twice in a row on a clean machine with: all CI jobs green, the full-lifecycle E2E test green, 0 critical/high findings in ZAP/Trivy, and the evaluation report (YOLO per-class metrics, classifier macro-F1, measurement error per tier, FIFO vs optimised plan) generated from the final data.
