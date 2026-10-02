---
name: run-prompt
description: Run one CivicBrain autopilot prompt (prompts/P<nn>_*.md) from start to finish on the single build laptop - plan without waiting, build, test, verify, record, commit, then ask the human short yes/no questions. Use when the user types /run-prompt P<nn>, "run P<nn>", or pastes a prompt file name.
argument-hint: "[P01-P30 or P03b]"
---
<!-- Generated from .agents/skills/run-prompt/SKILL.md by scripts/dev/sync-claude.ps1. Edit the source, then run the script. Claude Code: shell, browser and model notes are in CLAUDE.md. -->
# /run-prompt P<nn>

Autopilot mode: the human started this prompt and expects you to finish it alone. You stop only at the
points listed below. Everything in `AGENTS.md`, `.agents/rules/*` and the docs still applies.

## 0. Load
1. Open `prompts/P<nn>_*.md` (the id may have a letter, e.g. `P03b`). Read it completely.
2. Read `AGENTS.md`, the "Autopilot log" in `docs/PROGRESS.md` and every file in the prompt's **Read first** list.
3. Check **Needs**: every prompt listed there is `DONE` in the Autopilot log. If not, stop and say which one
   to run first (one sentence). Exception: the prompt says "can run any time".
4. If the log shows this prompt as `IN PROGRESS` (an earlier chat stopped), continue from its last finished task.

## 1. Plan (do not wait)
Write a short plan (max 15 lines: tasks, files, tests, commands) into the Autopilot log entry
(`P<nn> - IN PROGRESS`) and show it in the chat. **Do not wait for approval.** Ask first (one yes/no
question, then wait) only if the plan needs something on the ASK-FIRST list:
- a dependency or version that is not already pinned (`backend/pom.xml` BOM, `frontend/package.json`,
  `ai-service/requirements*.txt`);
- a new Flyway migration or any schema change; any change to a FROZEN rule (`.agents/rules/02-frozen-rules.md`);
- building something on the MVP OUT list (`docs/09_BUILD_PLAN_7DAY.md` sec. 1);
- deleting a file, or changing a test that already passed;
- a choice the documents leave open AND that is expensive to undo. For cheap choices take the option the
  documents prefer, write `DECISION: ...` into the log and continue.

## 2. Build
Task by task: tests first (the prompt's **Tests** list + `docs/09_BUILD_PLAN_7DAY.md` sec. 4), then code.
Stay inside the prompt's **Build** list. Small steps (one task <= ~300 changed lines).

## 3. Check after every task
Run the component checks yourself (AGENTS.md sec. 4 - one command per call, working directory set, no
`&&` chains, no servers except through `start-all.ps1`). A failure: read the error, fix, run again.
**Two failed fix attempts on the same error -> stop**: write what you tried, your best explanation and
a plan B into the log, and ask "Shall I try plan B: <one line>? (yes/no)".

## 4. Verify (the prompt's Verify list)
Do every item yourself and keep the evidence:
- command checks (tests, `scripts\dev\verify-all.ps1 -SkipE2E`, `tests\smoke\smoke_flow.py --stage ...`);
- running stack: `scripts\dev\start-all.ps1 [-Only ...] [-Restart]`, then health / `logs\<service>.log`;
- browser checks on `http://localhost:5173` / `http://localhost:8025` only: open the page, act like the user,
  take screenshots into `docs/screenshots/P<nn>_<name>.png` (commit them);
- E2E smoke: `start-all.ps1 -Stop` -> `seed-e2e.ps1` -> `start-all.ps1 -E2E` -> smoke -> `start-all.ps1 -Restart`
  (leave the dev stack running for the human at the end).
Never report PASS for something you did not run or see in this session.

## 5. Human step (only if the prompt has one)
Give numbered, copy-paste-ready instructions (max 6 steps, each with the expected result), then wait for the
human's answer. Never ask the human to do something you are allowed to do yourself.

## 6. Record and commit
Autopilot log entry: date/time, plan, files changed (summary), every check (command -> result line),
screenshots, decisions, open issues, anything cut. Then `/commit-step` (one commit per task or one for the
prompt). If a remote exists, `git push` (normal push only).

## 7. Finish with this report (exact shape)
```
P<nn> DONE - <one line what now works>        (or: P<nn> BLOCKED - <reason>)
| Check | Evidence | Result |
|---|---|---|
| ... | command / screenshot / log line | PASS / FAIL |
Please answer yes or no:
 Q1. <question from the prompt's "Ask the human" list, with the URL/screenshot to look at>
 Q2. ...
Next: /run-prompt P<next> - <title> (about <time>)
```

## 8. After the answers
- All "yes": mark `P<nn> - DONE (human yes <time>)` in the Autopilot log, commit `docs(progress): P<nn> done`, push.
- Any "no": ask one short follow-up ("What did you see?"), fix it inside this prompt, re-verify, and ask only
  the failed question again. Do not start the next prompt yourself; the human types it.

## 9. Time box
Each prompt states an estimate. At 1.5x the estimate, stop, report what is done and ask
"Cut <item> per docs/09_BUILD_PLAN_7DAY.md sec. 7 and continue? (yes/no)".
