# 10 — Setup on Windows 11 (install in this order)

Versions checked on **2026-09-30**. Install the listed version (or a newer patch of the same line). Do **not** install the "latest" major where a trap is noted. After installing, run `scripts/dev/check-env.ps1`; every line must say PASS.

## 1. Before you start
- Windows 11 23H2 or newer, **16 GB RAM recommended** for the single build laptop (Antigravity + Chrome + PostgreSQL + Java + Python + Node + Docker together; 8 GB works if you close other apps and keep Docker at 4 GB), 30 GB free disk, virtualization enabled in BIOS (for WSL/Docker).
- Create `C:\dev\` and keep the repo at `C:\dev\civicbrain` — **never inside OneDrive** and never at a drive root.
- Install **PowerShell 7** (`winget install Microsoft.PowerShell`) — Antigravity commands are wrapped in `pwsh -NoProfile -Command`.

## 2. Software list
7-day MVP: `scripts\dev\install-all.ps1` installs items 1–3, 5, 6, 8, 10, 12, 15, 20 + PowerShell 7 with winget (WSL comes with Docker Desktop; PostGIS through Stack Builder; Mailpit runs as a Docker container automatically). OSRM (13), QGIS (16), Bruno (17), 7-Zip (18), k6 (19) and ffmpeg (21) can wait for Phase 2.

| # | Tool | Version | Get it from | Notes / traps |
|---|---|---|---|---|
| 1 | Google Antigravity IDE (and optionally the 2.0 app) | current | antigravity.google | Sign in with the team's Google account; settings in §5 |
| 2 | Git for Windows | 2.56.x | git-scm.com | Tick "Git Credential Manager"; `git config --global core.autocrlf true` |
| 3 | Eclipse Temurin JDK | **25 LTS** (25.0.4+) | adoptium.net (MSI, tick "Set JAVA_HOME") | Spring Boot 4.1 supports Java 17–26: **do not install JDK 27** |
| 4 | Maven | none needed | project `mvnw.cmd` | Do not install Maven 4 RC |
| 5 | Node.js | **24 LTS** (24.21.x) | nodejs.org (MSI) | Node 20 is end-of-life. npm comes with it |
| 6 | Python | **3.13.x** | python.org → Python Install Manager: `py install 3.13` | Not 3.15 (no PyTorch wheels yet); not 3.11 |
| 7 | uv | 0.12.x | `py -3.13 -m pip install uv` | Required only to change Python dependencies (re-compiling the Windows lock file); installs work with plain `venv` + pip |
| 8 | PostgreSQL | **18.6** | postgresql.org → EDB installer | Port 5432; remember the postgres password (only in `.env`) |
| 9 | PostGIS | **3.6.2** bundle | StackBuilder (installed with PostgreSQL) → Spatial Extensions | Needed before restoring the backup |
| 10 | pgAdmin 4 | **9.18** | pgadmin.org | Older versions have security fixes pending |
| 11 | WSL 2 | ≥ 2.1.5 | `wsl --install` then `wsl --update` | Required by Docker Desktop |
| 12 | Docker Desktop | **4.93.x** | docker.com (free for education/small teams) | Backend integration tests (Testcontainers) + Mailpit container in the MVP; OSRM in Phase 2. One laptop: `.wslconfig` `memory=4GB` |
| 13 | OSRM image | `ghcr.io/project-osrm/osrm-backend:v26.8.0-debian` (pinned in `infra/osrm/docker-compose.yml`) | pulled by `prepare-osrm.ps1` | Images are tagged `vX.Y.Z-debian`; on 2026-09-30 the newest image is 26.8.0 (the v26.9.0 release has no image yet). **Never `latest`** — it moves without warning |
| 14 | Mailpit | 1.31.x | GitHub releases (`mailpit-windows-amd64.zip` → `mailpit.exe` in `tools\mailpit\` or on PATH) or Docker `axllent/mailpit:v1.31.3` (automatic fallback) | SMTP 1025, web UI http://localhost:8025 |
| 15 | cloudflared | 2026.9.x | Cloudflare downloads / `winget install Cloudflare.cloudflared` | Quick tunnel = HTTPS URL for phones (camera + GPS need HTTPS) |
| 16 | QGIS | **3.44 LTR** | qgis.org | For the ward review (P1) |
| 17 | Bruno | current | usebruno.com | API collections committed to git (Postman free is 1 user) |
| 18 | 7-Zip | current | 7-zip.org | For datasets |
| 19 | k6 | current | `winget install k6` | P10 load smoke |
| 20 | Google Chrome | current | google.com/chrome | Playwright uses its own Chromium; Chrome for manual tests |
| 21 | ffmpeg | current | `winget install Gyan.FFmpeg` | Creates `tests/fixtures/images/camera.y4m` (fake camera for Playwright) |

Python packages: `ai-service/requirements.txt` (pinned; resolved for Windows cp313 on 2026-09-30; lock files `requirements-win-py313.lock`). Key pins: torch 2.14.0 (CPU wheel from PyPI on Windows), ultralytics 8.4.168, ortools 9.15.6755 (pins protobuf 6.33.x), sentence-transformers 6.1.0, xgboost 3.4.1, fastapi 0.142.2. **Install only one OpenCV** (`opencv-python`, pulled in by ultralytics).
Frontend packages: `frontend/package.json` (pinned; peer dependencies verified): React 19.3.0, Vite 8.3.1, **TypeScript 6.0.3 (not 7: typescript-eslint supports < 6.1)**, Tailwind 4.3.3 (+ `@tailwindcss/vite`, no `tailwind.config.js`), react-router 7.18.4, react-leaflet 5.0.0 + **leaflet 1.9.4 (not 2.0 alpha)**, TanStack Query 5, zod 4, Vitest 5, MSW 3, Playwright 1.63. First install: `npm install` (not `npm ci`) on Windows, then commit `package-lock.json`.
Backend: versions managed by Spring Boot 4.1.1 (Spring Security 7.1.x, Hibernate 7.4.x incl. Spatial — use the normal PostgreSQL dialect, no `PostgisPG*Dialect`; Flyway 12.4.x **plus `flyway-database-postgresql`**; PostgreSQL JDBC 42.7.x; Testcontainers 2.0.x — older 1.x fails with Docker Engine 29).

## 3. First setup on the build laptop (human, about 1 hour + downloads)
The detailed, beginner-proof version (with where the images go and the exact Antigravity lists) is **`START_HERE.md`** in the
project root - follow that one; this section is the short form. After it, the agent does the rest (`/run-prompt P01`).
```powershell
# 1. in Windows PowerShell (5.1 is fine for this one), from the extracted kit folder:
powershell -ExecutionPolicy Bypass -File scripts\dev\install-all.ps1
#    PostgreSQL installer: port 5432, choose + note the postgres password; Stack Builder -> PostGIS 3.6 bundle
#    restart Windows; open Docker Desktop once (accept, "Start Docker Desktop when you sign in" = on)
# 2. memory limit for Docker/WSL on one laptop: create %UserProfile%\.wslconfig with
#      [wsl2]
#      memory=4GB
#    then in PowerShell: wsl --shutdown   (Docker restarts by itself)
# 3. project folder: copy ONLY the data\ and scripts\ folders of your old CivicBrain folder to C:\dev\civicbrain, then copy
#    this kit's contents into the same folder (replace when asked); then, in PowerShell 7 (pwsh):
cd C:\dev\civicbrain
Get-ChildItem -Recurse . | Unblock-File
pwsh -NoProfile -File scripts\dev\new-env.ps1      # writes .env + .env.test with random secrets; asks the postgres password
# 4. Antigravity: open C:\dev\civicbrain, settings as in sec. 5, then in the agent chat:  /run-prompt P01
```
If PowerShell says a script "is not digitally signed", run the `Unblock-File` line again (never change the machine-wide execution policy).
The agent creates the Python venv, installs npm packages, builds the databases and runs `check-env.ps1` itself (P01, P03, P04).

## 4. Scripts: who runs what
| Script | What it does | Who |
|---|---|---|
| `install-all.ps1 [-IncludeOptional]` | winget installs of sec. 2 (skips what exists) | **human** (once) |
| `new-env.ps1 [-Force]` | `.env` + `.env.test` with random secrets (asks the postgres password) | **human** (once) |
| `new-secret.ps1` | one random secret (only if you edit `.env` by hand) | human |
| `check-env.ps1` | versions, paths, `.env` sanity, DB/PostGIS, Docker, ports → PASS/WARN/FAIL | agent or human |
| `db-setup-main.ps1 [-Seed]` | login roles + empty `civicbrain` (Flyway builds it when the backend starts) / demo seed afterwards | agent (P01, P04) |
| `db-rebuild-test.ps1 -Force` | roles + rebuild `civicbrain_test` from `flyway/` + seed + SQL tests | agent |
| `start-all.ps1 [-Only s1,s2] [-Restart] [-Stop] [-Status] [-E2E]` | mailpit, AI API, worker, Vite, backend in minimised windows, logs in `logs\` | agent or human |
| `start-all.ps1 -Tunnel` / `-Demo -Tunnel` | + public HTTPS URL for phones / demo stack (jar with SPA) | **human only** |
| `seed-e2e.ps1 [-NoPackage] [-MinAccounts n]` | reset `civicbrain_e2e` + fixed test accounts | agent |
| `verify-all.ps1 [-SkipE2E] [-SkipDb] [-RebuildTestDb]` | DB → backend → AI → frontend (→ Playwright) | agent |
| `make-kaggle-package.ps1 [-Force]` | `kaggle_upload\civicbrain-yolo.zip` (existing dataset + training scripts) | agent (P03) |
| `backup-db.ps1 [-CopyTo E:\...]` | pg_dump + check + 14-day retention | agent or human |
| `bootstrap-admin.ps1 -Email <e-mail>` | first ADMIN of a database (password typed hidden; stop the backend first) | **human** (P24 demo admin) |
| single `start-*.ps1`, `start-e2e.ps1`, `start-tunnel.ps1`, `prepare-osrm.ps1`, `start-osrm.ps1` | building blocks of `start-all.ps1` / Phase 2 OSRM | human only |

PostgreSQL runs as a Windows service. Dev and E2E stacks use the same ports — `start-all.ps1` runs one at a time (`-Restart` switches).

## 5. Agent configuration (once, on the build laptop)
**Claude Code (default for this team):** nothing to type - `CLAUDE.md` (imports `AGENTS.md` + rules 01-03), `.claude/rules/`,
`.claude/skills/` and `.claude/settings.json` (allow / ask / deny, PowerShell tool, timeouts) ship with the kit. Open
`C:\dev\civicbrain`, trust the folder, choose Auto mode and model opus; check with `/context`, `/skills`, `/permissions` and
`pwsh -NoProfile -File scripts\dev\sync-claude.ps1 -Check` (`START_HERE.md` Step 6). The rest of this section is for Antigravity.

### 5a. Antigravity configuration
Settings names as of Sep 2026 on Windows; if your build shows slightly different labels, pick the matching option.
1. **Folder:** open `C:\dev\civicbrain` as the workspace. `AGENTS.md`, `.agents/rules/*.md` and `.agents/skills/*/SKILL.md` load automatically (older builds read `.agent/` - then copy the folder).
2. **Terminal command execution policy: "Request Review"** (never "Always Proceed"/"Turbo" - in December 2025 an agent in Turbo mode wiped a user's whole D: drive). The allow list below lets the safe commands run without a click; everything else asks you (Accept = one click).
3. **Allow list** (add each line as one entry; entries match the start of the command):
   `git status` · `git diff` · `git log` · `git add` · `git commit` · `git push` · `git init` · `git remote` · `git branch` · `git rev-parse` · `git ls-files` · `git tag` · `git check-ignore` · `git config core.` · `docker version` · `py -3.13 -m venv` ·
   `.\mvnw.cmd` · `npm install` · `npm run` · `npm test` · `npx vitest` · `npx playwright test` ·
   `.\.venv\Scripts\python.exe` · `ai-service\.venv\Scripts\python.exe` ·
   `pwsh -NoProfile -File scripts\dev\check-env.ps1` · `pwsh -NoProfile -File scripts\dev\db-setup-main.ps1` · `pwsh -NoProfile -File scripts\dev\db-rebuild-test.ps1` · `pwsh -NoProfile -File scripts\dev\seed-e2e.ps1` · `pwsh -NoProfile -File scripts\dev\verify-all.ps1` · `pwsh -NoProfile -File scripts\dev\backup-db.ps1` · `pwsh -NoProfile -File scripts\dev\make-kaggle-package.ps1` · `pwsh -NoProfile -File scripts\dev\start-all.ps1`
4. **Deny list** (always blocked, even if allowed above):
   `rm` · `rmdir` · `rd` · `del` · `erase` · `Remove-Item` · `ri` · `format` · `diskpart` · `Format-Volume` · `git push --force` · `git push -f` · `git reset --hard` · `git clean` · `docker system prune` · `docker volume rm` · `docker compose down -v` · `psql` · `pg_dump` · `pg_restore` · `createdb` · `dropdb` · `taskkill` · `Stop-Process` · `Stop-Service` · `Set-ExecutionPolicy` · `reg` · `netsh` · `runas` · `cloudflared` · `-Tunnel` · `-Demo` · `new-env.ps1` · `new-secret.ps1` · `install-all.ps1` · `bootstrap-admin.ps1` · `start-backend.ps1` · `start-frontend.ps1` · `start-worker.ps1` · `start-ai-api.ps1` · `start-mailpit.ps1` · `start-e2e.ps1` · `start-tunnel.ps1` · `start-osrm.ps1` · `prepare-osrm.ps1` · `.env` · `.env.test` · `curl` · `wget` · `Invoke-WebRequest` · `Invoke-RestMethod`
5. **Artifact / plan review policy: "Always Proceed"** (or "Agent Decides") - the agent writes its plan and continues (autopilot); the safety comes from the terminal policy and the lists.
6. **File access outside the workspace: "Deny".** Sandbox mode: off (it blocks the local ports the stack needs).
7. **Browser:** URL allowlist only `localhost` and `127.0.0.1`; JavaScript execution policy "Request Review" (a November 2025 prompt-injection attack stole `.env` keys through the browser agent).
8. **Secrets:** `.env` keeps `WHATSAPP_PROVIDER=log` and Mailpit while the agent builds. Real Twilio/Gmail values are typed in by you only in P16 and P28 (the agent never opens `.env`).
9. **Models:** heavy prompts (P06, P08, P12, P14, P17, P18, P20, P23) with the strongest model you have (Gemini 3.1 Pro or Claude Opus); screens and small prompts with a Flash model. Free quota refreshes weekly, Pro every 5 hours - plan the heavy prompts when the quota is fresh.
10. **Knowledge:** Antigravity's "Knowledge Items" are not in git - the real memory is `docs/PROGRESS.md` (Autopilot log); start a **new agent chat for every prompt** (keeps the context small); the skill re-reads the log.
11. **Windows terminal hangs:** one short command per call; servers only through `start-all.ps1` (it returns). If a command hangs > 10 min, press Stop and tell the agent "the last command hung".

## 6. Accounts to create (free) - and when you need them
| Account | Needed in | Notes |
|---|---|---|
| GitHub | P01 (optional but recommended: backup + CI) | empty repository, public (Ultralytics AGPL-3.0 expects open code); the agent pushes, you sign in once in the browser window Git opens |
| Kaggle | P03 | **verify your phone number** (Settings) - without it there is no GPU; ~30 GPU-h/week |
| Twilio | P16 | free trial; WhatsApp sandbox: every demo phone sends `join <code>` (lasts 72 h - redo it the day before the demo) and sends any message to the sandbox within 24 h before each test/demo (Twilio 24-hour session rule) |
| Gmail (project account) | P28 | 2-Step Verification on + an App Password for SMTP (until then Mailpit catches every mail) |
| Hugging Face | not needed | `download_models.py` downloads the public MiniLM model without an account |
Phase 2 only: Meta for Developers (WhatsApp Cloud API), Google Colab, Label Studio/CVAT.
