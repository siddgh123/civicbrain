# CivicBrain — START HERE (pehli baar setup, step by step)

Ye file **ek hi baar** follow karni hai, upar se neeche, kuch skip kiye bina. Total ≈ 1.5–2 ghante (downloads alag).
Iske baad aap **Claude Code** me pehle ek orientation (`prompts\P00_orientation.md`) aur phir sirf `/run-prompt P01`, `P02`, … doge
aur agent baaki sab banayega.

> Is guide me teen cheezon ka naam aata hai:
> - **Purana project folder** = aapka abhi wala CivicBrain folder. Isse sirf `data\` (images + research data) aur `scripts\`
>   (research code) lene hain - baaki project naya banega.
> - **Kit** = `CivicBrain_Kit_ClaudeCode.zip` (maine diya). Zip ke andar ek folder hai `civicbrain_kit`.
>   Purana `CivicBrain_Antigravity_Kit.zip` pehle hi copy kar diya ho to bhi koi baat nahi: Step 2.3 naye zip se dobara karo
>   ("Replace" choose karna) - aapka `data`/`scripts` research saamaan aur `.env` safe rehte hain.
> - **Naya project folder** = `C:\dev\civicbrain` — **yahi asli project hai.** Sab kaam isi me hoga.

Software ki poori list (versions, kya kis kaam ka): `SOFTWARE_LIST.md`.

---
## Step 1 — Windows ki 4 settings (5 min)
1. **File extensions dikhao:** File Explorer → View → Show → **File name extensions** ✔.
   (Warna Notepad `.wslconfig.txt` ya `.env.txt` bana deta hai aur pata nahi chalta.)
2. **Sleep band (charger lagne par):** Settings → System → Power → Screen and sleep → "When plugged in, put my device to sleep
   after" = **Never**. (Agent ghanto kaam karta hai; laptop sona nahi chahiye.)
3. **Disk:** C: drive pe kam se kam **30–40 GB free** hona chahiye (This PC me dekho).
4. **Virtualization:** Task Manager → Performance → CPU → "Virtualization: **Enabled**". Disabled ho to BIOS me ON karna padega
   (Intel VT-x / AMD SVM) — warna Docker nahi chalega.

---
## Step 2 — Naya project folder banao aur files copy karo (15 min)
**Rule:** project **kabhi** OneDrive, Desktop, Documents ya kisi drive ke root (`C:\`) me nahi. Sirf `C:\dev\civicbrain`.

**2.1 Folder banao** — File Explorer me `C:\` kholo → New folder `dev` → uske andar New folder `civicbrain`.
Result: `C:\dev\civicbrain` (abhi khaali).

**2.2 Purane folder se sirf `data` aur `scripts` copy karo** — ye **naya project** hai; purana folder sirf research ka
saamaan deta hai (images + validated Step 9–13 ka data/code). Purane folder ke andar jao → sirf **`data`** aur **`scripts`**
folder select karo → Copy → `C:\dev\civicbrain` me Paste. Root ki baaki files (`README.md`, `ers`, `exit`, `f`, `rstr`, `sd`,
`te`, koi purana `.git`) **copy mat karo**.

Ye kyun chahiye (kaunsa folder kis prompt me kaam aata hai):

| Purane folder ka hissa | Kis kaam ka | Na ho to kya |
|---|---|---|
| `data\yolo\images`, `labels`, `data.yaml` | YOLO training (P03) | **zaroori** — iske bina model nahi banega |
| `data\priority\*.csv` + `scripts\priority\priority_engine.py` | Step 11 priority bilkul same (P09 golden test "0 mismatches") | agent puchhega; documented formula + assumptions se banega (kam accurate) |
| `data\duplicates\*` + `scripts\duplicates\*` | Step 12 duplicate check same results (P09) | hand-calculated test se banega |
| `data\resources\models\*.json` + `scripts\resources\predict_resource_estimate.py` | workers/time/cost estimate (P12) | default assumptions se banega |
| `scripts\optimization\*` | Step 13 OR-Tools settings (P17) | docs ke settings se banega |
| `data\gis\…`, `data\complaints\…` baaki | reference (report/Phase 2) | koi farak nahi |

**GeoJSON alag se copy karne ki zaroorat NAHI:** 23 wards ka saaf kiya hua map kit me already hai
(`gis\tdmc_wards_clean_v2.geojson`) aur database migration (V3) me bhi andar hai — database banate hi wards aa jaate hain.
Disk kam ho to `data\yolo\raw`, `data\yolo\backup_*`, `data\yolo_v2` chhod sakte ho (training me use nahi hote).

✅ Check: ye file honi chahiye → `C:\dev\civicbrain\data\yolo\data.yaml`
❌ Galti: `C:\dev\civicbrain\CivicBrain\data\...` ya `C:\dev\civicbrain\data\data\...` (folder ke andar folder). Aisa ho gaya
to andar wala content ek level upar le aao.

**2.3 Kit copy karo (usi `C:\dev\civicbrain` me, `data`/`scripts` ke saath)** — `CivicBrain_Kit_ClaudeCode.zip` pe right-click → **Properties → "Unblock" ✔ →
OK** → right-click → **Extract All** (Downloads me hi). Extract hue folder me `civicbrain_kit` folder kholo → uske andar sab
select (**Ctrl+A** — `.claude`, `.agents`, `.github`, `.env.example`, `.gitignore` bhi) → Copy → `C:\dev\civicbrain` me Paste →
Windows puche to **"Replace the files in the destination"**.

✅ Check: ye sab `C:\dev\civicbrain` me dikhne chahiye:
`CLAUDE.md`, `AGENTS.md`, `START_HERE.md`, `SOFTWARE_LIST.md`, `prompts\`, `docs\`, `scripts\dev\`, `.claude\`, `.agents\`, `db\`, `flyway\`, `gis\`,
`ai-service\`, `frontend\package.json`, `tests\smoke\` — aur purane folder se aaye `data\yolo\images\`, `scripts\priority\` bhi.

---
## Step 2B — IMAGES kahan rakhne hain (sabse important)
YOLO training sirf is **exact** layout ko padhta hai. Aapke purane project me ye pehle se aisa hi hai (3,398 images) —
bas check kar lo:

```
C:\dev\civicbrain\data\yolo\
├── data.yaml                 ← 4 classes ka naam (neeche sample)
├── images\
│   ├── train\   (≈ 2,708 photos: .jpg / .png)
│   ├── val\     (≈ 351)
│   └── test\    (≈ 339)
└── labels\
    ├── train\   (har photo ke liye SAME naam ki .txt file)
    ├── val\
    └── test\
