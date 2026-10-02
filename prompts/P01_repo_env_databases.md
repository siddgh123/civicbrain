# P01 — Repository, environment check, databases
**Day 1 (Thu 1 Oct, evening) · agent ≈ 45 min · human ≈ 10 min · Needs: Step 0 of `prompts/README.md` · Model: any**

## Goal
The build laptop is proven ready: tools pass `check-env`, the old research files are inventoried, git is
initialised with nothing secret or huge in it, the login roles + `civicbrain` + `civicbrain_test` databases
exist and the SQL tests pass, the code is on GitHub, and we know whether the agent may start the stack.

## Read first
`AGENTS.md` · `.agents/rules/01-safety.md` · `.agents/skills/run-prompt/SKILL.md` · `docs/00_README_FIRST.md` ·
`docs/10_SETUP_WINDOWS.md` §3–§5 · `docs/03_DATABASE.md` §1 and §5 · `docs/PROGRESS.md`

## Build / do
1. **Rules loaded?** Without opening files, write into the log: safety rule "Human-only" list (1 line) and the
   names of the five skills. If you cannot, say so (Claude Code: the human checks `/context` and `/skills` and runs
   `scripts\dev\sync-claude.ps1`; Antigravity: `.agents/` vs `.agent/`). Claude Code: also run
   `pwsh -NoProfile -File scripts\dev\sync-claude.ps1 -Check` (must end with `PASS  sync-claude`).
2. **Environment:** `pwsh -NoProfile -File scripts\dev\check-env.ps1`. FAIL lines that need installing or PATH
   changes are human steps (give exact commands). This is the first real run of the kit scripts on Windows:
   if a script itself has a bug (parse error, wrong path), fix the script with a small edit, note
   `SCRIPT FIX: <file> <what>` in the log, and run it again. WARN lines for later prompts are fine.
3. **Inventory** (read-only PowerShell: `Get-ChildItem`, `Measure-Object`, `Test-Path`, `Get-Content -TotalCount`):
   write `docs/INVENTORY.md` with a table "path · present? · count/size · used by prompt":
   - `data/yolo/data.yaml` (class names), `data/yolo/images/{train,val,test}` and `labels/{train,val,test}` (counts)
   - `data/priority/priority_factor_dataset.csv`, `priority_scores.csv`, `official_ward_population.csv`, other `data/priority/*.csv`
   - `scripts/priority/priority_engine.py` (+ the other `scripts/priority/*.py`)
   - `data/duplicates/duplicate_engine_results.csv`, `duplicate_engine_config.json`, `scripts/duplicates/run_duplicate_engine_and_load.py`
   - `data/resources/models/*.json`, `scripts/resources/predict_resource_estimate.py`
   - `scripts/optimization/routing/*.py` (Step 13 OR-Tools code, used by P17)
   - `data/complaints/*` (kit text files), `gis/tdmc_wards_clean_v2.geojson`
   - files in the repo root that are not part of the kit or the project (e.g. `ers`, `exit`, `f`, `rstr`, `sd`, `te`)
   - every file > 20 MB that git would NOT ignore: `git check-ignore -v <file>` after `git init`
   For each missing research file write which prompt uses a fallback (P08, P09, P12 have fallbacks).
   **Format peek (read-only, no changes):** for every research file a later prompt uses, record in INVENTORY.md what it
   really contains - CSV: header row + row count (`Get-Content -TotalCount 3`, `Import-Csv | Measure-Object`); `data.yaml`:
   its `path`/`train`/`val`/`test`/`names` values; 3 random label files: first line (5 numbers, class 0-3?); Python scripts:
   imports, hard-coded file paths (`C:\Users\…`, `D:\…`, OneDrive), DB connection strings (never copy a password into the
   log - write "credential literal at file:line"); `data/resources/models/*.json`: top-level keys (XGBoost version if shown).
   Mark each line OK / NEEDS ADAPTING (e.g. absolute path, old column name) / UNKNOWN, and name the prompt that will handle it.
   Extra folders that no prompt uses (e.g. `data/yolo/raw`, `backup_before_final_merge`, `visual_validation`) are listed as
   "kept, not used in MVP" - never moved or deleted.
