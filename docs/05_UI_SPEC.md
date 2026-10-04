# 05 — UI Specification

One React app, three portals chosen by role after login. Citizen and contractor screens are **mobile-first (360 px)**; officer/admin screens are desktop-first (≥ 1280 px) but usable on a tablet. Tailwind 4, no UI kit required (headless components written in-house). All text through i18n keys (`en` now, `mr` later).

## 1. Status language (same everywhere)
| Status | Citizen label | Colour token | Icon |
|---|---|---|---|
| SUBMITTED | Received | neutral | inbox |
| VERIFIED | Under review | neutral | search |
| SCHEDULED | Planned | info | calendar |
| ASSIGNED | Contractor assigned | info | user-check |
| INSPECTED | Site inspected | info | clipboard |
| IN_PROGRESS | Work in progress | warning | hammer |
| COMPLETED | Work completed — please confirm | success | check |
| CLOSED | Closed | success | check-double |
| REOPENED | Reopened | warning | rotate |
| REJECTED | Not accepted | danger | x |
| MERGED | Linked to CB-xxxxxx | neutral | link |
Never show colour alone: every badge has text + icon. Icons are small inline SVG React components written in `src/components/icons/` (no icon package is installed; names above are descriptive).

## 2. Global rules for every screen
- **Four states:** loading (skeletons, not spinners, for lists), empty (one sentence + next action), error (message from the error code + "Try again"; `requestId` in small text), success.
- **Forms:** react-hook-form + zod schemas mirroring the API validation; inline field errors under the field; submit button disabled while submitting; server `fieldErrors` mapped to fields; never lose typed data on error.
- **Network:** TanStack Query; retries only for GET (2 retries, not on 4xx); mutations never auto-retry. Offline banner when `navigator.onLine` is false.
- **Auth:** access token in memory (React context), silent refresh on load, one shared refresh promise for parallel 401s, `BroadcastChannel` to sync logout across tabs, redirect to login with return URL. Route guards `RequireAuth`, `RequireRole` (UX only; server enforces).
- **Dates:** show Asia/Kolkata, e.g. "5 Oct 2026, 8:20 am". **Money:** ₹ with Indian grouping (₹1,23,456). **Distances:** m / km.
- **Accessibility:** labels on all inputs, focus visible, 44 px touch targets, contrast AA, keyboard-usable dialogs, `aria-live` for toasts.
- **Security in UI:** no `dangerouslySetInnerHTML`; photos loaded via `/api/v1/files/{id}` as blob URLs (bearer header), revoked on unmount; CSP-compatible (no inline scripts).
- **Maps:** react-leaflet 5 + Leaflet 1.9.4, OSM tiles with "© OpenStreetMap contributors"; 23 ward polygons (thin outline, label "Ward N" at zoom ≥ 14); centre 18.7248, 73.6846, zoom 14; when > 100 markers are in view, group them with a simple client-side grid (cells of ~40 px, a count bubble per cell; click zooms in) — no clustering package (none is pinned for react-leaflet 5).

## 3. Public / shared screens
- **Landing:** what CivicBrain does (3 steps), buttons Report a problem / Track / Log in; link to public map and privacy notice.
- **Register:** name, e-mail, phone (+91 prefix fixed), password (show/hide, strength hint, 12–128 chars), privacy notice (scroll box, version), required checkbox "I accept", optional checkboxes: WhatsApp updates, show my photo publicly after blurring, allow photos to improve the AI. → OTP screen (6 boxes, paste-friendly, resend timer 60 s).
- **Login:** identifier + password; then TOTP screen when required; first-time officer sees TOTP setup (QR + manual code + confirm). Contractor with `mustChangePassword` → forced change screen.
- **Forgot/reset password**, **Profile** (language, notification opt-ins, consents with withdraw, "Download my data", "Delete my account" request), **Public map** (filters category/status; supporters count; "Support" button for logged-in citizens), **About** (limits: AI estimates are preliminary; wards are analytical units).

