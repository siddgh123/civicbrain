-- =============================================================================
-- CivicBrain | test_V4.sql  - tests for V4 (run after V2 + V3 + V4). Rolls back.
--   psql -d civicbrain -f test_V4.sql      (pgAdmin: read the Messages tab)
-- =============================================================================
BEGIN;

DO $$
DECLARE
    v_uid bigint; v_cid bigint; v_job jobs%ROWTYPE; v_state text; v_ok int := 0; v_n int;
BEGIN
    -- citizen
    INSERT INTO users (full_name, email, phone, password_hash, role)
    VALUES ('V4 Tester', 'v4@test.local', '+919000000099', '$argon2id$dummy', 'CITIZEN')
    RETURNING user_id INTO v_uid;

    -- 1. a real complaint enqueues exactly one ANALYZE_COMPLAINT job
    PERFORM set_config('civicbrain.actor_role', 'CITIZEN', true);
    INSERT INTO complaints (user_id, category_id, title, description, location)
    VALUES (v_uid, 1, 'V4 pothole', 'test', ST_SetSRID(ST_MakePoint(73.676, 18.744), 4326))
    RETURNING complaint_id INTO v_cid;
    SELECT count(*) INTO v_n FROM jobs WHERE job_type = 'ANALYZE_COMPLAINT' AND ref_id = v_cid AND status = 'QUEUED';
    IF v_n = 1 THEN v_ok := v_ok + 1; RAISE NOTICE 'PASS 1 job enqueued on insert';
    ELSE RAISE NOTICE 'FAIL 1 expected 1 job, got %', v_n; END IF;

    -- 2. synthetic complaints are not enqueued
    INSERT INTO complaints (user_id, category_id, title, description, location, is_synthetic)
    VALUES (v_uid, 1, 'V4 synthetic', 'test', ST_SetSRID(ST_MakePoint(73.676, 18.744), 4326), true);
    SELECT count(*) INTO v_n FROM jobs j JOIN complaints c ON c.complaint_id = j.ref_id WHERE c.title = 'V4 synthetic';
    IF v_n = 0 THEN v_ok := v_ok + 1; RAISE NOTICE 'PASS 2 synthetic not enqueued';
    ELSE RAISE NOTICE 'FAIL 2 synthetic enqueued'; END IF;

    -- 3. claim -> fail -> requeued with backoff -> claim again -> fail x2 -> DEAD
    SELECT * INTO v_job FROM fn_claim_jobs('worker-a', ARRAY['ANALYZE_COMPLAINT'], 10) WHERE ref_id = v_cid;
    SELECT fn_finish_job(v_job.job_id, false, 'boom 1') INTO v_state;
    IF v_state = 'QUEUED' AND (SELECT run_after > now() FROM jobs WHERE job_id = v_job.job_id) THEN
        v_ok := v_ok + 1; RAISE NOTICE 'PASS 3 failed job requeued with backoff';
    ELSE RAISE NOTICE 'FAIL 3 state %', v_state; END IF;

    UPDATE jobs SET run_after = now() WHERE job_id = v_job.job_id;
    PERFORM fn_claim_jobs('worker-a', ARRAY['ANALYZE_COMPLAINT'], 10);
    PERFORM fn_finish_job(v_job.job_id, false, 'boom 2');
    UPDATE jobs SET run_after = now() WHERE job_id = v_job.job_id;
    PERFORM fn_claim_jobs('worker-a', ARRAY['ANALYZE_COMPLAINT'], 10);
    SELECT fn_finish_job(v_job.job_id, false, 'boom 3') INTO v_state;
    IF v_state = 'DEAD' THEN v_ok := v_ok + 1; RAISE NOTICE 'PASS 4 job DEAD after max attempts';
    ELSE RAISE NOTICE 'FAIL 4 state %', v_state; END IF;

    -- 5. a new job for the same complaint is allowed once the old one is DEAD; duplicates while active are not
    INSERT INTO jobs (job_type, ref_id) VALUES ('ANALYZE_COMPLAINT', v_cid);
    BEGIN
        INSERT INTO jobs (job_type, ref_id) VALUES ('ANALYZE_COMPLAINT', v_cid);
        RAISE NOTICE 'FAIL 5 duplicate active job accepted';
    EXCEPTION WHEN unique_violation THEN v_ok := v_ok + 1; RAISE NOTICE 'PASS 5 one active job per complaint';
    END;

    -- 6. stale RUNNING job is requeued
    UPDATE jobs SET status = 'RUNNING', locked_by = 'dead-worker', locked_at = now() - interval '1 hour'
     WHERE job_type = 'ANALYZE_COMPLAINT' AND ref_id = v_cid AND status = 'QUEUED';
    IF fn_requeue_stale_jobs() >= 1 THEN v_ok := v_ok + 1; RAISE NOTICE 'PASS 6 stale job requeued';
    ELSE RAISE NOTICE 'FAIL 6'; END IF;

    -- 7. consent history: latest decision wins
    INSERT INTO user_consents (user_id, consent_type, granted, notice_version) VALUES (v_uid, 'PUBLIC_PHOTO', true, '2026-10-v1');
    INSERT INTO user_consents (user_id, consent_type, granted, notice_version) VALUES (v_uid, 'PUBLIC_PHOTO', false, '2026-10-v1');
    IF (SELECT granted FROM v_current_consents WHERE user_id = v_uid AND consent_type = 'PUBLIC_PHOTO') = false THEN
        v_ok := v_ok + 1; RAISE NOTICE 'PASS 7 withdrawn consent is current';
    ELSE RAISE NOTICE 'FAIL 7'; END IF;

    -- 8. a photo cannot be public without blur + approval
    INSERT INTO complaint_images (complaint_id, file_url) VALUES (v_cid, 'local:test.jpg');
    BEGIN
        UPDATE complaint_images SET public_approved = true WHERE complaint_id = v_cid;
        RAISE NOTICE 'FAIL 8 unblurred photo made public';
    EXCEPTION WHEN check_violation THEN v_ok := v_ok + 1; RAISE NOTICE 'PASS 8 public photo needs blur + approval';
    END;

    -- 9. TOTP cannot be enabled without a secret
    BEGIN
        UPDATE users SET totp_enabled = true WHERE user_id = v_uid;
        RAISE NOTICE 'FAIL 9 totp enabled without secret';
    EXCEPTION WHEN check_violation THEN v_ok := v_ok + 1; RAISE NOTICE 'PASS 9 TOTP needs a secret';
    END;

    -- 10. public map has no personal columns and snaps location
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'v_public_complaint_map'
                      AND column_name IN ('user_id','description','title','location'))
       AND (SELECT latitude FROM v_public_complaint_map WHERE public_ref = (SELECT public_ref FROM complaints WHERE complaint_id = v_cid)) = 18.744 THEN
        v_ok := v_ok + 1; RAISE NOTICE 'PASS 10 public map anonymised and snapped';
    ELSE RAISE NOTICE 'FAIL 10'; END IF;

    -- 11. purge runs
    IF (SELECT count(*) FROM fn_purge_expired()) = 5 THEN v_ok := v_ok + 1; RAISE NOTICE 'PASS 11 purge function runs';
    ELSE RAISE NOTICE 'FAIL 11'; END IF;

    RAISE NOTICE 'V4 TESTS PASSED: % / 11', v_ok;
END $$;

ROLLBACK;
