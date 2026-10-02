# P27 — Bug bash (fixes only, no features)
**Day 7 (Wed 7 Oct) morning · agent ≈ 2–3 h · human ≈ 20 min · Needs: P24 · Model: strongest**
After 12:00 only blocker fixes.

## Goal
Every BUG-xx from P13/P24 (and anything the team noticed) is fixed with a regression test or consciously moved to the
"Known limitations" list; all checks and the full smoke are green again.

## Read first
`docs/PROGRESS.md` (BUG list) · `docs/TEST_RUN_P13.md`, `docs/TEST_RUN_P24.md` · `docs/09_BUILD_PLAN_7DAY.md` §7 (cut list:
never cut the "never cut" items)

## Do
1. Order the bugs: blocker → major → minor; estimate each (S/M/L). Ask ONE yes/no: "Fix in this order, and move <these minors>
   to Known limitations?".
2. For each bug: failing test first → fix → component checks → commit `fix(<scope>): BUG-xx …`.
3. Re-run `verify-all.ps1 -SkipE2E` and the E2E smoke `--stage all` at the end (seed first).
4. Update `docs/13_DEMO_AND_DEPLOY.md` §5 "Known limitations" with what stays open (honest, short).

## Human step (≈ 20 min)
Each team member opens the app in ANOTHER role than their own (laptop: http://localhost:5173 with the demo accounts; phones via
`start-all.ps1 -Tunnel` if needed) for 10 minutes and reports anything odd to the agent (one line each).

## Ask the human (yes/no)
- Q1. Are all blockers fixed in your re-test?
- Q2. Is the "Known limitations" list in `docs/13_DEMO_AND_DEPLOY.md` §5 acceptable for the demo?

## Done when
no open blocker · verify-all + `SMOKE ALL PASSED` · committed + pushed.

## Next
`/run-prompt P28` — demo build (≈ 1.5 h)
