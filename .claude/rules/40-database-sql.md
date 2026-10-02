---
paths:
  - "db/**"
  - "flyway/**"
  - "**/db/migration/**"
  - "**/*.sql"
---
<!-- Generated from .agents/rules/40-database-sql.md by scripts/dev/sync-claude.ps1. Edit the source, then run the script. -->
# Database rules (PostgreSQL 18 + PostGIS 3.6)

- Read `docs/03_DATABASE.md` and `db/SCHEMA_REFERENCE_after_V5.sql` before writing SQL or entities.
- Never edit V1–V5 (already applied). New change = `V<n>__<snake_name>.sql` in THREE places kept identical except the outer transaction: `db/` (with `BEGIN;`/`COMMIT;`), `flyway/` (without them, optionally starting with a one-line `-- Flyway copy: …` comment) and `backend/src/main/resources/db/migration/` (a byte-identical copy of the `flyway/` file). `scripts/ci/check-migrations.sh` fails CI on any drift. Plus a test `db/tests/test_V<n>.sql` (one transaction, own data, PASS/FAIL notices, final line `<NAME> TESTS PASSED: % / <total>`, ROLLBACK).
- Grants live only in the repeatable `R__civicbrain_grants.sql` (same file in `db/`, `flyway/`, backend). A new append-only or reference table must be added to its REVOKE lists; every new table must be added to the wipe or keep list of `db/tools/e2e_reset.sql` (the script stops on unclassified tables).
- Migrations must be additive and idempotent (`IF NOT EXISTS`, `DROP CONSTRAINT IF EXISTS` + `ADD`, `ON CONFLICT DO NOTHING`, DO blocks checking `pg_constraint`), must not change existing row values unless the phase plan says so, and must not use `${…}` (Flyway placeholders are disabled but keep them out anyway).
- SRID 4326 for storage; metres via `::geography`; use the existing GIST index on `(location::geography)` for radius queries (`ST_DWithin(a::geography, b::geography, m)`).
- Status changes only through the V2 trigger rules (set `civicbrain.actor_*` first). Plans only via `fn_approve_action_plan` / `fn_assign_action_plan`. Jobs only via the V4 functions.
- Join wards by `ward_id`; display `ward_number`. Children of duplicates: `master_complaint_id IS NOT NULL`.
- Legacy tables listed in `docs/03_DATABASE.md` §2 are not used by the app. `step13_*` are read-only research results.
- You never run `psql` yourself. You may run `scripts\dev\db-rebuild-test.ps1 -Force` (rebuilds `civicbrain_test` + SQL tests), `db-setup-main.ps1` and `seed-e2e.ps1` (`01-safety.md`); prove migrations with them, the Testcontainers integration tests and the CI `db` job. A new migration is on the ASK-FIRST list.
- The backend never connects to `civicbrain_test` (built by psql, no Flyway history); it uses `civicbrain` (dev) and `civicbrain_e2e` (E2E), both managed by Flyway.
