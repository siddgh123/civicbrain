-- =============================================================================
-- CivicBrain | R__civicbrain_grants.sql   (Flyway REPEATABLE migration)
-- Least-privilege grants for the two login roles. Flyway runs it after V1..Vn on every
-- migrate whenever this file changes, so grants always match the current schema - on the dev
-- database, civicbrain_test, civicbrain_e2e and Testcontainers alike.
--   civicbrain_app : Spring Boot API        civicbrain_ai : Python AI worker / FastAPI
-- The ROLES themselves (with passwords) are created once per PostgreSQL server by
-- db/tools/create_roles_template.sql. If they do not exist yet (e.g. Testcontainers) this file
-- only prints a NOTICE and changes nothing. CAREFUL: Flyway then records this file as applied and
-- re-applies it only when the file changes - so on a real database create the roles FIRST
-- (scripts/dev/start-backend.ps1 refuses to start without them). If it happened anyway, run this
-- file once by hand on that database (pgAdmin: db/R__civicbrain_grants.sql).
-- RULE: a new migration that adds an append-only or reference table must add it to the REVOKE
-- lists below in the same pull request (this changes the checksum, so Flyway re-applies it).
-- Must be run by the database owner (Flyway user). Safe to run any number of times.
-- =============================================================================
DO $grants$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'civicbrain_app')
     OR NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'civicbrain_ai') THEN
    RAISE NOTICE 'civicbrain_app / civicbrain_ai roles not found - grants skipped on database %. Create the roles (db/tools/create_roles_template.sql), then run this file once by hand on this database: Flyway re-applies R__ only when the file changes, so a plain re-migrate does NOT apply the grants', current_database();
    RETURN;
  END IF;

  EXECUTE format('GRANT CONNECT ON DATABASE %I TO civicbrain_app, civicbrain_ai', current_database());
  GRANT USAGE ON SCHEMA public TO civicbrain_app, civicbrain_ai;

  -- ---------- API role ----------
  GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO civicbrain_app;
  GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO civicbrain_app;
  GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO civicbrain_app;
  -- append-only logs
  REVOKE UPDATE, DELETE ON audit_logs, auth_events, complaint_status_history, ward_reassignment_log,
    ward_geometry_history FROM civicbrain_app;
  -- reference data and frozen research results are read-only for the app
  REVOKE INSERT, UPDATE, DELETE ON wards, roads, pois, municipal_boundary, complaint_categories, work_types,
    complaint_status_transitions, spatial_ref_sys,
    step13_teams, step13_team_equipment, step13_clusters, step13_cluster_complaint, step13_schedules,
    step13_schedule_job, step13_routes, step13_route_stops, step13_action_plans
    FROM civicbrain_app;

  -- ---------- AI worker role ----------
  GRANT SELECT ON ALL TABLES IN SCHEMA public TO civicbrain_ai;
  GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO civicbrain_ai;
  GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO civicbrain_ai;
  GRANT INSERT, UPDATE, DELETE ON ai_classifications, yolo_detections, defect_measurements, priority_assessments,
    resource_estimates, resource_estimate_materials, resource_estimate_equipment, authenticity_checks,
    duplicate_relation, jobs, optimizer_runs, action_plans, action_plan_items, action_plan_revisions
    TO civicbrain_ai;
  GRANT UPDATE ON complaints, complaint_images, users TO civicbrain_ai;   -- status/AI fields, phash, trust score
  -- rows written by the V2/V4 triggers when the worker changes a status or inserts a job
  GRANT INSERT ON complaint_status_history, notification_outbox, audit_logs TO civicbrain_ai;

  -- the Flyway history table is not application data (exists only in Flyway-managed databases)
  IF to_regclass('public.flyway_schema_history') IS NOT NULL THEN
    REVOKE ALL ON public.flyway_schema_history FROM civicbrain_app, civicbrain_ai;
  END IF;

  -- ---------- objects created later by the owner (next migrations) ----------
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO civicbrain_app;
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO civicbrain_ai;
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO civicbrain_app, civicbrain_ai;
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO civicbrain_app, civicbrain_ai;

  RAISE NOTICE 'CivicBrain grants applied to civicbrain_app and civicbrain_ai on database %', current_database();
END
$grants$;
