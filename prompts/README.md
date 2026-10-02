# CivicBrain — Autopilot prompt pack (one laptop, 7-day MVP)

You give the agent (**Claude Code**; Google Antigravity also works) **one prompt at a time**. It plans, builds, tests and verifies on its own, records everything
in `docs/PROGRESS.md`, commits, and at the end asks you a few **yes/no** questions. You only do the steps a machine cannot do
(installing software, typing passwords, Kaggle/Twilio/Gmail websites, phones) - each prompt says exactly when and how.

**What you provide:** your old CivicBrain folder (with `data/yolo` images + labels, `data/`, `scripts/`) and a few accounts.
**What the agent does:** everything else - databases, backend, frontend, AI service, model installation, tests, fixes.

---
## Step 0 — once, before P01 (≈ 1.5–2 hours + downloads)
Follow **`START_HERE.md`** in the project root, top to bottom - it is the single, detailed checklist (Windows settings,
the folder `C:\dev\civicbrain`, where the images go, software install with `install-all.ps1`, PostgreSQL + PostGIS screens,
Docker + `.wslconfig`, `new-env.ps1`, git identity, GitHub/Kaggle accounts, Antigravity settings with the allow/deny lists,
final checklist). The software list with versions is **`SOFTWARE_LIST.md`**.
Then, in the first Claude Code session, the read-only orientation: `Read prompts/P00_orientation.md and do exactly what it says.`
(the agent summarises the project, runs read-only checks and lists contradictions - nothing is changed).

## How to run a prompt
1. Open a **new session** (Claude Code: new session or `/clear`; Antigravity: new agent chat) - keeps the context small;
   the agent re-reads PROGRESS.
2. Pick the model the prompt's header suggests: "strongest" = `opus`, "any" / "Flash" = `sonnet` (`/model`; Antigravity:
   strongest model / Flash).
3. Type: `/run-prompt P01` (if the slash command is not recognised: "Use the run-prompt skill for P01").
4. Let it work. Claude Code runs in **Auto mode**; `.claude/settings.json` blocks the dangerous commands (deny) and asks you
   only for edits of the rule files, migrations and the smoke test, new npm packages and `git remote add` (ask). Read each
   prompt first - never approve anything with delete, `--force`, `.env`, or paths outside `C:\dev\civicbrain`. (Antigravity:
   click **Accept** for commands outside its allow list, same rule.)
5. When it asks for a human step, do it and answer "done". At the end answer the yes/no questions.
6. Next prompt: the agent's last line tells you which one.

If the agent stops with "BLOCKED" or "Shall I try plan B …?": answer yes/no (a `BLOCKED: <command>` line means a deny rule
or the auto-mode check stopped it on purpose - see START_HERE problems #16/#17). If a command hangs > 10 min: press Esc (Antigravity:
Stop) and type "the last command hung, continue". If the usage limit / quota runs out: wait for the reset or switch the model
(`/model sonnet`) and type `/run-prompt P<same>` in a new session - it continues from the log.

---
## Day plan (one laptop)
Agent times are estimates; you are free while it works except for the marked human steps.

| Day | Prompts (in order) | Agent | Human | Day gate (table "Day gates" below) |
|---|---|---|---|---|
| **D1 Thu 1 Oct** (evening) | Step 0 · P00 (orientation) · P01 · P02 · P03 (· P03b only if labels are missing) | ≈ 3 h | Step 0, GitHub repo, **Kaggle upload + start training** (runs overnight) | – |
| **D2 Fri 2 Oct** | P04 · P05 · P06 · P07 | ≈ 9 h | start.spring.io download (P04), register test (P07) | D1 gate after P05 |
| **D3 Sat 3 Oct** | P08 · P09 · P10 · P11 | ≈ 10 h | download the Kaggle model zip (P08) | D2 gate after P09 |
| **D4 Sun 4 Oct** | P12 · P13 · P14 · P15 | ≈ 9.5 h | **phone test inside TDMC** (P13) | D3 gate after P13 |
| **D5 Mon 5 Oct** | P16 · P17 · P18 · P19 | ≈ 9.5 h | Twilio sandbox (P16) | D4 gate after P17, D5 gate after P19 |
| **D6 Tue 6 Oct** | P20 · P21 · P22 · P23 (· P25 optional) | ≈ 9.5 h | – | feature freeze after P23 |
| **D7 Wed 7 Oct** | P24 · (P26 optional) · P27 · P28 · P29 · P30 | ≈ 7 h | **full flow with 2 phones** (P24), Gmail + USB (P28), rehearsal (P30) | D6 after P24, D7 after P30 |

