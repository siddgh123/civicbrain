# P24 — Full-flow test on the dev stack with 2 phones (+ the demo accounts)
**Day 6 evening / Day 7 morning · agent ≈ 30 min (+ fixes) · humans ≈ 1 h (2–3 people) · Needs: P13, P16, P23 · Model: any**

## Goal
The complete story works with real people and phones, exactly as in the demo: citizen → AI → officer → plan → assign →
contractor inspects, starts, completes with proof → officer verifies → CLOSED → citizen rates; every citizen-facing status
sends e-mail (+ WhatsApp). The demo accounts are created on the way. Every problem is logged for P27.

## Read first
`docs/13_DEMO_AND_DEPLOY.md` §2, §4 · `docs/09_BUILD_PLAN_7DAY.md` §5 Gate D6 · `docs/TEST_RUN_P13.md`

## Before the human step (agent)
1. `backup-db.ps1` (a restore point before the test), then `start-all.ps1 -Stop` (bootstrap-admin needs port 8080 free;
   the human starts the stack again with the tunnel in step 2).
2. Write `docs/TEST_RUN_P24.md`: table "#, who, device, step, expected, result, note" for the steps below (copy the expected
   values from the specs: status labels of 05 §1, the mails of each status, timings).

## Human step (≈ 1 h; people: A = officer at the laptop, B = citizen phone 1, C = citizen phone 2 / contractor phone)
1. A, PowerShell 7: `pwsh -NoProfile -File scripts\dev\bootstrap-admin.ps1 -Email <real admin e-mail>` (type a strong password,
   keep it in the team password manager).
2. A: `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Tunnel` → note the PHONE URL; send it to B and C.
3. A (laptop browser, http://localhost:5173): log in as admin → Admin → create the officer (`officer.road@<your domain>`,
   scope ROAD, all wards) → log out → log in as the officer (password from the admin screen / first-login change) →
   Contractors → create "Demo Road Works" (ROAD) with an e-mail and phone that NO citizen account uses (e.g. a team
   member's second address) → copy the one-time password to C (C will use the contractor login on the same phone).
4. B and C (inside TDMC, WhatsApp sandbox joined in P16 AND each sent "hi" to the sandbox number within the last 24 h): register on the PHONE URL (OTP from Mailpit on the laptop - A reads it),
   tick WhatsApp; B reports a pothole; C reports the same spot ~30 m away with a similar description.
5. A: the complaint appears in New within a minute; C's report shows as linked (MERGED). Generate a plan for today/tomorrow →
   reorder → approve → assign "Demo Road Works" → B and C get "contractor assigned" (mail + WhatsApp).
6. C (logs out as citizen, logs in with the contractor account + one-time password → must change it): Today → stop → inspection
   (tape values + photo) → start → completion with a proof photo.
7. A: open the complaint → Field tab → Approve → CLOSED. B: "Fixed" + 4 stars.
8. Stop the tunnel: `start-all.ps1 -Stop -Only tunnel`. Tell the agent each step's result and any problem (screenshot from the
   phone if possible).

## After the human step (agent)
- Read `logs\backend.log`, `logs\worker.log`, the Mailpit messages and the notification rows' status through the officer UI;
  fill `docs/TEST_RUN_P24.md`; every problem → a numbered bug in `docs/PROGRESS.md` ("BUG-xx: what, where, severity
  blocker/major/minor").
- Fix blockers immediately (test first), others in P27. `start-all.ps1 -Only backend -Restart` (links back to localhost).
- `/phase-gate D6`.

## Ask the human (yes/no)
- Q1. Did the whole flow reach CLOSED with the rating?
- Q2. Did B and C get the "contractor assigned" message by e-mail (Mailpit) and WhatsApp?
- Q3. Approve gate D6 (blockers fixed, the rest listed for P27)?

## Done when
TEST_RUN_P24 filled · bug list written · blockers fixed · D6 approved · demo accounts exist (admin, officer, contractor firm).

## Next
Optional `/run-prompt P25` (officer TOTP) only if it is before 16:00 and there are no open blockers; optional `P26`
(Playwright). Otherwise `/run-prompt P27` — bug bash.
