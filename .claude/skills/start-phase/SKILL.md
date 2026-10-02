---
name: start-phase
description: Start a CivicBrain build phase (P0-P12) or a 7-day MVP day (D1-D7) in the interactive way (plan, wait for approval). Use when the user types /start-phase P<n> or /start-phase D<n>. During the 7-day MVP the normal way is /run-prompt P<nn> (autopilot, see the run-prompt skill).
argument-hint: "[D1-D7 or P0-P12]"
---
<!-- Generated from .agents/skills/start-phase/SKILL.md by scripts/dev/sync-claude.ps1. Edit the source, then run the script. Claude Code: shell, browser and model notes are in CLAUDE.md. -->
# /start-phase P<n> | D<n>

**MVP day (`D<n>`):** read `AGENTS.md` §0 and `docs/09_BUILD_PLAN_7DAY.md` (§1 scope, §2 decisions, §4 tests, the Day <n> section for this member's task). The prerequisite is the previous day's gate marked PASSED in PROGRESS.md (D1 has none). Plan only the tasks of Day <n> that belong to the member who is asking (ask which member if unclear), with the §4 tests; then continue with steps 2–8 below. Never plan anything from the OUT list.

**Full phase (`P<n>`):**

1. Read `AGENTS.md`, `docs/PROGRESS.md` and the phase section in `docs/09_BUILD_PLAN.md`. Confirm every **prerequisite phase** listed for P<n> at the top of `docs/09_BUILD_PLAN.md` is PASSED and approved in PROGRESS.md (the ML track P2/P11 runs in parallel with the app track); if not, stop and say which gate items are missing.
2. Read every document section the phase needs (use `docs/00_README_FIRST.md` reading-order table). List them in your answer.
3. Check for conflicts between docs, code and the phase goal. If any, list them and ask; do not guess.
4. Produce the **implementation plan** (in plan mode) with numbered tasks. For each task: requirement IDs (FR/NFR), files to create/change, tests to write first (names + what they assert), commands you will run, risks. Keep each task small enough to finish and verify in one sitting (≤ ~300 changed lines).
5. Add the phase gate checklist from `docs/09_BUILD_PLAN.md` at the end of the plan, mapping each gate item to the task that satisfies it.
6. Update `docs/PROGRESS.md`: current phase = P<n> IN PROGRESS, list of planned tasks.
7. STOP and wait for the human to approve or edit the plan. Do not write code before approval.
8. After approval, for each task: write tests → implement → run `/verify <component>` → fix until green → update PROGRESS.md task log → `/commit-step`. Stop and ask after two failed fix attempts on the same error.
