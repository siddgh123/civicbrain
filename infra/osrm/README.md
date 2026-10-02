# OSRM for CivicBrain (road travel times)

The worker's `OPTIMIZE_PLAN` job asks OSRM for a travel-time matrix (depot D001 + the complaints of one cluster) and gives it to OR-Tools. OSRM runs in Docker on `127.0.0.1:5000`. The image tag is pinned in `docker-compose.yml` (`ghcr.io/project-osrm/osrm-backend:v26.8.0-debian`). Needed from phase **P8**.

## 1. Get the map data (once)
You need an OpenStreetMap extract that covers the whole TDMC boundary plus some margin: **73.60–73.77 °E, 18.65–18.80 °N**.

**Option A — BBBike custom extract (recommended, a few MB):**
1. Open https://extract.bbbike.org/ → format **Protocolbuffer (PBF)**.
2. Enter the box: left/west `73.60`, bottom/south `18.65`, right/east `73.77`, top/north `18.80`; name `talegaon`; your e-mail.
3. Download the link you receive → save as `infra/osrm/data/talegaon.osm.pbf`.

**Option B — Geofabrik (no e-mail, bigger):** download `western-zone-latest.osm.pbf` from https://download.geofabrik.de/asia/india.html (~210 MB in Sep 2026; extraction needs ~8 GB free RAM) and pass it to the prepare script; it is copied as `talegaon.osm.pbf`. If your laptop has 8 GB RAM, prefer Option A.

Licence: OpenStreetMap data is © OpenStreetMap contributors, ODbL 1.0. Show "© OpenStreetMap contributors" on every map and on the plan PDF.

## 2. Prepare (extract → partition → customize), once per new extract
```powershell
pwsh -NoProfile -File scripts\dev\prepare-osrm.ps1 -Pbf C:\Users\<you>\Downloads\talegaon.osm.pbf
```
The script copies the file to `infra/osrm/data/talegaon.osm.pbf` and runs, inside the pinned image:
```
osrm-extract   -p /opt/car.lua /data/talegaon.osm.pbf
osrm-partition /data/talegaon.osrm
osrm-customize /data/talegaon.osrm
```
Success = `infra/osrm/data/talegaon.osrm.mldgr` exists. The script checks each step's exit code and stops at the first failing step; an `[error]` line in the output tells you which one.

## 3. Run and check
```powershell
pwsh -NoProfile -File scripts\dev\start-osrm.ps1
```
It starts the container and calls:
`http://127.0.0.1:5000/route/v1/driving/73.699489,18.729411;73.6760,18.7440?overview=false`
(OSRM uses **longitude,latitude**; depot D001 → a point in ward 1). Expected: `"code":"Ok"` and a distance of a few km. The script prints PASS/FAIL.

Table check used by the optimizer:
`http://127.0.0.1:5000/table/v1/driving/73.699489,18.729411;73.6760,18.7440;73.6763,18.7442?annotations=duration,distance`

## 4. Stop / update
- Stop: `docker compose -f infra\osrm\docker-compose.yml stop` (never `down -v`, never `docker volume rm` — they are on the agent deny list anyway).
- New map data: run `prepare-osrm.ps1` again, then `docker compose -f infra\osrm\docker-compose.yml restart`.
- New OSRM version: change the tag in `docker-compose.yml` only after checking the tag exists on https://github.com/Project-OSRM/osrm-backend/pkgs/container/osrm-backend, then re-run prepare (data files are version-specific).

## 5. Tests do not need OSRM
Unit and integration tests use fixed fake matrices (`docs/08_TEST_PLAN.md` §3, Optimizer). Only E2E-03 and the demo need the real server. If OSRM is down, the optimizer run ends FAILED with "Routing service unavailable" (`docs/12_ERROR_HANDLING.md` §4, `docs/06_AI_PIPELINE.md` §3).
