-- CivicBrain | db/tests/test_roles.sql - run as postgres after create_roles_template.sql + R__civicbrain_grants.sql. Rolls back.
BEGIN;
DO $$
DECLARE v_ok int := 0; v_uid bigint; v_cid bigint;
BEGIN
  -- API role: normal work allowed
  SET LOCAL ROLE civicbrain_app;
  INSERT INTO users (full_name, email, password_hash, role) VALUES ('Role Test', 'role@test.local', 'x', 'CITIZEN') RETURNING user_id INTO v_uid;
  PERFORM set_config('civicbrain.actor_role', 'CITIZEN', true);
  INSERT INTO complaints (user_id, category_id, title, description, location)
  VALUES (v_uid, 1, 'role test', 'role test', ST_SetSRID(ST_MakePoint(73.676, 18.744), 4326)) RETURNING complaint_id INTO v_cid;
  v_ok := v_ok + 1; RAISE NOTICE 'PASS 1 app role can register a user and submit a complaint (triggers ran)';

  BEGIN
    UPDATE wards SET ward_name = 'x' WHERE ward_number = 1;
    RAISE NOTICE 'FAIL 2 app role changed reference data';
  EXCEPTION WHEN insufficient_privilege THEN v_ok := v_ok + 1; RAISE NOTICE 'PASS 2 reference data read-only';
  END;
  BEGIN
    DELETE FROM audit_logs;
    RAISE NOTICE 'FAIL 3 app role deleted audit logs';
  EXCEPTION WHEN insufficient_privilege THEN v_ok := v_ok + 1; RAISE NOTICE 'PASS 3 audit log append-only';
  END;
  PERFORM * FROM fn_purge_expired();           -- retention job works for the app role (SECURITY DEFINER)
  v_ok := v_ok + 1; RAISE NOTICE 'PASS 3b app role can run the retention purge';
  BEGIN
    EXECUTE 'DROP TABLE complaint_votes';
    RAISE NOTICE 'FAIL 4 app role dropped a table';
  EXCEPTION WHEN insufficient_privilege THEN v_ok := v_ok + 1; RAISE NOTICE 'PASS 4 no DDL for app role';
  END;
  RESET ROLE;

  -- AI role: claim the job, write results, move the status
  SET LOCAL ROLE civicbrain_ai;
  PERFORM fn_claim_jobs('role-test', ARRAY['ANALYZE_COMPLAINT'], 50);
  INSERT INTO ai_classifications (complaint_id, predicted_category, confidence, model_name, model_version)
  VALUES (v_cid, 'Pothole', 0.9, 'tfidf-lr', 'test');
  PERFORM set_config('civicbrain.actor_role', 'SYSTEM', true);
  UPDATE complaints SET status = 'VERIFIED', ai_status = 'COMPLETED' WHERE complaint_id = v_cid;
  v_ok := v_ok + 1; RAISE NOTICE 'PASS 5 ai role claims jobs, writes results, verifies complaint';
  BEGIN
    DELETE FROM users WHERE user_id = v_uid;
    RAISE NOTICE 'FAIL 6 ai role deleted a user';
  EXCEPTION WHEN insufficient_privilege THEN v_ok := v_ok + 1; RAISE NOTICE 'PASS 6 ai role cannot delete users';
  END;
  RESET ROLE;
  RAISE NOTICE 'ROLE TESTS PASSED: % / 7', v_ok;
END $$;
ROLLBACK;
