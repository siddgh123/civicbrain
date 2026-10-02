# CivicBrain — Software list (poora project banane ke liye)

Versions check kiye: 30 Sep – 1 Oct 2026. Ye list **ek hi build laptop** (Windows 11) ke liye hai.
Short me: aapko sirf **Table A** ka software install karna hai — #1–#11 ek command se (`install-all.ps1`), aur #12 Claude Code
(`START_HERE.md` Step 3.8).
Baaki sab (Python packages, npm packages, Maven, AI models, Docker images) agent khud download karega.

---
## 0. Laptop kaisa hona chahiye

| Cheez | Minimum | Recommended | Kyun |
|---|---|---|---|
| Windows | Windows 11 23H2 | Windows 11 24H2 / 25H2 | winget, WSL 2, Docker Desktop |
| RAM | 8 GB (sab apps band karke) | **16 GB** | Claude Code + Chrome + PostgreSQL + Java + Python + Node + Docker ek saath chalte hain |
| Free disk (C:) | 30 GB | 40 GB+ | dataset, Docker images, Python torch, node_modules, Maven |
| CPU | 4 cores | 6–8 cores | YOLO CPU par chalta hai, tests compile hote hain |
| BIOS | Virtualization ON | — | Docker/WSL 2 ke liye zaroori (Task Manager → Performance → CPU → "Virtualization: Enabled") |
| Internet | stable | — | pehle din kuch GB download hoga |
| Phone | 1 Android (Chrome) | + 1 iPhone (Safari) | camera + GPS test (P13, P24) |

---
## A. Ye install karna hai (abhi, Step 0 me) — `install-all.ps1` sab install karta hai

Command (Windows PowerShell me, `C:\dev\civicbrain` folder ke andar — `START_HERE.md` step 3):
```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev\install-all.ps1
```

| # | Software | Version | Kis kaam ka | winget ID (script yahi use karta hai) | Check command (naye PowerShell 7 window me) |
|---|---|---|---|---|---|
| 1 | **PowerShell 7** | 7.4 ya naya | saare project scripts isi me chalte hain | `Microsoft.PowerShell` | `pwsh --version` → `PowerShell 7.x` |
| 2 | **Git for Windows** | 2.5x (2.45 se upar) | code history, GitHub push | `Git.Git` | `git --version` |
| 3 | **Eclipse Temurin JDK** | **25** (LTS) — 27 mat lena | Spring Boot backend (Java) | `EclipseAdoptium.Temurin.25.JDK` (script JAVA_HOME bhi set karta hai) | `java -version` → `25.x` · `$env:JAVA_HOME` → `...jdk-25...` |
| 4 | **Node.js** | **24 LTS** (koi bhi 24.x) | React frontend (npm) | `OpenJS.NodeJS.LTS` | `node --version` → `v24.x` · `npm --version` |
| 5 | **Python** | **3.13.x** — 3.14/3.15 mat lena | AI worker (YOLO, OR-Tools) | `Python.Python.3.13` | `py -3.13 --version` → `Python 3.13.x` |
| 6 | **PostgreSQL** | **18.x** | main database (installer window khulega) | `PostgreSQL.PostgreSQL.18` (interactive) | `& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' --version` → `18.x` |
| 7 | **PostGIS** | **3.6.x** bundle | maps/GPS ke liye database extension | winget se nahi — PostgreSQL ke **Stack Builder** se (START_HERE step 3B) | agent P01 me `check-env` se check karega ("PostGIS available: 3.6") |
| 8 | **pgAdmin 4** | 9.x | database dekhne ka GUI (optional, debugging) | `PostgreSQL.pgAdmin` | Start menu → pgAdmin 4 |
| 9 | **Docker Desktop** (+ WSL 2) | latest 4.x | backend tests (Testcontainers) + Mailpit (fake e-mail server) | `Docker.DockerDesktop` | `docker --version` · `docker info` (Docker chalu hona chahiye) |
| 10 | **cloudflared** | 2026.x | phone ke liye HTTPS link (camera + GPS ko HTTPS chahiye) | `Cloudflare.cloudflared` | `cloudflared --version` |
| 11 | **Google Chrome** | latest | laptop pe app test karna | `Google.Chrome` | — |
| 12 | **Claude Code** (Claude desktop app ka Code hissa, ya terminal CLI) | latest | AI agent jo project banayega (aapke Claude Pro/Max subscription se) | winget se nahi — `START_HERE.md` Step 3.8 | desktop app me Code khulta hai · CLI: `claude --version` |
| 13 | Google Antigravity IDE (optional) | latest | sirf agar Claude Code ki jagah Antigravity use karna ho | `Google.AntigravityIDE` (`install-all.ps1 -IncludeOptional`) | Start menu → Antigravity |

