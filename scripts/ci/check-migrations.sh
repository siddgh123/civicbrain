#!/usr/bin/env bash
# =============================================================================
# CivicBrain | scripts/ci/check-migrations.sh  (CI job `db`)
# Guards against drift between the three copies of every migration:
#   db/Vn__x.sql (pgAdmin, with BEGIN;/COMMIT;)  ==  flyway/Vn__x.sql (without them, + 1 header line)
#   flyway/*.sql  ==  backend/src/main/resources/db/migration/*.sql  (once the backend exists)
#   db/R__*.sql   ==  flyway/R__*.sql
# Also rejects Flyway files that contain their own BEGIN;/COMMIT; or duplicate version numbers.
# =============================================================================
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
fail=0
err() { echo "FAIL  $*"; fail=1; }

shopt -s nullglob
for f in db/V*__*.sql; do
  name="$(basename "$f")"
  fw="flyway/$name"
  [ -f "$fw" ] || { err "$name exists in db/ but not in flyway/"; continue; }
  if ! diff -q <(grep -vxE 'BEGIN;|COMMIT;' "$f") <(sed '1{/^-- Flyway copy:/d}' "$fw") >/dev/null; then
    err "$name: db/ and flyway/ differ beyond BEGIN;/COMMIT; (diff <(grep -vxE 'BEGIN;|COMMIT;' $f) $fw)"
  fi
done
for fw in flyway/V*__*.sql; do
  name="$(basename "$fw")"
  [ -f "db/$name" ] || err "$name exists in flyway/ but not in db/"
  if grep -qxE 'BEGIN;|COMMIT;' "$fw"; then err "$name: Flyway copy must not contain its own BEGIN;/COMMIT;"; fi
done
for fw in flyway/R__*.sql; do
  name="$(basename "$fw")"
  if [ ! -f "db/$name" ]; then err "$name missing in db/"; elif ! cmp -s "$fw" "db/$name"; then err "$name: db/ and flyway/ copies differ"; fi
done
dups="$(for fw in flyway/V*__*.sql; do basename "$fw" | sed -E 's/^V([0-9]+)__.*/\1/'; done | sort | uniq -d)"
[ -z "$dups" ] || err "duplicate migration versions: $dups"

MIG=backend/src/main/resources/db/migration
if [ -d "$MIG" ]; then
  for fw in flyway/*.sql; do
    name="$(basename "$fw")"
    if [ ! -f "$MIG/$name" ]; then err "$name missing in $MIG (copy it from flyway/)";
    elif ! cmp -s "$fw" "$MIG/$name"; then err "$name: $MIG copy differs from flyway/"; fi
  done
  for b in "$MIG"/*.sql; do [ -f "flyway/$(basename "$b")" ] || err "$(basename "$b") is in $MIG but not in flyway/ (add it to flyway/ and db/ too)"; done
else
  echo "INFO  $MIG not present yet (created in P1)"
fi

if [ "$fail" -ne 0 ]; then echo "MIGRATION COPIES: DRIFT FOUND"; exit 1; fi
echo "MIGRATION COPIES: CONSISTENT ($(find flyway -maxdepth 1 -name '*.sql' | wc -l) files)"
