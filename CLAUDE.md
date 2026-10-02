# CivicBrain - Claude Code entry point

@AGENTS.md
@.agents/rules/01-safety.md
@.agents/rules/02-frozen-rules.md
@.agents/rules/03-testing.md

## Claude Code on this laptop (read after the files above)
The kit was first written for Google Antigravity. This section maps every Antigravity term to Claude Code.
Everything imported above applies unchanged; where they disagree on a tool detail, this section wins.

### Where things are
| The kit says | In Claude Code |
|---|---|
| `.agents/rules/01-03` (always on) | imported above |
| `.agents/rules/10-50` (by folder / topic) | `.claude/rules/*.md` - generated copies, scoped with `paths:` (security rule always on) |
| `.agents/skills/<name>` (`/run-prompt`, `/verify`, `/commit-step`, `/phase-gate`, `/start-phase`) | `.claude/skills/<name>/SKILL.md` - generated copies; the project `/verify` replaces Claude Code's bundled one |
| Antigravity allow / deny list, "Request Review", "Accept" | `.claude/settings.json` permissions (allow / ask / deny); a permission prompt is the human's "Accept" |
| "new agent chat" | a new Claude Code session (or `/clear`) |
| "browser tool", "browser walkthrough" | a Playwright walkthrough script (below) |
| model "strongest" / "Flash" / "any" | `opus` / `sonnet` / `sonnet` - the human switches with `/model`, you never do |
| first message of the project | `prompts/P00_orientation.md` (read-only orientation, before P01) |

`.agents/` is the source of the rules and skills. Never edit `CLAUDE.md`, `AGENTS.md`, `.claude/**` or `.agents/**`
yourself (an edit there asks the human): if one looks wrong or out of date, say so in one line. The human edits
`.agents/` and runs `scripts\dev\sync-claude.ps1`. You may run `pwsh -NoProfile -File scripts\dev\sync-claude.ps1 -Check` (read-only).
Project state lives in `docs/PROGRESS.md` (Autopilot log) and git - auto memory is off for this project.

### Permissions and auto mode
The human runs you in **Auto mode**: no prompt for normal work, a background safety check reviews commands.
`.claude/settings.json` adds three layers that hold in every mode:
- **deny** (hard block): deleting files (`Remove-Item`, `rm`, `del` …), disk/system/process commands, history-rewriting
  or force git, Docker data removal, `psql`/`pg_dump`/`createdb`/`dropdb`, `curl`/`Invoke-WebRequest`/`Invoke-RestMethod`,
  `cloudflared`, global installs (`winget`, `pip install`, `npm -g`), reading or writing `.env`/`.env.test` (and keys),
  and **every command that names a Human-only script** (`new-env.ps1`, `start-backend.ps1`, `start-all.ps1 -Tunnel`/`-Demo` …).
- **ask** (the human must click): edits of `AGENTS.md`, `CLAUDE.md`, `.agents/**`, `.claude/**`, `flyway/**`, `db/V*`/`R__*`,
  `db/tests/**`, any new `V6+` migration, `tests/smoke/smoke_flow.py`; `npm install <pkg>@<ver>`; `git remote add`; `git commit --amend`.
- **allow**: read-only git, `docker version/ps`, the allowed `scripts\dev\*.ps1`, `.\mvnw.cmd` verify/test/package,
  `npm ci`/`npm test`/`npm run <script>`, `npx vitest`/`playwright test`, venv `python.exe -m pytest/ruff/pip install -r <lock>`,
  smoke, each named training script. In Auto mode the classifier may still look at a few of these (allow-rule patterns that
  start with an interpreter like `pwsh -...` or that match a package-manager-run family are not pre-approved by the classifier,
  so a run with an unusual argument may wait a moment, which is normal). In Manual mode they all run without a prompt.
Rules for you:
- A denied or blocked command is blocked on purpose. Never retry it in another form (other shell, alias, `-c`, a script you
  write, `.NET` calls). Stop, write `BLOCKED: <command> - <why you needed it>` and tell the human.
- `.env.example` and `.env.test.example`: read them with the Read tool only. Never read `.env`, `.env.test` or
  `tests/e2e-ui-accounts.local.json` in any way - this replaces the exception in `01-safety.md`; the Playwright specs read
  the accounts file themselves at run time.
- To look at a Human-only script, use the Read/Grep tools (a shell command that names it is denied). Stage with `git add -A`.
- Local HTTP checks (`/health`, `/actuator/health`): `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Status`, or the
  `python.exe -c "import urllib.request ..."` one-liner below - never `curl`/`Invoke-RestMethod`.
- `git commit` and `git push` are reviewed by the auto-mode check (secrets, public repo). In P01 the first push to the new
  GitHub remote may ask the human once - that is expected.
