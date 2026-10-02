# P11 — Citizen screens (report wizard, my complaints, detail)
**Day 3 · agent ≈ 2.5 h · human 0 min (phone test is P13) · Needs: P07, P10 · Model: Flash is fine**

## Goal
A citizen can report a problem with the in-app camera on a phone (wizard of 05 §4), sees the CB number, the list
of own complaints and the detail with timeline, photos, contractor name and "Linked to CB-…".

## Read first
`docs/05_UI_SPEC.md` §1, §2, §4, §7, §8 · `docs/04_API_CONTRACT.md` §3, §5 · `docs/12_ERROR_HANDLING.md` §2 (intake codes), §6

## Build
1. Wizard `/citizen/new`: step 1 category tiles (from `/public/categories`), step 2 `CameraCapture` (tip line for
   Pothole/Waterlogging: "Optional: place an A4 sheet next to it"), step 3 details (title, description with counters,
   landmark; depth question only when `needsDepthAnswer` with the category-specific labels of 05 §4 → SHALLOW/FINGER/DEEP;
   "A4 sheet in photo" toggle), step 4 review (photo, read-only map pin, values) → `POST /citizen/capture-sessions` happens
   right before the camera opens (session id travels with the capture) → submit multipart → step 5 success with `CB-…` and
   "You'll get e-mail/WhatsApp updates". Every intake error code shows its message and the right way back (e.g. capture
   again for CAPTURE_SESSION_*/LOCATION_STALE, open sky for accuracy). Typed data is never lost on error.
2. `/citizen` home (big Report button, recent complaints), `/citizen/complaints` list (Open/Closed chips, skeleton, empty
   state), `/citizen/complaints/:id` detail (photos via `ProtectedImage`, vertical timeline newest first with remarks,
   contractor + planned date when present, MERGED → "Linked to CB-…" link; feedback buttons come in P22).
3. `/c/:publicRef` (link in e-mails) → after login opens the matching complaint of the user, else a friendly 404.
4. Status labels/colours/icons only through `StatusBadge` (05 §1).

## Tests (write first, Vitest + MSW)
wizard blocks submit without photo or GPS · depth question shown only for Pothole/Waterlogging and required there ·
422 GPS_ACCURACY_TOO_LOW shows the open-sky message and keeps the typed text · list empty state · detail shows "Linked to" for MERGED.

## Verify (agent)
1. in `frontend`: lint · typecheck · test · build.
2. E2E stack walkthrough (as in P07; log in as `ui.citizen`): wizard steps 1→3 with the fallback file input if your browser
   tool can attach `tests/fixtures/images/pothole_1.jpg` (submit then must fail with OUTSIDE_BOUNDARY or succeed only if the
   browser's location is inside TDMC - record what happened); the list of a new account shows the empty state.
   Screenshots `docs/screenshots/P11_*.png`
   (wizard steps, list empty, error message). Then `start-all.ps1 -Restart`.

## Ask the human (yes/no)
- Q1. Do the wizard screenshots look right on the narrow phone width (big buttons, nothing cut off)?

## Done when
checks green · screenshots committed · pushed. (The real camera + GPS test is P13.)

## Next
Day 4: `/run-prompt P12` — measurement, estimate, full analysis job (≈ 3 h, strongest model)
