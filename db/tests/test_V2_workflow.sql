-- =============================================================================
-- CivicBrain | test_V2_workflow.sql
-- End-to-end test of V2__civicbrain_app_layer.sql. Runs inside ONE transaction
-- and ROLLS BACK at the end, so the database is left unchanged.
--   pgAdmin: Query Tool -> open this file -> F5 -> read the Messages tab
--            (or Tools -> PSQL Tool, then  \i test_V2_workflow.sql  to see every result table)
--   psql   : psql -d civicbrain -f test_V2_workflow.sql
-- =============================================================================
BEGIN;

-- ---------- 1. Accounts: admin, officer, contractor (+ employee), two citizens
INSERT INTO users (full_name, email, phone, password_hash, role, email_verified_at)
VALUES ('Test Admin',      'admin@test.local',      '+919000000001', '$argon2id$dummy', 'ADMIN',      now()),
       ('Test Officer',    'officer@test.local',    '+919000000002', '$argon2id$dummy', 'OFFICER',    now()),
       ('Patil Constructions', 'patil@test.local',  '+919000000003', '$argon2id$dummy', 'CONTRACTOR', now()),
       ('Citizen One',     'citizen1@test.local',   '+919000000004', '$argon2id$dummy', 'CITIZEN',    now()),
       ('Citizen Two',     'citizen2@test.local',   '+919000000005', '$argon2id$dummy', 'CITIZEN',    now());

INSERT INTO officers (user_id, employee_code, department, designation, created_by_user_id)
SELECT u.user_id, 'EMP-T-001', 'Roads (test)', 'Junior Engineer (test)', a.user_id
  FROM users u, users a WHERE u.email = 'officer@test.local' AND a.email = 'admin@test.local';

INSERT INTO officer_scopes (officer_id, ward_id, work_type_code)
SELECT officer_id, NULL, 'ROAD' FROM officers WHERE employee_code = 'EMP-T-001';

INSERT INTO contractors (user_id, firm_name, contact_person, phone, email, crew_capacity, created_by_officer_id)
SELECT u.user_id, 'Patil Constructions (test)', 'R. Patil', '+919000000003', 'patil@test.local', 6, o.officer_id
  FROM users u, officers o WHERE u.email = 'patil@test.local' AND o.employee_code = 'EMP-T-001';
INSERT INTO contractor_work_types SELECT contractor_id, 'ROAD' FROM contractors WHERE firm_name LIKE 'Patil%';
INSERT INTO contractor_equipment  SELECT contractor_id, 'plate_compactor', 1 FROM contractors WHERE firm_name LIKE 'Patil%';
INSERT INTO contractor_workers (contractor_id, full_name, phone, skill)
SELECT contractor_id, 'S. Jadhav', '+919000000006', 'MASON' FROM contractors WHERE firm_name LIKE 'Patil%';

-- ---------- 2. Citizen One submits a pothole complaint from inside TDMC
SELECT 'locate point' AS step, * FROM fn_locate_point(18.7440, 73.6760);

INSERT INTO capture_sessions (user_id) SELECT user_id FROM users WHERE email = 'citizen1@test.local';

SELECT set_config('civicbrain.actor_user_id', (SELECT user_id::text FROM users WHERE email='citizen1@test.local'), true),
       set_config('civicbrain.actor_role', 'CITIZEN', true);

INSERT INTO complaints (user_id, category_id, title, description, location, ward_id, road_id, poi_id,
                        location_accuracy_m, location_captured_at, location_source, capture_session_id)
SELECT u.user_id, (SELECT category_id FROM complaint_categories WHERE category_name='Pothole'),
       'Big pothole near bus stop', 'Deep pothole in the left lane, two-wheelers are falling.',
       ST_SetSRID(ST_MakePoint(73.6760, 18.7440), 4326), l.ward_id, l.road_id, l.poi_id,
       8.5, now(), 'BROWSER_GPS', (SELECT capture_session_id FROM capture_sessions WHERE user_id = u.user_id)
  FROM users u, fn_locate_point(18.7440, 73.6760) l
 WHERE u.email = 'citizen1@test.local';

