# P22 — Contractor screens + citizen "Fixed / Not fixed" and rating
**Day 6 · agent ≈ 3 h · human ≈ 2 min · Needs: P19, P20 · Model: Flash is fine**

## Goal
The contractor works on a phone: today's stops on a map with Navigate links, stop detail, inspection form (camera + tape
values, no AI numbers), start, completion with proof photos; the citizen confirms "Fixed" or "Not fixed" and rates.

## Read first
`docs/05_UI_SPEC.md` §4 (detail feedback), §6, §7 (`CameraCapture`) · `docs/04_API_CONTRACT.md` §5 feedback, §7

## Build
1. `ContractorLayout` pages: **Today** (date switcher, assigned plans, map with numbered stops, stop cards with publicRef,
   category, landmark, planned time, status, "Navigate" → `https://www.google.com/maps/dir/?api=1&destination=lat,lon`, "Open").
2. **Stop detail** (photo + description, no citizen contact data) with the action for the status: ASSIGNED → Record inspection;
   INSPECTED → Start work; IN_PROGRESS → Mark completed.
3. **Inspection form**: issue confirmed yes/no, length/width/depth in m (numeric keypad, **no AI values shown**), findings
   (required), expected completion date, 1–3 photos through `CameraCapture` (contractor capture session + GPS); distance > 100 m
   → "You seem to be 240 m away — submit anyway?".
4. **Completion form**: work summary, actual workers, hours, cost (optional), materials rows (material, quantity, unit), 1–3 proof
   photos → "Waiting for officer verification".
5. Forced password change on first contractor login (from P07) is reached before any contractor page.
6. Citizen detail (P11): when COMPLETED/CLOSED show "Fixed" / "Not fixed" + 1–5 stars + comment (`canGiveFeedback`);
   "Not fixed" explains that the complaint will be reopened; show the proof photo.
7. Officer detail "Field" tab: inspection (AI vs contractor measurement side by side), completion proof photos, verify buttons
   (Approve → CLOSED / Reject with reason → REOPENED) using the P14 endpoint.

## Tests (write first, Vitest + MSW)
inspection form never renders AI measurement values · completion needs at least one photo · distance warning dialog at > 100 m ·
citizen feedback buttons only when `canGiveFeedback` · "Not fixed" requires confirmation.

## Verify (agent)
1. in `frontend`: lint · typecheck · test · build.
2. E2E walkthrough: `start-all.ps1 -Stop` → `seed-e2e.ps1` → `start-all.ps1 -E2E` → smoke `--stage officer` → as `ui.officer`
   generate/approve/assign a plan to "UI Test Road Works" (like P19) → as `ui.contractor` (change the one-time password if asked -
   it is a seeded account, so it should not ask) open Today, a stop, the inspection form (camera fallback in the agent browser).
   Screenshots at a 390 px wide window: `docs/screenshots/P22_today.png`, `P22_stop.png`, `P22_inspection.png`; desktop:
   `P22_officer_field.png` → `start-all.ps1 -Restart`.

## Human step
None (the real phone run with a contractor account is P24).

## Ask the human (yes/no)
- Q1. Do the contractor screenshots look usable on a phone (big buttons, readable stop cards)?
- Q2. Is it clear on the inspection form that no AI numbers are shown (blind measurement)?

## Done when
checks green · screenshots committed · pushed.

## Next
`/run-prompt P23` — close/reopen, plan lifecycle checks, security pass (≈ 2.5 h, strongest model)
