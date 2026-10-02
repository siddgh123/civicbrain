-- =============================================================================
-- CivicBrain | db/tools/e2e_reset.sql
-- Empties all application data in the E2E database and keeps reference data (wards, roads, POIs,
-- boundary, categories, work types, transitions, catalogs, depots, templates, privacy notice,
-- frozen step13_* results). Called by scripts/dev/seed-e2e.ps1 before the fixed accounts are created.
-- SAFETY: refuses to run unless the database name ends with "_e2e".
-- MAINTENANCE: every table in schema public must be in exactly one of the two lists below; a new
-- table added by a later migration makes this script stop until someone puts it in a list.
-- =============================================================================
DO $reset$
DECLARE
  v_wipe text[] := ARRAY[
    'action_plan_items','action_plan_revisions','action_plans','ai_classifications','audit_logs',
    'auth_events','auth_otp_codes','auth_refresh_tokens','authenticity_checks','capture_sessions',
    'complaint_feedback','complaint_images','complaint_status_history','complaint_votes','complaints',
    'complaints_import_staging','contractor_equipment','contractor_work_types','contractor_workers',
    'contractors','data_subject_requests','defect_measurements','duplicate_detections',
    'duplicate_import_staging','duplicate_relation','field_teams','jobs','notification_outbox',
    'notifications','officer_approvals','officer_scopes','officers','optimizer_runs',
    'priority_assessments','resource_estimate_equipment','resource_estimate_materials',
    'resource_estimates','resources','route_stops','routes','schedules','site_inspections',
    'user_consents','users','work_completions','work_order_resources','work_orders','yolo_detections'];
  v_keep text[] := ARRAY[
    'complaint_categories','complaint_status_transitions','depots','equipment_catalog',
    'material_catalog','municipal_boundary','notification_templates','pois','pois_import_raw',
    'pois_import_staging','privacy_notices','roads','roads_import_staging','spatial_ref_sys',
    'step13_action_plans','step13_cluster_complaint','step13_clusters','step13_route_stops',
    'step13_routes','step13_schedule_job','step13_schedules','step13_team_equipment','step13_teams',
    'ward_geometry_history','ward_reassignment_log','wards','work_types'];
  v_unknown text;
  v_missing text;
BEGIN
  IF current_database() !~ '_e2e$' THEN
    RAISE EXCEPTION 'e2e_reset.sql refused: database "%" is not an E2E database (name must end with _e2e)', current_database();
  END IF;

  SELECT string_agg(tablename, ', ' ORDER BY tablename) INTO v_unknown
  FROM pg_tables
  WHERE schemaname = 'public' AND tablename <> ALL (v_wipe) AND tablename <> ALL (v_keep)
    AND tablename <> 'flyway_schema_history';
  IF v_unknown IS NOT NULL THEN
    RAISE EXCEPTION 'e2e_reset.sql: tables not classified as wipe/keep: % (edit db/tools/e2e_reset.sql)', v_unknown;
  END IF;

  SELECT string_agg(t, ', ') INTO v_missing
  FROM unnest(v_wipe) AS t
  WHERE NOT EXISTS (SELECT 1 FROM pg_tables p WHERE p.schemaname = 'public' AND p.tablename = t);
  IF v_missing IS NOT NULL THEN
    RAISE EXCEPTION 'e2e_reset.sql: tables in the wipe list do not exist: % (run the migrations first)', v_missing;
  END IF;

  -- one statement for all tables: no CASCADE, so nothing outside the list can be emptied silently
  EXECUTE 'TRUNCATE TABLE ' || (SELECT string_agg(format('public.%I', t), ', ') FROM unnest(v_wipe) AS t)
          || ' RESTART IDENTITY';
  RAISE NOTICE 'E2E RESET DONE: % tables emptied, % reference tables kept (database %)',
    cardinality(v_wipe), cardinality(v_keep), current_database();
END
$reset$;