4. **Git:** `git config user.name` / `user.email` must be set (Step 0); if not, human step: `git config --global user.name "<name>"`
   and `git config --global user.email "<e-mail>"`. If `.git` is missing: `git init -b main`. If `.git` EXISTS (old folder):
   report the branch, the last 5 commits and whether images, `.env` files or big files were ever committed
   (`git rev-list --all --objects` + `git cat-file --batch-check`), then ask ONE yes/no: "Keep the old git history?" - yes →
   `git branch -m main` if needed (the CI's gitleaks scans the whole history, so a secret in it must be removed first: stop
   and say so); no → human step: rename the folder `.git` to `.git_old` in Explorer (you never touch `.git`), then
   `git init -b main`. Then `git config core.autocrlf true` (repo-local only).
   Stray root files from step 3 and big non-ignored files: add them to `.gitignore` under
   `# P01: not part of the project` (never delete them). DECISION line in the log.
5. **Secret scan before the first commit** (the CI runs gitleaks on the whole history): search the old
   folders for hard-coded secrets: `Select-String -Path scripts\*\*.py,scripts\*.py,data\**\*.json -Pattern 'password\s*=\s*[''"][^''"]+|PGPASSWORD|postgres(ql)?://[^ ]+:[^ ]+@'`
   (adapt the paths so every `.py`, `.sql`, `.json`, `.ipynb`, `.md` under `scripts/` and `data/` is covered).
   A hit = replace the literal with `os.environ["<NAME>"]` (Python) or a `-- set it in pgAdmin` comment (SQL), in a
   small edit; never print the secret in the chat or the log (say "file:line, a password literal").
6. **First commit:** `git add -A`, check `git status --short` (no `.env`, no images, no `storage/`), commit
   `chore: kit + existing research files`.
7. **Databases:** `pwsh -NoProfile -File scripts\dev\db-setup-main.ps1` (roles + empty `civicbrain`), then
   `pwsh -NoProfile -File scripts\dev\db-rebuild-test.ps1 -Force` → must print V2 6/6, V4 11/11, V5 11/11, roles 7/7.
8. **Can the agent start services?** `pwsh -NoProfile -File scripts\dev\start-all.ps1 -SelfTest`, wait 5 s, run the
   same command again (a separate call). PASS → write `AGENT_CAN_START=yes` in the log. FAIL → `AGENT_CAN_START=no`:
   from now on, whenever a prompt says "run start-all", give the human the exact command to run in their own
   PowerShell 7 window and wait for "done".
9. **Docker for tests:** `docker version` (read-only). If the server part is missing, human step: start Docker Desktop.

## Tests
No new code. The SQL tests of step 7 are the test.

## Verify (agent, with evidence)
- `check-env.ps1` summary: 0 FAIL (paste the summary lines).
- `db-rebuild-test.ps1 -Force`: the four PASS lines.
- `git log --oneline -1`, `git status --short` empty.
- `start-all.ps1 -SelfTest` result.

## Human step
1. github.com → New repository → name `civicbrain` → **Public** (Ultralytics AGPL-3.0) → no README/.gitignore → Create.
2. Paste the repository URL into the chat.
Agent then: `git remote add origin <url>` · `git push -u origin main`. If a browser sign-in window opens,
the human signs in; the agent retries the push once.
(If the human answers "skip GitHub": continue without a remote; mention it in every Done report.)

## Ask the human (yes/no)
- Q1. On GitHub, do you see the project files, and is there **no** `.env` file in the list?
- Q2. GitHub → Actions → the latest "CI" run: is the job "Database (V1-V5 + R__ grants + SQL tests)" green? (other jobs say "skipped"/green until P02–P05)
- Q3. Does `docs/INVENTORY.md` list your important research files as present (nothing you know of is missing)?

## Done when
0 FAIL in check-env · SQL tests 4/4 PASS · first commit pushed (or GitHub skipped by the human) · INVENTORY written ·
`AGENT_CAN_START` recorded · all answers yes.

## Next
`/run-prompt P02` — AI service skeleton + venv + worker loop (≈ 1.5 h)