SELECT 'new complaint' AS step, complaint_id, public_ref, status, is_synthetic, ai_status
  FROM complaints WHERE title = 'Big pothole near bus stop';

SELECT 'history after submit' AS step, old_status, new_status, actor_role FROM v_complaint_timeline
 WHERE public_ref = (SELECT public_ref FROM complaints WHERE title = 'Big pothole near bus stop');
SELECT 'outbox after submit' AS step, event_type, event_status, payload->>'public_ref' AS ref
  FROM notification_outbox WHERE complaint_id = (SELECT complaint_id FROM complaints WHERE title = 'Big pothole near bus stop');

-- ---------- 3. AI pipeline writes its evidence (values are test values)
INSERT INTO complaint_images (complaint_id, file_url, image_role, capture_method, sha256, phash, width_px, height_px,
                              device_pitch_deg, capture_location, capture_accuracy_m, processing_status)
SELECT complaint_id, 's3://civicbrain-private/c/test1.jpg', 'CITIZEN_EVIDENCE', 'IN_APP_CAMERA',
       repeat('a', 64), x'f0e1d2c3b4a59687'::bigint, 1920, 1080, 58.0, location, 8.5, 'COMPLETED'
  FROM complaints WHERE title = 'Big pothole near bus stop';

INSERT INTO yolo_detections (image_id, detected_class, confidence, bbox_x, bbox_y, bbox_width, bbox_height, model_name, model_version)
SELECT image_id, 'Pothole', 0.8710, 812, 540, 300, 190, 'yolov8n-civicbrain', 'test'
  FROM complaint_images WHERE file_url = 's3://civicbrain-private/c/test1.jpg';

INSERT INTO defect_measurements (complaint_id, image_id, detection_id, source, method, length_m, width_m, area_m2,
                                 depth_m, depth_source, volume_m3, severity_class, confidence, error_band_pct, assumptions)
SELECT i.complaint_id, i.image_id, d.detection_id, 'AI', 'GROUND_PLANE_HOMOGRAPHY', 0.600, 0.400, 0.240,
       0.050, 'ASSUMED_FROM_SEVERITY_CLASS', 0.0315, 'MEDIUM', 0.600, 25.0,
       '{"camera_height_m":1.4,"pitch_deg":58,"cut_margin_m":0.15}'::jsonb
  FROM complaint_images i JOIN yolo_detections d ON d.image_id = i.image_id
 WHERE i.file_url = 's3://civicbrain-private/c/test1.jpg';

INSERT INTO authenticity_checks (complaint_id, check_code, result, score_delta, details)
SELECT complaint_id, 'BOUNDARY', 'PASS', 0, '{"inside":true}'::jsonb FROM complaints WHERE title = 'Big pothole near bus stop'
UNION ALL
SELECT complaint_id, 'GPS_ACCURACY', 'PASS', 0, '{"accuracy_m":8.5}'::jsonb FROM complaints WHERE title = 'Big pothole near bus stop';

INSERT INTO priority_assessments (complaint_id, severity_score, urgency_score, location_score, impact_score,
                                  frequency_score, infrastructure_score, historical_risk_score, final_score, priority_level, reason)
SELECT complaint_id, 70, 10, 60, 50, 20, 80, 30,
       0.25*70 + 0.15*50 + 0.15*60 + 0.10*20 + 0.10*10 + 0.15*80 + 0.10*30, 'MEDIUM', 'test'
  FROM complaints WHERE title = 'Big pothole near bus stop';

INSERT INTO resource_estimates (complaint_id, measurement_id, estimate_source, workers_required, duration_hours,
                                total_cost_min, total_cost_expected, total_cost_max, rate_reference)
SELECT m.complaint_id, m.measurement_id, 'RULE_BASED', 3, 3.5, 2200, 3100, 4300, 'Maharashtra PWD SSR 2022-23 (rates to be configured)'
  FROM defect_measurements m JOIN complaints c ON c.complaint_id = m.complaint_id
 WHERE c.title = 'Big pothole near bus stop';
