---
name: commit-step
description: Commit one finished and verified CivicBrain task with a conventional commit message (and push it when a remote exists). Use after /verify is green for the task, at the end of a /run-prompt, or when the user types /commit-step.
---

# /commit-step

1. Confirm `/verify` for the touched components passed in this session. If not, run it first; never commit red.
2. `git status --short` - make sure no `.env*` (except the two examples), secrets, `storage/`, `logs/`, `node_modules/`, `.venv/`, `target/`, `kaggle_upload/`, `kaggle_download/`, model weights or dataset images are staged (see `.gitignore`), and no file over 20 MB. If any are, stop and tell the human.
3. `git add -A`
4. `git commit -m "<type>(<scope>): <summary>" -m "Prompt P<nn>; implements FR-xx; docs/<file> sec. <n>. Verified: <command> -> <result>."` with type in feat|fix|test|refactor|docs|chore|build|ci and scope in backend|frontend|ai|db|infra|docs|smoke.
5. If `git remote` shows `origin`: `git push` (first time: `git push -u origin main`). Never `git push --force`/`-f`, `git reset --hard`, `git clean`, or amend commits that are already pushed. A push that asks for a login: tell the human to finish the browser sign-in (Git Credential Manager) and run the push again.