```
- Photo `images\train\pothole_0012.jpg` ka label **zaroor** `labels\train\pothole_0012.txt` hona chahiye (same naam, `.txt`).
- Label file ki har line: `class x_center y_center width height` (0–1 ke beech numbers), class id: **0 = Pothole,
  1 = Garbage Accumulation, 2 = Waterlogging, 3 = Road Damage** (ye order FROZEN hai, kabhi mat badlo).
- `data.yaml` aisa dikhna chahiye (path ki line jo bhi ho, chalega):
  ```yaml
  path: .
  train: images/train
  val: images/val
  test: images/test
  nc: 4
  names: ['Pothole', 'Garbage Accumulation', 'Waterlogging', 'Road Damage']
  ```

**Counting check** (Step 5 ke baad PowerShell 7 me, ya abhi Explorer me folder pe right-click → Properties):
```powershell
foreach ($s in 'train','val','test') {
  $i = (Get-ChildItem "C:\dev\civicbrain\data\yolo\images\$s" -File).Count
  $l = (Get-ChildItem "C:\dev\civicbrain\data\yolo\labels\$s" -File -Filter *.txt).Count
  "$s : images=$i labels=$l"
}
```
Images aur labels ki ginti lagbhag barabar honi chahiye.

**Agar aapke images alag layout me hain:**
| Aapke paas aisa hai | Kya karna hai |
|---|---|
| Roboflow-style: `train\images`, `train\labels`, `valid\images`, `valid\labels`, `test\...` | Move karo: `train\images`→`images\train`, `train\labels`→`labels\train`, `valid\images`→`images\val`, `valid\labels`→`labels\val`, `test\images`→`images\test`, `test\labels`→`labels\test` (sab `data\yolo\` ke andar) |
| Images hain par **labels nahi** | Images ko `images\train`, `images\val`, `images\test` me rakho (≈ 80/10/10 %); P03 khud bolega "labels missing" → tab `/run-prompt P03b` (agent YOLO-World se auto-label karega) |
| Class-wise folders (`pothole\`, `garbage\` …) bina split ke | P01 se pehle mujhe/agent ko folder ka screenshot dikhao — warna training galat hogi |
| Purane extra folders `data\yolo\raw\`, `backup_*`, `yolo_v2` | wahi rehne do; git aur Kaggle zip unko ignore karte hain |

**Images ke alawa baaki "image/file" kahan jaate hain (aapko kuch nahi karna, sirf jaankari):**
| Folder | Kya hai | Kaun daalta hai |
|---|---|---|
| `data\yolo\images\…`, `labels\…` | training dataset | **aap** (purane project se) |
| `kaggle_upload\civicbrain-yolo.zip` | Kaggle pe upload karne wala zip | agent (P03) — **aap** isko Kaggle pe upload karte ho |
| `kaggle_download\civicbrain_yolo_outputs.zip` | Kaggle se trained model | **aap** download karke yahan rakhte ho (P08; folder khud bana lena) |
| `ai-service\models\` | installed AI models | agent (P08, P09) |
| `tests\fixtures\images\` | test ke liye 4–6 photos (dataset se copy) | agent (P03) |
| `storage\` | app me citizens/contractors ki photos | app khud (phone se capture). Kabhi haath se mat daalo |
| `docs\screenshots\`, `docs\reports\` | agent ke screenshots, metrics | agent |
| `logs\` | services ke logs | `start-all.ps1` |
| `gis\tdmc_wards_clean_v2.geojson` | 23 wards ka map | kit me already hai |
Demo ke liye photos ka koi folder nahi chahiye — demo me photo **app ke andar camera** se hi li jaati hai (gallery upload band hai).

---
## Step 3 — Software install (≈ 45 min, kuch window khulenge)
**3.1** Start → **"Windows PowerShell"** kholo (normal, Run as administrator NAHI). Phir:
```powershell
cd C:\dev\civicbrain
powershell -ExecutionPolicy Bypass -File scripts\dev\install-all.ps1
```
Script har software install karta hai jo missing hai (list: `SOFTWARE_LIST.md` table A). Beech me Windows "Yes/Allow"
puche (UAC) to **Yes** dabao.

**3.2 PostgreSQL ka installer window khulega** — ye screens aise bharo:
- Installation Directory: default · Components: sab ✔ (PostgreSQL Server, pgAdmin 4, Stack Builder, Command Line Tools)
- Data Directory: default
- **Password:** ek password socho (sirf letters + numbers, jaise `Civic2026Db`) — **kaagaz pe likh lo**, Step 5 me lagega
- **Port: 5432** (agar installer 5433 dikhaye → purana PostgreSQL pehle se chal raha hai, neeche "Problems" #5 dekho)
- Locale: Default · Next → Install
- End me **"Launch Stack Builder at exit" ✔** → Finish

**3.3 Stack Builder (PostGIS):** "PostgreSQL 18 (x64) on port 5432" choose → Next → **Spatial Extensions** khol ke
**PostGIS 3.6 Bundle for PostgreSQL 18** ✔ → Next → download → install → License "I Agree" → agar
**"Create spatial database"** ka option aaye to ✖ untick → baaki sawaal (GDAL_DATA, raster drivers) pe **Yes** → Finish.

**3.4 Script khatam hone ke baad:** ek table dikhegi (INSTALLED / already installed / FAILED). FAILED ho to wahi line wala
software `SOFTWARE_LIST.md` ke winget ID se dobara: `winget install --id <ID> --exact`.

**3.5 Restart Windows** (zaroori — PATH, Docker, WSL).

**3.6 Docker Desktop pehli baar:** Start → Docker Desktop → Accept → sign-in skip kar sakte ho → agar "WSL update" maange to
PowerShell me `wsl --update` → Docker restart. Settings (⚙) → General → **"Start Docker Desktop when you sign in" ✔** ·
**"Use the WSL 2 based engine" ✔**.

**3.7 Docker ki memory limit (ek laptop pe zaroori):** Notepad kholo → ye 2 lines likho:
```
[wsl2]
memory=4GB
```
File → Save As → folder `C:\Users\<aapka-naam>` → File name: **`.wslconfig`** → "Save as type": **All Files (*.*)** → Save.
(Explorer me check: naam `.wslconfig` ho, `.wslconfig.txt` NAHI.) Phir PowerShell me: `wsl --shutdown` (Docker khud wapas aata hai).

**3.8 Claude Code (aapke Claude subscription se chalta hai)** — dono me se ek tareeka:
- **A. Claude desktop app** (aapke paas already ho to wahi): https://claude.com/download se install/update → apne Claude
  account (Pro/Max) se sign in. Isme **Code** wala hissa Claude Code hai.
- **B. Terminal (CLI):** Step 3.5 ke restart ke baad **PowerShell 7** me: `irm https://claude.ai/install.ps1 | iex` →
  naya window → `claude --version` (version number aana chahiye) → pehli baar `claude` chalane pe browser me sign in.
