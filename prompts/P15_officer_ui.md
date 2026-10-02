# P15 — Officer portal UI
**Day 4 · agent ≈ 3 h · human ≈ 5 min · Needs: P07, P14 · Model: Flash, strongest for the map/detail**

## Goal
The officer works on a laptop: dashboard, complaint tabs with table + ward map, full complaint detail with the YOLO box,
AI numbers with confidence tier, priority factors, authenticity, duplicates and timeline, action dialogs, contractor
management with the one-time-password dialog, and a minimal admin page for officers + scopes.

## Read first
`docs/05_UI_SPEC.md` §1, §2, §5 (MVP parts), §7, §8 · `docs/04_API_CONTRACT.md` §6, §8 · `docs/12_ERROR_HANDLING.md` §6 ·
`docs/09_BUILD_PLAN_7DAY.md` §1 OUT list (no duplicates queue page, no notification log page, no rates editor, no jobs/audit pages)

## Build
1. `OfficerLayout` (left nav: Dashboard, Complaints, Action Plans (P19), Contractors, Admin* for ADMIN; top bar with the scope
   text, e.g. "All wards · ROAD").
2. Dashboard: cards from `/officer/stats` (New, In progress, Completed this week, Flagged, Overdue > 7 days), counts by ward,
   top-priority new complaints.
3. Complaints: tabs with counts; filter bar (ward, category, work type, priority, authenticity, dates; "include synthetic"
   off); split view table (publicRef, title, category, ward, priority badge + score, authenticity badge, cost range, age, status)
   + `WardMap` (react-leaflet 5, OSM tiles `https://tile.openstreetmap.org/{z}/{x}/{y}.png` - no `{s}` subdomains, the CSP
   allows only this host - with attribution, 23 wards from `/public/wards` with "Ward N" labels at zoom ≥ 14,
   centre 18.7248, 73.6846 zoom 14, markers coloured by work type and sized by priority, simple client-side grid grouping above
   100 markers, click syncs the table row). "Needs review" rows show why + "Re-run analysis" / "Accept"; "Rejected" rows "Restore".
   Row checkboxes → "Plan selected" (navigates to the plan builder in P19 with the ids).
4. Detail page: photo viewer with YOLO boxes drawn on a canvas/SVG overlay scaled from pixel coordinates + confidence;
   tabs Overview (text, mini map, ward), AI (text classification vs chosen category + "possible wrong category" badge,
   detections, measurement with tier letter and range, estimate lines with "rate not configured", priority factor bars with
   the explanation), Authenticity (each check PASS/WARN/FAIL + detail), Duplicates (children, candidates), Timeline, Field
   (inspection / completion, from P20). Action buttons with `ConfirmDialog` (reason required) for the P14 actions.
5. Contractors: list + create/edit form (firm, contact, phone, e-mail, work types, crew capacity, shift) + one-time password
   dialog (copy button, shown once, warning text) + workers table (data only).
6. Admin (ADMIN only): officers list, create officer, edit scopes (ward numbers and/or work types), disable.

## Tests (write first, Vitest + MSW)
tabs show counts and switch the query · reject dialog requires a reason · YOLO overlay scales a 1280×960 box onto a 640 px
wide image correctly · one-time password dialog shows the password once and hides it after closing · `RequireRole` keeps a
citizen out of `/officer`.

## Verify (agent)
1. in `frontend`: lint · typecheck · test · build.
2. E2E walkthrough: `start-all.ps1 -Stop` → `seed-e2e.ps1` → `start-all.ps1 -E2E` →
   `ai-service\.venv\Scripts\python.exe tests\smoke\smoke_flow.py --stage officer` (creates analysed complaints A, B, C) →
   browser: log in as `ui.officer` (`tests/e2e-ui-accounts.local.json`) → dashboard, complaints NEW tab with the map, open A's
   detail (YOLO box, tier, priority, authenticity), open the contractors page, create a test firm and see the one-time password
   dialog. Screenshots `docs/screenshots/P15_dashboard.png`, `P15_complaints_map.png`, `P15_detail_ai.png`,
   `P15_contractor_otp.png` → `start-all.ps1 -Restart`.

## Human step (≈ 5 min)
Look at the 4 screenshots (or log in yourself on the E2E stack if the agent left it running).

## Ask the human (yes/no)
- Q1. Is the ward map with the 23 wards and the complaint markers readable in `P15_complaints_map.png`?
- Q2. Does the detail page show the photo with the YOLO box and the AI numbers with their confidence tier?

## Done when
checks green · screenshots committed · answers yes · pushed.

## Next
Day 5: `/run-prompt P16` — WhatsApp through the Twilio sandbox (≈ 1.5 h + your Twilio setup)