INSERT INTO resource_estimate_materials (estimate_id, material_code, quantity, unit)
SELECT estimate_id, 'BITUMINOUS_HOT_MIX', 0.078, 'tonne' FROM resource_estimates r JOIN complaints c USING (complaint_id)
 WHERE c.title = 'Big pothole near bus stop'
UNION ALL
SELECT estimate_id, 'TACK_COAT_EMULSION', 0.16, 'kg' FROM resource_estimates r JOIN complaints c USING (complaint_id)
 WHERE c.title = 'Big pothole near bus stop';

SELECT set_config('civicbrain.actor_role', 'SYSTEM', true), set_config('civicbrain.actor_user_id', '', true);
UPDATE complaints SET status = 'VERIFIED', ai_status = 'COMPLETED', ai_processed_at = now(),
                      authenticity_status = 'PASSED', authenticity_score = 92, current_priority_score = 51.0,
                      current_priority_level = 'HIGH'
 WHERE title = 'Big pothole near bus stop';

-- ---------- 4. Citizen Two reports the same pothole 40 m away -> duplicate -> MERGED
SELECT set_config('civicbrain.actor_user_id', (SELECT user_id::text FROM users WHERE email='citizen2@test.local'), true),
       set_config('civicbrain.actor_role', 'CITIZEN', true);
INSERT INTO complaints (user_id, category_id, title, description, location, location_source)
SELECT user_id, (SELECT category_id FROM complaint_categories WHERE category_name='Pothole'),
       'Pothole near bus stop', 'Large pothole on the road near the bus stop.',
       ST_SetSRID(ST_MakePoint(73.6763, 18.7442), 4326), 'BROWSER_GPS'
  FROM users WHERE email = 'citizen2@test.local';

SELECT 'duplicate candidates' AS step, * FROM fn_duplicate_candidates(
       (SELECT complaint_id FROM complaints WHERE title = 'Pothole near bus stop'));

SELECT set_config('civicbrain.actor_role', 'SYSTEM', true), set_config('civicbrain.actor_user_id', '', true),
       set_config('civicbrain.status_remarks', 'Same pothole as an earlier complaint (score 0.81)', true);
UPDATE complaints
   SET status = 'MERGED', duplicate_status = 'DUPLICATE', duplicate_checked_at = now(),
       master_complaint_id = (SELECT complaint_id FROM complaints WHERE title = 'Big pothole near bus stop'),
       matched_complaint_id = (SELECT complaint_id FROM complaints WHERE title = 'Big pothole near bus stop')
 WHERE title = 'Pothole near bus stop';
SELECT set_config('civicbrain.status_remarks', '', true);

-- ---------- 5. Officer generates + approves an action plan, then assigns the contractor
INSERT INTO optimizer_runs (requested_by, request, status, finished_at, result_summary)
SELECT user_id, '{"ward_ids":[],"work_type":"ROAD","date":"2026-10-05"}'::jsonb, 'SUCCEEDED', now(), '{"jobs":1}'::jsonb
  FROM users WHERE email = 'officer@test.local';

INSERT INTO action_plans (plan_code, work_type_code, planned_date, depot_id, optimizer_run_id, created_by_user_id,
                          est_service_hours, est_travel_hours, total_distance_km, est_total_cost, planned_start, planned_end)
SELECT 'AP-2026-10-05-ROAD-T01', 'ROAD', DATE '2026-10-05', 'D001', r.run_id, u.user_id, 3.5, 0.4, 9.8, 3100, '08:00', '12:00'
  FROM optimizer_runs r, users u WHERE u.email = 'officer@test.local' ORDER BY r.run_id DESC LIMIT 1;

INSERT INTO action_plan_items (action_plan_id, complaint_id, sequence_no, planned_start, planned_end, service_duration_h, est_workers, est_cost)
SELECT ap.action_plan_id, c.complaint_id, 1, TIMESTAMP '2026-10-05 08:20', TIMESTAMP '2026-10-05 11:50', 3.5, 3, 3100
  FROM action_plans ap, complaints c
 WHERE ap.plan_code = 'AP-2026-10-05-ROAD-T01' AND c.title = 'Big pothole near bus stop';

