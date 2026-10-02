-- =============================================================================
-- CivicBrain | db/tests/test_V5.sql - tests for V5__capture_answers_plan_release.sql
-- One transaction, own data only, ROLLBACK at the end (the database is left unchanged).
--   pgAdmin: open, F5, read the Messages tab.   psql: psql -d civicbrain_test -f test_V5.sql
-- =============================================================================
BEGIN;

DO $$
DECLARE
    v_ok int := 0;
    v_off bigint; v_cit bigint; v_con_user bigint; v_officer bigint; v_contr bigint;
    v_cid bigint; v_run bigint; v_plan1 bigint; v_plan2 bigint; v_plan3 bigint; v_n int;
    v_plan_id bigint; v_contr_id bigint; v_item text;
BEGIN
    -- ---------- own accounts, firm and one verified pothole complaint ----------
    INSERT INTO users (full_name, email, password_hash, role, email_verified_at)
    VALUES ('V5 Officer', 'v5.officer@test.local', 'x', 'OFFICER', now()) RETURNING user_id INTO v_off;
    INSERT INTO users (full_name, email, password_hash, role, email_verified_at)
    VALUES ('V5 Citizen', 'v5.citizen@test.local', 'x', 'CITIZEN', now()) RETURNING user_id INTO v_cit;
    INSERT INTO users (full_name, email, password_hash, role, email_verified_at)
    VALUES ('V5 Contractor', 'v5.contractor@test.local', 'x', 'CONTRACTOR', now()) RETURNING user_id INTO v_con_user;
    INSERT INTO officers (user_id, employee_code, department, designation)
    VALUES (v_off, 'EMP-V5-001', 'Roads (test)', 'JE (test)') RETURNING officer_id INTO v_officer;
    INSERT INTO contractors (user_id, firm_name, contact_person, phone, email, created_by_officer_id)
    VALUES (v_con_user, 'V5 Test Firm', 'V5', '+919111100001', 'v5.contractor@test.local', v_officer)
    RETURNING contractor_id INTO v_contr;
    INSERT INTO contractor_work_types (contractor_id, work_type_code) VALUES (v_contr, 'ROAD');

    PERFORM set_config('civicbrain.actor_user_id', v_cit::text, true);
    PERFORM set_config('civicbrain.actor_role', 'CITIZEN', true);
    INSERT INTO complaints (user_id, category_id, title, description, location, depth_answer, a4_in_frame)
    VALUES (v_cit, (SELECT category_id FROM complaint_categories WHERE category_name = 'Pothole'),
            'V5 pothole', 'V5 pothole test', ST_SetSRID(ST_MakePoint(73.6760, 18.7440), 4326), 'FINGER', true)
    RETURNING complaint_id INTO v_cid;
    PERFORM set_config('civicbrain.actor_user_id', '', true);
    PERFORM set_config('civicbrain.actor_role', 'SYSTEM', true);
    UPDATE complaints SET status = 'VERIFIED' WHERE complaint_id = v_cid;

    -- 1. depth answer values are checked
    BEGIN
        UPDATE complaints SET depth_answer = 'HUGE' WHERE complaint_id = v_cid;
        RAISE NOTICE 'FAIL 1 invalid depth_answer accepted';
    EXCEPTION WHEN check_violation THEN v_ok := v_ok + 1; RAISE NOTICE 'PASS 1 depth_answer limited to SHALLOW/FINGER/DEEP';
    END;

    -- 2. categories that ask for depth
    SELECT count(*) INTO v_n FROM complaint_categories
     WHERE needs_depth_answer AND category_name IN ('Pothole', 'Waterlogging');
    IF v_n = 2 AND (SELECT count(*) FROM complaint_categories WHERE needs_depth_answer) = 2 THEN
        v_ok := v_ok + 1; RAISE NOTICE 'PASS 2 needs_depth_answer = Pothole + Waterlogging only';
    ELSE RAISE NOTICE 'FAIL 2 needs_depth_answer wrong'; END IF;

    -- 3. image quality score range
    BEGIN
        INSERT INTO complaint_images (complaint_id, file_url, image_role, quality_score)
        VALUES (v_cid, 'storage://v5/q.jpg', 'CITIZEN_EVIDENCE', 1.5);
        RAISE NOTICE 'FAIL 3 quality_score 1.5 accepted';
    EXCEPTION WHEN check_violation THEN v_ok := v_ok + 1; RAISE NOTICE 'PASS 3 quality_score must be 0..1';
    END;

    -- plan 1: approve + assign
    INSERT INTO optimizer_runs (requested_by, request, status) VALUES (v_off, '{"work_type":"ROAD"}', 'SUCCEEDED')
    RETURNING run_id INTO v_run;
    INSERT INTO action_plans (plan_code, work_type_code, planned_date, depot_id, optimizer_run_id, created_by_user_id)
    VALUES ('AP-V5-TEST-1', 'ROAD', DATE '2026-10-05', 'D001', v_run, v_off) RETURNING action_plan_id INTO v_plan1;
    INSERT INTO action_plan_items (action_plan_id, complaint_id, sequence_no) VALUES (v_plan1, v_cid, 1);
    PERFORM fn_approve_action_plan(v_plan1, v_off);
    PERFORM fn_assign_action_plan(v_plan1, v_contr, v_off);

    -- 4. officer pulls the complaint back (ASSIGNED -> VERIFIED): plan links cleared, item REMOVED
    PERFORM set_config('civicbrain.actor_user_id', v_off::text, true);
    PERFORM set_config('civicbrain.actor_role', 'OFFICER', true);
    UPDATE complaints SET status = 'VERIFIED' WHERE complaint_id = v_cid;
    SELECT current_action_plan_id, assigned_contractor_id INTO v_plan_id, v_contr_id FROM complaints WHERE complaint_id = v_cid;
    SELECT item_status INTO v_item FROM action_plan_items WHERE action_plan_id = v_plan1 AND complaint_id = v_cid;
    IF v_plan_id IS NULL AND v_contr_id IS NULL AND v_item = 'REMOVED' THEN
        v_ok := v_ok + 1; RAISE NOTICE 'PASS 4 ASSIGNED -> VERIFIED frees the complaint and removes the plan item';
    ELSE RAISE NOTICE 'FAIL 4 plan=% contractor=% item=%', v_plan_id, v_contr_id, v_item; END IF;

    -- 5. it can be planned again
    INSERT INTO action_plans (plan_code, work_type_code, planned_date, depot_id, created_by_user_id)
    VALUES ('AP-V5-TEST-2', 'ROAD', DATE '2026-10-06', 'D001', v_off) RETURNING action_plan_id INTO v_plan2;
    INSERT INTO action_plan_items (action_plan_id, complaint_id, sequence_no) VALUES (v_plan2, v_cid, 1);
    IF fn_approve_action_plan(v_plan2, v_off) = 1 THEN
        v_ok := v_ok + 1; RAISE NOTICE 'PASS 5 released complaint approved into a new plan';
    ELSE RAISE NOTICE 'FAIL 5 re-plan approved 0 complaints'; END IF;
    PERFORM fn_assign_action_plan(v_plan2, v_contr, v_off);

    -- 6. work done while plan 2 is still running, citizen says "not fixed": REOPENED frees the
    --    complaint AND removes its item from the running plan (plan can finish, old firm loses access)
    PERFORM set_config('civicbrain.actor_user_id', v_con_user::text, true);
    PERFORM set_config('civicbrain.actor_role', 'CONTRACTOR', true);
    UPDATE complaints SET status = 'INSPECTED'   WHERE complaint_id = v_cid;
    UPDATE complaints SET status = 'IN_PROGRESS' WHERE complaint_id = v_cid;
    UPDATE complaints SET status = 'COMPLETED'   WHERE complaint_id = v_cid;
    PERFORM set_config('civicbrain.actor_user_id', v_cit::text, true);
    PERFORM set_config('civicbrain.actor_role', 'CITIZEN', true);
    UPDATE complaints SET status = 'REOPENED' WHERE complaint_id = v_cid;
    SELECT current_action_plan_id, assigned_contractor_id INTO v_plan_id, v_contr_id FROM complaints WHERE complaint_id = v_cid;
    SELECT item_status INTO v_item FROM action_plan_items WHERE action_plan_id = v_plan2 AND complaint_id = v_cid;
    IF v_plan_id IS NULL AND v_contr_id IS NULL AND v_item = 'REMOVED' THEN
        v_ok := v_ok + 1; RAISE NOTICE 'PASS 6 REOPENED during a running plan: complaint freed, item REMOVED';
    ELSE RAISE NOTICE 'FAIL 6 plan=% contractor=% item=%', v_plan_id, v_contr_id, v_item; END IF;

    -- 7. the reopened complaint can be planned again
    INSERT INTO action_plans (plan_code, work_type_code, planned_date, depot_id, created_by_user_id)
    VALUES ('AP-V5-TEST-3', 'ROAD', DATE '2026-10-07', 'D001', v_off) RETURNING action_plan_id INTO v_plan3;
    INSERT INTO action_plan_items (action_plan_id, complaint_id, sequence_no) VALUES (v_plan3, v_cid, 1);
    v_n := fn_approve_action_plan(v_plan3, v_off);   -- separate statement: a subquery in the same
    SELECT status INTO v_item FROM complaints WHERE complaint_id = v_cid;   -- expression would see the old row
    IF v_n = 1 AND v_item = 'SCHEDULED' THEN
        v_ok := v_ok + 1; RAISE NOTICE 'PASS 7 reopened complaint planned again (REOPENED -> SCHEDULED)';
    ELSE RAISE NOTICE 'FAIL 7 reopened complaint could not be planned'; END IF;

    -- 8. the status guard still rejects invalid moves (release trigger does not bypass it)
    PERFORM set_config('civicbrain.actor_user_id', v_off::text, true);
    PERFORM set_config('civicbrain.actor_role', 'OFFICER', true);
    BEGIN
        UPDATE complaints SET status = 'COMPLETED' WHERE complaint_id = v_cid;
        RAISE NOTICE 'FAIL 8 SCHEDULED -> COMPLETED accepted';
    EXCEPTION WHEN check_violation THEN v_ok := v_ok + 1; RAISE NOTICE 'PASS 8 guard still blocks SCHEDULED -> COMPLETED';
    END;

    -- 9. plan 3 finishes (backend marks it COMPLETED), officer closes, citizen reopens later:
    --    complaint freed, but the finished plan keeps its item as history
    PERFORM fn_assign_action_plan(v_plan3, v_contr, v_off);
    PERFORM set_config('civicbrain.actor_user_id', v_con_user::text, true);
    PERFORM set_config('civicbrain.actor_role', 'CONTRACTOR', true);
    UPDATE complaints SET status = 'INSPECTED'   WHERE complaint_id = v_cid;
    UPDATE complaints SET status = 'IN_PROGRESS' WHERE complaint_id = v_cid;
    UPDATE complaints SET status = 'COMPLETED'   WHERE complaint_id = v_cid;
    UPDATE action_plans SET status = 'COMPLETED' WHERE action_plan_id = v_plan3;
    PERFORM set_config('civicbrain.actor_user_id', v_off::text, true);
    PERFORM set_config('civicbrain.actor_role', 'OFFICER', true);
    UPDATE complaints SET status = 'CLOSED' WHERE complaint_id = v_cid;
    PERFORM set_config('civicbrain.actor_user_id', v_cit::text, true);
    PERFORM set_config('civicbrain.actor_role', 'CITIZEN', true);
    UPDATE complaints SET status = 'REOPENED' WHERE complaint_id = v_cid;
    SELECT current_action_plan_id, assigned_contractor_id INTO v_plan_id, v_contr_id FROM complaints WHERE complaint_id = v_cid;
    SELECT item_status INTO v_item FROM action_plan_items WHERE action_plan_id = v_plan3 AND complaint_id = v_cid;
    IF v_plan_id IS NULL AND v_contr_id IS NULL AND v_item = 'ACTIVE' THEN
        v_ok := v_ok + 1; RAISE NOTICE 'PASS 9 CLOSED -> REOPENED after the plan finished: complaint freed, history kept';
    ELSE RAISE NOTICE 'FAIL 9 plan=% contractor=% item=%', v_plan_id, v_contr_id, v_item; END IF;

    -- 10. new auth event types
    INSERT INTO auth_events (user_id, event_type) VALUES (v_off, 'TOTP_VERIFIED');
    INSERT INTO auth_events (user_id, event_type) VALUES (v_off, 'LOGOUT_ALL');
    BEGIN
        INSERT INTO auth_events (user_id, event_type) VALUES (v_off, 'BOGUS_EVENT');
        RAISE NOTICE 'FAIL 10 unknown auth event accepted';
    EXCEPTION WHEN check_violation THEN v_ok := v_ok + 1; RAISE NOTICE 'PASS 10 TOTP_VERIFIED/LOGOUT_ALL allowed, unknown types rejected';
    END;

    -- 11. audit rows keyed by code; at least one key required
    INSERT INTO audit_logs (user_id, actor_type, entity_type, entity_id, entity_key, action)
    VALUES (v_off, 'USER', 'material_rate', NULL, 'BITUMINOUS_HOT_MIX', 'RATE_UPDATED');
    BEGIN
        INSERT INTO audit_logs (user_id, actor_type, entity_type, entity_id, entity_key, action)
        VALUES (v_off, 'USER', 'material_rate', NULL, NULL, 'RATE_UPDATED');
        RAISE NOTICE 'FAIL 11 audit row without entity_id and entity_key accepted';
    EXCEPTION WHEN check_violation THEN v_ok := v_ok + 1; RAISE NOTICE 'PASS 11 audit_logs needs entity_id or entity_key';
    END;

    RAISE NOTICE 'V5 TESTS PASSED: % / 11', v_ok;
END $$;

ROLLBACK;