**Install NAHI karna (zaroorat nahi):**
- **Maven** — project ka `mvnw.cmd` khud sahi Maven download karta hai.
- **Mailpit** — `start-all.ps1` usko Docker container me khud chala deta hai (http://localhost:8025).
- **OSRM** (road routing) — MVP me straight-line routing hai; OSRM Phase 2 me.

**Galti se ye versions mat install karna:** JDK 27 · Python 3.14/3.15 (PyTorch wheels nahi) · Node 20 (end-of-life) ·
Maven 4 RC · TypeScript 7 · Leaflet 2 alpha. (npm/Python versions pinned files me already fixed hain — aapko kuch nahi karna.)

---
## B. Ye agent khud install/download karega (aapko kuch nahi karna)

| Kya | Kab | Kahan aata hai | Kaise pinned hai |
|---|---|---|---|
| Python virtual environment + packages (FastAPI, ultralytics 8.4.168, torch 2.14 CPU, OR-Tools, sentence-transformers, onnxruntime, onnx …) | P02 | `ai-service\.venv\` | `ai-service\requirements-dev-win-py313.lock` (exact versions) |
| npm packages (React 19.3, Vite 8.3, TypeScript 6.0, Tailwind 4.3, react-leaflet 5, Vitest, Playwright …) | P05 | `frontend\node_modules\` | `frontend\package.json` (exact versions) |
| Maven + Java libraries (Spring Boot 4.1.1, Flyway, Hibernate, Testcontainers …) | P04 | `C:\Users\<aap>\.m2\` | `backend\pom.xml` |
| Docker images: `postgis/postgis:18-3.6` (tests), `axllent/mailpit:v1.31.3` (mail) | P04 / pehli baar `start-all` | Docker Desktop | fixed tags |
| AI model: YOLOv8s (aapke images pe Kaggle me train hoga) | P03 → P08 | `ai-service\models\yolov8s_civicbrain.onnx` | SHA-256 `ai-service\models\MANIFEST.json` me |
| AI model: all-MiniLM-L6-v2 (duplicate complaints) | P09 | `ai-service\models\all-MiniLM-L6-v2\` | commit + SHA-256 MANIFEST me |
| Text classifier (complaint text → category) | P08 | `ai-service\models\text_clf.joblib` | MANIFEST |

---
## C. Accounts (sab free) — kab chahiye

| Account | Kab | Kya karna hai |
|---|---|---|
| **Claude account (Pro ya Max)** | Step 0 | Claude Code me sign in. Pro pe usage limit jaldi khatam ho sakti hai — Max better; halki prompts `sonnet` pe |
| Google account (optional) | — | sirf agar Antigravity use karo |
| **GitHub** | P01 | account bana lo; P01 me ek **empty Public repository** `civicbrain` banana hoga (README mat add karna) |
| **Kaggle** | P03 (aaj raat) | account + **phone number verify** (Settings) — bina verify GPU nahi milta |
| **Twilio** | P16 (optional) | WhatsApp sandbox; har demo phone se `join <code>` bhejna (72 ghante valid) |
| **Gmail (project ka alag account)** | P28 (demo) | 2-Step Verification ON → App Password banana |

---
## D. Baad me / optional (Phase 2 — abhi install mat karo)

| Software | Kab kaam aayega | winget ID |
|---|---|---|
| uv | sirf jab Python dependency badalni ho (lock file dobara banana) | `py -3.13 -m pip install uv` |
| QGIS 3.44 LTR | wards ka manual review | `OSGeo.QGIS_LTR` (`install-all.ps1 -IncludeOptional`) |
| ffmpeg | Playwright fake camera (P26 me agent bina ffmpeg bhi kar leta hai) | `Gyan.FFmpeg` (`-IncludeOptional`) |
| 7-Zip, k6, Bruno | datasets, load test, API collections | `7zip.7zip`, `GrafanaLabs.k6`, `Bruno.Bruno` |
| OSRM Docker image | road-network routing | `infra\osrm\README.md` |

---
## E. Sab install hone ke baad — ek baar check (naya PowerShell 7 window)
```powershell
pwsh --version
git --version
java -version
$env:JAVA_HOME
node --version
npm --version
py -3.13 --version
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' --version
docker --version
docker info --format '{{.ServerVersion}}'
cloudflared --version
claude --version        # sirf agar terminal (CLI) wala Claude Code install kiya
```
Expected: PowerShell 7.x · git 2.5x · java 25 · JAVA_HOME me `jdk-25` · node v24 · Python 3.13 · psql 18 · Docker version +
ek server version number (Docker Desktop chalu ho) · cloudflared version.
Koi line error de to `START_HERE.md` → "Problems aur unka hal" dekho. Poora automatic check agent P01 me
`scripts\dev\check-env.ps1` se karega (har line PASS/WARN/FAIL).