- Auto mode makes you keep going without questions. The kit's questions still apply: the ASK-FIRST list and "two failed
  fixes -> stop" (run-prompt skill), the human steps, and the final yes/no questions.

### Shell
- Use the **PowerShell tool** (pwsh 7) for project commands: the kit's commands are PowerShell (`.\mvnw.cmd`,
  `\` paths, `pwsh -NoProfile -File scripts\dev\<name>.ps1 <args>`). Use the Bash tool (Git Bash) only for plain `git`
  commands, and only if the PowerShell tool is unavailable.
- Type commands exactly in the form the kit shows, so the allow rules in `.claude/settings.json` match:
  `pwsh -NoProfile -File scripts\dev\<script>.ps1 <args>` · `.\mvnw.cmd <args>` · `ai-service\.venv\Scripts\python.exe <args>` ·
  `.\.venv\Scripts\python.exe <args>` · `npm run <script>` · `npx playwright test <args>`.
- "Working directory set as shown" = one call `Set-Location <folder>` (for example `Set-Location backend`), then the
  command in its own call; the location stays for the next calls. Go back with `Set-Location C:\dev\civicbrain` before a
  repo-root command. Never leave `C:\dev\civicbrain`. "No `cd`" in the skills means no `cd X && cmd` chains - never chain
  with `&&`, `;` or `|` to change folders.
- Commands that can run longer than 10 minutes (the first `-m pip install -r <lock>` in P02, the first `.\mvnw.cmd -q verify`
  in P04, the first `npm install` in P05, `make-kaggle-package.ps1`): give them a 30-minute timeout or run them as a
  background task and read the output until it finishes. Never start a second copy while one still runs.
- Environment variables do not persist between calls. The scripts and the smoke test load `.env`/`.env.test` themselves.

### Browser checks (Claude Code has no built-in browser here)
Where a prompt says "browser tool", "browser walkthrough", "in the browser" or asks for screenshots:
1. **From P05 on**, write a Playwright script `frontend/walkthrough/P<nn>_<name>.spec.ts` and run it in `frontend`:
   `npx playwright test --config playwright.walkthrough.config.ts walkthrough/P<nn>` (the stack must be up via `start-all.ps1`).
   Create `frontend/playwright.walkthrough.config.ts` in P05 and commit it: `testDir: './walkthrough'`, `workers: 1`,
   `retries: 0`, `reporter: 'line'`, `use: { channel: 'chrome', headless: true, baseURL: 'http://localhost:5173' }`
   (the installed Google Chrome - no browser download), projects `desktop` (viewport 1280x800) and `phone`
   (viewport 390x844, `isMobile: true`, `hasTouch: true`), no `webServer`. Keep `walkthrough/` out of the main
   `playwright.config.ts` of P26 (its `testDir` is `./e2e`). Vitest must be told to skip the Playwright specs
   (`test.include: ['src/**/*.test.{ts,tsx}']`, `test.exclude: ['node_modules', 'e2e', 'walkthrough', ...]` - set in P05's
   `vitest.config.ts`), otherwise `npm test -- --run` tries to run them under jsdom and fails.
2. Each spec saves `await page.screenshot({ path: '../docs/screenshots/P<nn>_<name>.png', fullPage: true })` with the
   file names the prompt asks for. Logins on the E2E stack read `../tests/e2e-ui-accounts.local.json` inside the spec at
   run time - never print, log, screenshot or copy the passwords. Mailpit is `http://localhost:8025`.
3. Open every PNG with the Read tool and check it yourself (readable, nothing overlapping or cut off, the right data)
   before you ask the human about it. Fix and re-shoot first if it looks wrong.
4. The headless browser has no camera and no GPS unless the spec grants them - that is how the camera fallback is
   tested (P07, P11, P22). P11's "browser location inside TDMC": grant geolocation 18.7440, 73.6760 in that spec.
5. **P02** (no frontend yet): instead of `P02_health.png`, run
   `ai-service\.venv\Scripts\python.exe -c "import urllib.request,sys;sys.stdout.write(urllib.request.urlopen('http://127.0.0.1:8001/health',timeout=10).read().decode())"`,
   save the printed JSON as `docs/screenshots/P02_health.json` and ask Q1 about that file.
6. If the human started Claude Code with Chrome connected (`claude --chrome`), you may also look at `localhost` pages in
   their Chrome to debug. The screenshots for the human still come from Playwright.

### Sessions, models, limits
- One prompt per session: the human types `/run-prompt P<nn>` in a fresh session (or after `/clear`).
- A session can stop at a usage limit. Keep the Autopilot log current after every task, so the next session continues
  with `/run-prompt P<same>` from the `IN PROGRESS` entry and loses nothing.
- Ask the prompt's yes/no questions as plain numbered text (the report shape in the run-prompt skill).
- Claude Code may add its own co-author line to commits; that is fine. Otherwise commit exactly as `/commit-step` says.