INSERT INTO action_plan_revisions (action_plan_id, version, changed_by, change_summary, snapshot)
SELECT action_plan_id, 1, created_by_user_id, 'Generated by optimizer', to_jsonb(ap) FROM action_plans ap
 WHERE plan_code = 'AP-2026-10-05-ROAD-T01';

SELECT 'approve plan' AS step, fn_approve_action_plan(
         (SELECT action_plan_id FROM action_plans WHERE plan_code = 'AP-2026-10-05-ROAD-T01'),
         (SELECT user_id FROM users WHERE email = 'officer@test.local')) AS complaints_scheduled;

SELECT 'assign plan' AS step, fn_assign_action_plan(
         (SELECT action_plan_id FROM action_plans WHERE plan_code = 'AP-2026-10-05-ROAD-T01'),
         (SELECT contractor_id FROM contractors WHERE firm_name LIKE 'Patil%'),
         (SELECT user_id FROM users WHERE email = 'officer@test.local')) AS complaints_assigned;

SELECT 'recipients of ASSIGNED' AS step, u.full_name, r.relation
  FROM fn_complaint_notification_recipients((SELECT complaint_id FROM complaints WHERE title = 'Big pothole near bus stop')) r
  JOIN users u USING (user_id);

SELECT 'contractor worklist' AS step, plan_code, sequence_no, public_ref, complaint_status, category_name
  FROM v_contractor_worklist;

-- ---------- 6. Contractor: inspection -> in progress -> completed with proof
SELECT set_config('civicbrain.actor_user_id', (SELECT user_id::text FROM users WHERE email='patil@test.local'), true),
       set_config('civicbrain.actor_role', 'CONTRACTOR', true),
       set_config('civicbrain.status_remarks', 'Pothole 0.7 x 0.5 m, 60 mm deep. Work on 5 Oct.', true);

INSERT INTO defect_measurements (complaint_id, source, method, length_m, width_m, area_m2, depth_m, depth_source,
                                 volume_m3, severity_class, measured_by)
SELECT complaint_id, 'CONTRACTOR', 'MANUAL_TAPE', 0.70, 0.50, 0.35, 0.060, 'MEASURED_ON_SITE', 0.021, 'LARGE',
       (SELECT user_id FROM users WHERE email='patil@test.local')
  FROM complaints WHERE title = 'Big pothole near bus stop';

INSERT INTO site_inspections (complaint_id, action_plan_id, contractor_id, inspected_by_user_id, inspector_location,
                              inspector_accuracy_m, issue_confirmed, findings, measurement_id, expected_completion_date)
SELECT c.complaint_id, c.current_action_plan_id, c.assigned_contractor_id,
       (SELECT user_id FROM users WHERE email='patil@test.local'),
       ST_SetSRID(ST_MakePoint(73.67605, 18.74402), 4326), 6, true,
       'Pothole 0.7 x 0.5 m, 60 mm deep. Work on 5 Oct.',
       (SELECT max(measurement_id) FROM defect_measurements WHERE source = 'CONTRACTOR'), DATE '2026-10-05'
  FROM complaints c WHERE c.title = 'Big pothole near bus stop';

UPDATE complaints SET status = 'INSPECTED'   WHERE title = 'Big pothole near bus stop';
SELECT set_config('civicbrain.status_remarks', '', true);
UPDATE complaints SET status = 'IN_PROGRESS' WHERE title = 'Big pothole near bus stop';

INSERT INTO work_completions (complaint_id, action_plan_id, contractor_id, submitted_by_user_id, completion_location,
                              work_summary, actual_workers, actual_hours, actual_cost, materials_used)
SELECT c.complaint_id, c.current_action_plan_id, c.assigned_contractor_id,
       (SELECT user_id FROM users WHERE email='patil@test.local'),
       ST_SetSRID(ST_MakePoint(73.67598, 18.74399), 4326),
       'Cut to rectangle, tack coat, hot mix in one 60 mm layer, compacted.', 3, 3.0, 2950,
       '[{"material_code":"BITUMINOUS_HOT_MIX","quantity":0.05,"unit":"tonne"}]'::jsonb
  FROM complaints c WHERE c.title = 'Big pothole near bus stop';

