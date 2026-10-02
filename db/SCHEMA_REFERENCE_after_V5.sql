-- =============================================================================
-- CivicBrain | db/SCHEMA_REFERENCE_after_V5.sql - READ-ONLY REFERENCE, do not run.
-- Full schema (tables, constraints, functions, triggers, views) after V1..V5, made with
-- pg_dump --schema-only --no-owner --no-privileges from a fresh database built from flyway/.
-- Grants are in R__civicbrain_grants.sql. Regenerate after every new migration.
-- =============================================================================
--
-- PostgreSQL database dump
--


-- Dumped from database version 16.13 (Ubuntu 16.13-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.13 (Ubuntu 16.13-0ubuntu0.24.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: postgis; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;


--
-- Name: EXTENSION postgis; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION postgis IS 'PostGIS geometry and geography spatial types and functions';


--
-- Name: fn_approve_action_plan(bigint, bigint); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_approve_action_plan(p_action_plan_id bigint, p_officer_user_id bigint) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_status  text;
    v_count   integer;
    v_blocked bigint;
BEGIN
    SELECT status INTO v_status FROM action_plans WHERE action_plan_id = p_action_plan_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Action plan % not found', p_action_plan_id;
    END IF;
    IF v_status <> 'DRAFT' THEN
        RAISE EXCEPTION 'Only DRAFT plans can be approved (plan % is %)', p_action_plan_id, v_status;
    END IF;

    SELECT i.complaint_id INTO v_blocked
      FROM action_plan_items i JOIN complaints c ON c.complaint_id = i.complaint_id
     WHERE i.action_plan_id = p_action_plan_id AND i.item_status = 'ACTIVE'
       AND (c.status NOT IN ('VERIFIED','REOPENED')
            OR (c.current_action_plan_id IS NOT NULL AND c.current_action_plan_id <> p_action_plan_id))
     LIMIT 1;
    IF v_blocked IS NOT NULL THEN
        RAISE EXCEPTION 'Complaint % is not free for planning (wrong status or already in another plan)', v_blocked;
    END IF;

    PERFORM set_config('civicbrain.actor_user_id', p_officer_user_id::text, true);
    PERFORM set_config('civicbrain.actor_role', 'OFFICER', true);

    UPDATE complaints c
       SET status = 'SCHEDULED', current_action_plan_id = p_action_plan_id
      FROM action_plan_items i
     WHERE i.action_plan_id = p_action_plan_id AND i.item_status = 'ACTIVE'
       AND c.complaint_id = i.complaint_id;
    GET DIAGNOSTICS v_count = ROW_COUNT;

    UPDATE action_plans
       SET status = 'APPROVED', approved_by_user_id = p_officer_user_id, approved_at = now(), job_count = v_count
     WHERE action_plan_id = p_action_plan_id;
    RETURN v_count;
END $$;


--
-- Name: fn_assign_action_plan(bigint, bigint, bigint); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_assign_action_plan(p_action_plan_id bigint, p_contractor_id bigint, p_officer_user_id bigint) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_status    text;
    v_work_type text;
    v_count     integer;
BEGIN
    SELECT status, work_type_code INTO v_status, v_work_type
      FROM action_plans WHERE action_plan_id = p_action_plan_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Action plan % not found', p_action_plan_id;
    END IF;
    IF v_status <> 'APPROVED' THEN
        RAISE EXCEPTION 'Plan % must be APPROVED before assignment (is %)', p_action_plan_id, v_status;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM contractors WHERE contractor_id = p_contractor_id AND status = 'ACTIVE') THEN
        RAISE EXCEPTION 'Contractor % is not active', p_contractor_id;
    END IF;
    IF v_work_type IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM contractor_work_types WHERE contractor_id = p_contractor_id AND work_type_code = v_work_type) THEN
        RAISE EXCEPTION 'Contractor % is not registered for work type %', p_contractor_id, v_work_type;
    END IF;

    PERFORM set_config('civicbrain.actor_user_id', p_officer_user_id::text, true);
    PERFORM set_config('civicbrain.actor_role', 'OFFICER', true);

    UPDATE action_plans
       SET contractor_id = p_contractor_id, status = 'ASSIGNED',
           assigned_by_user_id = p_officer_user_id, assigned_at = now()
     WHERE action_plan_id = p_action_plan_id;

    UPDATE complaints c
       SET status = 'ASSIGNED', assigned_contractor_id = p_contractor_id
      FROM action_plan_items i
     WHERE i.action_plan_id = p_action_plan_id AND i.item_status = 'ACTIVE'
       AND c.complaint_id = i.complaint_id AND c.status = 'SCHEDULED';
    GET DIAGNOSTICS v_count = ROW_COUNT;

    INSERT INTO notification_outbox (event_type, action_plan_id, payload)
    VALUES ('ACTION_PLAN_ASSIGNED', p_action_plan_id,
            jsonb_build_object('contractor_id', p_contractor_id, 'complaints_assigned', v_count));
    RETURN v_count;
END $$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.jobs (
    job_id bigint NOT NULL,
    job_type character varying(40) NOT NULL,
    ref_id bigint NOT NULL,
    payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    status character varying(20) DEFAULT 'QUEUED'::character varying NOT NULL,
    priority smallint DEFAULT 100 NOT NULL,
    attempts integer DEFAULT 0 NOT NULL,
    max_attempts integer DEFAULT 3 NOT NULL,
    run_after timestamp with time zone DEFAULT now() NOT NULL,
    locked_by text,
    locked_at timestamp with time zone,
    last_error text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    finished_at timestamp with time zone,
    CONSTRAINT ck_jobs_attempts CHECK (((attempts >= 0) AND (max_attempts > 0))),
    CONSTRAINT ck_jobs_status CHECK (((status)::text = ANY ((ARRAY['QUEUED'::character varying, 'RUNNING'::character varying, 'SUCCEEDED'::character varying, 'FAILED'::character varying, 'DEAD'::character varying])::text[]))),
    CONSTRAINT ck_jobs_type CHECK (((job_type)::text = ANY ((ARRAY['ANALYZE_COMPLAINT'::character varying, 'ANALYZE_IMAGE'::character varying, 'OPTIMIZE_PLAN'::character varying, 'BLUR_IMAGE'::character varying, 'RENDER_EXPORT'::character varying])::text[])))
);