Claude Code ko Windows pe **Git for Windows** chahiye — wo `install-all.ps1` already daal deta hai.

---
## Step 4 — PowerShell 7 me project setup (10 min)
Ab se hamesha **PowerShell 7** use karna: Start → **"PowerShell 7"** (ya Windows Terminal → dropdown → PowerShell).
Naye window me:
```powershell
cd C:\dev\civicbrain
Get-ChildItem -Recurse . | Unblock-File
git config --global user.name "Aapka Naam"
git config --global user.email "aapka-email@example.com"
git config --global core.autocrlf true
pwsh -NoProfile -File scripts\dev\new-env.ps1
```
- `new-env.ps1` sirf **PostgreSQL ka password** poochta hai (Step 3.2 wala; type karte waqt dikhega nahi — normal hai).
- Ye 2 secret files banata hai: `C:\dev\civicbrain\.env` aur `.env.test` (random passwords/keys ke saath).
  **In dono ko kabhi share mat karna, GitHub pe kabhi nahi jaati** (`.gitignore` rokta hai), aur agent inko kabhi kholta nahi.
  Sirf 2 baar aap khud Notepad me khologe: P16 (Twilio keys) aur P28 (Gmail).
- Software check (optional, P01 me agent bhi karega): `SOFTWARE_LIST.md` section E ke commands.

