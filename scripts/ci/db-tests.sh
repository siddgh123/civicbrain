#!/usr/bin/env bash
# =============================================================================
# CivicBrain | scripts/ci/db-tests.sh   (used by .github/workflows/ci.yml job `db`; also runs on Linux/WSL)
# Builds a brand-new database the same way Flyway does (each flyway/V*.sql in its own transaction,
# then flyway/R__*.sql), creates the login roles, loads the demo seed and runs every db/tests/test_*.sql.
# With SOURCE=db it uses the pgAdmin copies in db/ instead (their own BEGIN/COMMIT).
# A test file passes only if psql exits 0, it prints "<NAME> TESTS PASSED: n / n" with equal numbers,
# and no NOTICE line starts with "FAIL".
# Needs: psql on PATH; PGHOST, PGPORT, PGUSER (superuser), PGPASSWORD in the environment.
# Optional: DB (default civicbrain_ci), SOURCE (flyway|db, default flyway),
#           SKIP_BUILD=1 (only run the tests on an existing database).
# The target database is DROPPED and re-created: the name must start with civicbrain_ci.
# =============================================================================
set -euo pipefail

DB="${DB:-civicbrain_ci}"
SOURCE="${SOURCE:-flyway}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PSQL=(psql -X -q -v ON_ERROR_STOP=1)

case "$DB" in civicbrain_ci*) ;; *) echo "Refusing to drop '$DB' (name must start with civicbrain_ci)"; exit 2 ;; esac
case "$SOURCE" in flyway|db) ;; *) echo "SOURCE must be flyway or db"; exit 2 ;; esac

if [ "${SKIP_BUILD:-0}" != "1" ]; then
echo "==> fresh database $DB (migrations from $SOURCE/)"
"${PSQL[@]}" -d postgres -c "DROP DATABASE IF EXISTS \"$DB\"" -c "CREATE DATABASE \"$DB\""

echo "==> login roles (once per server; idempotent)"
# escape for a SQL string literal ('' ) and for the sed replacement (/ & \)
sql_sed_escape() { printf '%s' "$1" | sed -e "s/'/''/g" -e 's/[\/&\\]/\\&/g'; }
sed -e "s/CHANGE_ME_APP_PASSWORD/$(sql_sed_escape "${CI_APP_PASSWORD:-ci-app-password}")/" \
    -e "s/CHANGE_ME_AI_PASSWORD/$(sql_sed_escape "${CI_AI_PASSWORD:-ci-ai-password}")/" \
    "$ROOT/db/tools/create_roles_template.sql" | "${PSQL[@]}" -d "$DB" -f -

echo "==> versioned migrations"
mapfile -t versioned < <(find "$ROOT/$SOURCE" -maxdepth 1 -name 'V*__*.sql' -printf '%f\n' | sort -V)
[ "${#versioned[@]}" -gt 0 ] || { echo "no migrations found in $SOURCE/"; exit 1; }
for f in "${versioned[@]}"; do
  echo "    $f"
  if [ "$SOURCE" = flyway ]; then "${PSQL[@]}" -1 -d "$DB" -f "$ROOT/$SOURCE/$f"
  else "${PSQL[@]}" -d "$DB" -f "$ROOT/$SOURCE/$f"; fi
done

echo "==> repeatable migrations"
for f in "$ROOT/$SOURCE"/R__*.sql; do
  [ -e "$f" ] || continue
  echo "    $(basename "$f")"
  "${PSQL[@]}" -1 -d "$DB" -f "$f"
done

echo "==> demo seed"
"${PSQL[@]}" -d "$DB" -f "$ROOT/db/seed/seed_synthetic_demo_data.sql" >/dev/null

echo "==> repeatable migrations again (must be idempotent - Flyway re-runs them when they change)"
for f in "$ROOT/$SOURCE"/R__*.sql; do
  [ -e "$f" ] || continue
  "${PSQL[@]}" -1 -d "$DB" -f "$f" >/dev/null
done
fi

echo "==> SQL tests"
failed=0
for t in "$ROOT"/db/tests/test_*.sql; do
  name="$(basename "$t")"
  if ! out="$("${PSQL[@]}" -d "$DB" -f "$t" 2>&1)"; then
    echo "$out" | tail -40; echo "FAIL  $name (psql error)"; failed=1; continue
  fi
  summary="$(grep -Eo '[A-Z0-9 ]+TESTS PASSED: [0-9]+ / [0-9]+' <<<"$out" | tail -1 || true)"
  bad="$(grep -E 'NOTICE: +FAIL' <<<"$out" || true)"
  if [ -z "$summary" ]; then echo "$out" | tail -40; echo "FAIL  $name (no 'TESTS PASSED' summary)"; failed=1; continue; fi
  passed="$(sed -E 's/.*PASSED: ([0-9]+) \/ ([0-9]+)/\1/' <<<"$summary")"
  total="$(sed -E 's/.*PASSED: ([0-9]+) \/ ([0-9]+)/\2/' <<<"$summary")"
  if [ -n "$bad" ] || [ "$passed" != "$total" ]; then
    echo "$bad"; echo "FAIL  $name ->${summary}"; failed=1
  else
    echo "PASS  $name ->${summary}"
  fi
done

echo "==> schema facts"
"${PSQL[@]}" -d "$DB" -At -c "
  SELECT 'app tables: ' || count(*) FROM pg_tables WHERE schemaname = 'public' AND tablename <> 'spatial_ref_sys';" \
  -c "SELECT 'wards: ' || count(*) FROM wards;" \
  -c "SELECT 'fn_locate_point(18.7440,73.6760) -> ward_number ' || w.ward_number || ' (ward_id ' || w.ward_id || ')'
        FROM fn_locate_point(18.7440, 73.6760) p JOIN wards w ON w.ward_id = p.ward_id;"
tables="$("${PSQL[@]}" -d "$DB" -At -c "SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tablename <> 'spatial_ref_sys'")"
if [ "$tables" -lt 74 ]; then echo "FAIL  expected at least 74 application tables, found $tables"; failed=1; fi

if [ "$failed" -ne 0 ]; then echo "DB TESTS: FAILED"; exit 1; fi
echo "DB TESTS: ALL PASSED"