-- proof photo: its pHash differs from the "before" photo by 1 bit -> must be flagged as reuse
INSERT INTO complaint_images (complaint_id, file_url, image_role, capture_method, uploaded_by, completion_id, phash)
SELECT complaint_id, 's3://civicbrain-private/c/test1_done.jpg', 'COMPLETION_PROOF', 'IN_APP_CAMERA',
       submitted_by_user_id, completion_id, x'f0e1d2c3b4a59686'::bigint
  FROM work_completions;

SELECT 'proof photo reuse check' AS step, image_role, hamming_bits, same_complaint
  FROM fn_similar_images((SELECT image_id FROM complaint_images WHERE file_url = 's3://civicbrain-private/c/test1_done.jpg'));

SELECT set_config('civicbrain.status_remarks', 'Completed with proof photo', true);
UPDATE complaints SET status = 'COMPLETED' WHERE title = 'Big pothole near bus stop';

SELECT 'distance checks (m)' AS step,
       (SELECT round(distance_from_complaint_m, 1) FROM site_inspections) AS inspection_m,
       (SELECT round(distance_from_complaint_m, 1) FROM work_completions) AS completion_m;

-- ---------- 7. Negative tests: every one of these must be REJECTED by the database
DO $$
DECLARE v_id bigint; v_skip bigint; v_ok int := 0;
BEGIN
  SELECT complaint_id INTO v_id FROM complaints WHERE title = 'Big pothole near bus stop';

  -- a) contractor tries to close the complaint (only officer may)
  PERFORM set_config('civicbrain.actor_role', 'CONTRACTOR', true);
  BEGIN
    UPDATE complaints SET status = 'CLOSED' WHERE complaint_id = v_id;
    RAISE NOTICE 'FAIL a) contractor closed complaint';
  EXCEPTION WHEN insufficient_privilege THEN v_ok := v_ok + 1; RAISE NOTICE 'PASS a) contractor cannot close';
  END;

  -- b) skipping steps: a fresh SUBMITTED complaint cannot jump to COMPLETED
  --    (own row, so the test does not depend on demo data or on identity values)
  PERFORM set_config('civicbrain.actor_role', 'CITIZEN', true);
  INSERT INTO complaints (user_id, category_id, title, description, location)
  VALUES ((SELECT user_id FROM users WHERE email='citizen1@test.local'), 1, 'skip test', 'skip test',
          ST_SetSRID(ST_MakePoint(73.676, 18.744), 4326))
  RETURNING complaint_id INTO v_skip;
  PERFORM set_config('civicbrain.actor_role', 'OFFICER', true);
  BEGIN
    UPDATE complaints SET status = 'COMPLETED' WHERE complaint_id = v_skip;
    RAISE NOTICE 'FAIL b) skipped lifecycle';
  EXCEPTION WHEN check_violation THEN v_ok := v_ok + 1; RAISE NOTICE 'PASS b) SUBMITTED -> COMPLETED blocked';
  END;

  -- c) new real complaint cannot start as ASSIGNED
  BEGIN
    INSERT INTO complaints (user_id, category_id, title, description, status, location)
    VALUES ((SELECT user_id FROM users WHERE email='citizen1@test.local'), 1, 'x', 'x', 'ASSIGNED',
            ST_SetSRID(ST_MakePoint(73.676, 18.744), 4326));
    RAISE NOTICE 'FAIL c) inserted ASSIGNED';
  EXCEPTION WHEN check_violation THEN v_ok := v_ok + 1; RAISE NOTICE 'PASS c) new complaint must be SUBMITTED';
  END;

  -- d) assign to a contractor not registered for the plan work type
  BEGIN
    INSERT INTO contractors (firm_name, contact_person, phone) VALUES ('Water Only (test)', 'X', '+919000000009');
    INSERT INTO contractor_work_types SELECT contractor_id, 'WATER' FROM contractors WHERE firm_name = 'Water Only (test)';
    INSERT INTO action_plans (plan_code, work_type_code, planned_date, status) VALUES ('AP-NEG-1', 'ROAD', DATE '2026-10-06', 'APPROVED');
    PERFORM fn_assign_action_plan((SELECT action_plan_id FROM action_plans WHERE plan_code='AP-NEG-1'),
                                  (SELECT contractor_id FROM contractors WHERE firm_name='Water Only (test)'),
                                  (SELECT user_id FROM users WHERE email='officer@test.local'));
    RAISE NOTICE 'FAIL d) wrong-work-type contractor assigned';
  EXCEPTION WHEN raise_exception THEN v_ok := v_ok + 1; RAISE NOTICE 'PASS d) contractor work type enforced';
  END;

  -- e) a role outside the CHECK list
  BEGIN
    INSERT INTO users (full_name, email, password_hash, role) VALUES ('Bad', 'bad@test.local', 'x', 'SUPERUSER');
    RAISE NOTICE 'FAIL e) bad role accepted';
  EXCEPTION WHEN check_violation THEN v_ok := v_ok + 1; RAISE NOTICE 'PASS e) unknown role rejected';
  END;

  -- f) same e-mail with different case
  BEGIN
    INSERT INTO users (full_name, email, password_hash) VALUES ('Dup', 'CITIZEN1@test.local', 'x');
    RAISE NOTICE 'FAIL f) case-duplicate e-mail accepted';
  EXCEPTION WHEN unique_violation THEN v_ok := v_ok + 1; RAISE NOTICE 'PASS f) e-mail unique ignoring case';
  END;

  RAISE NOTICE 'NEGATIVE TESTS PASSED: % / 6', v_ok;
