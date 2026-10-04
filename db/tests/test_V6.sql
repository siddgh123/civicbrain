-- =============================================================================
-- CivicBrain | db/tests/test_V6.sql - tests for V6__citizen_selectable_categories.sql
-- One transaction, own data only, ROLLBACK at the end (the database is left unchanged).
--   pgAdmin: open, F5, read the Messages tab.   psql: psql -d civicbrain_test -f test_V6.sql
-- =============================================================================
BEGIN;

DO $$
DECLARE
    v_ok int := 0;
    v_n int;
    v_cit bigint;
    v_cid bigint;
    v_comment text;
BEGIN
    -- 1. exactly the 3 categories are hidden from citizens
    SELECT count(*) INTO v_n FROM complaint_categories
     WHERE NOT citizen_selectable AND category_name IN ('Water Leakage', 'Blocked Drain', 'Streetlight');
    IF v_n = 3 THEN v_ok := v_ok + 1; RAISE NOTICE 'PASS 1 Water Leakage, Blocked Drain, Streetlight not citizen-selectable';
    ELSE RAISE NOTICE 'FAIL 1 hidden categories: % of 3', v_n; END IF;

    -- 2. the 5 MVP categories stay selectable, and nothing else is selectable
    SELECT count(*) INTO v_n FROM complaint_categories
     WHERE citizen_selectable AND category_name IN ('Pothole', 'Road Damage', 'Waterlogging', 'Garbage Accumulation', 'Other');
    IF v_n = 5 AND (SELECT count(*) FROM complaint_categories WHERE citizen_selectable) = 5 THEN
        v_ok := v_ok + 1; RAISE NOTICE 'PASS 2 exactly the 5 MVP categories are citizen-selectable';
    ELSE RAISE NOTICE 'FAIL 2 selectable MVP categories: % of 5', v_n; END IF;

    -- 3. nothing deleted: the 8 categories of the data model are still there and active
    SELECT count(*) INTO v_n FROM complaint_categories WHERE is_active;
    IF v_n = 8 THEN v_ok := v_ok + 1; RAISE NOTICE 'PASS 3 still 8 active categories';
    ELSE RAISE NOTICE 'FAIL 3 active categories: %', v_n; END IF;

    -- 4. no rename, no work-type or YOLO-class change for the hidden ones (frozen mapping, V2)
    SELECT count(*) INTO v_n FROM complaint_categories
     WHERE (category_name, work_type_code) IN (('Water Leakage', 'WATER'), ('Blocked Drain', 'WATER'), ('Streetlight', 'ELECTRICITY'))
       AND yolo_class_id IS NULL;
    IF v_n = 3 THEN v_ok := v_ok + 1; RAISE NOTICE 'PASS 4 hidden categories keep their work type and have no YOLO class';
    ELSE RAISE NOTICE 'FAIL 4 work type / YOLO class changed (% of 3 unchanged)', v_n; END IF;

    -- 5. the database still accepts a complaint in a hidden category (existing and synthetic rows stay valid;
    --    only the citizen API refuses new ones) and it keeps its work type for the officer
    INSERT INTO users (full_name, email, password_hash, role, email_verified_at)
    VALUES ('V6 Citizen', 'v6.citizen@test.local', 'x', 'CITIZEN', now()) RETURNING user_id INTO v_cit;
    PERFORM set_config('civicbrain.actor_user_id', v_cit::text, true);
    PERFORM set_config('civicbrain.actor_role', 'CITIZEN', true);
    INSERT INTO complaints (user_id, category_id, title, description, location)
    VALUES (v_cit, (SELECT category_id FROM complaint_categories WHERE category_name = 'Streetlight'),
            'V6 streetlight', 'V6 existing streetlight complaint', ST_SetSRID(ST_MakePoint(73.6760, 18.7440), 4326))
    RETURNING complaint_id INTO v_cid;
    PERFORM set_config('civicbrain.actor_user_id', '', true);
    PERFORM set_config('civicbrain.actor_role', 'SYSTEM', true);
    SELECT count(*) INTO v_n FROM complaints c JOIN complaint_categories cc ON cc.category_id = c.category_id
     WHERE c.complaint_id = v_cid AND cc.category_name = 'Streetlight' AND cc.work_type_code = 'ELECTRICITY';
    IF v_n = 1 THEN v_ok := v_ok + 1; RAISE NOTICE 'PASS 5 a complaint in a hidden category is still stored with its work type';
    ELSE RAISE NOTICE 'FAIL 5 complaint in a hidden category not found with its work type'; END IF;

    -- 6. idempotent: the migration's UPDATE run again changes no row
    UPDATE complaint_categories SET citizen_selectable = false
     WHERE category_name IN ('Water Leakage', 'Blocked Drain', 'Streetlight') AND citizen_selectable;
    GET DIAGNOSTICS v_n = ROW_COUNT;
    IF v_n = 0 THEN v_ok := v_ok + 1; RAISE NOTICE 'PASS 6 re-running the V6 update changes nothing';
    ELSE RAISE NOTICE 'FAIL 6 re-run changed % rows', v_n; END IF;

    -- 7. the column says what false means
    SELECT col_description('complaint_categories'::regclass,
                           (SELECT attnum FROM pg_attribute
                             WHERE attrelid = 'complaint_categories'::regclass AND attname = 'citizen_selectable'))
      INTO v_comment;
    IF v_comment LIKE '%V6%' THEN v_ok := v_ok + 1; RAISE NOTICE 'PASS 7 citizen_selectable column comment explains V6';
    ELSE RAISE NOTICE 'FAIL 7 column comment missing'; END IF;

    RAISE NOTICE 'V6 TESTS PASSED: % / 7', v_ok;
END $$;

ROLLBACK;