## 4. Citizen portal (mobile-first)
1. **Home:** big "Report a problem" button; my recent complaints (status badges); link to map.
2. **New complaint — step 1 Category:** large tiles with icons for the citizen-selectable categories only (`citizenSelectable` of `GET /public/categories`): **5 tiles** in the 7-day MVP (V6) — Pothole, Road Damage, Waterlogging, Garbage Accumulation, Other; two per row on a phone, "Other" spans the last row. Water Leakage, Blocked Drain and Streetlight are not offered (they stay in the data model).
3. **Step 2 Photo & location:** "Capture" button → iOS orientation permission prompt (if needed) → in-page camera (`getUserMedia({video:{facingMode:'environment', width:{ideal:1920}}})`) with overlay: guide frame, live tilt indicator (green when 45–70° down, roll < 5°), GPS accuracy chip (green ≤ 50 m, amber ≤ 150 m, red > 150 m). Tip line for Pothole/Waterlogging: "Optional: place an A4 sheet next to it". Shutter → canvas JPEG (quality 0.9, verify MIME) + `getCurrentPosition({enableHighAccuracy:true, maximumAge:0, timeout:20000})` + current `beta/gamma`. Preview with Retake. No gallery button. Camera denied → explain + fallback `<input type="file" accept="image/*" capture="environment">`. Location denied → explain how to enable; cannot continue. Accuracy > 150 m → "Move to open sky and retry".
4. **Step 3 Details:** title, description (char counters), landmark (optional); for Pothole/Waterlogging the depth question (3 pictograms with category-specific labels — Pothole: "shallower than a finger" / "about a finger deep" / "deeper"; Waterlogging: "below the ankle" / "below the knee" / "above the knee" — sent as SHALLOW / FINGER / DEEP); "A4 sheet in photo" toggle.
5. **Step 4 Review & submit:** summary with photo, map pin (read-only, from GPS), ward number shown after server response. Submit → success screen with `CB-000123`, "You'll get e-mail/WhatsApp updates".
6. **My complaints:** list with filter chips (Open / Closed); pull-to-refresh.
7. **Complaint detail:** photo(s), status timeline (vertical, newest first, with remarks), contractor name + planned date when assigned, inspection notes, proof photo when completed, buttons "Fixed" / "Not fixed" + rating (1–5 stars) + comment when COMPLETED/CLOSED; MERGED shows "Linked to CB-…" with link.