END $$;

-- ---------- 8. Officer verifies and closes
SELECT set_config('civicbrain.actor_user_id', (SELECT user_id::text FROM users WHERE email='officer@test.local'), true),
       set_config('civicbrain.actor_role', 'OFFICER', true),
       set_config('civicbrain.status_remarks', 'Verified on site photo', true);
UPDATE work_completions SET verification_status = 'APPROVED', verified_at = now(),
       verified_by_user_id = (SELECT user_id FROM users WHERE email='officer@test.local');
UPDATE complaints SET status = 'CLOSED' WHERE title = 'Big pothole near bus stop';

-- ---------- 9. Results
SELECT 'full timeline' AS step, old_status, new_status, actor_role, remarks
  FROM v_complaint_timeline
 WHERE public_ref = (SELECT public_ref FROM complaints WHERE title = 'Big pothole near bus stop')
 ORDER BY status_history_id;

SELECT 'outbox events' AS step, event_type, event_status, count(*) AS n
  FROM notification_outbox GROUP BY 2, 3 ORDER BY min(outbox_id);

SELECT 'officer queue row' AS step, public_ref, status, dashboard_tab, category_name, work_type_code, ward_number,
       linked_duplicates, priority_level, total_cost_expected, contractor_name, plan_code
  FROM v_officer_complaint_queue WHERE NOT is_synthetic;

SELECT 'closed_at set' AS step, public_ref, status, closed_at IS NOT NULL AS closed_at_set
  FROM complaints WHERE title = 'Big pothole near bus stop';

SELECT 'live clustering of all DB complaints' AS step, work_type_code, count(DISTINCT cluster_key) AS clusters,
       count(*) AS jobs, max(cluster_size) AS max_jobs_per_cluster
  FROM fn_cluster_jobs((SELECT array_agg(complaint_id) FROM complaints WHERE is_synthetic))
 GROUP BY work_type_code ORDER BY work_type_code;

SELECT 'synthetic rows untouched' AS step, count(*) AS rows, count(*) FILTER (WHERE status = 'SUBMITTED') AS still_submitted,
       count(*) FILTER (WHERE is_synthetic) AS flagged_synthetic
  FROM complaints WHERE is_synthetic;

ROLLBACK;