---
## Step 5 — Accounts (aaj raat ke liye 2 zaroori)
1. **GitHub** account (github.com) — P01 me agent puchhega tab ek **empty Public** repo `civicbrain` banana (README ✖).
2. **Kaggle** account (kaggle.com) → Settings → **Phone verification** (bina iske GPU nahi) — P03 me lagega, aaj raat.
3. Baad me: Twilio (P16, optional), Gmail project account + App Password (P28). Details `SOFTWARE_LIST.md` table C.

---
## Step 6 — Claude Code setup (10 min) — safety ke liye zaroori
Kit me Claude Code ke liye sab ready hai — aapko rules kahin type nahi karne:
- `CLAUDE.md` (project root) — har session me **apne aap** load hota hai. Ye `AGENTS.md` + safety/frozen/testing rules ko andar laata hai.
- `.claude\rules\` — backend/frontend/AI/database/security rules (us folder me kaam karte hi load hote hain).
- `.claude\skills\` — `/run-prompt`, `/verify`, `/commit-step`, `/phase-gate`, `/start-phase`.
- `.claude\settings.json` — Antigravity wali allow/deny list ka Claude Code version (≈ 380 deny rules: delete, `.env`,
  `psql`, force push, human-only scripts …). **deny** rules Auto mode me bhi lagu hoti hain; **ask** rules bhi prompt
  karti hain. **allow** rules zyadatar auto-approve karti hain; par Auto mode ka safety classifier `pwsh -…` jaise
  interpreter-shape allow rules ko sometimes dekh leta hai, isliye ekaad command par ek chhota pause normal hai.

1. **Project kholo:**
   - Desktop app: Claude app → **Code** → **New** → Environment **Local** (Cloud / SSH / WSL NAHI) → folder choose karo →
     **`C:\dev\civicbrain`**. Agar "Isolate in worktree" / "Use git worktree" ka option dikhe → **OFF** (warna agent ko
     ek alag folder milega jisme `data\yolo`, `.env`, `.venv` nahi hoti aur sab fail hoga).
   - Ya terminal: PowerShell 7 → `cd C:\dev\civicbrain` → `claude`.
2. **"Do you trust the files in this folder?"** → **Yes** (iske bina `settings.json` ki allow rules lagu nahi hoti; deny rules hamesha lagu).
3. **Mode = Auto:** desktop app me mode selector se **Auto** choose karo; terminal me `Shift+Tab` dabate raho jab tak
   neeche "auto mode" na dikhe (naye versions me terminal Auto se hi start hota hai). **"Bypass permissions" kabhi nahi**
   (project settings me humne usko band bhi kar diya hai).
4. **Model:** `/model` → **opus** (prompt header me "Model: strongest") · **sonnet** ("Model: any" / "Flash"). Pro plan pe
   limit jaldi khatam ho sakti hai - halki prompts sonnet pe chalao.
5. **Check (2 min)** — session me type karo:
   - `/context` → "Memory files" me `CLAUDE.md` (aur `AGENTS.md`, rules) dikhne chahiye.
   - `/skills` → `run-prompt`, `verify`, `commit-step`, `phase-gate`, `start-phase` dikhne chahiye.
   - `/permissions` → Deny me `PowerShell(Remove-Item *)`, `Read(.env)` jaisi lines dikhni chahiye.
   - Alag PowerShell 7 window me: `pwsh -NoProfile -File scripts\dev\sync-claude.ps1 -Check` → last line
     `PASS  sync-claude: .claude/ is current`.
6. **Permission prompt aaye to:** Auto mode me prompt kam aate hain. Jo aate hain wo jaan-boojh kar hain ("ask" rules):
   `AGENTS.md`/`CLAUDE.md`/`.agents`/`.claude` edit, migration (`flyway\`, `db\V…`), smoke test edit, naya npm package,
   P01 me `git remote add`. Agent ne chat me wajah batayi ho aur prompt me wahi kaam ho → **Yes**; samajh na aaye → **No**
   aur mujhse pucho. Agar Claude Code puche ki `C:\dev\civicbrain` ke **bahar** ki file padhe → **"No, and ask again
   next time"** choose karo (sirf "No" na dabao - "No, and block reads outside the working directories from now on"
   aapke user settings me permanent setting daal deta hai jo baaki projects me bhi lagu hoga). Sirf
   `C:\Users\<aap>\.claude\...` Claude ka apna folder ho to Yes. Delete / `--force` / `.env` wali cheez pe kabhi
   "Yes, and don't ask again" mat dabana.
7. `.agents\` me kabhi kuch badla (normally nahi badlega) → PowerShell 7 me `pwsh -NoProfile -File scripts\dev\sync-claude.ps1`
   (copies `.claude\` me update ho jaati hain).

---
## Step 7 — Final checklist (sab ✔ hone ke baad hi P01)
- [ ] `C:\dev\civicbrain\data\yolo\data.yaml` hai, aur `images\train|val|test` + `labels\train|val|test` me files hain
- [ ] `C:\dev\civicbrain\CLAUDE.md`, `AGENTS.md`, `.claude\` aur `prompts\` hain (kit copy hua)
- [ ] Project OneDrive/Desktop me NAHI hai
- [ ] `install-all.ps1` ki table me koi FAILED nahi; PostGIS Stack Builder se install hua
- [ ] Windows restart ho chuka; Docker Desktop chal raha hai (taskbar me whale icon, "Engine running")
- [ ] `C:\Users\<aap>\.wslconfig` bana (4GB)
- [ ] PowerShell 7 me `new-env.ps1` ne `.env` + `.env.test` bana diye
- [ ] git name/email set
- [ ] GitHub account hai; Kaggle account + phone verified
- [ ] Claude Code: folder trusted, mode **Auto**, `/context` me CLAUDE.md, `/skills` me 5 skills, `sync-claude.ps1 -Check` PASS
- [ ] Laptop charger pe, sleep = Never

---
## Step 8 — Building shuru (aaj raat: P00 → P01 → P02 → P03)
1. **Pehli session = orientation (P00, ≈ 10 min, kuch nahi badalta):** Claude Code → nayi session (Auto, model opus) → type:
   ```
   Read prompts/P00_orientation.md and do exactly what it says.
   ```
   Agent project samjhega, kuch read-only checks karega aur ek report dega. Report me ye sab hona chahiye:
   - pehli line `P00 ORIENTATION - READY`
   - Talegaon Dabhade, **23 wards**; 4 classes: Pothole, Garbage Accumulation, Waterlogging, Road Damage
   - routing haversine · WhatsApp Twilio sandbox ya `log` · test mail Mailpit · officer TOTP sirf stretch (P25)
   - Human-only list (install-all, new-env, bootstrap-admin, `-Tunnel`/`-Demo`, `.env` edit, web consoles, phone)
   - `sync-claude.ps1 -Check` PASS · train images/labels ≈ 2,700
   - point 9 (contradictions) — kuch aaye to **wo list mujhe paste karo**, agent ko fix mat karne do.
   `NOT READY` aaye to reason padho (zyaadatar koi software missing / folder galat) → theek karo → P00 dobara.
2. **P01:** nayi session (`/clear` ya new session) → type:
   ```
   /run-prompt P01
   ```
3. P01 me agent GitHub repo ka URL maangega → GitHub pe empty **Public** repo `civicbrain` banao → URL chat me paste karo.
   `git remote add` pe permission prompt aayega → **Yes**. Pehli push pe browser me GitHub login aa sakta hai → sign in.
4. End me agent "P01 DONE" + yes/no sawaal deta hai → jawab do. Last line me next prompt likha hota hai.
5. Phir **nayi session** → `/run-prompt P02` → phir nayi session → `/run-prompt P03`.
6. P03 ke end me aapka kaam (≈ 30 min): Kaggle pe `C:\dev\civicbrain\kaggle_upload\civicbrain-yolo.zip` upload → notebook
   `ai-service\training\kaggle_train_mvp.ipynb` import → GPU + Internet ON → cells 1–4 run → **Save Version → Save & Run All
   (Commit)**. Training raat bhar Kaggle pe chalegi (laptop band bhi ho to chalegi).
7. Kal subah se: `prompts\README.md` ka **Day plan** follow karo (D2: P04 → P05 → P06 → P07 …).

---
## Roz ka routine (D2 – D7)
- Laptop on → Docker Desktop chal raha hai? (auto start hona chahiye) → Claude Code kholo (`C:\dev\civicbrain`, Auto mode).
- Har prompt = **nayi session** + `/run-prompt P<nn>`. Agent pichla status `docs\PROGRESS.md` se padh leta hai.
- App dekhna: http://localhost:5173 · Fake e-mails (OTP etc.): http://localhost:8025 · Backend health:
  http://localhost:8080/actuator/health · Services ka haal: `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Status`
- Progress: `docs\PROGRESS.md` (Autopilot log table) · Screenshots: `docs\screenshots\` · Logs: `logs\`.
- Phone test (P13, P24): aap khud `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Tunnel` chalate ho → jo
  `PHONE URL: https://….trycloudflare.com` aaye wo phone pe kholo. Kaam khatam →
  `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Stop -Only tunnel`.