## 5. Officer portal (desktop)
- **Layout:** left nav (Dashboard, Complaints, Duplicates, Action Plans, Contractors, Notifications, Admin*), top bar with scope ("Wards 1–8 · ROAD"), user menu.
- **Dashboard:** cards (New, In progress, Completed this week, Flagged, Overdue > 7 days), bar by ward, list of top-priority new complaints.
- **Complaints:** tabs New / Needs review / In Progress / Completed / Rejected with counts (`04_API_CONTRACT.md` §6 defines each tab); "Needs review" rows show why (analysis failed, flagged, uncertain duplicate, stuck > 10 min) with the buttons "Re-run analysis" and "Accept"; "Rejected" rows have "Restore"; filter bar (ward, category, work type, priority, authenticity, date range, "include synthetic" off by default); split view: table (publicRef, title, category, ward, priority badge + score, authenticity badge, cost range, age, status) + map (markers by work type colour, size by priority; click syncs row); bulk select → "Plan selected".
- **Complaint detail (drawer or page):** photo viewer with YOLO boxes overlay and confidence; tabs: Overview (text, location mini-map, ward, road, POI), AI (classification vs chosen category, detections, measurement tier + range, estimate lines materials/equipment/labour with "rate not configured" markers, priority factors bar list with explanation), Authenticity (each check PASS/WARN/FAIL + details), Duplicates (linked children, candidates), Timeline, Field (inspection: AI vs contractor measurement side by side; completion proof; verification). Action buttons with confirmation dialogs requiring a reason. The main photo shown is the group's best photo (`displayImageId`, highest quality score among the master and merged children); all photos stay available. Contractor proof photos show a reuse badge when ANALYZE_IMAGE found a match. Public-photo approval dialog: shows the auto-blurred preview (faces), lets the officer drag rectangles over number plates or anything else to blur, re-runs blur, then Approve / Keep private.
- **Duplicates review:** queue of UNCERTAIN pairs side by side (photos, text, distance, time gap, score) → Merge / Keep separate.
- **Action plan builder:** step 1 filters (date, work type, wards or "use selected complaints", contractors to consider) → Generate (progress bar polling every 2 s, cancel) → result: map with numbered stops + route polyline per crew, stop list (reorder by native HTML5 drag-and-drop **and** keyboard-accessible ▲/▼ buttons — no drag-and-drop package; remove; add from sidebar), totals (jobs, workers, service h, travel h, km, ₹), dropped jobs with reasons, version badge, "Save changes" (re-time job), Approve, Assign contractor (dropdown shows only ACTIVE contractors registered for the work type, with crew capacity), Download PDF / Excel, Cancel plan (allowed until work starts; `PLAN_STATE_CONFLICT` otherwise). An item whose inspection says "issue not found" shows "Remove from plan". Stale version → dialog "Plan changed by someone else — reload".
- **Contractors:** list (status, work types, crew, active plans); create/edit form (firm, contact person, phone, e-mail, address, registration no., work types multi-select, crew capacity, shift start/end, equipment quantities); one-time password dialog after create (copy button, shown once); workers table (add/edit/deactivate; optional login).
- **Notifications log:** table (time, complaint, recipient masked, channel, template, status, provider id, error) with filters.
- **Admin (ADMIN only):** officers & scopes, jobs monitor (counts by status, DEAD jobs with error, requeue), audit log search, material/equipment rates editor, privacy requests queue.

## 6. Contractor portal (mobile-first)
- **Today:** date switcher; assigned plans; map with numbered stops; stop cards (publicRef, category, landmark, planned time, status) with "Navigate" (opens `https://www.google.com/maps/dir/?api=1&destination=lat,lon`) and "Open".
- **Stop detail:** complaint photo + description (no citizen contact details), actions by status: ASSIGNED → "Record inspection"; INSPECTED → "Start work"; IN_PROGRESS → "Mark completed".
- **Inspection form:** issue confirmed (yes/no), tape measurements length/width/depth (m, numeric keypad; **no AI values shown**), findings (required), expected completion date, 1–3 photos via the same in-page camera component (capture session + GPS); distance-from-site warning if > 100 m ("You seem to be 240 m away — submit anyway?").
- **Completion form:** work summary, actual workers, hours, cost (optional), materials used (rows: material dropdown, quantity, unit), 1–3 proof photos (same camera component). After submit: "Waiting for officer verification".

## 7. Components to build once and reuse
`CameraCapture` (getUserMedia + orientation + geolocation + fallback, returns `{blob, lat, lon, accuracyM, capturedAt, pitchDeg, rollDeg, method}`), `StatusBadge`, `Timeline`, `WardMap` (wards layer + markers + route layer), `ProtectedImage`, `ConfirmDialog` (reason field), `DataTable` (server pagination/sort), `FilterBar`, `MoneyRange`, `EmptyState`, `ErrorState` (maps error codes to messages), `PageSkeleton`, `Toast`.

## 8. Test IDs
Every interactive element used by E2E tests gets `data-testid` (kebab-case, e.g. `capture-shutter`, `complaint-submit`, `plan-generate`, `plan-approve`, `plan-assign`, `inspection-submit`, `completion-submit`, `verify-approve`). Playwright tests use roles/labels first and test IDs only where needed.