Dependencies (a prompt needs these DONE): P02←P01 · P03←P02 · P03b←P02 · P04←P01 · P05←P01 · P06←P04,P05 · P07←P05,P06 ·
P08←P02,P03 · P09←P02 · P10←P02,P06 · P11←P07,P10 · P12←P08,P09,P10 · P13←P11,P12 · P14←P10,P12 · P15←P07,P14 · P16←P10 ·
P17←P12 · P18←P14,P17 · P19←P15,P18 · P20←P18 · P21←P12,P20 · P22←P19,P20 · P23←P20,P22 · P24←P13,P16,P23 · P25←P24 ·
P26←P23 · P27←P24 · P28←P27 · P29←P27 · P30←P28,P29.
If Kaggle is not finished when P08 starts, the agent builds the rest of P08 and asks for the zip at the end; P09–P11 can run
meanwhile (the worker only requires the model files from P12 on).

## Day gates (`/phase-gate D<n>` checks these during autopilot; they replace the gate lines of 09_BUILD_PLAN_7DAY §5)
| Gate | When | Items (each proven by a command, file or your yes) |
|---|---|---|
| D1 | after P05 | check-env 0 FAIL · SQL tests 4/4 · AI pytest green · dataset check passed + Kaggle run committed · backend verify green, Flyway built `civicbrain`, seed 500 complaints · frontend lint/typecheck/test/build green · CI green (if GitHub) |
| D2 | after P09 | `SMOKE AUTH PASSED` · register → OTP → login in the browser (P07 yes) · YOLO model installed + metrics in `docs/reports` (or Kaggle still running, noted) · classifier metrics · priority golden 0 mismatches · duplicate repro |
| D3 | after P13 | `SMOKE INTAKE` + `SMOKE ANALYSIS` passed · SUBMITTED e-mail · phone capture → CB number → "Under review" (P13 yes) |
| D4 | after P17 | `SMOKE OFFICER PASSED` · officer UI screenshots approved · WhatsApp test message (or `log` decided) · optimizer tests green |
| D5 | after P19 | `SMOKE PLAN PASSED` · plan PDF checked · plan builder screenshots approved |
| D6 | after P24 | `SMOKE ALL PASSED` · `docs/SECURITY_CHECK.md` all PASS · full flow with phones to CLOSED + rating (P24 yes) |
| D7 | after P30 | two clean rehearsals · demo from the jar with real mail · backup on USB · tag `mvp-v1` |

**Honest time note:** this is tight for one laptop. The agent hours include its own testing, but one E2E smoke cycle
(stop → seed → start → smoke → back to dev) takes 10–15 min and `mvnw verify` with Testcontainers several minutes, so the agent
runs the full smoke once at the end of a prompt, not after every small fix. 16 GB RAM is strongly recommended. P13 and P24 need
people with phones **inside the TDMC boundary**; D7 has no buffer, so keep P24 on the evening of D6 if you can. If a day runs late, say "yes" to the agent's cut proposal, in this order
(09_BUILD_PLAN_7DAY §7): P26 → PDF route sketch → WhatsApp (keep `log`) → plan re-order → contractor workers data → merge UI →
Needs-review/Rejected tabs. Never cut: login, ownership checks, DB status rules, AI analysis, messages with the contractor name,
the proof-photo loop.

## What the agent checks by itself
- Unit/integration tests of each component, `verify-all.ps1`.
- **`tests/smoke/smoke_flow.py`** - an API "robot" that plays citizen, officer and contractor on a fresh test database
  (stages auth → intake → analysis → officer → plan → contractor → close) and reads the mails in Mailpit.
- Browser walkthroughs on the test stack with its own UI test accounts (`tests/e2e-ui-accounts.local.json`) and screenshots in
  `docs/screenshots/` - you answer yes/no looking at them.
Your yes/no answers cover what a machine cannot judge: does it look right, did the phone/WhatsApp/Gmail really get it.

## Files
`P00_orientation.md` - the first, read-only session (project brief + checks). `P01…P30` (+ `P03b`) - one file per prompt:
Goal · Read first · Build · Tests · Verify · Human step · yes/no questions · Done when · Next.
The agent's rules for running them: `.agents/skills/run-prompt/SKILL.md` (Claude Code reads the copy in `.claude/skills/`).
What it may run alone: `.agents/rules/01-safety.md` + `CLAUDE.md` "Permissions and auto mode" + `.claude/settings.json`.
