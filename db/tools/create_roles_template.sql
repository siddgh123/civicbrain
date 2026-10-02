-- =============================================================================
-- CivicBrain | db/tools/create_roles_template.sql
-- Creates the two least-privilege LOGIN roles. Roles belong to the whole PostgreSQL server, so
-- run this ONCE per server (per laptop), as postgres, BEFORE the backend starts for the first time.
-- Replace the two passwords first with the values of DB_PASSWORD / DB_AI_PASSWORD from your .env
-- (never commit the real ones). scripts/dev/db-rebuild-test.ps1 does this for you from .env.
--   civicbrain_app : Spring Boot API          civicbrain_ai : Python AI worker / FastAPI
-- The GRANTS are not here: they live in flyway/R__civicbrain_grants.sql (repeatable migration),
-- which Flyway applies after every migrate (pgAdmin users: run db/R__civicbrain_grants.sql in
-- each database after V1-V5). Flyway itself runs as the database owner (PG_ADMIN_USER, postgres
-- in local dev). Re-running this file is safe. To change a password later:
--   ALTER ROLE civicbrain_app PASSWORD '<new>';
-- =============================================================================
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'civicbrain_app') THEN
    CREATE ROLE civicbrain_app LOGIN PASSWORD 'CHANGE_ME_APP_PASSWORD' NOSUPERUSER NOCREATEDB NOCREATEROLE;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'civicbrain_ai') THEN
    CREATE ROLE civicbrain_ai LOGIN PASSWORD 'CHANGE_ME_AI_PASSWORD' NOSUPERUSER NOCREATEDB NOCREATEROLE;
  END IF;
END $$;