---
## Kya NAHI karna
- Project ko OneDrive/Desktop me rakhna · `.env`/`.env.test` kisi ko bhejna, chat me paste karna ya GitHub pe daalna
- Claude Code me **Bypass permissions** mode · delete/`--force`/`.env` wali prompt pe "Yes, and don't ask again"
- `.claude\settings.json` se deny rules hatana ya allow me delete/`psql` jaisi cheez daalna
- `data\yolo\images` / `labels` me files rename/delete karna (training aur test fixtures unpe depend karte hain)
- Ek saath do jagah se `start-all.ps1` chalana · agent ke kaam ke beech `.env` edit karna (sirf jab prompt bole: P16, P28)
- Ek session me kai prompts chalana — har prompt nayi session
- Purana README/blueprint/purani chats agent ko dena (kit ke docs me sab hai; purane versions confuse karte hain)

---
## Problems aur unka hal
| # | Problem | Hal |
|---|---|---|
| 1 | "script is not digitally signed" | Step 4 wali `Unblock-File` wali line PowerShell 7 me `C:\dev\civicbrain` se dobara chalao |
| 2 | `winget` not found | Microsoft Store → **App Installer** update/install → PowerShell dobara kholo |
| 3 | `java -version` 25 nahi / `$env:JAVA_HOME` khaali ya purane JDK pe | PowerShell 7: `[Environment]::SetEnvironmentVariable('JAVA_HOME', (Get-ChildItem 'C:\Program Files\Eclipse Adoptium' -Directory -Filter 'jdk-25*')[0].FullName, 'User')` → naya window |
| 4 | `py -3.13` not found | `winget install --id Python.Python.3.13 --exact` → naya window |
| 5 | PostgreSQL installer port **5433** dikha raha hai | purana PostgreSQL (16/17) chal raha hai: `services.msc` → `postgresql-x64-16` (ya 17) → Stop + Startup type **Disabled** → PostgreSQL 18 installer dobara (port 5432). Purane DB ki zaroorat nahi — naya DB agent banata hai |
| 6 | PostgreSQL password bhool gaye | abhi (data se pehle) sabse aasaan: Settings → Apps → PostgreSQL 18 uninstall → `C:\Program Files\PostgreSQL\18\data` folder bhi hata do → Step 3 se PostgreSQL dobara → `new-env.ps1 -Force` |
| 7 | Docker: "WSL update required" / engine start nahi hota | `wsl --update` → Docker restart; BIOS virtualization ON (Step 1.4) |
| 8 | `.wslconfig` kaam nahi kar raha | naam `.wslconfig.txt` to nahi? (Step 1.1 se extension dekho) → rename → `wsl --shutdown` |
| 9 | `/skills` me project skills nahi / `/context` me CLAUDE.md nahi | Claude Code galat folder me khula hai → `C:\dev\civicbrain` hi kholo; `.claude\skills\` folder copy hua? → `pwsh -NoProfile -File scripts\dev\sync-claude.ps1` → nayi session |
| 10 | Kaggle me GPU option disabled | Kaggle phone verification nahi hua (Settings) |
| 11 | Agent ki command 10 min se atki hai | **Esc** dabao → likho: `the last command hung, continue` |
| 12 | Claude usage limit khatam | limit reset hone tak ruko, ya `/model sonnet` → **nayi session** me wahi `/run-prompt P<nn>` (agent log se continue karega) |
| 13 | Laptop restart ho gaya | kuch nahi — agent agle prompt me `start-all.ps1` se sab chala dega. Docker Desktop auto start hona chahiye |
| 14 | P01 me "AGENT_CAN_START=no" aaya | jab bhi agent bole "run start-all", wahi command aap apne PowerShell 7 window me chalao aur "done" likho |
| 15 | Auto mode option nahi dikhta | Claude Code update karo (desktop app update / terminal me `claude update`) aur model opus/sonnet rakho. Tab bhi na mile → normal (Manual) mode chalega, bas prompts zyada aayenge (allow list wali commands bina puchhe chalti hain) |
| 16 | Agent likhe `BLOCKED: <command>` | wo command jaan-boojh kar band hai. Human-only script ho to aap khud PowerShell 7 me chalao aur "done" likho; samajh na aaye to wo line mujhe bhejo |
| 17 | Auto mode ne kuch block kiya (notification) | agent khud ruk kar batayega. Sahi kaam ho to `/permissions` → **Recently denied** → us line pe retry; galat ho to "No" |

---
## Appendix — Agar Antigravity use karna ho (Claude Code ki jagah)
Kit dono ke saath chalta hai (`.agents\` Antigravity padhta hai, `.claude\` + `CLAUDE.md` Claude Code). Build ka status
`docs\PROGRESS.md` + git me rehta hai, isliye beech me tool badal sakte ho. Antigravity ke settings:

1. Antigravity kholo → Google account se **sign in**.
2. **File → Open Folder → `C:\dev\civicbrain`**.
3. Settings (⚙) → **Agent** section me ye set karo (labels thode alag ho sakte hain, matching option choose karo):

| Setting | Value |
|---|---|
| Terminal command execution policy | **Request Review** (kabhi "Always Proceed"/"Turbo" NAHI) |
| Artifact / plan review policy | **Always Proceed** (ya "Agent Decides") |
| File access outside workspace | **Deny** |
| Sandbox mode | Off |
| Browser URL allowlist | `localhost`, `127.0.0.1` (bas yahi 2) |
| Browser JavaScript execution | **Request Review** |

4. **Allow list** (har line ek alag entry — "+ Add"):
```
git status
git diff
git log
git add
git commit
git push
git init
git remote
git branch
git rev-parse
git ls-files
git tag
git check-ignore
git config core.
docker version
py -3.13 -m venv
.\mvnw.cmd
npm install
npm run
npm test
npx vitest
npx playwright test
.\.venv\Scripts\python.exe
ai-service\.venv\Scripts\python.exe
pwsh -NoProfile -File scripts\dev\check-env.ps1
pwsh -NoProfile -File scripts\dev\db-setup-main.ps1
pwsh -NoProfile -File scripts\dev\db-rebuild-test.ps1
pwsh -NoProfile -File scripts\dev\seed-e2e.ps1
pwsh -NoProfile -File scripts\dev\verify-all.ps1
pwsh -NoProfile -File scripts\dev\backup-db.ps1
pwsh -NoProfile -File scripts\dev\make-kaggle-package.ps1
pwsh -NoProfile -File scripts\dev\start-all.ps1
```
5. **Deny list** (har line ek entry):
```
rm
rmdir
rd
del
erase
Remove-Item
ri
format
diskpart
Format-Volume
git push --force
git push -f
git reset --hard
git clean
docker system prune
docker volume rm
docker compose down -v
psql
pg_dump
pg_restore
createdb
dropdb
taskkill
Stop-Process
Stop-Service
Set-ExecutionPolicy
reg
netsh
runas
cloudflared
-Tunnel
-Demo
new-env.ps1
new-secret.ps1
install-all.ps1
bootstrap-admin.ps1
start-backend.ps1
start-frontend.ps1
start-worker.ps1
start-ai-api.ps1
start-mailpit.ps1
start-e2e.ps1
start-tunnel.ps1
start-osrm.ps1
prepare-osrm.ps1
.env
.env.test
curl
wget
Invoke-WebRequest
Invoke-RestMethod
```
6. **Check ki rules load hue:** nayi agent chat → likho: `Without opening any file: list your skills and quote the
   "Human-only" safety rule.` → jawab me `run-prompt`, `verify`, `commit-step`, `phase-gate`, `start-phase` aane chahiye.
   Na aaye to: `C:\dev\civicbrain\.agents` folder copy karke uska naam `.agent` rakh do (dono rahenge) aur dobara try.