--
-- Name: fn_claim_jobs(text, text[], integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_claim_jobs(p_worker text, p_types text[], p_limit integer DEFAULT 1) RETURNS SETOF public.jobs
    LANGUAGE sql
    AS $$
    UPDATE jobs j
       SET status = 'RUNNING', locked_by = p_worker, locked_at = now(), attempts = j.attempts + 1
     WHERE j.job_id IN (SELECT q.job_id
                          FROM jobs q
                         WHERE q.status = 'QUEUED'
                           AND q.run_after <= now()
                           AND q.job_type = ANY (p_types)
                         ORDER BY q.priority, q.run_after, q.job_id
                         LIMIT p_limit
                         FOR UPDATE SKIP LOCKED)
    RETURNING j.*;
$$;


--
-- Name: fn_cluster_jobs(bigint[], double precision, integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_cluster_jobs(p_complaint_ids bigint[], p_max_diameter_m double precision DEFAULT 2000, p_max_jobs integer DEFAULT 10) RETURNS TABLE(complaint_id bigint, work_type_code character varying, cluster_key text, cluster_size integer)
    LANGUAGE sql STABLE
    AS $$
    WITH sel AS (
        SELECT c.complaint_id, cat.work_type_code AS wt, ST_Transform(c.location, 32643) AS g
          FROM complaints c
          JOIN complaint_categories cat ON cat.category_id = c.category_id
         WHERE c.complaint_id = ANY (p_complaint_ids)
           AND cat.work_type_code IS NOT NULL
           AND cat.work_type_code <> 'REVIEW_REQUIRED'
    ), d AS (
        SELECT sel.*, ST_ClusterDBSCAN(sel.g, eps => p_max_diameter_m, minpoints => 1)
                        OVER (PARTITION BY sel.wt ORDER BY sel.complaint_id) AS c1   -- ORDER BY = deterministic
          FROM sel
    ), n AS (
        SELECT d.*, count(*) OVER (PARTITION BY d.wt, d.c1) AS n1 FROM d
    ), k AS (
        SELECT n.*, ST_ClusterKMeans(n.g, GREATEST(1, ceil(n.n1::numeric / p_max_jobs))::integer,
                                     p_max_diameter_m / 2.0)
                      OVER (PARTITION BY n.wt, n.c1 ORDER BY n.complaint_id) AS c2   -- K-means seeds depend on input order
          FROM n
    ), s AS (
        SELECT k.*, (row_number() OVER (PARTITION BY k.wt, k.c1, k.c2 ORDER BY k.complaint_id) - 1) / p_max_jobs AS c3
          FROM k
    )
    SELECT s.complaint_id, s.wt,
           s.wt || '-' || s.c1 || '-' || s.c2 || '-' || s.c3,
           (count(*) OVER (PARTITION BY s.wt, s.c1, s.c2, s.c3))::integer
      FROM s;
$$;


--
-- Name: fn_complaint_notification_recipients(bigint); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_complaint_notification_recipients(p_complaint_id bigint) RETURNS TABLE(user_id bigint, complaint_id bigint, relation text)
    LANGUAGE sql STABLE
    AS $$
    SELECT c.user_id, c.complaint_id, 'OWNER'::text
      FROM complaints c
     WHERE c.complaint_id = p_complaint_id
    UNION
    SELECT ch.user_id, ch.complaint_id, 'MERGED_CHILD_OWNER'::text
      FROM complaints ch
     WHERE ch.master_complaint_id = p_complaint_id
       AND ch.status = 'MERGED';
$$;


--
-- Name: fn_complaint_status_guard(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_complaint_status_guard() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_role    text := nullif(current_setting('civicbrain.actor_role', true), '');
    v_allowed text[];
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.status <> 'SUBMITTED' AND NOT NEW.is_synthetic THEN
            RAISE EXCEPTION 'New complaints must start in SUBMITTED (got %)', NEW.status
                USING ERRCODE = 'check_violation';
        END IF;
        RETURN NEW;
    END IF;

    IF NEW.status IS NOT DISTINCT FROM OLD.status THEN
        RETURN NEW;
    END IF;

    SELECT t.allowed_roles INTO v_allowed
      FROM complaint_status_transitions t
     WHERE t.from_status = OLD.status AND t.to_status = NEW.status;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Invalid complaint status transition % -> % (complaint %)',
            OLD.status, NEW.status, OLD.complaint_id USING ERRCODE = 'check_violation';
    END IF;

    IF v_role IS NOT NULL AND NOT (v_role = ANY (v_allowed)) THEN
        RAISE EXCEPTION 'Role % may not move complaint % from % to %',
            v_role, OLD.complaint_id, OLD.status, NEW.status USING ERRCODE = 'insufficient_privilege';
    END IF;

    IF NEW.status = 'CLOSED' THEN
        NEW.closed_at := now();
    ELSIF NEW.status = 'REOPENED' THEN
        NEW.closed_at := NULL;
    END IF;
    RETURN NEW;
END $$;


--
-- Name: fn_complaint_status_log(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_complaint_status_log() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_actor   bigint := nullif(current_setting('civicbrain.actor_user_id', true), '')::bigint;
    v_role    text   := nullif(current_setting('civicbrain.actor_role', true), '');
    v_remarks text   := nullif(current_setting('civicbrain.status_remarks', true), '');
    v_old     text;
    v_notify  boolean := true;
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF NEW.status IS NOT DISTINCT FROM OLD.status THEN
            RETURN NULL;
        END IF;
        v_old := OLD.status;
        SELECT t.notify_citizen INTO v_notify
          FROM complaint_status_transitions t
         WHERE t.from_status = OLD.status AND t.to_status = NEW.status;
    END IF;

    INSERT INTO complaint_status_history (complaint_id, old_status, new_status, changed_by, remarks, actor_role, source, changed_at)
    VALUES (NEW.complaint_id, v_old, NEW.status, v_actor, v_remarks, v_role,
            CASE WHEN v_role = 'SYSTEM' THEN 'SYSTEM' ELSE 'WEB' END,
            clock_timestamp());   -- real time, so several changes in one transaction keep their order

    IF coalesce(v_notify, true) AND NOT NEW.is_synthetic THEN
        INSERT INTO notification_outbox (event_type, complaint_id, action_plan_id, event_status, payload)
        VALUES ('COMPLAINT_STATUS_CHANGED', NEW.complaint_id, NEW.current_action_plan_id, NEW.status,
                jsonb_build_object('old_status', v_old,
                                   'new_status', NEW.status,
                                   'public_ref', NEW.public_ref,
                                   'actor_role', v_role,
                                   'remarks', v_remarks,
                                   'contractor_id', NEW.assigned_contractor_id,
                                   'master_complaint_id', NEW.master_complaint_id));
    END IF;
    RETURN NULL;
END $$;


--
-- Name: fn_complaint_status_release_plan(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_complaint_status_release_plan() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND NEW.status IS DISTINCT FROM OLD.status THEN
        IF NEW.status = 'VERIFIED' AND OLD.status IN ('SCHEDULED', 'ASSIGNED', 'INSPECTED')
           AND OLD.current_action_plan_id IS NOT NULL THEN
            UPDATE action_plan_items
               SET item_status = 'REMOVED',
                   drop_reason = coalesce(drop_reason, 'Removed from the plan: complaint returned to ' || NEW.status)
             WHERE action_plan_id = OLD.current_action_plan_id
               AND complaint_id = NEW.complaint_id
               AND item_status = 'ACTIVE';
        END IF;
        IF NEW.status = 'REOPENED' AND OLD.current_action_plan_id IS NOT NULL THEN
            UPDATE action_plan_items i
               SET item_status = 'REMOVED',
                   drop_reason = coalesce(i.drop_reason, 'Reopened before the plan finished; will be re-planned')
             WHERE i.action_plan_id = OLD.current_action_plan_id
               AND i.complaint_id = NEW.complaint_id
               AND i.item_status = 'ACTIVE'
               AND EXISTS (SELECT 1 FROM action_plans p
                            WHERE p.action_plan_id = OLD.current_action_plan_id
                              AND p.status IN ('ASSIGNED', 'IN_PROGRESS'));
        END IF;
        IF NEW.status = 'REOPENED'
           OR (NEW.status = 'VERIFIED' AND OLD.status IN ('SCHEDULED', 'ASSIGNED', 'INSPECTED')) THEN
            NEW.current_action_plan_id := NULL;
            NEW.assigned_contractor_id := NULL;
        END IF;
    END IF;
    RETURN NEW;
END $$;


--
-- Name: fn_duplicate_candidates(bigint); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_duplicate_candidates(p_complaint_id bigint) RETURNS TABLE(candidate_id bigint, distance_m double precision, hours_apart double precision, same_work_type boolean, candidate_status character varying)
    LANGUAGE sql STABLE
    AS $$
    SELECT o.complaint_id,
           ST_Distance(c.location::geography, o.location::geography),
           extract(epoch FROM (c.submitted_at - o.submitted_at)) / 3600.0,
           (co.work_type_code IS NOT DISTINCT FROM oc.work_type_code),
           o.status
      FROM complaints c
      JOIN complaints o
        ON o.complaint_id <> c.complaint_id
       AND o.master_complaint_id IS NULL
       AND o.status NOT IN ('REJECTED','MERGED')
       AND o.submitted_at BETWEEN c.submitted_at - interval '7 days' AND c.submitted_at
       AND ST_DWithin(c.location::geography, o.location::geography, 300)
      LEFT JOIN complaint_categories co ON co.category_id = c.category_id
      LEFT JOIN complaint_categories oc ON oc.category_id = o.category_id
     WHERE c.complaint_id = p_complaint_id
     ORDER BY 2;
$$;


--
-- Name: fn_enqueue_complaint_analysis(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_enqueue_complaint_analysis() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NOT NEW.is_synthetic THEN
        INSERT INTO jobs (job_type, ref_id, priority)
        VALUES ('ANALYZE_COMPLAINT', NEW.complaint_id, 50)
        ON CONFLICT (job_type, ref_id) WHERE status IN ('QUEUED','RUNNING') DO NOTHING;
    END IF;
    RETURN NULL;
END $$;


--
-- Name: fn_enqueue_optimizer_run(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_enqueue_optimizer_run() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.status = 'QUEUED' THEN
        INSERT INTO jobs (job_type, ref_id, priority)
        VALUES ('OPTIMIZE_PLAN', NEW.run_id, 20)
        ON CONFLICT (job_type, ref_id) WHERE status IN ('QUEUED','RUNNING') DO NOTHING;
    END IF;
    RETURN NULL;
END $$;


--
-- Name: fn_finish_job(bigint, boolean, text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_finish_job(p_job_id bigint, p_success boolean, p_error text DEFAULT NULL::text) RETURNS character varying
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_job jobs%ROWTYPE;
    v_new varchar;
BEGIN
    SELECT * INTO v_job FROM jobs WHERE job_id = p_job_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Job % not found', p_job_id;
    END IF;
    IF v_job.status <> 'RUNNING' THEN
        RAISE EXCEPTION 'Job % is % (only RUNNING jobs can be finished)', p_job_id, v_job.status;
    END IF;
    IF p_success THEN
        v_new := 'SUCCEEDED';
        UPDATE jobs SET status = v_new, finished_at = now(), last_error = NULL, locked_by = NULL, locked_at = NULL
         WHERE job_id = p_job_id;
    ELSIF v_job.attempts >= v_job.max_attempts THEN
        v_new := 'DEAD';
        UPDATE jobs SET status = v_new, finished_at = now(), last_error = left(p_error, 4000), locked_by = NULL, locked_at = NULL
         WHERE job_id = p_job_id;
    ELSE
        v_new := 'QUEUED';
        UPDATE jobs SET status = v_new, last_error = left(p_error, 4000), locked_by = NULL, locked_at = NULL,
                        run_after = now() + interval '1 minute' * power(5, v_job.attempts - 1)
         WHERE job_id = p_job_id;
    END IF;
    RETURN v_new;
END $$;


--
-- Name: fn_locate_point(double precision, double precision); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_locate_point(p_lat double precision, p_lon double precision) RETURNS TABLE(inside_boundary boolean, ward_id bigint, ward_match text, road_id bigint, road_distance_m double precision, poi_id bigint, poi_distance_m double precision)
    LANGUAGE sql STABLE
    AS $$
    WITH p AS (SELECT ST_SetSRID(ST_MakePoint(p_lon, p_lat), 4326) AS g)
    SELECT
        EXISTS (SELECT 1 FROM municipal_boundary b
                 WHERE b.status IN ('VERIFIED','ACTIVE') AND ST_Covers(b.geometry, p.g)),
        w.ward_id, w.match,
        r.road_id, r.dist,
        q.poi_id,  q.dist
    FROM p
    LEFT JOIN LATERAL (
        SELECT x.ward_id,
               CASE WHEN ST_Covers(x.geometry, p.g) THEN 'CONTAINS' ELSE 'NEAREST' END AS match
          FROM wards x
         ORDER BY ST_Covers(x.geometry, p.g) DESC,          -- containing wards first
                  ST_Distance(x.geometry, p.g) ASC,
                  ST_Area(x.geometry) ASC                   -- overlapping wards: smallest wins
         LIMIT 1) w ON true
    LEFT JOIN LATERAL (
        SELECT rd.road_id, ST_Distance(rd.geometry::geography, p.g::geography) AS dist
          FROM roads rd ORDER BY rd.geometry <-> p.g LIMIT 1) r ON true
    LEFT JOIN LATERAL (
        SELECT pi.poi_id, ST_Distance(pi.geometry::geography, p.g::geography) AS dist
          FROM pois pi ORDER BY pi.geometry <-> p.g LIMIT 1) q ON true;
$$;


--
-- Name: fn_phash_distance(bigint, bigint); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_phash_distance(a bigint, b bigint) RETURNS integer
    LANGUAGE sql IMMUTABLE STRICT
    AS $$
    SELECT bit_count((a # b)::bit(64))::integer;
$$;


--
-- Name: fn_purge_expired(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_purge_expired() RETURNS TABLE(item text, deleted bigint)
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
DECLARE n bigint;
BEGIN
    DELETE FROM auth_otp_codes WHERE created_at < now() - interval '30 days';
    GET DIAGNOSTICS n = ROW_COUNT; item := 'auth_otp_codes > 30 d'; deleted := n; RETURN NEXT;

    DELETE FROM auth_refresh_tokens WHERE expires_at < now() - interval '30 days';
    GET DIAGNOSTICS n = ROW_COUNT; item := 'expired refresh tokens > 30 d'; deleted := n; RETURN NEXT;

    DELETE FROM capture_sessions WHERE issued_at < now() - interval '7 days' AND used_at IS NULL;
    GET DIAGNOSTICS n = ROW_COUNT; item := 'unused capture sessions > 7 d'; deleted := n; RETURN NEXT;

    DELETE FROM jobs WHERE status = 'SUCCEEDED' AND finished_at < now() - interval '90 days';
    GET DIAGNOSTICS n = ROW_COUNT; item := 'succeeded jobs > 90 d'; deleted := n; RETURN NEXT;

    DELETE FROM auth_events WHERE created_at < now() - interval '365 days';
    GET DIAGNOSTICS n = ROW_COUNT; item := 'auth events > 365 d'; deleted := n; RETURN NEXT;
END $$;


--
-- Name: fn_requeue_stale_jobs(interval); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_requeue_stale_jobs(p_stale interval DEFAULT '00:15:00'::interval) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE v_count integer;
BEGIN
    UPDATE jobs SET status = CASE WHEN attempts >= max_attempts THEN 'DEAD' ELSE 'QUEUED' END,
                    locked_by = NULL, locked_at = NULL,
                    last_error = coalesce(last_error, '') || ' [requeued: stale lock]'
     WHERE status = 'RUNNING' AND locked_at < now() - p_stale;
    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END $$;


--
-- Name: fn_set_distance_from_complaint(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_set_distance_from_complaint() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_point geometry;
BEGIN
    IF TG_TABLE_NAME = 'site_inspections' THEN
        v_point := NEW.inspector_location;
    ELSE
        v_point := NEW.completion_location;
    END IF;
    IF v_point IS NOT NULL THEN
        SELECT ST_Distance(c.location::geography, v_point::geography)
          INTO NEW.distance_from_complaint_m
          FROM complaints c WHERE c.complaint_id = NEW.complaint_id;
    END IF;
    RETURN NEW;
END $$;


--
-- Name: fn_similar_images(bigint, integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_similar_images(p_image_id bigint, p_max_bits integer DEFAULT 10) RETURNS TABLE(image_id bigint, complaint_id bigint, image_role character varying, hamming_bits integer, same_complaint boolean, distance_m double precision)
    LANGUAGE sql STABLE
    AS $$
    SELECT o.image_id, o.complaint_id, o.image_role,
           fn_phash_distance(i.phash, o.phash),
           o.complaint_id = i.complaint_id,
           ST_Distance(ci.location::geography, co.location::geography)
      FROM complaint_images i
      JOIN complaints ci       ON ci.complaint_id = i.complaint_id
      JOIN complaint_images o  ON o.image_id <> i.image_id AND o.phash IS NOT NULL
      JOIN complaints co       ON co.complaint_id = o.complaint_id
     WHERE i.image_id = p_image_id
       AND i.phash IS NOT NULL
       AND fn_phash_distance(i.phash, o.phash) <= p_max_bits
     ORDER BY 4, 6;
$$;


--
-- Name: set_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.set_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


--
-- Name: action_plan_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.action_plan_items (
    item_id bigint NOT NULL,
    action_plan_id bigint NOT NULL,
    complaint_id bigint NOT NULL,
    sequence_no integer NOT NULL,
    item_status character varying(25) DEFAULT 'ACTIVE'::character varying NOT NULL,
    planned_start timestamp without time zone,
    planned_end timestamp without time zone,
    service_duration_h numeric(8,3),
    travel_from_prev_km numeric(10,3),
    travel_from_prev_min numeric(10,2),
    est_workers numeric(6,2),
    est_cost numeric(12,2),
    priority_score numeric(6,2),
    drop_reason text,
    CONSTRAINT ck_action_plan_item_seq CHECK ((sequence_no > 0)),
    CONSTRAINT ck_action_plan_item_status CHECK (((item_status)::text = ANY ((ARRAY['ACTIVE'::character varying, 'REMOVED'::character varying, 'DROPPED_BY_OPTIMIZER'::character varying])::text[]))),
    CONSTRAINT ck_action_plan_item_times CHECK (((planned_start IS NULL) OR (planned_end IS NULL) OR (planned_end > planned_start)))
);


--
-- Name: action_plan_items_item_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.action_plan_items ALTER COLUMN item_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.action_plan_items_item_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: action_plan_revisions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.action_plan_revisions (
    revision_id bigint NOT NULL,
    action_plan_id bigint NOT NULL,
    version integer NOT NULL,
    changed_by bigint,
    change_summary text,
    snapshot jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: action_plan_revisions_revision_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.action_plan_revisions ALTER COLUMN revision_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.action_plan_revisions_revision_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: action_plans; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.action_plans (
    action_plan_id bigint NOT NULL,
    plan_code character varying(60) NOT NULL,
    work_type_code character varying(30),
    planned_date date NOT NULL,
    status character varying(20) DEFAULT 'DRAFT'::character varying NOT NULL,
    depot_id character varying(20),
    contractor_id bigint,
    optimizer_run_id bigint,
    generation_source character varying(20) DEFAULT 'OPTIMIZER'::character varying NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    job_count integer DEFAULT 0 NOT NULL,
    total_workers numeric(8,2),
    est_service_hours numeric(10,3),
    est_travel_hours numeric(10,3),
    total_distance_km numeric(12,3),
    est_total_cost numeric(14,2),
    planned_start time without time zone,
    planned_end time without time zone,
    route_geometry public.geometry(Geometry,4326),
    notes text,
    export_pdf_key text,
    export_xlsx_key text,
    created_by_user_id bigint,
    approved_by_user_id bigint,
    approved_at timestamp with time zone,
    assigned_by_user_id bigint,
    assigned_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_action_plans_assigned CHECK ((((status)::text <> ALL ((ARRAY['ASSIGNED'::character varying, 'IN_PROGRESS'::character varying, 'COMPLETED'::character varying])::text[])) OR (contractor_id IS NOT NULL))),
    CONSTRAINT ck_action_plans_numbers CHECK (((job_count >= 0) AND (version >= 1) AND ((est_total_cost IS NULL) OR (est_total_cost >= (0)::numeric)) AND ((total_distance_km IS NULL) OR (total_distance_km >= (0)::numeric)))),
    CONSTRAINT ck_action_plans_source CHECK (((generation_source)::text = ANY ((ARRAY['OPTIMIZER'::character varying, 'MANUAL'::character varying])::text[]))),
    CONSTRAINT ck_action_plans_status CHECK (((status)::text = ANY ((ARRAY['DRAFT'::character varying, 'APPROVED'::character varying, 'ASSIGNED'::character varying, 'IN_PROGRESS'::character varying, 'COMPLETED'::character varying, 'CANCELLED'::character varying])::text[]))),
    CONSTRAINT ck_action_plans_times CHECK (((planned_start IS NULL) OR (planned_end IS NULL) OR (planned_end > planned_start)))
);


--
-- Name: action_plans_action_plan_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.action_plans ALTER COLUMN action_plan_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.action_plans_action_plan_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: ai_classifications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ai_classifications (
    classification_id bigint NOT NULL,
    complaint_id bigint NOT NULL,
    predicted_category character varying(100) NOT NULL,
    confidence numeric(5,4) NOT NULL,
    model_name character varying(150) NOT NULL,
    model_version character varying(50) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    model_type character varying(20) DEFAULT 'TEXT'::character varying NOT NULL,
    predicted_category_id bigint,
    top_k jsonb,
    is_accepted boolean,
    CONSTRAINT ck_ai_classifications_category CHECK ((btrim((predicted_category)::text) <> ''::text)),
    CONSTRAINT ck_ai_classifications_confidence CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))),
    CONSTRAINT ck_ai_classifications_model_name CHECK ((btrim((model_name)::text) <> ''::text)),
    CONSTRAINT ck_ai_classifications_model_type CHECK (((model_type)::text = ANY ((ARRAY['TEXT'::character varying, 'IMAGE'::character varying, 'FUSION'::character varying])::text[]))),
    CONSTRAINT ck_ai_classifications_model_version CHECK ((btrim((model_version)::text) <> ''::text))
);


--
-- Name: ai_classifications_classification_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.ai_classifications ALTER COLUMN classification_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.ai_classifications_classification_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs (
    audit_id bigint NOT NULL,
    user_id bigint,
    entity_type character varying(100) NOT NULL,
    entity_id bigint,
    action character varying(100) NOT NULL,
    old_value jsonb,
    new_value jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    actor_type character varying(20) DEFAULT 'USER'::character varying NOT NULL,
    ip_address inet,
    request_id character varying(64),
    entity_key character varying(100),
    CONSTRAINT ck_audit_action CHECK ((btrim((action)::text) <> ''::text)),
    CONSTRAINT ck_audit_actor_type CHECK (((actor_type)::text = ANY ((ARRAY['USER'::character varying, 'SYSTEM'::character varying, 'AI'::character varying])::text[]))),
    CONSTRAINT ck_audit_entity_id CHECK ((((entity_id IS NULL) OR (entity_id > 0)) AND ((entity_id IS NOT NULL) OR (entity_key IS NOT NULL)))),
    CONSTRAINT ck_audit_entity_type CHECK ((btrim((entity_type)::text) <> ''::text)),
    CONSTRAINT ck_audit_user_actor CHECK ((((actor_type)::text <> 'USER'::text) OR (user_id IS NOT NULL)))
);


--
-- Name: audit_logs_audit_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.audit_logs ALTER COLUMN audit_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.audit_logs_audit_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_events (
    auth_event_id bigint NOT NULL,
    user_id bigint,
    identifier character varying(255),
    event_type character varying(40) NOT NULL,
    ip_address inet,
    user_agent text,
    details jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_auth_event_type CHECK (((event_type)::text = ANY ((ARRAY['LOGIN_SUCCESS'::character varying, 'LOGIN_FAILED'::character varying, 'ACCOUNT_LOCKED'::character varying, 'LOGOUT'::character varying, 'OTP_SENT'::character varying, 'OTP_VERIFIED'::character varying, 'OTP_FAILED'::character varying, 'PASSWORD_RESET'::character varying, 'PASSWORD_CHANGED'::character varying, 'REFRESH_REUSE_DETECTED'::character varying, 'ROLE_CHANGED'::character varying, 'ACCOUNT_CREATED'::character varying, 'TOTP_ENABLED'::character varying, 'TOTP_VERIFIED'::character varying, 'TOTP_FAILED'::character varying, 'TOTP_RESET'::character varying, 'LOGOUT_ALL'::character varying])::text[])))
);


--
-- Name: auth_events_auth_event_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.auth_events ALTER COLUMN auth_event_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_events_auth_event_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_otp_codes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_otp_codes (
    otp_id bigint NOT NULL,
    user_id bigint,
    destination character varying(255) NOT NULL,
    channel character varying(20) NOT NULL,
    purpose character varying(30) NOT NULL,
    code_hmac character(64) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    attempt_count smallint DEFAULT 0 NOT NULL,
    max_attempts smallint DEFAULT 5 NOT NULL,
    consumed_at timestamp with time zone,
    request_ip inet,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_otp_attempts CHECK (((attempt_count >= 0) AND (max_attempts > 0))),
    CONSTRAINT ck_otp_channel CHECK (((channel)::text = ANY ((ARRAY['EMAIL'::character varying, 'WHATSAPP'::character varying, 'SMS'::character varying])::text[]))),
    CONSTRAINT ck_otp_expiry CHECK ((expires_at > created_at)),
    CONSTRAINT ck_otp_hmac CHECK ((code_hmac ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT ck_otp_purpose CHECK (((purpose)::text = ANY ((ARRAY['REGISTER'::character varying, 'LOGIN'::character varying, 'RESET_PASSWORD'::character varying, 'VERIFY_EMAIL'::character varying, 'VERIFY_PHONE'::character varying])::text[])))
);


--
-- Name: auth_otp_codes_otp_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.auth_otp_codes ALTER COLUMN otp_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_otp_codes_otp_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_refresh_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_refresh_tokens (
    refresh_token_id bigint NOT NULL,
    user_id bigint NOT NULL,
    token_hash character(64) NOT NULL,
    family_id uuid NOT NULL,
    family_expires_at timestamp with time zone,
    issued_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    last_used_at timestamp with time zone,
    revoked_at timestamp with time zone,
    revoke_reason character varying(40),
    replaced_by_token_id bigint,
    user_agent text,
    ip_address inet,
    CONSTRAINT ck_refresh_expiry CHECK ((expires_at > issued_at)),
    CONSTRAINT ck_refresh_hash CHECK ((token_hash ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT ck_refresh_reason CHECK (((revoke_reason IS NULL) OR ((revoke_reason)::text = ANY ((ARRAY['LOGOUT'::character varying, 'ROTATED'::character varying, 'REUSE_DETECTED'::character varying, 'PASSWORD_CHANGED'::character varying, 'ADMIN_REVOKED'::character varying, 'EXPIRED'::character varying])::text[]))))
);


--
-- Name: auth_refresh_tokens_refresh_token_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.auth_refresh_tokens ALTER COLUMN refresh_token_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_refresh_tokens_refresh_token_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: authenticity_checks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.authenticity_checks (
    check_id bigint NOT NULL,
    complaint_id bigint NOT NULL,
    image_id bigint,
    check_code character varying(40) NOT NULL,
    result character varying(10) NOT NULL,
    score_delta numeric(6,2) DEFAULT 0 NOT NULL,
    details jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_authenticity_code CHECK (((check_code)::text = ANY ((ARRAY['BOUNDARY'::character varying, 'GPS_ACCURACY'::character varying, 'GPS_FRESHNESS'::character varying, 'CAPTURE_SESSION'::character varying, 'IMAGE_REUSE_SHA256'::character varying, 'IMAGE_REUSE_PHASH'::character varying, 'EXIF_CONSISTENCY'::character varying, 'SUBMISSION_RATE'::character varying, 'IMPOSSIBLE_TRAVEL'::character varying, 'ACCOUNT_TRUST'::character varying, 'CATEGORY_IMAGE_MISMATCH'::character varying])::text[]))),
    CONSTRAINT ck_authenticity_result CHECK (((result)::text = ANY ((ARRAY['PASS'::character varying, 'WARN'::character varying, 'FAIL'::character varying, 'SKIPPED'::character varying])::text[])))
);


--
-- Name: authenticity_checks_check_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.authenticity_checks ALTER COLUMN check_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.authenticity_checks_check_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: capture_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.capture_sessions (
    capture_session_id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id bigint NOT NULL,
    issued_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone DEFAULT (now() + '00:10:00'::interval) NOT NULL,
    used_at timestamp with time zone,
    used_by_complaint_id bigint,
    client_ip inet,
    user_agent text,
    CONSTRAINT ck_capture_session_expiry CHECK ((expires_at > issued_at))
);


--
-- Name: complaint_categories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.complaint_categories (
    category_id bigint NOT NULL,
    category_name character varying(100) NOT NULL,
    description text,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    work_type_code character varying(30),
    yolo_class_id smallint,
    citizen_selectable boolean DEFAULT true NOT NULL,
    display_order smallint,
    needs_depth_answer boolean DEFAULT false NOT NULL,
    CONSTRAINT ck_complaint_categories_name CHECK ((btrim((category_name)::text) <> ''::text)),
    CONSTRAINT ck_complaint_categories_yolo_class CHECK (((yolo_class_id IS NULL) OR ((yolo_class_id >= 0) AND (yolo_class_id <= 3))))
);


--
-- Name: COLUMN complaint_categories.yolo_class_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.complaint_categories.yolo_class_id IS 'Step 9 frozen YOLO class id (0 Pothole, 1 Garbage Accumulation, 2 Waterlogging, 3 Road Damage). NULL = category has no visual model; image is stored as evidence only.';


--
-- Name: complaint_categories_category_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.complaint_categories ALTER COLUMN category_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.complaint_categories_category_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: complaint_feedback; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.complaint_feedback (
    feedback_id bigint NOT NULL,
    complaint_id bigint NOT NULL,
    user_id bigint NOT NULL,
    is_resolved boolean NOT NULL,
    rating smallint,
    comment text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_feedback_rating CHECK (((rating IS NULL) OR ((rating >= 1) AND (rating <= 5))))
);


--
-- Name: complaint_feedback_feedback_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.complaint_feedback ALTER COLUMN feedback_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.complaint_feedback_feedback_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: complaint_images; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.complaint_images (
    image_id bigint NOT NULL,
    complaint_id bigint NOT NULL,
    file_url text NOT NULL,
    file_name character varying(255),
    mime_type character varying(100),
    uploaded_at timestamp with time zone DEFAULT now() NOT NULL,
    processing_status character varying(30) DEFAULT 'PENDING'::character varying NOT NULL,
    image_role character varying(30) DEFAULT 'CITIZEN_EVIDENCE'::character varying NOT NULL,
    uploaded_by bigint,
    storage_key text,
    sha256 character(64),
    phash bigint,
    width_px integer,
    height_px integer,
    file_size_bytes bigint,
    capture_method character varying(20),
    client_captured_at timestamp with time zone,
    capture_location public.geometry(Point,4326),
    capture_accuracy_m numeric(8,2),
    device_pitch_deg numeric(6,2),
    device_roll_deg numeric(6,2),
    focal_length_35mm_eq numeric(6,2),
    exif_extracted jsonb,
    inspection_id bigint,
    completion_id bigint,
    public_approved boolean DEFAULT false NOT NULL,
    blurred_storage_key text,
    approved_by bigint,
    approved_at timestamp with time zone,
    quality_score numeric(4,3),
    CONSTRAINT ck_complaint_images_angles CHECK ((((device_pitch_deg IS NULL) OR ((device_pitch_deg >= ('-180'::integer)::numeric) AND (device_pitch_deg <= (180)::numeric))) AND ((device_roll_deg IS NULL) OR ((device_roll_deg >= ('-180'::integer)::numeric) AND (device_roll_deg <= (180)::numeric))))),
    CONSTRAINT ck_complaint_images_capture_method CHECK (((capture_method IS NULL) OR ((capture_method)::text = ANY ((ARRAY['IN_APP_CAMERA'::character varying, 'FILE_CAPTURE'::character varying, 'FILE_UPLOAD'::character varying])::text[])))),
    CONSTRAINT ck_complaint_images_dimensions CHECK ((((width_px IS NULL) OR (width_px > 0)) AND ((height_px IS NULL) OR (height_px > 0)) AND ((file_size_bytes IS NULL) OR (file_size_bytes > 0)))),
    CONSTRAINT ck_complaint_images_file_url CHECK ((btrim(file_url) <> ''::text)),
    CONSTRAINT ck_complaint_images_hashes CHECK (((sha256 IS NULL) OR (sha256 ~ '^[0-9a-f]{64}$'::text))),
    CONSTRAINT ck_complaint_images_processing_status CHECK (((processing_status)::text = ANY (ARRAY[('PENDING'::character varying)::text, ('PROCESSING'::character varying)::text, ('COMPLETED'::character varying)::text, ('FAILED'::character varying)::text]))),
    CONSTRAINT ck_complaint_images_public CHECK (((NOT public_approved) OR ((blurred_storage_key IS NOT NULL) AND (approved_by IS NOT NULL) AND (approved_at IS NOT NULL)))),
    CONSTRAINT ck_complaint_images_quality CHECK (((quality_score IS NULL) OR ((quality_score >= (0)::numeric) AND (quality_score <= (1)::numeric)))),
    CONSTRAINT ck_complaint_images_role CHECK (((image_role)::text = ANY ((ARRAY['CITIZEN_EVIDENCE'::character varying, 'INSPECTION'::character varying, 'WORK_IN_PROGRESS'::character varying, 'COMPLETION_PROOF'::character varying])::text[])))
);


--
-- Name: COLUMN complaint_images.quality_score; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.complaint_images.quality_score IS '0.5 x normalised sharpness (Laplacian variance) + 0.3 x primary detection confidence + 0.2 x min(1, pixels / 2 MP); written by the worker.';


--
-- Name: complaint_images_image_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.complaint_images ALTER COLUMN image_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.complaint_images_image_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: complaint_status_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.complaint_status_history (
    status_history_id bigint NOT NULL,
    complaint_id bigint NOT NULL,
    old_status character varying(30),
    new_status character varying(30) NOT NULL,
    changed_by bigint,
    remarks text,
    changed_at timestamp with time zone DEFAULT now() NOT NULL,
    actor_role character varying(20),
    source character varying(20) DEFAULT 'WEB'::character varying NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    CONSTRAINT ck_status_history_new_status CHECK (((new_status)::text = ANY ((ARRAY['SUBMITTED'::character varying, 'VERIFIED'::character varying, 'REJECTED'::character varying, 'MERGED'::character varying, 'SCHEDULED'::character varying, 'ASSIGNED'::character varying, 'INSPECTED'::character varying, 'IN_PROGRESS'::character varying, 'COMPLETED'::character varying, 'CLOSED'::character varying, 'REOPENED'::character varying])::text[]))),
    CONSTRAINT ck_status_history_old_status CHECK (((old_status IS NULL) OR ((old_status)::text = ANY ((ARRAY['SUBMITTED'::character varying, 'VERIFIED'::character varying, 'REJECTED'::character varying, 'MERGED'::character varying, 'SCHEDULED'::character varying, 'ASSIGNED'::character varying, 'INSPECTED'::character varying, 'IN_PROGRESS'::character varying, 'COMPLETED'::character varying, 'CLOSED'::character varying, 'REOPENED'::character varying])::text[])))),
    CONSTRAINT ck_status_history_source CHECK (((source)::text = ANY ((ARRAY['WEB'::character varying, 'SYSTEM'::character varying, 'AI'::character varying, 'MIGRATION'::character varying])::text[])))
);


--
-- Name: complaint_status_history_status_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.complaint_status_history ALTER COLUMN status_history_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.complaint_status_history_status_history_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: complaint_status_transitions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.complaint_status_transitions (
    from_status character varying(30) NOT NULL,
    to_status character varying(30) NOT NULL,
    allowed_roles text[] NOT NULL,
    notify_citizen boolean DEFAULT true NOT NULL,
    description text
);


--
-- Name: complaint_votes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.complaint_votes (
    complaint_id bigint NOT NULL,
    user_id bigint NOT NULL,
    vote_type character varying(10) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_vote_type CHECK (((vote_type)::text = ANY ((ARRAY['UP'::character varying, 'DOWN'::character varying])::text[])))
);


--
-- Name: complaints; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.complaints (
    complaint_id bigint NOT NULL,
    user_id bigint NOT NULL,
    category_id bigint,
    title character varying(200) NOT NULL,
    description text NOT NULL,
    status character varying(30) DEFAULT 'SUBMITTED'::character varying NOT NULL,
    location public.geometry(Point,4326) NOT NULL,
    ward_id bigint,
    road_id bigint,
    poi_id bigint,
    is_outside_boundary boolean DEFAULT false NOT NULL,
    submitted_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    closed_at timestamp with time zone,
    duplicate_status character varying(20) DEFAULT 'NOT_EVALUATED'::character varying NOT NULL,
    master_complaint_id bigint,
    matched_complaint_id bigint,
    duplicate_checked_at timestamp with time zone,
    duplicate_review_required boolean DEFAULT false NOT NULL,
    public_ref character varying(20) GENERATED ALWAYS AS (('CB-'::text || lpad((complaint_id)::text, 6, '0'::text))) STORED,
    is_synthetic boolean DEFAULT false NOT NULL,
    landmark text,
    address_text text,
    location_accuracy_m numeric(8,2),
    location_captured_at timestamp with time zone,
    location_source character varying(20),
    capture_session_id uuid,
    authenticity_status character varying(20) DEFAULT 'NOT_CHECKED'::character varying NOT NULL,
    authenticity_score numeric(5,2),
    ai_status character varying(20) DEFAULT 'PENDING'::character varying NOT NULL,
    ai_processed_at timestamp with time zone,
    current_priority_score numeric(6,2),
    current_priority_level character varying(10),
    current_action_plan_id bigint,
    assigned_contractor_id bigint,
    rejection_reason text,
    depth_answer character varying(10),
    a4_in_frame boolean DEFAULT false NOT NULL,
    CONSTRAINT ck_complaints_ai_status CHECK (((ai_status)::text = ANY ((ARRAY['PENDING'::character varying, 'PROCESSING'::character varying, 'COMPLETED'::character varying, 'FAILED'::character varying, 'SKIPPED'::character varying])::text[]))),
    CONSTRAINT ck_complaints_authenticity_score CHECK (((authenticity_score IS NULL) OR ((authenticity_score >= (0)::numeric) AND (authenticity_score <= (100)::numeric)))),
    CONSTRAINT ck_complaints_authenticity_status CHECK (((authenticity_status)::text = ANY ((ARRAY['NOT_CHECKED'::character varying, 'PASSED'::character varying, 'FLAGGED'::character varying, 'REJECTED'::character varying])::text[]))),
    CONSTRAINT ck_complaints_closed_at CHECK ((((status)::text = 'CLOSED'::text) OR (closed_at IS NULL) OR (closed_at >= submitted_at))),
    CONSTRAINT ck_complaints_depth_answer CHECK (((depth_answer IS NULL) OR ((depth_answer)::text = ANY ((ARRAY['SHALLOW'::character varying, 'FINGER'::character varying, 'DEEP'::character varying])::text[])))),
    CONSTRAINT ck_complaints_description CHECK ((btrim(description) <> ''::text)),
    CONSTRAINT ck_complaints_duplicate_status CHECK (((duplicate_status)::text = ANY (ARRAY[('NOT_EVALUATED'::character varying)::text, ('DUPLICATE'::character varying)::text, ('UNCERTAIN'::character varying)::text, ('NOT_DUPLICATE'::character varying)::text]))),
    CONSTRAINT ck_complaints_location_accuracy CHECK (((location_accuracy_m IS NULL) OR (location_accuracy_m >= (0)::numeric))),
    CONSTRAINT ck_complaints_location_source CHECK (((location_source IS NULL) OR ((location_source)::text = ANY ((ARRAY['BROWSER_GPS'::character varying, 'EXIF'::character varying, 'OFFICER_CORRECTED'::character varying, 'SYNTHETIC'::character varying])::text[])))),
    CONSTRAINT ck_complaints_priority_level CHECK (((current_priority_level IS NULL) OR ((current_priority_level)::text = ANY ((ARRAY['LOW'::character varying, 'MEDIUM'::character varying, 'HIGH'::character varying, 'CRITICAL'::character varying])::text[])))),
    CONSTRAINT ck_complaints_status CHECK (((status)::text = ANY ((ARRAY['SUBMITTED'::character varying, 'VERIFIED'::character varying, 'REJECTED'::character varying, 'MERGED'::character varying, 'SCHEDULED'::character varying, 'ASSIGNED'::character varying, 'INSPECTED'::character varying, 'IN_PROGRESS'::character varying, 'COMPLETED'::character varying, 'CLOSED'::character varying, 'REOPENED'::character varying])::text[]))),
    CONSTRAINT ck_complaints_title CHECK ((btrim((title)::text) <> ''::text))
);


--
-- Name: COLUMN complaints.duplicate_status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.complaints.duplicate_status IS 'Step 12 duplicate decision state: NOT_EVALUATED, DUPLICATE, UNCERTAIN, NOT_DUPLICATE.';


--
-- Name: COLUMN complaints.master_complaint_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.complaints.master_complaint_id IS 'Canonical complaint representing the master physical issue. Multiple complaints may reference the same master complaint.';


--
-- Name: COLUMN complaints.matched_complaint_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.complaints.matched_complaint_id IS 'Best/selected complaint match used by the duplicate decision.';


--
-- Name: COLUMN complaints.public_ref; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.complaints.public_ref IS 'Citizen-facing complaint number used in e-mail / WhatsApp, e.g. CB-000123.';


--
-- Name: COLUMN complaints.is_synthetic; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.complaints.is_synthetic IS 'true for the 500 Step 8 synthetic complaints; false for real web submissions.';


--
-- Name: COLUMN complaints.depth_answer; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.complaints.depth_answer IS 'Citizen answer to "how deep?" (SHALLOW / FINGER / DEEP). Mapped to an assumed depth by the worker (06_AI_PIPELINE 2.4). NULL = not asked or not answered.';


--
-- Name: COLUMN complaints.a4_in_frame; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.complaints.a4_in_frame IS 'Citizen says an A4 sheet lies next to the defect in the photo; the worker then tries measurement Tier A.';


--
-- Name: complaints_complaint_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.complaints ALTER COLUMN complaint_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.complaints_complaint_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: complaints_import_staging; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.complaints_import_staging (
    complaint_id integer,
    title text,
    description text,
    category text,
    latitude double precision,
    longitude double precision,
    created_at timestamp without time zone,
    status text,
    image_path text,
    is_synthetic boolean,
    ward_id integer,
    road_id integer,
    poi_id integer
);


--
-- Name: contractor_equipment; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contractor_equipment (
    contractor_id bigint NOT NULL,
    equipment_code character varying(60) NOT NULL,
    quantity integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_contractor_equipment_qty CHECK ((quantity >= 0))
);


--
-- Name: contractor_work_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contractor_work_types (
    contractor_id bigint NOT NULL,
    work_type_code character varying(30) NOT NULL
);


--
-- Name: contractor_workers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contractor_workers (
    worker_id bigint NOT NULL,
    contractor_id bigint NOT NULL,
    user_id bigint,
    full_name character varying(150) NOT NULL,
    phone character varying(20),
    skill character varying(30) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_by_user_id bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_workers_name CHECK ((btrim((full_name)::text) <> ''::text)),
    CONSTRAINT ck_workers_phone CHECK (((phone IS NULL) OR ((phone)::text ~ '^\+?[0-9]{10,15}$'::text))),
    CONSTRAINT ck_workers_skill CHECK (((skill)::text = ANY ((ARRAY['SUPERVISOR'::character varying, 'MASON'::character varying, 'LABOURER'::character varying, 'ELECTRICIAN'::character varying, 'PLUMBER'::character varying, 'MACHINE_OPERATOR'::character varying, 'DRIVER'::character varying, 'SANITATION_WORKER'::character varying, 'OTHER'::character varying])::text[])))
);


--
-- Name: contractor_workers_worker_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.contractor_workers ALTER COLUMN worker_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.contractor_workers_worker_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: contractors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contractors (
    contractor_id bigint NOT NULL,
    user_id bigint,
    firm_name character varying(200) NOT NULL,
    contact_person character varying(150) NOT NULL,
    phone character varying(20) NOT NULL,
    email character varying(255),
    address text,
    registration_no character varying(100),
    crew_capacity integer DEFAULT 4 NOT NULL,
    shift_start time without time zone DEFAULT '08:00:00'::time without time zone NOT NULL,
    shift_end time without time zone DEFAULT '17:00:00'::time without time zone NOT NULL,
    status character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    rating numeric(3,2),
    created_by_officer_id bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_contractors_capacity CHECK ((crew_capacity > 0)),
    CONSTRAINT ck_contractors_firm CHECK ((btrim((firm_name)::text) <> ''::text)),
    CONSTRAINT ck_contractors_phone CHECK (((phone)::text ~ '^\+?[0-9]{10,15}$'::text)),
    CONSTRAINT ck_contractors_rating CHECK (((rating IS NULL) OR ((rating >= (0)::numeric) AND (rating <= (5)::numeric)))),
    CONSTRAINT ck_contractors_shift CHECK ((shift_end > shift_start)),
    CONSTRAINT ck_contractors_status CHECK (((status)::text = ANY ((ARRAY['ACTIVE'::character varying, 'INACTIVE'::character varying, 'SUSPENDED'::character varying])::text[])))
);


--
-- Name: contractors_contractor_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.contractors ALTER COLUMN contractor_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.contractors_contractor_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: data_subject_requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.data_subject_requests (
    request_id bigint NOT NULL,
    user_id bigint NOT NULL,
    request_type character varying(20) NOT NULL,
    status character varying(20) DEFAULT 'RECEIVED'::character varying NOT NULL,
    details text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    due_at timestamp with time zone DEFAULT (now() + '90 days'::interval) NOT NULL,
    completed_at timestamp with time zone,
    handled_by bigint,
    resolution text,
    CONSTRAINT ck_dsr_done CHECK ((((status)::text <> ALL ((ARRAY['COMPLETED'::character varying, 'REJECTED'::character varying])::text[])) OR (completed_at IS NOT NULL))),
    CONSTRAINT ck_dsr_status CHECK (((status)::text = ANY ((ARRAY['RECEIVED'::character varying, 'IN_PROGRESS'::character varying, 'COMPLETED'::character varying, 'REJECTED'::character varying])::text[]))),
    CONSTRAINT ck_dsr_type CHECK (((request_type)::text = ANY ((ARRAY['ACCESS'::character varying, 'CORRECTION'::character varying, 'ERASURE'::character varying, 'WITHDRAW_CONSENT'::character varying, 'GRIEVANCE'::character varying])::text[])))
);


--
-- Name: data_subject_requests_request_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.data_subject_requests ALTER COLUMN request_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.data_subject_requests_request_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: defect_measurements; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.defect_measurements (
    measurement_id bigint NOT NULL,
    complaint_id bigint NOT NULL,
    image_id bigint,
    detection_id bigint,
    source character varying(20) NOT NULL,
    method character varying(40) NOT NULL,
    mask_area_px numeric(14,2),
    length_m numeric(8,3),
    width_m numeric(8,3),
    area_m2 numeric(10,3),
    depth_m numeric(6,3),
    depth_source character varying(30),
    volume_m3 numeric(10,4),
    severity_class character varying(10),
    confidence numeric(4,3),
    error_band_pct numeric(5,1),
    assumptions jsonb DEFAULT '{}'::jsonb NOT NULL,
    model_name character varying(150),
    model_version character varying(50),
    measured_by bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_measure_confidence CHECK (((confidence IS NULL) OR ((confidence >= (0)::numeric) AND (confidence <= (1)::numeric)))),
    CONSTRAINT ck_measure_depth_src CHECK (((depth_source IS NULL) OR ((depth_source)::text = ANY ((ARRAY['ASSUMED_FROM_SEVERITY_CLASS'::character varying, 'MEASURED_ON_SITE'::character varying, 'MODEL_ESTIMATE'::character varying])::text[])))),
    CONSTRAINT ck_measure_method CHECK (((method)::text = ANY ((ARRAY['GROUND_PLANE_HOMOGRAPHY'::character varying, 'REFERENCE_OBJECT'::character varying, 'MONOCULAR_DEPTH'::character varying, 'CATEGORY_DEFAULT'::character varying, 'MANUAL_TAPE'::character varying])::text[]))),
    CONSTRAINT ck_measure_severity CHECK (((severity_class IS NULL) OR ((severity_class)::text = ANY ((ARRAY['SMALL'::character varying, 'MEDIUM'::character varying, 'LARGE'::character varying])::text[])))),
    CONSTRAINT ck_measure_source CHECK (((source)::text = ANY ((ARRAY['AI'::character varying, 'CONTRACTOR'::character varying, 'OFFICER'::character varying])::text[]))),
    CONSTRAINT ck_measure_values CHECK ((((length_m IS NULL) OR (length_m > (0)::numeric)) AND ((width_m IS NULL) OR (width_m > (0)::numeric)) AND ((area_m2 IS NULL) OR (area_m2 > (0)::numeric)) AND ((depth_m IS NULL) OR (depth_m >= (0)::numeric)) AND ((volume_m3 IS NULL) OR (volume_m3 >= (0)::numeric))))
);


--
-- Name: TABLE defect_measurements; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.defect_measurements IS 'Real-world size estimates. AI rows are preliminary (single photo; depth cannot be measured from one RGB photo and is assumed from IRC:82 class: SMALL <=25 mm, MEDIUM 25-50 mm, LARGE >50 mm). CONTRACTOR rows are tape measurements at inspection and override AI for costing.';


--
-- Name: defect_measurements_measurement_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.defect_measurements ALTER COLUMN measurement_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.defect_measurements_measurement_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: depots; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.depots (
    depot_id character varying(20) NOT NULL,
    depot_name character varying(150) NOT NULL,
    location public.geometry(Point,4326) NOT NULL,
    source text NOT NULL,
    is_prototype boolean DEFAULT true NOT NULL
);


--
-- Name: duplicate_detections; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.duplicate_detections (
    duplicate_detection_id bigint NOT NULL,
    complaint_id_1 bigint NOT NULL,
    complaint_id_2 bigint NOT NULL,
    similarity_score numeric(5,4) NOT NULL,
    detection_method character varying(100) NOT NULL,
    is_duplicate boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_duplicate_method CHECK ((btrim((detection_method)::text) <> ''::text)),
    CONSTRAINT ck_duplicate_pair_order CHECK ((complaint_id_1 < complaint_id_2)),
    CONSTRAINT ck_duplicate_similarity CHECK (((similarity_score >= (0)::numeric) AND (similarity_score <= (1)::numeric)))
);


--
-- Name: duplicate_detections_duplicate_detection_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.duplicate_detections ALTER COLUMN duplicate_detection_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.duplicate_detections_duplicate_detection_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: duplicate_import_staging; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.duplicate_import_staging (
    complaint_id_1 bigint,
    complaint_id_2 bigint,
    similarity_score numeric,
    detection_method character varying,
    is_duplicate boolean
);


--
-- Name: duplicate_relation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.duplicate_relation (
    duplicate_relation_id bigint NOT NULL,
    complaint_id bigint NOT NULL,
    master_complaint_id bigint,
    similar_complaint_id bigint NOT NULL,
    text_similarity double precision NOT NULL,
    distance_meters double precision NOT NULL,
    time_difference_hours double precision NOT NULL,
    duplicate_score double precision NOT NULL,
    decision character varying(20) NOT NULL,
    decision_source character varying(20) DEFAULT 'AI'::character varying NOT NULL,
    review_required boolean DEFAULT false NOT NULL,
    review_decision character varying(20),
    reviewed_by bigint,
    reviewed_at timestamp with time zone,
    review_comment text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_duplicate_relation_decision CHECK (((decision)::text = ANY (ARRAY[('DUPLICATE'::character varying)::text, ('UNCERTAIN'::character varying)::text, ('NOT_DUPLICATE'::character varying)::text]))),
    CONSTRAINT ck_duplicate_relation_distance CHECK ((distance_meters >= (0.0)::double precision)),
    CONSTRAINT ck_duplicate_relation_not_self CHECK ((complaint_id <> similar_complaint_id)),
    CONSTRAINT ck_duplicate_relation_review_action_metadata CHECK (((review_decision IS NULL) OR ((reviewed_by IS NOT NULL) AND (reviewed_at IS NOT NULL)))),
    CONSTRAINT ck_duplicate_relation_review_decision CHECK (((review_decision IS NULL) OR ((review_decision)::text = ANY (ARRAY[('MERGE'::character varying)::text, ('KEEP_SEPARATE'::character varying)::text])))),
    CONSTRAINT ck_duplicate_relation_review_metadata CHECK ((((reviewed_by IS NULL) AND (reviewed_at IS NULL)) OR ((reviewed_by IS NOT NULL) AND (reviewed_at IS NOT NULL)))),
    CONSTRAINT ck_duplicate_relation_score CHECK (((duplicate_score >= (0.0)::double precision) AND (duplicate_score <= (1.0)::double precision))),
    CONSTRAINT ck_duplicate_relation_source CHECK (((decision_source)::text = ANY (ARRAY[('AI'::character varying)::text, ('MANUAL'::character varying)::text, ('SYSTEM'::character varying)::text]))),
    CONSTRAINT ck_duplicate_relation_text_similarity CHECK (((text_similarity >= (0.0)::double precision) AND (text_similarity <= (1.0)::double precision))),
    CONSTRAINT ck_duplicate_relation_time CHECK ((time_difference_hours >= (0.0)::double precision)),
    CONSTRAINT ck_duplicate_relation_uncertain_review CHECK ((((decision)::text <> 'UNCERTAIN'::text) OR (review_required = true)))
);


--
-- Name: TABLE duplicate_relation; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.duplicate_relation IS 'CivicBrain Step 12 duplicate-pair evidence and review history. duplicate_score is an uncalibrated model score, not a statistical probability.';


--
-- Name: duplicate_relation_duplicate_relation_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.duplicate_relation ALTER COLUMN duplicate_relation_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.duplicate_relation_duplicate_relation_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: equipment_catalog; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.equipment_catalog (
    equipment_code character varying(60) NOT NULL,
    display_name character varying(150) NOT NULL,
    unit character varying(30) DEFAULT 'day'::character varying NOT NULL,
    rate_per_unit numeric(12,2),
    rate_source text,
    is_prototype_assumption boolean DEFAULT true NOT NULL,
    CONSTRAINT ck_equipment_rate CHECK (((rate_per_unit IS NULL) OR (rate_per_unit >= (0)::numeric)))
);


--
-- Name: field_teams; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.field_teams (
    team_id bigint NOT NULL,
    team_name character varying(150) NOT NULL,
    department character varying(100) NOT NULL,
    team_leader character varying(150),
    contact character varying(20),
    status character varying(30) DEFAULT 'ACTIVE'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_field_teams_department CHECK ((btrim((department)::text) <> ''::text)),
    CONSTRAINT ck_field_teams_name CHECK ((btrim((team_name)::text) <> ''::text)),
    CONSTRAINT ck_field_teams_status CHECK (((status)::text = ANY (ARRAY[('ACTIVE'::character varying)::text, ('INACTIVE'::character varying)::text, ('BUSY'::character varying)::text])))
);


--
-- Name: field_teams_team_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.field_teams ALTER COLUMN team_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.field_teams_team_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: jobs_job_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.jobs ALTER COLUMN job_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.jobs_job_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: material_catalog; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.material_catalog (
    material_code character varying(60) NOT NULL,
    display_name character varying(150) NOT NULL,
    unit character varying(20) NOT NULL,
    work_type_code character varying(30),
    density_t_per_m3 numeric(6,3),
    application_rate numeric(10,4),
    application_rate_unit character varying(40),
    rate_per_unit numeric(12,2),
    rate_source text,
    notes text,
    CONSTRAINT ck_material_rate CHECK (((rate_per_unit IS NULL) OR (rate_per_unit >= (0)::numeric)))
);


--
-- Name: municipal_boundary; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.municipal_boundary (
    boundary_id bigint NOT NULL,
    municipality_name character varying(150) NOT NULL,
    boundary_type character varying(50) NOT NULL,
    source text NOT NULL,
    status character varying(30) DEFAULT 'UNVERIFIED'::character varying NOT NULL,
    geometry public.geometry(Geometry,4326) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_municipal_boundary_name CHECK ((btrim((municipality_name)::text) <> ''::text)),
    CONSTRAINT ck_municipal_boundary_status CHECK (((status)::text = ANY (ARRAY[('ACTIVE'::character varying)::text, ('INACTIVE'::character varying)::text, ('VERIFIED'::character varying)::text, ('UNVERIFIED'::character varying)::text]))),
    CONSTRAINT ck_municipal_boundary_type CHECK (((boundary_type)::text = 'MUNICIPAL_BOUNDARY'::text))
);


--
-- Name: municipal_boundary_boundary_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.municipal_boundary ALTER COLUMN boundary_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.municipal_boundary_boundary_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: notification_outbox; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notification_outbox (
    outbox_id bigint NOT NULL,
    event_type character varying(40) NOT NULL,
    complaint_id bigint,
    action_plan_id bigint,
    event_status character varying(30),
    payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    processed_at timestamp with time zone,
    attempt_count integer DEFAULT 0 NOT NULL,
    last_error text,
    CONSTRAINT ck_outbox_event_type CHECK (((event_type)::text = ANY ((ARRAY['COMPLAINT_STATUS_CHANGED'::character varying, 'ACTION_PLAN_ASSIGNED'::character varying, 'COMPLETION_SUBMITTED'::character varying, 'ACCOUNT_CREATED'::character varying, 'OTP'::character varying, 'GENERIC'::character varying])::text[])))
);


--
-- Name: notification_outbox_outbox_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.notification_outbox ALTER COLUMN outbox_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.notification_outbox_outbox_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: notification_templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notification_templates (
    template_id bigint NOT NULL,
    template_code character varying(60) NOT NULL,
    channel character varying(20) NOT NULL,
    locale character varying(5) DEFAULT 'en'::character varying NOT NULL,
    event_status character varying(30),
    subject text,
    body text NOT NULL,
    provider_template_name character varying(100),
    include_photo boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    CONSTRAINT ck_template_channel CHECK (((channel)::text = ANY ((ARRAY['EMAIL'::character varying, 'WHATSAPP'::character varying, 'SMS'::character varying, 'IN_APP'::character varying])::text[]))),
    CONSTRAINT ck_template_locale CHECK (((locale)::text = ANY ((ARRAY['en'::character varying, 'mr'::character varying, 'hi'::character varying])::text[])))
);


--
-- Name: notification_templates_template_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.notification_templates ALTER COLUMN template_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.notification_templates_template_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: notifications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notifications (
    notification_id bigint NOT NULL,
    outbox_id bigint,
    user_id bigint NOT NULL,
    complaint_id bigint,
    channel character varying(20) NOT NULL,
    template_code character varying(60),
    destination character varying(255),
    rendered_subject text,
    rendered_body text,
    media_url text,
    status character varying(20) DEFAULT 'QUEUED'::character varying NOT NULL,
    provider character varying(30),
    provider_message_id character varying(128),
    attempt_count smallint DEFAULT 0 NOT NULL,
    next_attempt_at timestamp with time zone,
    last_error text,
    dedupe_key character varying(200) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    sent_at timestamp with time zone,
    delivered_at timestamp with time zone,
    read_at timestamp with time zone,
    CONSTRAINT ck_notifications_channel CHECK (((channel)::text = ANY ((ARRAY['EMAIL'::character varying, 'WHATSAPP'::character varying, 'SMS'::character varying, 'IN_APP'::character varying])::text[]))),
    CONSTRAINT ck_notifications_provider CHECK (((provider IS NULL) OR ((provider)::text = ANY ((ARRAY['GMAIL_SMTP'::character varying, 'BREVO'::character varying, 'RESEND'::character varying, 'META_CLOUD_API'::character varying, 'TWILIO_SANDBOX'::character varying, 'INTERNAL'::character varying])::text[])))),
    CONSTRAINT ck_notifications_status CHECK (((status)::text = ANY ((ARRAY['QUEUED'::character varying, 'SENDING'::character varying, 'SENT'::character varying, 'DELIVERED'::character varying, 'READ'::character varying, 'FAILED'::character varying, 'SKIPPED'::character varying])::text[])))
);


--
-- Name: notifications_notification_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.notifications ALTER COLUMN notification_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.notifications_notification_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: officer_approvals; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.officer_approvals (
    approval_id bigint NOT NULL,
    complaint_id bigint NOT NULL,
    officer_id bigint NOT NULL,
    recommendation_type character varying(50) NOT NULL,
    decision character varying(30) NOT NULL,
    remarks text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_officer_approvals_decision CHECK (((decision)::text = ANY (ARRAY[('APPROVED'::character varying)::text, ('REJECTED'::character varying)::text, ('MODIFIED'::character varying)::text]))),
    CONSTRAINT ck_officer_approvals_recommendation CHECK ((btrim((recommendation_type)::text) <> ''::text))
);


--
-- Name: officer_approvals_approval_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.officer_approvals ALTER COLUMN approval_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.officer_approvals_approval_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: officer_scopes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.officer_scopes (
    officer_scope_id bigint NOT NULL,
    officer_id bigint NOT NULL,
    ward_id bigint,
    work_type_code character varying(30),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: officer_scopes_officer_scope_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.officer_scopes ALTER COLUMN officer_scope_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.officer_scopes_officer_scope_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: officers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.officers (
    officer_id bigint NOT NULL,
    user_id bigint NOT NULL,
    employee_code character varying(50) NOT NULL,
    department character varying(100) NOT NULL,
    designation character varying(100) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by_user_id bigint,
    CONSTRAINT ck_officers_department CHECK ((btrim((department)::text) <> ''::text)),
    CONSTRAINT ck_officers_designation CHECK ((btrim((designation)::text) <> ''::text)),
    CONSTRAINT ck_officers_employee_code CHECK ((btrim((employee_code)::text) <> ''::text))
);


--
-- Name: officers_officer_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.officers ALTER COLUMN officer_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.officers_officer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: optimizer_runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.optimizer_runs (
    run_id bigint NOT NULL,
    requested_by bigint,
    request jsonb NOT NULL,
    solver character varying(30) DEFAULT 'ORTOOLS_ROUTING'::character varying NOT NULL,
    status character varying(20) DEFAULT 'QUEUED'::character varying NOT NULL,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    result_summary jsonb,
    dropped_jobs jsonb,
    error_message text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_optimizer_solver CHECK (((solver)::text = ANY ((ARRAY['ORTOOLS_ROUTING'::character varying, 'ORTOOLS_CPSAT'::character varying, 'MANUAL'::character varying])::text[]))),
    CONSTRAINT ck_optimizer_status CHECK (((status)::text = ANY ((ARRAY['QUEUED'::character varying, 'RUNNING'::character varying, 'SUCCEEDED'::character varying, 'FAILED'::character varying, 'CANCELLED'::character varying])::text[])))
);


--
-- Name: optimizer_runs_run_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.optimizer_runs ALTER COLUMN run_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.optimizer_runs_run_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: pois; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pois (
    poi_id bigint NOT NULL,
    name character varying(200) NOT NULL,
    type character varying(50) NOT NULL,
    latitude double precision NOT NULL,
    longitude double precision NOT NULL,
    ward_id bigint,
    source text NOT NULL,
    geometry public.geometry(Point,4326) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_pois_latitude CHECK (((latitude >= ('-90'::integer)::double precision) AND (latitude <= (90)::double precision))),
    CONSTRAINT ck_pois_longitude CHECK (((longitude >= ('-180'::integer)::double precision) AND (longitude <= (180)::double precision))),
    CONSTRAINT ck_pois_name CHECK ((btrim((name)::text) <> ''::text)),
    CONSTRAINT ck_pois_type CHECK (((type)::text = ANY (ARRAY[('hospital'::character varying)::text, ('school'::character varying)::text, ('college'::character varying)::text, ('government_office'::character varying)::text, ('police_station'::character varying)::text, ('fire_station'::character varying)::text, ('bus_stop'::character varying)::text, ('railway_station'::character varying)::text, ('market'::character varying)::text, ('other'::character varying)::text])))
);


--
-- Name: pois_import_raw; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pois_import_raw (
    poi_id integer NOT NULL,
    geometry public.geometry(Point,4326),
    full_id character varying,
    osm_id character varying,
    osm_type character varying,
    amenity character varying,
    education character varying,
    name character varying,
    check_date date,
    "healthcare:speciality" character varying,
    healthcare character varying,
    "addr:state" character varying,
    "addr:postcode" character varying,
    "addr:full" character varying,
    "addr:district" character varying,
    religion character varying,
    grades character varying,
    description character varying,
    "addr:street" character varying,
    "addr:city" character varying,
    highway character varying,
    public_transport character varying,
    bus character varying,
    office character varying,
    "name:mr" character varying,
    government character varying,
    layer character varying,
    path character varying,
    type character varying,
    ward_id integer,
    ward_number integer,
    ward_name character varying
);


--
-- Name: pois_import_staging; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pois_import_staging (
    poi_id integer,
    name text,
    type text,
    ward_id integer,
    geometry public.geometry(Point,4326)
);


--
-- Name: pois_poi_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.pois ALTER COLUMN poi_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.pois_poi_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: priority_assessments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.priority_assessments (
    priority_assessment_id bigint NOT NULL,
    complaint_id bigint NOT NULL,
    severity_score numeric(6,2) NOT NULL,
    urgency_score numeric(6,2) NOT NULL,
    location_score numeric(6,2) NOT NULL,
    impact_score numeric(6,2) NOT NULL,
    final_score numeric(8,2) NOT NULL,
    priority_level character varying(30) NOT NULL,
    reason text,
    calculated_at timestamp with time zone DEFAULT now() NOT NULL,
    frequency_score numeric(6,2),
    infrastructure_score numeric(6,2),
    historical_risk_score numeric(6,2),
    formula_version character varying(40) DEFAULT 'STEP11_FROZEN_V1'::character varying NOT NULL,
    weights jsonb DEFAULT '{"severity": 0.25, "frequency": 0.10, "wait_time": 0.10, "location_risk": 0.15, "historical_risk": 0.10, "population_impact": 0.15, "infrastructure_importance": 0.15}'::jsonb NOT NULL,
    explanation jsonb,
    is_current boolean DEFAULT true NOT NULL,
    CONSTRAINT ck_priority_extra_factors CHECK ((((frequency_score IS NULL) OR (frequency_score >= (0)::numeric)) AND ((infrastructure_score IS NULL) OR (infrastructure_score >= (0)::numeric)) AND ((historical_risk_score IS NULL) OR (historical_risk_score >= (0)::numeric)))),
    CONSTRAINT ck_priority_final_score CHECK ((final_score >= (0)::numeric)),
    CONSTRAINT ck_priority_impact CHECK ((impact_score >= (0)::numeric)),
    CONSTRAINT ck_priority_level CHECK (((priority_level)::text = ANY (ARRAY[('LOW'::character varying)::text, ('MEDIUM'::character varying)::text, ('HIGH'::character varying)::text, ('CRITICAL'::character varying)::text]))),
    CONSTRAINT ck_priority_location CHECK ((location_score >= (0)::numeric)),
    CONSTRAINT ck_priority_severity CHECK ((severity_score >= (0)::numeric)),
    CONSTRAINT ck_priority_urgency CHECK ((urgency_score >= (0)::numeric))
);


--
-- Name: COLUMN priority_assessments.severity_score; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.priority_assessments.severity_score IS 'Step 11 factor S (weight 0.25)';


--
-- Name: COLUMN priority_assessments.urgency_score; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.priority_assessments.urgency_score IS 'Step 11 factor Twait - wait time (weight 0.10)';


--
-- Name: COLUMN priority_assessments.location_score; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.priority_assessments.location_score IS 'Step 11 factor Rloc - location risk (weight 0.15)';


--
-- Name: COLUMN priority_assessments.impact_score; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.priority_assessments.impact_score IS 'Step 11 factor Ipop - population impact (weight 0.15)';


--
-- Name: COLUMN priority_assessments.frequency_score; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.priority_assessments.frequency_score IS 'Step 11 factor F (weight 0.10)';


--
-- Name: COLUMN priority_assessments.infrastructure_score; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.priority_assessments.infrastructure_score IS 'Step 11 factor Iinfra (weight 0.15)';


--
-- Name: COLUMN priority_assessments.historical_risk_score; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.priority_assessments.historical_risk_score IS 'Step 11 factor H (weight 0.10)';


--
-- Name: priority_assessments_priority_assessment_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.priority_assessments ALTER COLUMN priority_assessment_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.priority_assessments_priority_assessment_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: privacy_notices; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.privacy_notices (
    version character varying(20) NOT NULL,
    published_at timestamp with time zone DEFAULT now() NOT NULL,
    summary text NOT NULL,
    content_hash character(64),
    is_current boolean DEFAULT false NOT NULL
);


--
-- Name: resource_estimate_equipment; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.resource_estimate_equipment (
    estimate_id bigint NOT NULL,
    equipment_code character varying(60) NOT NULL,
    quantity numeric(10,2) NOT NULL,
    unit character varying(30) NOT NULL,
    rate numeric(12,2),
    amount numeric(12,2),
    CONSTRAINT ck_estimate_equipment_qty CHECK ((quantity >= (0)::numeric))
);


--
-- Name: resource_estimate_materials; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.resource_estimate_materials (
    estimate_id bigint NOT NULL,
    material_code character varying(60) NOT NULL,
    quantity numeric(12,4) NOT NULL,
    unit character varying(20) NOT NULL,
    rate numeric(12,2),
    amount numeric(12,2),
    CONSTRAINT ck_estimate_material_qty CHECK ((quantity >= (0)::numeric))
);


--
-- Name: resource_estimates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.resource_estimates (
    estimate_id bigint NOT NULL,
    complaint_id bigint NOT NULL,
    measurement_id bigint,
    estimate_source character varying(30) NOT NULL,
    workers_required numeric(6,2),
    duration_hours numeric(8,2),
    labour_cost numeric(12,2),
    material_cost numeric(12,2),
    equipment_cost numeric(12,2),
    total_cost_min numeric(12,2),
    total_cost_expected numeric(12,2),
    total_cost_max numeric(12,2),
    rate_reference text,
    model_name character varying(150),
    model_version character varying(50),
    input_features jsonb DEFAULT '{}'::jsonb NOT NULL,
    is_current boolean DEFAULT true NOT NULL,
    created_by bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_estimate_range CHECK (((total_cost_min IS NULL) OR (total_cost_max IS NULL) OR (total_cost_min <= total_cost_max))),
    CONSTRAINT ck_estimate_source CHECK (((estimate_source)::text = ANY ((ARRAY['AI_MODEL'::character varying, 'RULE_BASED'::character varying, 'STEP10_PRECOMPUTED'::character varying, 'CONTRACTOR_INSPECTION'::character varying, 'OFFICER_OVERRIDE'::character varying])::text[]))),
    CONSTRAINT ck_estimate_values CHECK ((((workers_required IS NULL) OR (workers_required > (0)::numeric)) AND ((duration_hours IS NULL) OR (duration_hours > (0)::numeric)) AND ((total_cost_expected IS NULL) OR (total_cost_expected >= (0)::numeric))))
);


--
-- Name: resource_estimates_estimate_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.resource_estimates ALTER COLUMN estimate_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.resource_estimates_estimate_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: resources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.resources (
    resource_id bigint NOT NULL,
    resource_name character varying(150) NOT NULL,
    resource_type character varying(100) NOT NULL,
    quantity numeric(12,2) NOT NULL,
    unit character varying(50) NOT NULL,
    availability_status character varying(30) DEFAULT 'AVAILABLE'::character varying NOT NULL,
    cost_per_unit numeric(12,2),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_resources_availability CHECK (((availability_status)::text = ANY (ARRAY[('AVAILABLE'::character varying)::text, ('IN_USE'::character varying)::text, ('MAINTENANCE'::character varying)::text, ('UNAVAILABLE'::character varying)::text]))),
    CONSTRAINT ck_resources_cost CHECK (((cost_per_unit IS NULL) OR (cost_per_unit >= (0)::numeric))),
    CONSTRAINT ck_resources_name CHECK ((btrim((resource_name)::text) <> ''::text)),
    CONSTRAINT ck_resources_quantity CHECK ((quantity >= (0)::numeric)),
    CONSTRAINT ck_resources_type CHECK ((btrim((resource_type)::text) <> ''::text))
);


--
-- Name: resources_resource_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.resources ALTER COLUMN resource_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.resources_resource_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: roads; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.roads (
    road_id bigint NOT NULL,
    road_name character varying(200),
    road_type character varying(100),
    ward_id bigint,
    source text NOT NULL,
    geometry public.geometry(Geometry,4326) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_roads_name CHECK (((road_name IS NULL) OR (btrim((road_name)::text) <> ''::text)))
);


--
-- Name: roads_import_staging; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.roads_import_staging (
    ogc_fid integer NOT NULL,
    road_name character varying,
    road_type character varying,
    wkb_geometry public.geometry(MultiLineString,4326)
);


--
-- Name: roads_import_staging_ogc_fid_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.roads_import_staging_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: roads_import_staging_ogc_fid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.roads_import_staging_ogc_fid_seq OWNED BY public.roads_import_staging.ogc_fid;


--
-- Name: roads_road_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.roads ALTER COLUMN road_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.roads_road_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: route_stops; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.route_stops (
    route_stop_id bigint NOT NULL,
    route_id bigint NOT NULL,
    work_order_id bigint NOT NULL,
    stop_order integer NOT NULL,
    arrival_time timestamp with time zone,
    completion_time timestamp with time zone,
    CONSTRAINT ck_route_stop_completion CHECK (((completion_time IS NULL) OR (arrival_time IS NULL) OR (completion_time >= arrival_time))),
    CONSTRAINT ck_route_stop_order CHECK ((stop_order > 0))
);


--
-- Name: route_stops_route_stop_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.route_stops ALTER COLUMN route_stop_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.route_stops_route_stop_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: routes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.routes (
    route_id bigint NOT NULL,
    team_id bigint NOT NULL,
    schedule_date date NOT NULL,
    start_location public.geometry(Point,4326),
    end_location public.geometry(Point,4326),
    total_distance numeric(12,2),
    estimated_duration interval,
    status character varying(30) DEFAULT 'PLANNED'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_routes_distance CHECK (((total_distance IS NULL) OR (total_distance >= (0)::numeric))),
    CONSTRAINT ck_routes_duration CHECK (((estimated_duration IS NULL) OR (estimated_duration >= '00:00:00'::interval))),
    CONSTRAINT ck_routes_status CHECK (((status)::text = ANY (ARRAY[('PLANNED'::character varying)::text, ('OPTIMIZED'::character varying)::text, ('IN_PROGRESS'::character varying)::text, ('COMPLETED'::character varying)::text, ('CANCELLED'::character varying)::text])))
);


--
-- Name: routes_route_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.routes ALTER COLUMN route_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.routes_route_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: schedules; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schedules (
    schedule_id bigint NOT NULL,
    work_order_id bigint NOT NULL,
    team_id bigint NOT NULL,
    scheduled_date date NOT NULL,
    start_time time without time zone NOT NULL,
    end_time time without time zone NOT NULL,
    status character varying(30) DEFAULT 'PLANNED'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_schedules_status CHECK (((status)::text = ANY (ARRAY[('PLANNED'::character varying)::text, ('CONFIRMED'::character varying)::text, ('IN_PROGRESS'::character varying)::text, ('COMPLETED'::character varying)::text, ('CANCELLED'::character varying)::text]))),
    CONSTRAINT ck_schedules_time CHECK ((end_time > start_time))
);


--
-- Name: schedules_schedule_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.schedules ALTER COLUMN schedule_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.schedules_schedule_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: site_inspections; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.site_inspections (
    inspection_id bigint NOT NULL,
    complaint_id bigint NOT NULL,
    action_plan_id bigint,
    contractor_id bigint NOT NULL,
    inspected_by_user_id bigint,
    inspected_at timestamp with time zone DEFAULT now() NOT NULL,
    inspector_location public.geometry(Point,4326),
    inspector_accuracy_m numeric(8,2),
    distance_from_complaint_m numeric(10,2),
    issue_confirmed boolean NOT NULL,
    findings text NOT NULL,
    measurement_id bigint,
    revised_estimate_id bigint,
    expected_completion_date date,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_inspection_findings CHECK ((btrim(findings) <> ''::text))
);


--
-- Name: site_inspections_inspection_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.site_inspections ALTER COLUMN inspection_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.site_inspections_inspection_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: step13_action_plans; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.step13_action_plans (
    action_plan_id character varying(100) NOT NULL,
    schedule_date date NOT NULL,
    team_id character varying(20) NOT NULL,
    job_count integer NOT NULL,
    jobs text NOT NULL,
    priority_sum numeric(12,3),
    priority_avg numeric(8,3),
    priority_max numeric(8,3),
    priority_min numeric(8,3),
    workers_required numeric(8,2) NOT NULL,
    equipment text NOT NULL,
    prototype_team_equipment text,
    start_time time without time zone NOT NULL,
    end_time time without time zone NOT NULL,
    service_time_h numeric(12,3) NOT NULL,
    travel_time_h numeric(12,3) NOT NULL,
    total_route_time_h numeric(12,3) NOT NULL,
    distance_km numeric(14,3) NOT NULL,
    estimated_cost numeric(14,2) NOT NULL,
    route text NOT NULL,
    status character varying(50) NOT NULL,
    CONSTRAINT ck_step13_action_cost CHECK ((estimated_cost >= (0)::numeric)),
    CONSTRAINT ck_step13_action_distance CHECK ((distance_km >= (0)::numeric)),
    CONSTRAINT ck_step13_action_job_count CHECK ((job_count > 0)),
    CONSTRAINT ck_step13_action_service CHECK ((service_time_h >= (0)::numeric)),
    CONSTRAINT ck_step13_action_times CHECK ((end_time > start_time)),
    CONSTRAINT ck_step13_action_total CHECK ((total_route_time_h >= (0)::numeric)),
    CONSTRAINT ck_step13_action_travel CHECK ((travel_time_h >= (0)::numeric)),
    CONSTRAINT ck_step13_action_workers CHECK ((workers_required > (0)::numeric))
);


--
-- Name: step13_cluster_complaint; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.step13_cluster_complaint (
    cluster_id character varying(50) NOT NULL,
    job_id character varying(50) NOT NULL
);


--
-- Name: step13_clusters; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.step13_clusters (
    cluster_id character varying(50) NOT NULL,
    work_type character varying(30) NOT NULL,
    complaint_count integer NOT NULL,
    total_service_hours numeric(10,3) NOT NULL,
    max_workers numeric(6,2) NOT NULL,
    required_equipment text,
    serviceability_status character varying(30) NOT NULL,
    required_shift_blocks numeric(10,3),
    centroid_latitude double precision,
    centroid_longitude double precision,
    internal_radius_m numeric(12,3),
    CONSTRAINT ck_step13_cluster_count CHECK ((complaint_count >= 0)),
    CONSTRAINT ck_step13_cluster_service CHECK ((total_service_hours >= (0)::numeric)),
    CONSTRAINT ck_step13_cluster_work_type CHECK (((work_type)::text = ANY (ARRAY[('ROAD'::character varying)::text, ('WATER'::character varying)::text, ('GARBAGE'::character varying)::text, ('ELECTRICITY'::character varying)::text]))),
    CONSTRAINT ck_step13_cluster_workers CHECK ((max_workers >= (0)::numeric))
);


--
-- Name: step13_route_stops; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.step13_route_stops (
    route_id bigint NOT NULL,
    stop_order integer NOT NULL,
    node_type character varying(20) NOT NULL,
    job_id character varying(50),
    latitude double precision,
    longitude double precision,
    travel_distance_m numeric(14,3),
    travel_time_s numeric(12,3),
    CONSTRAINT ck_step13_route_stop_distance CHECK (((travel_distance_m IS NULL) OR (travel_distance_m >= (0)::numeric))),
    CONSTRAINT ck_step13_route_stop_order CHECK ((stop_order >= 0)),
    CONSTRAINT ck_step13_route_stop_time CHECK (((travel_time_s IS NULL) OR (travel_time_s >= (0)::numeric))),
    CONSTRAINT ck_step13_route_stop_type CHECK (((node_type)::text = ANY (ARRAY[('DEPOT'::character varying)::text, ('JOB'::character varying)::text])))
);


--
-- Name: step13_routes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.step13_routes (
    route_id bigint NOT NULL,
    team_id character varying(20) NOT NULL,
    schedule_date date NOT NULL,
    distance_km numeric(14,3) DEFAULT 0 NOT NULL,
    travel_time_h numeric(12,3) DEFAULT 0 NOT NULL,
    service_time_h numeric(12,3) DEFAULT 0 NOT NULL,
    total_route_time_h numeric(12,3) DEFAULT 0 NOT NULL,
    finish_time time without time zone,
    status character varying(40) NOT NULL,
    source character varying(100),
    CONSTRAINT ck_step13_route_distance CHECK ((distance_km >= (0)::numeric)),
    CONSTRAINT ck_step13_route_service CHECK ((service_time_h >= (0)::numeric)),
    CONSTRAINT ck_step13_route_total CHECK ((total_route_time_h >= (0)::numeric)),
    CONSTRAINT ck_step13_route_travel CHECK ((travel_time_h >= (0)::numeric))
);


--
-- Name: step13_routes_route_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.step13_routes_route_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: step13_routes_route_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.step13_routes_route_id_seq OWNED BY public.step13_routes.route_id;


--
-- Name: step13_schedule_job; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.step13_schedule_job (
    schedule_id character varying(100) NOT NULL,
    job_id character varying(50) NOT NULL,
    sequence_no integer NOT NULL,
    cluster_id character varying(50),
    planned_start timestamp without time zone NOT NULL,
    planned_end timestamp without time zone NOT NULL,
    service_duration_h numeric(10,3) NOT NULL,
    travel_distance_m numeric(14,3),
    travel_time_min numeric(10,3),
    priority_score numeric(8,3),
    estimated_cost numeric(14,2),
    status character varying(40) NOT NULL,
    repair_action character varying(150),
    CONSTRAINT ck_step13_schedule_job_distance CHECK (((travel_distance_m IS NULL) OR (travel_distance_m >= (0)::numeric))),
    CONSTRAINT ck_step13_schedule_job_sequence CHECK ((sequence_no > 0)),
    CONSTRAINT ck_step13_schedule_job_service CHECK ((service_duration_h >= (0)::numeric)),
    CONSTRAINT ck_step13_schedule_job_times CHECK ((planned_end > planned_start)),
    CONSTRAINT ck_step13_schedule_job_travel CHECK (((travel_time_min IS NULL) OR (travel_time_min >= (0)::numeric)))
);


--
-- Name: step13_schedules; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.step13_schedules (
    schedule_id character varying(100) NOT NULL,
    team_id character varying(20) NOT NULL,
    schedule_date date NOT NULL,
    schedule_status character varying(40) NOT NULL,
    source character varying(100)
);


--
-- Name: step13_team_equipment; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.step13_team_equipment (
    team_id character varying(20) NOT NULL,
    equipment_type character varying(150) NOT NULL,
    quantity integer DEFAULT 1 NOT NULL,
    available boolean DEFAULT true NOT NULL,
    valid_from date,
    valid_to date,
    source character varying(100),
    assumption_note text,
    CONSTRAINT ck_step13_equipment_dates CHECK (((valid_to IS NULL) OR (valid_from IS NULL) OR (valid_to >= valid_from))),
    CONSTRAINT ck_step13_equipment_quantity CHECK ((quantity >= 0))
);


--
-- Name: step13_teams; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.step13_teams (
    team_id character varying(20) NOT NULL,
    team_name character varying(150) NOT NULL,
    work_type character varying(30) NOT NULL,
    worker_capacity numeric(6,2) NOT NULL,
    shift_start time without time zone NOT NULL,
    shift_end time without time zone NOT NULL,
    source character varying(100) NOT NULL,
    assumption_note text,
    CONSTRAINT ck_step13_team_shift CHECK ((shift_end > shift_start)),
    CONSTRAINT ck_step13_team_work_type CHECK (((work_type)::text = ANY (ARRAY[('ROAD'::character varying)::text, ('WATER'::character varying)::text, ('GARBAGE'::character varying)::text, ('ELECTRICITY'::character varying)::text]))),
    CONSTRAINT ck_step13_team_workers CHECK ((worker_capacity > (0)::numeric))
);


--
-- Name: user_consents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_consents (
    consent_id bigint NOT NULL,
    user_id bigint NOT NULL,
    consent_type character varying(30) NOT NULL,
    granted boolean NOT NULL,
    notice_version character varying(20) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    ip_address inet,
    CONSTRAINT ck_consent_type CHECK (((consent_type)::text = ANY ((ARRAY['PRIVACY_NOTICE'::character varying, 'PUBLIC_PHOTO'::character varying, 'AI_TRAINING'::character varying, 'WHATSAPP_MESSAGES'::character varying])::text[])))
);


--
-- Name: user_consents_consent_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.user_consents ALTER COLUMN consent_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.user_consents_consent_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    user_id bigint NOT NULL,
    full_name character varying(150) NOT NULL,
    email character varying(255),
    phone character varying(20),
    password_hash text NOT NULL,
    role character varying(30) DEFAULT 'CITIZEN'::character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    email_verified_at timestamp with time zone,
    phone_verified_at timestamp with time zone,
    whatsapp_opt_in boolean DEFAULT false NOT NULL,
    email_opt_in boolean DEFAULT true NOT NULL,
    preferred_language character varying(5) DEFAULT 'en'::character varying NOT NULL,
    trust_score numeric(5,2) DEFAULT 50.00 NOT NULL,
    failed_login_count integer DEFAULT 0 NOT NULL,
    locked_until timestamp with time zone,
    last_login_at timestamp with time zone,
    password_changed_at timestamp with time zone,
    must_change_password boolean DEFAULT false NOT NULL,
    created_by_user_id bigint,
    totp_secret_enc text,
    totp_enabled boolean DEFAULT false NOT NULL,
    totp_last_used_step bigint,
    token_valid_after timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_users_contact_present CHECK (((email IS NOT NULL) OR (phone IS NOT NULL))),
    CONSTRAINT ck_users_failed_logins CHECK ((failed_login_count >= 0)),
    CONSTRAINT ck_users_full_name CHECK ((btrim((full_name)::text) <> ''::text)),
    CONSTRAINT ck_users_language CHECK (((preferred_language)::text = ANY ((ARRAY['en'::character varying, 'mr'::character varying, 'hi'::character varying])::text[]))),
    CONSTRAINT ck_users_phone_format CHECK (((phone IS NULL) OR ((phone)::text ~ '^\+?[0-9]{10,15}$'::text))),
    CONSTRAINT ck_users_role CHECK (((role)::text = ANY ((ARRAY['CITIZEN'::character varying, 'OFFICER'::character varying, 'ADMIN'::character varying, 'CONTRACTOR'::character varying, 'CONTRACTOR_STAFF'::character varying, 'FIELD_TEAM'::character varying])::text[]))),
    CONSTRAINT ck_users_totp CHECK (((NOT totp_enabled) OR (totp_secret_enc IS NOT NULL))),
    CONSTRAINT ck_users_trust_score CHECK (((trust_score >= (0)::numeric) AND (trust_score <= (100)::numeric)))
);


--
-- Name: COLUMN users.totp_secret_enc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.totp_secret_enc IS 'Base64(IV || AES-256-GCM ciphertext) of the RFC 6238 secret. Key from env TOTP_ENC_KEY (32 bytes, base64). Required for OFFICER and ADMIN.';


--
-- Name: COLUMN users.token_valid_after; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.token_valid_after IS 'Logout-all, password change, role change, disable: set to now(); JWTs with iat < token_valid_after are rejected.';


--
-- Name: users_user_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.users ALTER COLUMN user_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.users_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: v_complaint_timeline; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_complaint_timeline AS
 SELECT h.complaint_id,
    c.public_ref,
    c.user_id AS owner_user_id,
    h.old_status,
    h.new_status,
    h.remarks,
    h.actor_role,
    h.changed_at,
    h.status_history_id
   FROM (public.complaint_status_history h
     JOIN public.complaints c ON ((c.complaint_id = h.complaint_id)));


--
-- Name: v_contractor_worklist; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_contractor_worklist AS
 SELECT ap.contractor_id,
    ap.action_plan_id,
    ap.plan_code,
    ap.planned_date,
    ap.status AS plan_status,
    i.sequence_no,
    c.complaint_id,
    c.public_ref,
    c.title,
    c.status AS complaint_status,
    cat.category_name,
    public.st_y(c.location) AS latitude,
    public.st_x(c.location) AS longitude,
    c.landmark,
    i.planned_start,
    i.planned_end,
    i.est_workers,
    i.est_cost
   FROM (((public.action_plans ap
     JOIN public.action_plan_items i ON (((i.action_plan_id = ap.action_plan_id) AND ((i.item_status)::text = 'ACTIVE'::text))))
     JOIN public.complaints c ON ((c.complaint_id = i.complaint_id)))
     LEFT JOIN public.complaint_categories cat ON ((cat.category_id = c.category_id)))
  WHERE ((ap.status)::text = ANY ((ARRAY['ASSIGNED'::character varying, 'IN_PROGRESS'::character varying])::text[]));


--
-- Name: v_current_consents; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_current_consents AS
 SELECT DISTINCT ON (user_id, consent_type) user_id,
    consent_type,
    granted,
    notice_version,
    created_at
   FROM public.user_consents
  ORDER BY user_id, consent_type, created_at DESC, consent_id DESC;


--
-- Name: v_duplicate_review_queue; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_duplicate_review_queue AS
 SELECT duplicate_relation_id,
    complaint_id,
    similar_complaint_id,
    master_complaint_id,
    text_similarity,
    distance_meters,
    time_difference_hours,
    duplicate_score,
    decision,
    decision_source,
    review_required,
    review_decision,
    reviewed_by,
    reviewed_at,
    review_comment,
    created_at
   FROM public.duplicate_relation dr
  WHERE ((review_required = true) AND (reviewed_at IS NULL));


--
-- Name: wards; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.wards (
    ward_id bigint NOT NULL,
    ward_number integer NOT NULL,
    ward_name character varying(150),
    source text NOT NULL,
    geometry public.geometry(Geometry,4326) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    ward_scheme character varying(30) DEFAULT 'ANALYTICAL_GIS_23'::character varying NOT NULL,
    CONSTRAINT ck_wards_number CHECK ((ward_number > 0))
);


--
-- Name: COLUMN wards.ward_scheme; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.wards.ward_scheme IS 'ANALYTICAL_GIS_23 = the 23 analytical GIS units used by CivicBrain. Not the 2025 electoral structure (14 wards / 28 seats).';


--
-- Name: v_officer_complaint_queue; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_officer_complaint_queue AS
 SELECT c.complaint_id,
    c.public_ref,
    c.title,
    c.status,
        CASE
            WHEN ((c.status)::text = ANY ((ARRAY['SUBMITTED'::character varying, 'VERIFIED'::character varying, 'REOPENED'::character varying])::text[])) THEN 'NEW'::text
            WHEN ((c.status)::text = ANY ((ARRAY['SCHEDULED'::character varying, 'ASSIGNED'::character varying, 'INSPECTED'::character varying, 'IN_PROGRESS'::character varying])::text[])) THEN 'IN_PROGRESS'::text
            WHEN ((c.status)::text = ANY ((ARRAY['COMPLETED'::character varying, 'CLOSED'::character varying])::text[])) THEN 'COMPLETED'::text
            ELSE 'CLOSED_OUT'::text
        END AS dashboard_tab,
    cat.category_name,
    cat.work_type_code,
    c.ward_id,
    w.ward_number,
    public.st_y(c.location) AS latitude,
    public.st_x(c.location) AS longitude,
    c.submitted_at,
    c.duplicate_status,
    ( SELECT count(*) AS count
           FROM public.complaints ch
          WHERE (ch.master_complaint_id = c.complaint_id)) AS linked_duplicates,
    COALESCE(c.current_priority_score, pa.final_score) AS priority_score,
    COALESCE(c.current_priority_level, pa.priority_level) AS priority_level,
    re.workers_required,
    re.duration_hours,
    re.total_cost_expected,
    c.authenticity_status,
    c.authenticity_score,
    c.ai_status,
    c.current_action_plan_id,
    ap.plan_code,
    ct.firm_name AS contractor_name,
    c.is_synthetic
   FROM ((((((public.complaints c
     LEFT JOIN public.complaint_categories cat ON ((cat.category_id = c.category_id)))
     LEFT JOIN public.wards w ON ((w.ward_id = c.ward_id)))
     LEFT JOIN LATERAL ( SELECT p.final_score,
            p.priority_level
           FROM public.priority_assessments p
          WHERE ((p.complaint_id = c.complaint_id) AND p.is_current)
          ORDER BY p.calculated_at DESC
         LIMIT 1) pa ON (true))
     LEFT JOIN LATERAL ( SELECT r.workers_required,
            r.duration_hours,
            r.total_cost_expected
           FROM public.resource_estimates r
          WHERE ((r.complaint_id = c.complaint_id) AND r.is_current)
          ORDER BY r.created_at DESC
         LIMIT 1) re ON (true))
     LEFT JOIN public.action_plans ap ON ((ap.action_plan_id = c.current_action_plan_id)))
     LEFT JOIN public.contractors ct ON ((ct.contractor_id = c.assigned_contractor_id)))
  WHERE (c.master_complaint_id IS NULL);


--
-- Name: v_public_complaint_map; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_public_complaint_map AS
 SELECT c.public_ref,
    cat.category_name,
    cat.work_type_code,
        CASE
            WHEN ((c.status)::text = ANY ((ARRAY['SUBMITTED'::character varying, 'VERIFIED'::character varying, 'REOPENED'::character varying])::text[])) THEN 'OPEN'::text
            WHEN ((c.status)::text = ANY ((ARRAY['SCHEDULED'::character varying, 'ASSIGNED'::character varying, 'INSPECTED'::character varying, 'IN_PROGRESS'::character varying])::text[])) THEN 'IN_PROGRESS'::text
            ELSE 'RESOLVED'::text
        END AS public_status,
    w.ward_number,
    round((public.st_y(public.st_snaptogrid(c.location, (0.002)::double precision)))::numeric, 3) AS latitude,
    round((public.st_x(public.st_snaptogrid(c.location, (0.002)::double precision)))::numeric, 3) AS longitude,
    (c.submitted_at)::date AS reported_on,
    ( SELECT count(*) AS count
           FROM public.complaint_votes v
          WHERE ((v.complaint_id = c.complaint_id) AND ((v.vote_type)::text = 'UP'::text))) AS supporters,
    c.is_synthetic
   FROM ((public.complaints c
     LEFT JOIN public.complaint_categories cat ON ((cat.category_id = c.category_id)))
     LEFT JOIN public.wards w ON ((w.ward_id = c.ward_id)))
  WHERE (((c.status)::text <> ALL ((ARRAY['REJECTED'::character varying, 'MERGED'::character varying])::text[])) AND (c.master_complaint_id IS NULL));


--
-- Name: ward_geometry_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ward_geometry_history (
    ward_id bigint,
    ward_number integer,
    geometry_before public.geometry(Geometry,4326),
    archived_at timestamp with time zone DEFAULT now(),
    version text
);


--
-- Name: TABLE ward_geometry_history; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.ward_geometry_history IS 'Ward geometries archived before a geometry change. version = the geometry version that replaced them (v2 = topology-cleaned, V3 migration).';


--
-- Name: ward_reassignment_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ward_reassignment_log (
    entity text,
    entity_id bigint,
    old_ward_id bigint,
    new_ward_id bigint,
    logged_at timestamp with time zone DEFAULT now()
);


--
-- Name: TABLE ward_reassignment_log; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.ward_reassignment_log IS 'One row per complaint / poi / road whose ward_id was changed by a ward geometry migration (logged before the update).';


--
-- Name: wards_ward_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.wards ALTER COLUMN ward_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.wards_ward_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: work_completions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.work_completions (
    completion_id bigint NOT NULL,
    complaint_id bigint NOT NULL,
    action_plan_id bigint,
    contractor_id bigint NOT NULL,
    submitted_by_user_id bigint,
    completed_at timestamp with time zone DEFAULT now() NOT NULL,
    completion_location public.geometry(Point,4326),
    completion_accuracy_m numeric(8,2),
    distance_from_complaint_m numeric(10,2),
    work_summary text NOT NULL,
    actual_workers numeric(6,2),
    actual_hours numeric(8,2),
    actual_cost numeric(12,2),
    materials_used jsonb DEFAULT '[]'::jsonb NOT NULL,
    verification_status character varying(20) DEFAULT 'PENDING'::character varying NOT NULL,
    verified_by_user_id bigint,
    verified_at timestamp with time zone,
    verification_remarks text,
    CONSTRAINT ck_completion_actuals CHECK ((((actual_cost IS NULL) OR (actual_cost >= (0)::numeric)) AND ((actual_hours IS NULL) OR (actual_hours >= (0)::numeric)) AND ((actual_workers IS NULL) OR (actual_workers > (0)::numeric)))),
    CONSTRAINT ck_completion_summary CHECK ((btrim(work_summary) <> ''::text)),
    CONSTRAINT ck_completion_verification CHECK (((verification_status)::text = ANY ((ARRAY['PENDING'::character varying, 'APPROVED'::character varying, 'REJECTED'::character varying])::text[]))),
    CONSTRAINT ck_completion_verified_meta CHECK ((((verification_status)::text = 'PENDING'::text) OR ((verified_by_user_id IS NOT NULL) AND (verified_at IS NOT NULL))))
);


--
-- Name: work_completions_completion_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.work_completions ALTER COLUMN completion_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.work_completions_completion_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: work_order_resources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.work_order_resources (
    work_order_resource_id bigint NOT NULL,
    work_order_id bigint NOT NULL,
    resource_id bigint NOT NULL,
    quantity numeric(12,2) NOT NULL,
    estimated_cost numeric(12,2),
    actual_cost numeric(12,2),
    CONSTRAINT ck_work_order_resources_actual_cost CHECK (((actual_cost IS NULL) OR (actual_cost >= (0)::numeric))),
    CONSTRAINT ck_work_order_resources_estimated_cost CHECK (((estimated_cost IS NULL) OR (estimated_cost >= (0)::numeric))),
    CONSTRAINT ck_work_order_resources_quantity CHECK ((quantity > (0)::numeric))
);


--
-- Name: work_order_resources_work_order_resource_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.work_order_resources ALTER COLUMN work_order_resource_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.work_order_resources_work_order_resource_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: work_orders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.work_orders (
    work_order_id bigint NOT NULL,
    complaint_id bigint NOT NULL,
    team_id bigint,
    assigned_officer_id bigint,
    description text NOT NULL,
    status character varying(30) DEFAULT 'CREATED'::character varying NOT NULL,
    estimated_cost numeric(12,2),
    actual_cost numeric(12,2),
    estimated_duration interval,
    actual_duration interval,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    CONSTRAINT ck_work_orders_actual_cost CHECK (((actual_cost IS NULL) OR (actual_cost >= (0)::numeric))),
    CONSTRAINT ck_work_orders_actual_duration CHECK (((actual_duration IS NULL) OR (actual_duration >= '00:00:00'::interval))),
    CONSTRAINT ck_work_orders_completed_at CHECK (((completed_at IS NULL) OR (completed_at >= created_at))),
    CONSTRAINT ck_work_orders_description CHECK ((btrim(description) <> ''::text)),
    CONSTRAINT ck_work_orders_estimated_cost CHECK (((estimated_cost IS NULL) OR (estimated_cost >= (0)::numeric))),
    CONSTRAINT ck_work_orders_estimated_duration CHECK (((estimated_duration IS NULL) OR (estimated_duration >= '00:00:00'::interval))),
    CONSTRAINT ck_work_orders_status CHECK (((status)::text = ANY (ARRAY[('CREATED'::character varying)::text, ('ASSIGNED'::character varying)::text, ('SCHEDULED'::character varying)::text, ('IN_PROGRESS'::character varying)::text, ('COMPLETED'::character varying)::text, ('CANCELLED'::character varying)::text])))
);


--
-- Name: work_orders_work_order_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.work_orders ALTER COLUMN work_order_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.work_orders_work_order_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: work_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.work_types (
    work_type_code character varying(30) NOT NULL,
    display_name character varying(100) NOT NULL,
    is_operational boolean DEFAULT true NOT NULL,
    note text,
    CONSTRAINT ck_work_types_code CHECK (((work_type_code)::text = ANY ((ARRAY['ROAD'::character varying, 'WATER'::character varying, 'GARBAGE'::character varying, 'ELECTRICITY'::character varying, 'REVIEW_REQUIRED'::character varying])::text[])))
);


--
-- Name: yolo_detections; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.yolo_detections (
    detection_id bigint NOT NULL,
    image_id bigint NOT NULL,
    detected_class character varying(100) NOT NULL,
    confidence numeric(5,4) NOT NULL,
    bbox_x numeric NOT NULL,
    bbox_y numeric NOT NULL,
    bbox_width numeric NOT NULL,
    bbox_height numeric NOT NULL,
    model_name character varying(150) NOT NULL,
    model_version character varying(50) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_yolo_bbox_height CHECK ((bbox_height > (0)::numeric)),
    CONSTRAINT ck_yolo_bbox_width CHECK ((bbox_width > (0)::numeric)),
    CONSTRAINT ck_yolo_bbox_x CHECK ((bbox_x >= (0)::numeric)),
    CONSTRAINT ck_yolo_bbox_y CHECK ((bbox_y >= (0)::numeric)),
    CONSTRAINT ck_yolo_confidence CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))),
    CONSTRAINT ck_yolo_detected_class CHECK ((btrim((detected_class)::text) <> ''::text)),
    CONSTRAINT ck_yolo_model_name CHECK ((btrim((model_name)::text) <> ''::text)),
    CONSTRAINT ck_yolo_model_version CHECK ((btrim((model_version)::text) <> ''::text))
);


--
-- Name: yolo_detections_detection_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.yolo_detections ALTER COLUMN detection_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.yolo_detections_detection_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: roads_import_staging ogc_fid; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roads_import_staging ALTER COLUMN ogc_fid SET DEFAULT nextval('public.roads_import_staging_ogc_fid_seq'::regclass);


--
-- Name: step13_routes route_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.step13_routes ALTER COLUMN route_id SET DEFAULT nextval('public.step13_routes_route_id_seq'::regclass);


--
-- Name: action_plan_items action_plan_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_plan_items
    ADD CONSTRAINT action_plan_items_pkey PRIMARY KEY (item_id);


--
-- Name: action_plan_revisions action_plan_revisions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_plan_revisions
    ADD CONSTRAINT action_plan_revisions_pkey PRIMARY KEY (revision_id);


--
-- Name: action_plans action_plans_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_plans
    ADD CONSTRAINT action_plans_pkey PRIMARY KEY (action_plan_id);


--
-- Name: auth_events auth_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_events
    ADD CONSTRAINT auth_events_pkey PRIMARY KEY (auth_event_id);


--
-- Name: auth_otp_codes auth_otp_codes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_otp_codes
    ADD CONSTRAINT auth_otp_codes_pkey PRIMARY KEY (otp_id);


--
-- Name: auth_refresh_tokens auth_refresh_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_refresh_tokens
    ADD CONSTRAINT auth_refresh_tokens_pkey PRIMARY KEY (refresh_token_id);


--
-- Name: authenticity_checks authenticity_checks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.authenticity_checks
    ADD CONSTRAINT authenticity_checks_pkey PRIMARY KEY (check_id);


--
-- Name: capture_sessions capture_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.capture_sessions
    ADD CONSTRAINT capture_sessions_pkey PRIMARY KEY (capture_session_id);


--
-- Name: complaint_feedback complaint_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaint_feedback
    ADD CONSTRAINT complaint_feedback_pkey PRIMARY KEY (feedback_id);


--
-- Name: complaint_status_transitions complaint_status_transitions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaint_status_transitions
    ADD CONSTRAINT complaint_status_transitions_pkey PRIMARY KEY (from_status, to_status);


--
-- Name: complaint_votes complaint_votes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaint_votes
    ADD CONSTRAINT complaint_votes_pkey PRIMARY KEY (complaint_id, user_id);


--
-- Name: contractor_equipment contractor_equipment_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractor_equipment
    ADD CONSTRAINT contractor_equipment_pkey PRIMARY KEY (contractor_id, equipment_code);


--
-- Name: contractor_work_types contractor_work_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractor_work_types
    ADD CONSTRAINT contractor_work_types_pkey PRIMARY KEY (contractor_id, work_type_code);


--
-- Name: contractor_workers contractor_workers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractor_workers
    ADD CONSTRAINT contractor_workers_pkey PRIMARY KEY (worker_id);


--
-- Name: contractor_workers contractor_workers_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractor_workers
    ADD CONSTRAINT contractor_workers_user_id_key UNIQUE (user_id);


--
-- Name: contractors contractors_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractors
    ADD CONSTRAINT contractors_pkey PRIMARY KEY (contractor_id);


--
-- Name: contractors contractors_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractors
    ADD CONSTRAINT contractors_user_id_key UNIQUE (user_id);


--
-- Name: data_subject_requests data_subject_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_subject_requests
    ADD CONSTRAINT data_subject_requests_pkey PRIMARY KEY (request_id);


--
-- Name: defect_measurements defect_measurements_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.defect_measurements
    ADD CONSTRAINT defect_measurements_pkey PRIMARY KEY (measurement_id);


--
-- Name: depots depots_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.depots
    ADD CONSTRAINT depots_pkey PRIMARY KEY (depot_id);


--
-- Name: duplicate_relation duplicate_relation_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.duplicate_relation
    ADD CONSTRAINT duplicate_relation_pkey PRIMARY KEY (duplicate_relation_id);


--
-- Name: equipment_catalog equipment_catalog_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.equipment_catalog
    ADD CONSTRAINT equipment_catalog_pkey PRIMARY KEY (equipment_code);


--
-- Name: jobs jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (job_id);


--
-- Name: material_catalog material_catalog_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.material_catalog
    ADD CONSTRAINT material_catalog_pkey PRIMARY KEY (material_code);


--
-- Name: notification_outbox notification_outbox_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_outbox
    ADD CONSTRAINT notification_outbox_pkey PRIMARY KEY (outbox_id);


--
-- Name: notification_templates notification_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_templates
    ADD CONSTRAINT notification_templates_pkey PRIMARY KEY (template_id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (notification_id);


--
-- Name: officer_scopes officer_scopes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.officer_scopes
    ADD CONSTRAINT officer_scopes_pkey PRIMARY KEY (officer_scope_id);


--
-- Name: optimizer_runs optimizer_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.optimizer_runs
    ADD CONSTRAINT optimizer_runs_pkey PRIMARY KEY (run_id);


--
-- Name: ai_classifications pk_ai_classifications; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_classifications
    ADD CONSTRAINT pk_ai_classifications PRIMARY KEY (classification_id);


--
-- Name: audit_logs pk_audit_logs; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT pk_audit_logs PRIMARY KEY (audit_id);


--
-- Name: complaint_categories pk_complaint_categories; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaint_categories
    ADD CONSTRAINT pk_complaint_categories PRIMARY KEY (category_id);


--
-- Name: complaint_images pk_complaint_images; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaint_images
    ADD CONSTRAINT pk_complaint_images PRIMARY KEY (image_id);


--
-- Name: complaint_status_history pk_complaint_status_history; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaint_status_history
    ADD CONSTRAINT pk_complaint_status_history PRIMARY KEY (status_history_id);


--
-- Name: complaints pk_complaints; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaints
    ADD CONSTRAINT pk_complaints PRIMARY KEY (complaint_id);


--
-- Name: duplicate_detections pk_duplicate_detections; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.duplicate_detections
    ADD CONSTRAINT pk_duplicate_detections PRIMARY KEY (duplicate_detection_id);


--
-- Name: field_teams pk_field_teams; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.field_teams
    ADD CONSTRAINT pk_field_teams PRIMARY KEY (team_id);


--
-- Name: municipal_boundary pk_municipal_boundary; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.municipal_boundary
    ADD CONSTRAINT pk_municipal_boundary PRIMARY KEY (boundary_id);


--
-- Name: officer_approvals pk_officer_approvals; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.officer_approvals
    ADD CONSTRAINT pk_officer_approvals PRIMARY KEY (approval_id);


--
-- Name: officers pk_officers; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.officers
    ADD CONSTRAINT pk_officers PRIMARY KEY (officer_id);


--
-- Name: pois pk_pois; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pois
    ADD CONSTRAINT pk_pois PRIMARY KEY (poi_id);


--
-- Name: priority_assessments pk_priority_assessments; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.priority_assessments
    ADD CONSTRAINT pk_priority_assessments PRIMARY KEY (priority_assessment_id);


--
-- Name: resources pk_resources; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resources
    ADD CONSTRAINT pk_resources PRIMARY KEY (resource_id);


--
-- Name: roads pk_roads; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roads
    ADD CONSTRAINT pk_roads PRIMARY KEY (road_id);


--
-- Name: route_stops pk_route_stops; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.route_stops
    ADD CONSTRAINT pk_route_stops PRIMARY KEY (route_stop_id);


--
-- Name: routes pk_routes; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.routes
    ADD CONSTRAINT pk_routes PRIMARY KEY (route_id);


--
-- Name: schedules pk_schedules; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedules
    ADD CONSTRAINT pk_schedules PRIMARY KEY (schedule_id);


--
-- Name: users pk_users; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT pk_users PRIMARY KEY (user_id);


--
-- Name: wards pk_wards; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wards
    ADD CONSTRAINT pk_wards PRIMARY KEY (ward_id);


--
-- Name: work_order_resources pk_work_order_resources; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_order_resources
    ADD CONSTRAINT pk_work_order_resources PRIMARY KEY (work_order_resource_id);


--
-- Name: work_orders pk_work_orders; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_orders
    ADD CONSTRAINT pk_work_orders PRIMARY KEY (work_order_id);


--
-- Name: yolo_detections pk_yolo_detections; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.yolo_detections
    ADD CONSTRAINT pk_yolo_detections PRIMARY KEY (detection_id);


--
-- Name: pois_import_raw pois_import_raw_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pois_import_raw
    ADD CONSTRAINT pois_import_raw_pkey PRIMARY KEY (poi_id);


--
-- Name: privacy_notices privacy_notices_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.privacy_notices
    ADD CONSTRAINT privacy_notices_pkey PRIMARY KEY (version);


--
-- Name: resource_estimate_equipment resource_estimate_equipment_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_estimate_equipment
    ADD CONSTRAINT resource_estimate_equipment_pkey PRIMARY KEY (estimate_id, equipment_code);


--
-- Name: resource_estimate_materials resource_estimate_materials_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_estimate_materials
    ADD CONSTRAINT resource_estimate_materials_pkey PRIMARY KEY (estimate_id, material_code);


--
-- Name: resource_estimates resource_estimates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_estimates
    ADD CONSTRAINT resource_estimates_pkey PRIMARY KEY (estimate_id);


--
-- Name: roads_import_staging roads_import_staging_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roads_import_staging
    ADD CONSTRAINT roads_import_staging_pkey PRIMARY KEY (ogc_fid);


--
-- Name: site_inspections site_inspections_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.site_inspections
    ADD CONSTRAINT site_inspections_pkey PRIMARY KEY (inspection_id);


--
-- Name: step13_action_plans step13_action_plans_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.step13_action_plans
    ADD CONSTRAINT step13_action_plans_pkey PRIMARY KEY (action_plan_id);


--
-- Name: step13_cluster_complaint step13_cluster_complaint_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.step13_cluster_complaint
    ADD CONSTRAINT step13_cluster_complaint_pkey PRIMARY KEY (cluster_id, job_id);


--
-- Name: step13_clusters step13_clusters_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.step13_clusters
    ADD CONSTRAINT step13_clusters_pkey PRIMARY KEY (cluster_id);


--
-- Name: step13_route_stops step13_route_stops_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.step13_route_stops
    ADD CONSTRAINT step13_route_stops_pkey PRIMARY KEY (route_id, stop_order);


--
-- Name: step13_routes step13_routes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.step13_routes
    ADD CONSTRAINT step13_routes_pkey PRIMARY KEY (route_id);


--
-- Name: step13_schedule_job step13_schedule_job_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.step13_schedule_job
    ADD CONSTRAINT step13_schedule_job_pkey PRIMARY KEY (schedule_id, job_id);


--
-- Name: step13_schedules step13_schedules_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.step13_schedules
    ADD CONSTRAINT step13_schedules_pkey PRIMARY KEY (schedule_id);


--
-- Name: step13_team_equipment step13_team_equipment_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.step13_team_equipment
    ADD CONSTRAINT step13_team_equipment_pkey PRIMARY KEY (team_id, equipment_type);


--
-- Name: step13_teams step13_teams_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.step13_teams
    ADD CONSTRAINT step13_teams_pkey PRIMARY KEY (team_id);


--
-- Name: action_plan_items uq_action_plan_item; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_plan_items
    ADD CONSTRAINT uq_action_plan_item UNIQUE (action_plan_id, complaint_id);


--
-- Name: action_plan_revisions uq_action_plan_revision; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_plan_revisions
    ADD CONSTRAINT uq_action_plan_revision UNIQUE (action_plan_id, version);


--
-- Name: action_plan_items uq_action_plan_sequence; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_plan_items
    ADD CONSTRAINT uq_action_plan_sequence UNIQUE (action_plan_id, sequence_no) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: action_plans uq_action_plans_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_plans
    ADD CONSTRAINT uq_action_plans_code UNIQUE (plan_code);


--
-- Name: authenticity_checks uq_authenticity_check; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.authenticity_checks
    ADD CONSTRAINT uq_authenticity_check UNIQUE NULLS NOT DISTINCT (complaint_id, image_id, check_code);


--
-- Name: complaint_categories uq_complaint_categories_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaint_categories
    ADD CONSTRAINT uq_complaint_categories_name UNIQUE (category_name);


--
-- Name: complaint_feedback uq_complaint_feedback; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaint_feedback
    ADD CONSTRAINT uq_complaint_feedback UNIQUE (complaint_id, user_id);


--
-- Name: duplicate_detections uq_duplicate_detection_pair; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.duplicate_detections
    ADD CONSTRAINT uq_duplicate_detection_pair UNIQUE (complaint_id_1, complaint_id_2, detection_method);


--
-- Name: field_teams uq_field_teams_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.field_teams
    ADD CONSTRAINT uq_field_teams_name UNIQUE (team_name);


--
-- Name: municipal_boundary uq_municipal_boundary_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.municipal_boundary
    ADD CONSTRAINT uq_municipal_boundary_name UNIQUE (municipality_name);


--
-- Name: notification_templates uq_notification_template; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_templates
    ADD CONSTRAINT uq_notification_template UNIQUE (template_code, channel, locale);


--
-- Name: notifications uq_notifications_dedupe; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT uq_notifications_dedupe UNIQUE (dedupe_key);


--
-- Name: officer_scopes uq_officer_scope; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.officer_scopes
    ADD CONSTRAINT uq_officer_scope UNIQUE NULLS NOT DISTINCT (officer_id, ward_id, work_type_code);


--
-- Name: officers uq_officers_employee_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.officers
    ADD CONSTRAINT uq_officers_employee_code UNIQUE (employee_code);


--
-- Name: officers uq_officers_user; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.officers
    ADD CONSTRAINT uq_officers_user UNIQUE (user_id);


--
-- Name: auth_refresh_tokens uq_refresh_token_hash; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_refresh_tokens
    ADD CONSTRAINT uq_refresh_token_hash UNIQUE (token_hash);


--
-- Name: resources uq_resources_name_type; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resources
    ADD CONSTRAINT uq_resources_name_type UNIQUE (resource_name, resource_type);


--
-- Name: route_stops uq_route_stop_order; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.route_stops
    ADD CONSTRAINT uq_route_stop_order UNIQUE (route_id, stop_order);


--
-- Name: route_stops uq_route_work_order; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.route_stops
    ADD CONSTRAINT uq_route_work_order UNIQUE (route_id, work_order_id);


--
-- Name: routes uq_routes_team_date; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.routes
    ADD CONSTRAINT uq_routes_team_date UNIQUE (team_id, schedule_date);


--
-- Name: schedules uq_schedules; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedules
    ADD CONSTRAINT uq_schedules UNIQUE (team_id, scheduled_date, start_time, end_time, work_order_id);


--
-- Name: step13_routes uq_step13_route_team_date; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.step13_routes
    ADD CONSTRAINT uq_step13_route_team_date UNIQUE (team_id, schedule_date);


--
-- Name: step13_schedule_job uq_step13_schedule_sequence; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.step13_schedule_job
    ADD CONSTRAINT uq_step13_schedule_sequence UNIQUE (schedule_id, sequence_no);


--
-- Name: users uq_users_email; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT uq_users_email UNIQUE (email);


--
-- Name: users uq_users_phone; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT uq_users_phone UNIQUE (phone);


--
-- Name: wards uq_wards_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wards
    ADD CONSTRAINT uq_wards_number UNIQUE (ward_number);


--
-- Name: work_order_resources uq_work_order_resource; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_order_resources
    ADD CONSTRAINT uq_work_order_resource UNIQUE (work_order_id, resource_id);


--
-- Name: work_orders uq_work_orders_complaint; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_orders
    ADD CONSTRAINT uq_work_orders_complaint UNIQUE (complaint_id);


--
-- Name: user_consents user_consents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_consents
    ADD CONSTRAINT user_consents_pkey PRIMARY KEY (consent_id);


--
-- Name: work_completions work_completions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_completions
    ADD CONSTRAINT work_completions_pkey PRIMARY KEY (completion_id);


--
-- Name: work_types work_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_types
    ADD CONSTRAINT work_types_pkey PRIMARY KEY (work_type_code);


--
-- Name: idx_action_plan_items_complaint; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_action_plan_items_complaint ON public.action_plan_items USING btree (complaint_id);


--
-- Name: idx_action_plans_contractor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_action_plans_contractor ON public.action_plans USING btree (contractor_id);


--
-- Name: idx_action_plans_route; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_action_plans_route ON public.action_plans USING gist (route_geometry);


--
-- Name: idx_action_plans_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_action_plans_status ON public.action_plans USING btree (status, planned_date);


--
-- Name: idx_ai_classifications_complaint_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_classifications_complaint_id ON public.ai_classifications USING btree (complaint_id);


--
-- Name: idx_audit_logs_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_logs_created_at ON public.audit_logs USING btree (created_at);


--
-- Name: idx_audit_logs_entity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_logs_entity ON public.audit_logs USING btree (entity_type, entity_id);


--
-- Name: idx_audit_logs_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_logs_user_id ON public.audit_logs USING btree (user_id);


--
-- Name: idx_auth_events_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_auth_events_created ON public.auth_events USING btree (created_at);


--
-- Name: idx_auth_events_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_auth_events_user ON public.auth_events USING btree (user_id, created_at DESC);


--
-- Name: idx_authenticity_checks_complaint; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_authenticity_checks_complaint ON public.authenticity_checks USING btree (complaint_id);


--
-- Name: idx_capture_sessions_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_capture_sessions_user ON public.capture_sessions USING btree (user_id, issued_at DESC);


--
-- Name: idx_complaint_images_capture; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_complaint_images_capture ON public.complaint_images USING gist (capture_location);


--
-- Name: idx_complaint_images_complaint_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_complaint_images_complaint_id ON public.complaint_images USING btree (complaint_id);


--
-- Name: idx_complaint_images_phash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_complaint_images_phash ON public.complaint_images USING btree (phash);


--
-- Name: idx_complaint_images_processing_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_complaint_images_processing_status ON public.complaint_images USING btree (processing_status);


--
-- Name: idx_complaint_images_role; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_complaint_images_role ON public.complaint_images USING btree (complaint_id, image_role);


--
-- Name: idx_complaint_images_sha256; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_complaint_images_sha256 ON public.complaint_images USING btree (sha256);


--
-- Name: idx_complaints_action_plan; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_complaints_action_plan ON public.complaints USING btree (current_action_plan_id);


--
-- Name: idx_complaints_ai_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_complaints_ai_status ON public.complaints USING btree (ai_status) WHERE ((ai_status)::text = ANY ((ARRAY['PENDING'::character varying, 'PROCESSING'::character varying])::text[]));


--
-- Name: idx_complaints_category_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_complaints_category_id ON public.complaints USING btree (category_id);


--
-- Name: idx_complaints_contractor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_complaints_contractor ON public.complaints USING btree (assigned_contractor_id);


--
-- Name: idx_complaints_duplicate_checked_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_complaints_duplicate_checked_at ON public.complaints USING btree (duplicate_checked_at);


--
-- Name: idx_complaints_duplicate_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_complaints_duplicate_status ON public.complaints USING btree (duplicate_status);


--
-- Name: idx_complaints_location; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_complaints_location ON public.complaints USING gist (location);


--
-- Name: idx_complaints_location_geog; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_complaints_location_geog ON public.complaints USING gist (((location)::public.geography));


--
-- Name: idx_complaints_master_complaint_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_complaints_master_complaint_id ON public.complaints USING btree (master_complaint_id);


--
-- Name: idx_complaints_matched_complaint_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_complaints_matched_complaint_id ON public.complaints USING btree (matched_complaint_id);


--
-- Name: idx_complaints_poi_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_complaints_poi_id ON public.complaints USING btree (poi_id);


--
-- Name: idx_complaints_road_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_complaints_road_id ON public.complaints USING btree (road_id);


--
-- Name: idx_complaints_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_complaints_status ON public.complaints USING btree (status);


--
-- Name: idx_complaints_submitted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_complaints_submitted_at ON public.complaints USING btree (submitted_at);


--
-- Name: idx_complaints_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_complaints_user_id ON public.complaints USING btree (user_id);


--
-- Name: idx_complaints_ward_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_complaints_ward_id ON public.complaints USING btree (ward_id);


--
-- Name: idx_contractor_workers_contractor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contractor_workers_contractor ON public.contractor_workers USING btree (contractor_id);


--
-- Name: idx_contractors_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contractors_status ON public.contractors USING btree (status);


--
-- Name: idx_defect_measurements_complaint; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_defect_measurements_complaint ON public.defect_measurements USING btree (complaint_id, source);


--
-- Name: idx_dsr_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dsr_status ON public.data_subject_requests USING btree (status, due_at);


--
-- Name: idx_duplicate_complaint_1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_duplicate_complaint_1 ON public.duplicate_detections USING btree (complaint_id_1);


--
-- Name: idx_duplicate_complaint_2; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_duplicate_complaint_2 ON public.duplicate_detections USING btree (complaint_id_2);


--
-- Name: idx_duplicate_relation_complaint_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_duplicate_relation_complaint_id ON public.duplicate_relation USING btree (complaint_id);


--
-- Name: idx_duplicate_relation_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_duplicate_relation_created_at ON public.duplicate_relation USING btree (created_at);


--
-- Name: idx_duplicate_relation_decision; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_duplicate_relation_decision ON public.duplicate_relation USING btree (decision);


--
-- Name: idx_duplicate_relation_master_complaint_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_duplicate_relation_master_complaint_id ON public.duplicate_relation USING btree (master_complaint_id);


--
-- Name: idx_duplicate_relation_review_queue; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_duplicate_relation_review_queue ON public.duplicate_relation USING btree (review_required, reviewed_at);


--
-- Name: idx_duplicate_relation_similar_complaint_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_duplicate_relation_similar_complaint_id ON public.duplicate_relation USING btree (similar_complaint_id);


--
-- Name: idx_jobs_pick; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_jobs_pick ON public.jobs USING btree (priority, run_after) WHERE ((status)::text = 'QUEUED'::text);


--
-- Name: idx_municipal_boundary_geometry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_municipal_boundary_geometry ON public.municipal_boundary USING gist (geometry);


--
-- Name: idx_notifications_complaint; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notifications_complaint ON public.notifications USING btree (complaint_id);


--
-- Name: idx_notifications_provider; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notifications_provider ON public.notifications USING btree (provider_message_id);


--
-- Name: idx_notifications_retry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notifications_retry ON public.notifications USING btree (status, next_attempt_at) WHERE ((status)::text = ANY ((ARRAY['QUEUED'::character varying, 'FAILED'::character varying])::text[]));


--
-- Name: idx_notifications_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notifications_user ON public.notifications USING btree (user_id, created_at DESC);


--
-- Name: idx_officer_approvals_complaint_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_officer_approvals_complaint_id ON public.officer_approvals USING btree (complaint_id);


--
-- Name: idx_officer_approvals_decision; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_officer_approvals_decision ON public.officer_approvals USING btree (decision);


--
-- Name: idx_officer_approvals_officer_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_officer_approvals_officer_id ON public.officer_approvals USING btree (officer_id);


--
-- Name: idx_officer_scopes_officer; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_officer_scopes_officer ON public.officer_scopes USING btree (officer_id);


--
-- Name: idx_officers_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_officers_user_id ON public.officers USING btree (user_id);


--
-- Name: idx_otp_destination; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_otp_destination ON public.auth_otp_codes USING btree (destination, purpose, created_at DESC);


--
-- Name: idx_outbox_pending; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_outbox_pending ON public.notification_outbox USING btree (created_at) WHERE (processed_at IS NULL);


--
-- Name: idx_pois_geometry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pois_geometry ON public.pois USING gist (geometry);


--
-- Name: idx_pois_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pois_type ON public.pois USING btree (type);


--
-- Name: idx_pois_ward_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pois_ward_id ON public.pois USING btree (ward_id);


--
-- Name: idx_priority_complaint_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_priority_complaint_id ON public.priority_assessments USING btree (complaint_id);


--
-- Name: idx_priority_level; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_priority_level ON public.priority_assessments USING btree (priority_level);


--
-- Name: idx_refresh_tokens_family; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_refresh_tokens_family ON public.auth_refresh_tokens USING btree (family_id);


--
-- Name: idx_refresh_tokens_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_refresh_tokens_user ON public.auth_refresh_tokens USING btree (user_id);


--
-- Name: idx_roads_geometry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_roads_geometry ON public.roads USING gist (geometry);


--
-- Name: idx_roads_ward_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_roads_ward_id ON public.roads USING btree (ward_id);


--
-- Name: idx_route_stops_route_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_route_stops_route_id ON public.route_stops USING btree (route_id);


--
-- Name: idx_route_stops_work_order_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_route_stops_work_order_id ON public.route_stops USING btree (work_order_id);


--
-- Name: idx_routes_end_location; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_routes_end_location ON public.routes USING gist (end_location);


--
-- Name: idx_routes_schedule_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_routes_schedule_date ON public.routes USING btree (schedule_date);


--
-- Name: idx_routes_start_location; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_routes_start_location ON public.routes USING gist (start_location);


--
-- Name: idx_routes_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_routes_status ON public.routes USING btree (status);


--
-- Name: idx_routes_team_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_routes_team_id ON public.routes USING btree (team_id);


--
-- Name: idx_schedules_scheduled_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_schedules_scheduled_date ON public.schedules USING btree (scheduled_date);


--
-- Name: idx_schedules_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_schedules_status ON public.schedules USING btree (status);


--
-- Name: idx_schedules_team_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_schedules_team_id ON public.schedules USING btree (team_id);


--
-- Name: idx_site_inspections_complaint; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_site_inspections_complaint ON public.site_inspections USING btree (complaint_id);


--
-- Name: idx_status_history_changed_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_status_history_changed_at ON public.complaint_status_history USING btree (changed_at);


--
-- Name: idx_status_history_changed_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_status_history_changed_by ON public.complaint_status_history USING btree (changed_by);


--
-- Name: idx_status_history_complaint_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_status_history_complaint_id ON public.complaint_status_history USING btree (complaint_id);


--
-- Name: idx_user_consents_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_consents_user ON public.user_consents USING btree (user_id, consent_type, created_at DESC);


--
-- Name: idx_users_role; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_role ON public.users USING btree (role);


--
-- Name: idx_ward_geometry_history_version; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ward_geometry_history_version ON public.ward_geometry_history USING btree (version, ward_number);


--
-- Name: idx_ward_reassignment_log_entity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ward_reassignment_log_entity ON public.ward_reassignment_log USING btree (entity, entity_id);


--
-- Name: idx_wards_geometry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_wards_geometry ON public.wards USING gist (geometry);


--
-- Name: idx_wards_ward_number; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_wards_ward_number ON public.wards USING btree (ward_number);


--
-- Name: idx_work_completions_complaint; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_work_completions_complaint ON public.work_completions USING btree (complaint_id);


--
-- Name: idx_work_order_resources_resource_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_work_order_resources_resource_id ON public.work_order_resources USING btree (resource_id);


--
-- Name: idx_work_orders_officer_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_work_orders_officer_id ON public.work_orders USING btree (assigned_officer_id);


--
-- Name: idx_work_orders_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_work_orders_status ON public.work_orders USING btree (status);


--
-- Name: idx_work_orders_team_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_work_orders_team_id ON public.work_orders USING btree (team_id);


--
-- Name: idx_yolo_detections_image_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_yolo_detections_image_id ON public.yolo_detections USING btree (image_id);


--
-- Name: roads_import_staging_wkb_geometry_geom_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX roads_import_staging_wkb_geometry_geom_idx ON public.roads_import_staging USING gist (wkb_geometry);


--
-- Name: uq_complaints_public_ref; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_complaints_public_ref ON public.complaints USING btree (public_ref);


--
-- Name: uq_duplicate_relation_pair; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_duplicate_relation_pair ON public.duplicate_relation USING btree (LEAST(complaint_id, similar_complaint_id), GREATEST(complaint_id, similar_complaint_id));


--
-- Name: uq_jobs_active; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_jobs_active ON public.jobs USING btree (job_type, ref_id) WHERE ((status)::text = ANY ((ARRAY['QUEUED'::character varying, 'RUNNING'::character varying])::text[]));


--
-- Name: uq_priority_current; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_priority_current ON public.priority_assessments USING btree (complaint_id) WHERE is_current;


--
-- Name: uq_privacy_notice_current; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_privacy_notice_current ON public.privacy_notices USING btree ((true)) WHERE is_current;


--
-- Name: uq_resource_estimate_current; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_resource_estimate_current ON public.resource_estimates USING btree (complaint_id) WHERE is_current;


--
-- Name: uq_users_email_lower; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_users_email_lower ON public.users USING btree (lower((email)::text)) WHERE (email IS NOT NULL);


--
-- Name: action_plans trg_action_plans_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_action_plans_updated_at BEFORE UPDATE ON public.action_plans FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: complaints trg_complaints_enqueue_analysis; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_complaints_enqueue_analysis AFTER INSERT ON public.complaints FOR EACH ROW EXECUTE FUNCTION public.fn_enqueue_complaint_analysis();


--
-- Name: complaints trg_complaints_status_guard; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_complaints_status_guard BEFORE INSERT OR UPDATE OF status ON public.complaints FOR EACH ROW EXECUTE FUNCTION public.fn_complaint_status_guard();


--
-- Name: complaints trg_complaints_status_log; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_complaints_status_log AFTER INSERT OR UPDATE OF status ON public.complaints FOR EACH ROW EXECUTE FUNCTION public.fn_complaint_status_log();


--
-- Name: complaints trg_complaints_status_release; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_complaints_status_release BEFORE UPDATE OF status ON public.complaints FOR EACH ROW EXECUTE FUNCTION public.fn_complaint_status_release_plan();


--
-- Name: complaints trg_complaints_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_complaints_updated_at BEFORE UPDATE ON public.complaints FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: contractors trg_contractors_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_contractors_updated_at BEFORE UPDATE ON public.contractors FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: optimizer_runs trg_optimizer_runs_enqueue; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_optimizer_runs_enqueue AFTER INSERT ON public.optimizer_runs FOR EACH ROW EXECUTE FUNCTION public.fn_enqueue_optimizer_run();


--
-- Name: site_inspections trg_site_inspections_distance; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_site_inspections_distance BEFORE INSERT OR UPDATE OF inspector_location ON public.site_inspections FOR EACH ROW EXECUTE FUNCTION public.fn_set_distance_from_complaint();


--
-- Name: users trg_users_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: work_completions trg_work_completions_distance; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_work_completions_distance BEFORE INSERT OR UPDATE OF completion_location ON public.work_completions FOR EACH ROW EXECUTE FUNCTION public.fn_set_distance_from_complaint();


--
-- Name: action_plan_items action_plan_items_action_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_plan_items
    ADD CONSTRAINT action_plan_items_action_plan_id_fkey FOREIGN KEY (action_plan_id) REFERENCES public.action_plans(action_plan_id) ON DELETE CASCADE;


--
-- Name: action_plan_items action_plan_items_complaint_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_plan_items
    ADD CONSTRAINT action_plan_items_complaint_id_fkey FOREIGN KEY (complaint_id) REFERENCES public.complaints(complaint_id) ON DELETE RESTRICT;


--
-- Name: action_plan_revisions action_plan_revisions_action_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_plan_revisions
    ADD CONSTRAINT action_plan_revisions_action_plan_id_fkey FOREIGN KEY (action_plan_id) REFERENCES public.action_plans(action_plan_id) ON DELETE CASCADE;


--
-- Name: action_plan_revisions action_plan_revisions_changed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_plan_revisions
    ADD CONSTRAINT action_plan_revisions_changed_by_fkey FOREIGN KEY (changed_by) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: action_plans action_plans_approved_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_plans
    ADD CONSTRAINT action_plans_approved_by_user_id_fkey FOREIGN KEY (approved_by_user_id) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: action_plans action_plans_assigned_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_plans
    ADD CONSTRAINT action_plans_assigned_by_user_id_fkey FOREIGN KEY (assigned_by_user_id) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: action_plans action_plans_contractor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_plans
    ADD CONSTRAINT action_plans_contractor_id_fkey FOREIGN KEY (contractor_id) REFERENCES public.contractors(contractor_id) ON DELETE SET NULL;


--
-- Name: action_plans action_plans_created_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_plans
    ADD CONSTRAINT action_plans_created_by_user_id_fkey FOREIGN KEY (created_by_user_id) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: action_plans action_plans_depot_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_plans
    ADD CONSTRAINT action_plans_depot_id_fkey FOREIGN KEY (depot_id) REFERENCES public.depots(depot_id);


--
-- Name: action_plans action_plans_optimizer_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_plans
    ADD CONSTRAINT action_plans_optimizer_run_id_fkey FOREIGN KEY (optimizer_run_id) REFERENCES public.optimizer_runs(run_id) ON DELETE SET NULL;


--
-- Name: action_plans action_plans_work_type_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_plans
    ADD CONSTRAINT action_plans_work_type_code_fkey FOREIGN KEY (work_type_code) REFERENCES public.work_types(work_type_code);


--
-- Name: ai_classifications ai_classifications_predicted_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_classifications
    ADD CONSTRAINT ai_classifications_predicted_category_id_fkey FOREIGN KEY (predicted_category_id) REFERENCES public.complaint_categories(category_id) ON DELETE SET NULL;


--
-- Name: auth_events auth_events_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_events
    ADD CONSTRAINT auth_events_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: auth_otp_codes auth_otp_codes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_otp_codes
    ADD CONSTRAINT auth_otp_codes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: auth_refresh_tokens auth_refresh_tokens_replaced_by_token_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_refresh_tokens
    ADD CONSTRAINT auth_refresh_tokens_replaced_by_token_id_fkey FOREIGN KEY (replaced_by_token_id) REFERENCES public.auth_refresh_tokens(refresh_token_id) ON DELETE SET NULL;


--
-- Name: auth_refresh_tokens auth_refresh_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_refresh_tokens
    ADD CONSTRAINT auth_refresh_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: authenticity_checks authenticity_checks_complaint_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.authenticity_checks
    ADD CONSTRAINT authenticity_checks_complaint_id_fkey FOREIGN KEY (complaint_id) REFERENCES public.complaints(complaint_id) ON DELETE CASCADE;


--
-- Name: authenticity_checks authenticity_checks_image_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.authenticity_checks
    ADD CONSTRAINT authenticity_checks_image_id_fkey FOREIGN KEY (image_id) REFERENCES public.complaint_images(image_id) ON DELETE CASCADE;


--
-- Name: capture_sessions capture_sessions_used_by_complaint_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.capture_sessions
    ADD CONSTRAINT capture_sessions_used_by_complaint_id_fkey FOREIGN KEY (used_by_complaint_id) REFERENCES public.complaints(complaint_id) ON DELETE SET NULL;


--
-- Name: capture_sessions capture_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.capture_sessions
    ADD CONSTRAINT capture_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: complaint_categories complaint_categories_work_type_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaint_categories
    ADD CONSTRAINT complaint_categories_work_type_code_fkey FOREIGN KEY (work_type_code) REFERENCES public.work_types(work_type_code);


--
-- Name: complaint_feedback complaint_feedback_complaint_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaint_feedback
    ADD CONSTRAINT complaint_feedback_complaint_id_fkey FOREIGN KEY (complaint_id) REFERENCES public.complaints(complaint_id) ON DELETE CASCADE;


--
-- Name: complaint_feedback complaint_feedback_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaint_feedback
    ADD CONSTRAINT complaint_feedback_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: complaint_images complaint_images_approved_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaint_images
    ADD CONSTRAINT complaint_images_approved_by_fkey FOREIGN KEY (approved_by) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: complaint_images complaint_images_uploaded_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaint_images
    ADD CONSTRAINT complaint_images_uploaded_by_fkey FOREIGN KEY (uploaded_by) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: complaint_votes complaint_votes_complaint_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaint_votes
    ADD CONSTRAINT complaint_votes_complaint_id_fkey FOREIGN KEY (complaint_id) REFERENCES public.complaints(complaint_id) ON DELETE CASCADE;


--
-- Name: complaint_votes complaint_votes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaint_votes
    ADD CONSTRAINT complaint_votes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: complaints complaints_assigned_contractor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaints
    ADD CONSTRAINT complaints_assigned_contractor_id_fkey FOREIGN KEY (assigned_contractor_id) REFERENCES public.contractors(contractor_id) ON DELETE SET NULL;


--
-- Name: contractor_equipment contractor_equipment_contractor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractor_equipment
    ADD CONSTRAINT contractor_equipment_contractor_id_fkey FOREIGN KEY (contractor_id) REFERENCES public.contractors(contractor_id) ON DELETE CASCADE;


--
-- Name: contractor_equipment contractor_equipment_equipment_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractor_equipment
    ADD CONSTRAINT contractor_equipment_equipment_code_fkey FOREIGN KEY (equipment_code) REFERENCES public.equipment_catalog(equipment_code);


--
-- Name: contractor_work_types contractor_work_types_contractor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractor_work_types
    ADD CONSTRAINT contractor_work_types_contractor_id_fkey FOREIGN KEY (contractor_id) REFERENCES public.contractors(contractor_id) ON DELETE CASCADE;


--
-- Name: contractor_work_types contractor_work_types_work_type_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractor_work_types
    ADD CONSTRAINT contractor_work_types_work_type_code_fkey FOREIGN KEY (work_type_code) REFERENCES public.work_types(work_type_code);


--
-- Name: contractor_workers contractor_workers_contractor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractor_workers
    ADD CONSTRAINT contractor_workers_contractor_id_fkey FOREIGN KEY (contractor_id) REFERENCES public.contractors(contractor_id) ON DELETE CASCADE;


--
-- Name: contractor_workers contractor_workers_created_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractor_workers
    ADD CONSTRAINT contractor_workers_created_by_user_id_fkey FOREIGN KEY (created_by_user_id) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: contractor_workers contractor_workers_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractor_workers
    ADD CONSTRAINT contractor_workers_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: contractors contractors_created_by_officer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractors
    ADD CONSTRAINT contractors_created_by_officer_id_fkey FOREIGN KEY (created_by_officer_id) REFERENCES public.officers(officer_id) ON DELETE SET NULL;


--
-- Name: contractors contractors_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractors
    ADD CONSTRAINT contractors_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: data_subject_requests data_subject_requests_handled_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_subject_requests
    ADD CONSTRAINT data_subject_requests_handled_by_fkey FOREIGN KEY (handled_by) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: data_subject_requests data_subject_requests_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_subject_requests
    ADD CONSTRAINT data_subject_requests_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: defect_measurements defect_measurements_complaint_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.defect_measurements
    ADD CONSTRAINT defect_measurements_complaint_id_fkey FOREIGN KEY (complaint_id) REFERENCES public.complaints(complaint_id) ON DELETE CASCADE;


--
-- Name: defect_measurements defect_measurements_detection_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.defect_measurements
    ADD CONSTRAINT defect_measurements_detection_id_fkey FOREIGN KEY (detection_id) REFERENCES public.yolo_detections(detection_id) ON DELETE SET NULL;


--
-- Name: defect_measurements defect_measurements_image_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.defect_measurements
    ADD CONSTRAINT defect_measurements_image_id_fkey FOREIGN KEY (image_id) REFERENCES public.complaint_images(image_id) ON DELETE SET NULL;


--
-- Name: defect_measurements defect_measurements_measured_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.defect_measurements
    ADD CONSTRAINT defect_measurements_measured_by_fkey FOREIGN KEY (measured_by) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: ai_classifications fk_ai_classifications_complaint; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_classifications
    ADD CONSTRAINT fk_ai_classifications_complaint FOREIGN KEY (complaint_id) REFERENCES public.complaints(complaint_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: audit_logs fk_audit_logs_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT fk_audit_logs_user FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: complaint_images fk_complaint_images_complaint; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaint_images
    ADD CONSTRAINT fk_complaint_images_complaint FOREIGN KEY (complaint_id) REFERENCES public.complaints(complaint_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: complaint_images fk_complaint_images_completion; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaint_images
    ADD CONSTRAINT fk_complaint_images_completion FOREIGN KEY (completion_id) REFERENCES public.work_completions(completion_id) ON DELETE SET NULL;


--
-- Name: complaint_images fk_complaint_images_inspection; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaint_images
    ADD CONSTRAINT fk_complaint_images_inspection FOREIGN KEY (inspection_id) REFERENCES public.site_inspections(inspection_id) ON DELETE SET NULL;


--
-- Name: complaints fk_complaints_capture_session; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaints
    ADD CONSTRAINT fk_complaints_capture_session FOREIGN KEY (capture_session_id) REFERENCES public.capture_sessions(capture_session_id) ON DELETE SET NULL;


--
-- Name: complaints fk_complaints_category; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaints
    ADD CONSTRAINT fk_complaints_category FOREIGN KEY (category_id) REFERENCES public.complaint_categories(category_id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: complaints fk_complaints_current_action_plan; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaints
    ADD CONSTRAINT fk_complaints_current_action_plan FOREIGN KEY (current_action_plan_id) REFERENCES public.action_plans(action_plan_id) ON DELETE SET NULL;


--
-- Name: complaints fk_complaints_master_complaint; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaints
    ADD CONSTRAINT fk_complaints_master_complaint FOREIGN KEY (master_complaint_id) REFERENCES public.complaints(complaint_id) ON DELETE SET NULL;


--
-- Name: complaints fk_complaints_matched_complaint; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaints
    ADD CONSTRAINT fk_complaints_matched_complaint FOREIGN KEY (matched_complaint_id) REFERENCES public.complaints(complaint_id) ON DELETE SET NULL;


--
-- Name: complaints fk_complaints_poi; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaints
    ADD CONSTRAINT fk_complaints_poi FOREIGN KEY (poi_id) REFERENCES public.pois(poi_id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: complaints fk_complaints_road; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaints
    ADD CONSTRAINT fk_complaints_road FOREIGN KEY (road_id) REFERENCES public.roads(road_id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: complaints fk_complaints_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaints
    ADD CONSTRAINT fk_complaints_user FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: complaints fk_complaints_ward; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaints
    ADD CONSTRAINT fk_complaints_ward FOREIGN KEY (ward_id) REFERENCES public.wards(ward_id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: duplicate_detections fk_duplicate_complaint_1; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.duplicate_detections
    ADD CONSTRAINT fk_duplicate_complaint_1 FOREIGN KEY (complaint_id_1) REFERENCES public.complaints(complaint_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: duplicate_detections fk_duplicate_complaint_2; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.duplicate_detections
    ADD CONSTRAINT fk_duplicate_complaint_2 FOREIGN KEY (complaint_id_2) REFERENCES public.complaints(complaint_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: duplicate_relation fk_duplicate_relation_complaint; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.duplicate_relation
    ADD CONSTRAINT fk_duplicate_relation_complaint FOREIGN KEY (complaint_id) REFERENCES public.complaints(complaint_id) ON DELETE CASCADE;


--
-- Name: duplicate_relation fk_duplicate_relation_master; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.duplicate_relation
    ADD CONSTRAINT fk_duplicate_relation_master FOREIGN KEY (master_complaint_id) REFERENCES public.complaints(complaint_id) ON DELETE SET NULL;


--
-- Name: duplicate_relation fk_duplicate_relation_reviewer; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.duplicate_relation
    ADD CONSTRAINT fk_duplicate_relation_reviewer FOREIGN KEY (reviewed_by) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: duplicate_relation fk_duplicate_relation_similar; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.duplicate_relation
    ADD CONSTRAINT fk_duplicate_relation_similar FOREIGN KEY (similar_complaint_id) REFERENCES public.complaints(complaint_id) ON DELETE CASCADE;


--
-- Name: officer_approvals fk_officer_approvals_complaint; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.officer_approvals
    ADD CONSTRAINT fk_officer_approvals_complaint FOREIGN KEY (complaint_id) REFERENCES public.complaints(complaint_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: officer_approvals fk_officer_approvals_officer; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.officer_approvals
    ADD CONSTRAINT fk_officer_approvals_officer FOREIGN KEY (officer_id) REFERENCES public.officers(officer_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: officers fk_officers_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.officers
    ADD CONSTRAINT fk_officers_user FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: notification_outbox fk_outbox_action_plan; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_outbox
    ADD CONSTRAINT fk_outbox_action_plan FOREIGN KEY (action_plan_id) REFERENCES public.action_plans(action_plan_id) ON DELETE CASCADE;


--
-- Name: pois fk_pois_ward; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pois
    ADD CONSTRAINT fk_pois_ward FOREIGN KEY (ward_id) REFERENCES public.wards(ward_id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: priority_assessments fk_priority_complaint; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.priority_assessments
    ADD CONSTRAINT fk_priority_complaint FOREIGN KEY (complaint_id) REFERENCES public.complaints(complaint_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: roads fk_roads_ward; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roads
    ADD CONSTRAINT fk_roads_ward FOREIGN KEY (ward_id) REFERENCES public.wards(ward_id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: route_stops fk_route_stops_route; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.route_stops
    ADD CONSTRAINT fk_route_stops_route FOREIGN KEY (route_id) REFERENCES public.routes(route_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: route_stops fk_route_stops_work_order; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.route_stops
    ADD CONSTRAINT fk_route_stops_work_order FOREIGN KEY (work_order_id) REFERENCES public.work_orders(work_order_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: routes fk_routes_team; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.routes
    ADD CONSTRAINT fk_routes_team FOREIGN KEY (team_id) REFERENCES public.field_teams(team_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: schedules fk_schedules_team; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedules
    ADD CONSTRAINT fk_schedules_team FOREIGN KEY (team_id) REFERENCES public.field_teams(team_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: schedules fk_schedules_work_order; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedules
    ADD CONSTRAINT fk_schedules_work_order FOREIGN KEY (work_order_id) REFERENCES public.work_orders(work_order_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: complaint_status_history fk_status_history_complaint; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaint_status_history
    ADD CONSTRAINT fk_status_history_complaint FOREIGN KEY (complaint_id) REFERENCES public.complaints(complaint_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: complaint_status_history fk_status_history_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaint_status_history
    ADD CONSTRAINT fk_status_history_user FOREIGN KEY (changed_by) REFERENCES public.users(user_id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: step13_action_plans fk_step13_action_team; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.step13_action_plans
    ADD CONSTRAINT fk_step13_action_team FOREIGN KEY (team_id) REFERENCES public.step13_teams(team_id);


--
-- Name: step13_cluster_complaint fk_step13_cluster_complaint_cluster; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.step13_cluster_complaint
    ADD CONSTRAINT fk_step13_cluster_complaint_cluster FOREIGN KEY (cluster_id) REFERENCES public.step13_clusters(cluster_id);


--
-- Name: step13_route_stops fk_step13_route_stop_route; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.step13_route_stops
    ADD CONSTRAINT fk_step13_route_stop_route FOREIGN KEY (route_id) REFERENCES public.step13_routes(route_id);


--
-- Name: step13_routes fk_step13_route_team; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.step13_routes
    ADD CONSTRAINT fk_step13_route_team FOREIGN KEY (team_id) REFERENCES public.step13_teams(team_id);


--
-- Name: step13_schedule_job fk_step13_schedule_job_schedule; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.step13_schedule_job
    ADD CONSTRAINT fk_step13_schedule_job_schedule FOREIGN KEY (schedule_id) REFERENCES public.step13_schedules(schedule_id);


--
-- Name: step13_schedules fk_step13_schedule_team; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.step13_schedules
    ADD CONSTRAINT fk_step13_schedule_team FOREIGN KEY (team_id) REFERENCES public.step13_teams(team_id);


--
-- Name: step13_team_equipment fk_step13_team_equipment_team; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.step13_team_equipment
    ADD CONSTRAINT fk_step13_team_equipment_team FOREIGN KEY (team_id) REFERENCES public.step13_teams(team_id);


--
-- Name: work_order_resources fk_work_order_resources_resource; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_order_resources
    ADD CONSTRAINT fk_work_order_resources_resource FOREIGN KEY (resource_id) REFERENCES public.resources(resource_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: work_order_resources fk_work_order_resources_work_order; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_order_resources
    ADD CONSTRAINT fk_work_order_resources_work_order FOREIGN KEY (work_order_id) REFERENCES public.work_orders(work_order_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: work_orders fk_work_orders_complaint; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_orders
    ADD CONSTRAINT fk_work_orders_complaint FOREIGN KEY (complaint_id) REFERENCES public.complaints(complaint_id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: work_orders fk_work_orders_officer; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_orders
    ADD CONSTRAINT fk_work_orders_officer FOREIGN KEY (assigned_officer_id) REFERENCES public.officers(officer_id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: work_orders fk_work_orders_team; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_orders
    ADD CONSTRAINT fk_work_orders_team FOREIGN KEY (team_id) REFERENCES public.field_teams(team_id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: yolo_detections fk_yolo_detections_image; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.yolo_detections
    ADD CONSTRAINT fk_yolo_detections_image FOREIGN KEY (image_id) REFERENCES public.complaint_images(image_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: material_catalog material_catalog_work_type_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.material_catalog
    ADD CONSTRAINT material_catalog_work_type_code_fkey FOREIGN KEY (work_type_code) REFERENCES public.work_types(work_type_code);


--
-- Name: notification_outbox notification_outbox_complaint_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_outbox
    ADD CONSTRAINT notification_outbox_complaint_id_fkey FOREIGN KEY (complaint_id) REFERENCES public.complaints(complaint_id) ON DELETE CASCADE;


--
-- Name: notifications notifications_complaint_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_complaint_id_fkey FOREIGN KEY (complaint_id) REFERENCES public.complaints(complaint_id) ON DELETE CASCADE;


--
-- Name: notifications notifications_outbox_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_outbox_id_fkey FOREIGN KEY (outbox_id) REFERENCES public.notification_outbox(outbox_id) ON DELETE SET NULL;


--
-- Name: notifications notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: officer_scopes officer_scopes_officer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.officer_scopes
    ADD CONSTRAINT officer_scopes_officer_id_fkey FOREIGN KEY (officer_id) REFERENCES public.officers(officer_id) ON DELETE CASCADE;


--
-- Name: officer_scopes officer_scopes_ward_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.officer_scopes
    ADD CONSTRAINT officer_scopes_ward_id_fkey FOREIGN KEY (ward_id) REFERENCES public.wards(ward_id) ON DELETE CASCADE;


--
-- Name: officer_scopes officer_scopes_work_type_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.officer_scopes
    ADD CONSTRAINT officer_scopes_work_type_code_fkey FOREIGN KEY (work_type_code) REFERENCES public.work_types(work_type_code);


--
-- Name: officers officers_created_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.officers
    ADD CONSTRAINT officers_created_by_user_id_fkey FOREIGN KEY (created_by_user_id) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: optimizer_runs optimizer_runs_requested_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.optimizer_runs
    ADD CONSTRAINT optimizer_runs_requested_by_fkey FOREIGN KEY (requested_by) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: resource_estimate_equipment resource_estimate_equipment_equipment_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_estimate_equipment
    ADD CONSTRAINT resource_estimate_equipment_equipment_code_fkey FOREIGN KEY (equipment_code) REFERENCES public.equipment_catalog(equipment_code);


--
-- Name: resource_estimate_equipment resource_estimate_equipment_estimate_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_estimate_equipment
    ADD CONSTRAINT resource_estimate_equipment_estimate_id_fkey FOREIGN KEY (estimate_id) REFERENCES public.resource_estimates(estimate_id) ON DELETE CASCADE;


--
-- Name: resource_estimate_materials resource_estimate_materials_estimate_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_estimate_materials
    ADD CONSTRAINT resource_estimate_materials_estimate_id_fkey FOREIGN KEY (estimate_id) REFERENCES public.resource_estimates(estimate_id) ON DELETE CASCADE;


--
-- Name: resource_estimate_materials resource_estimate_materials_material_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_estimate_materials
    ADD CONSTRAINT resource_estimate_materials_material_code_fkey FOREIGN KEY (material_code) REFERENCES public.material_catalog(material_code);


--
-- Name: resource_estimates resource_estimates_complaint_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_estimates
    ADD CONSTRAINT resource_estimates_complaint_id_fkey FOREIGN KEY (complaint_id) REFERENCES public.complaints(complaint_id) ON DELETE CASCADE;


--
-- Name: resource_estimates resource_estimates_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_estimates
    ADD CONSTRAINT resource_estimates_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: resource_estimates resource_estimates_measurement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_estimates
    ADD CONSTRAINT resource_estimates_measurement_id_fkey FOREIGN KEY (measurement_id) REFERENCES public.defect_measurements(measurement_id) ON DELETE SET NULL;


--
-- Name: site_inspections site_inspections_action_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.site_inspections
    ADD CONSTRAINT site_inspections_action_plan_id_fkey FOREIGN KEY (action_plan_id) REFERENCES public.action_plans(action_plan_id) ON DELETE SET NULL;


--
-- Name: site_inspections site_inspections_complaint_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.site_inspections
    ADD CONSTRAINT site_inspections_complaint_id_fkey FOREIGN KEY (complaint_id) REFERENCES public.complaints(complaint_id) ON DELETE CASCADE;


--
-- Name: site_inspections site_inspections_contractor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.site_inspections
    ADD CONSTRAINT site_inspections_contractor_id_fkey FOREIGN KEY (contractor_id) REFERENCES public.contractors(contractor_id) ON DELETE RESTRICT;


--
-- Name: site_inspections site_inspections_inspected_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.site_inspections
    ADD CONSTRAINT site_inspections_inspected_by_user_id_fkey FOREIGN KEY (inspected_by_user_id) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: site_inspections site_inspections_measurement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.site_inspections
    ADD CONSTRAINT site_inspections_measurement_id_fkey FOREIGN KEY (measurement_id) REFERENCES public.defect_measurements(measurement_id) ON DELETE SET NULL;


--
-- Name: site_inspections site_inspections_revised_estimate_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.site_inspections
    ADD CONSTRAINT site_inspections_revised_estimate_id_fkey FOREIGN KEY (revised_estimate_id) REFERENCES public.resource_estimates(estimate_id) ON DELETE SET NULL;


--
-- Name: user_consents user_consents_notice_version_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_consents
    ADD CONSTRAINT user_consents_notice_version_fkey FOREIGN KEY (notice_version) REFERENCES public.privacy_notices(version);


--
-- Name: user_consents user_consents_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_consents
    ADD CONSTRAINT user_consents_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: users users_created_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_created_by_user_id_fkey FOREIGN KEY (created_by_user_id) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: work_completions work_completions_action_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_completions
    ADD CONSTRAINT work_completions_action_plan_id_fkey FOREIGN KEY (action_plan_id) REFERENCES public.action_plans(action_plan_id) ON DELETE SET NULL;


--
-- Name: work_completions work_completions_complaint_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_completions
    ADD CONSTRAINT work_completions_complaint_id_fkey FOREIGN KEY (complaint_id) REFERENCES public.complaints(complaint_id) ON DELETE CASCADE;


--
-- Name: work_completions work_completions_contractor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_completions
    ADD CONSTRAINT work_completions_contractor_id_fkey FOREIGN KEY (contractor_id) REFERENCES public.contractors(contractor_id) ON DELETE RESTRICT;


--
-- Name: work_completions work_completions_submitted_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_completions
    ADD CONSTRAINT work_completions_submitted_by_user_id_fkey FOREIGN KEY (submitted_by_user_id) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: work_completions work_completions_verified_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.work_completions
    ADD CONSTRAINT work_completions_verified_by_user_id_fkey FOREIGN KEY (verified_by_user_id) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--


