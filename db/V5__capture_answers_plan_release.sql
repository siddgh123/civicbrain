-- =============================================================================
-- CivicBrain | V5__capture_answers_plan_release.sql
-- Closes the gaps found in the kit review of 2026-09-30 (docs/PROGRESS.md decisions log):
--   1. where the citizen's depth answer and "A4 sheet in the photo" flag are stored (FR-10, FR-23)
--   2. an image quality score, so a duplicate group shows its best photo (FR-22 "keep the better one")
--   3. a complaint that leaves its action plan (reopened, or pulled back to VERIFIED) becomes
--      plannable again: current_action_plan_id / assigned_contractor_id are cleared by the database,
--      and its item leaves a plan that is still running (so the plan can complete and the old firm
--      loses access)
--   4. auth_events types for TOTP and logout-all; audit rows keyed by a text code (rates, settings)
--   5. corrected column comment (the TOTP key variable is TOTP_ENC_KEY)
-- Order   : run AFTER V4 (and after R__civicbrain_grants.sql if you use pgAdmin; no new tables here)
-- Target  : PostgreSQL 16-18 + PostGIS 3.4+   (tested on PG 16.13 + PostGIS 3.4.2)
-- Rules   : additive, idempotent, one transaction. Existing rows keep their values, except
--           complaint_categories.needs_depth_answer set to true for Pothole and Waterlogging.
-- =============================================================================
BEGIN;
SET LOCAL search_path = public;

-- -----------------------------------------------------------------------------
-- 1. Citizen capture answers (04_API_CONTRACT §5: depthAnswer, a4InFrame; §3 needsDepthAnswer)
-- -----------------------------------------------------------------------------
ALTER TABLE complaints
    ADD COLUMN IF NOT EXISTS depth_answer varchar(10),
    ADD COLUMN IF NOT EXISTS a4_in_frame  boolean NOT NULL DEFAULT false;
ALTER TABLE complaints DROP CONSTRAINT IF EXISTS ck_complaints_depth_answer;
ALTER TABLE complaints ADD  CONSTRAINT ck_complaints_depth_answer
    CHECK (depth_answer IS NULL OR depth_answer IN ('SHALLOW', 'FINGER', 'DEEP'));
COMMENT ON COLUMN complaints.depth_answer IS
  'Citizen answer to "how deep?" (SHALLOW / FINGER / DEEP). Mapped to an assumed depth by the worker (06_AI_PIPELINE 2.4). NULL = not asked or not answered.';
COMMENT ON COLUMN complaints.a4_in_frame IS
  'Citizen says an A4 sheet lies next to the defect in the photo; the worker then tries measurement Tier A.';

ALTER TABLE complaint_categories
    ADD COLUMN IF NOT EXISTS needs_depth_answer boolean NOT NULL DEFAULT false;
UPDATE complaint_categories SET needs_depth_answer = true
 WHERE category_name IN ('Pothole', 'Waterlogging') AND NOT needs_depth_answer;

-- -----------------------------------------------------------------------------
-- 2. Image quality score (0..1) - the display photo of a duplicate group is the best one
-- -----------------------------------------------------------------------------
ALTER TABLE complaint_images
    ADD COLUMN IF NOT EXISTS quality_score numeric(4,3);
ALTER TABLE complaint_images DROP CONSTRAINT IF EXISTS ck_complaint_images_quality;
ALTER TABLE complaint_images ADD  CONSTRAINT ck_complaint_images_quality
    CHECK (quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 1));
COMMENT ON COLUMN complaint_images.quality_score IS
  '0.5 x normalised sharpness (Laplacian variance) + 0.3 x primary detection confidence + 0.2 x min(1, pixels / 2 MP); written by the worker.';

-- -----------------------------------------------------------------------------
-- 3. Leaving a plan frees the complaint for the next plan
--    VERIFIED from SCHEDULED/ASSIGNED/INSPECTED (officer pulls it out or cancels the plan):
--    the plan item becomes REMOVED and the complaint becomes plannable.
--    REOPENED (from COMPLETED/CLOSED): the complaint becomes plannable; its item becomes REMOVED
--    only if that plan is still ASSIGNED/IN_PROGRESS (a COMPLETED plan keeps its item as history).
--    Fires after trg_complaints_status_guard (alphabetical order of BEFORE triggers), so only
--    transitions that the guard accepted reach it.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_complaint_status_release_plan()
RETURNS trigger
LANGUAGE plpgsql AS $$
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

DROP TRIGGER IF EXISTS trg_complaints_status_release ON complaints;
CREATE TRIGGER trg_complaints_status_release
    BEFORE UPDATE OF status ON complaints
    FOR EACH ROW EXECUTE FUNCTION fn_complaint_status_release_plan();

-- -----------------------------------------------------------------------------
-- 4a. auth_events: TOTP and logout-all events (07_SECURITY §1)
-- -----------------------------------------------------------------------------
ALTER TABLE auth_events DROP CONSTRAINT IF EXISTS ck_auth_event_type;
ALTER TABLE auth_events ADD  CONSTRAINT ck_auth_event_type CHECK (event_type IN (
    'LOGIN_SUCCESS', 'LOGIN_FAILED', 'ACCOUNT_LOCKED', 'LOGOUT', 'OTP_SENT', 'OTP_VERIFIED', 'OTP_FAILED',
    'PASSWORD_RESET', 'PASSWORD_CHANGED', 'REFRESH_REUSE_DETECTED', 'ROLE_CHANGED', 'ACCOUNT_CREATED',
    'TOTP_ENABLED', 'TOTP_VERIFIED', 'TOTP_FAILED', 'TOTP_RESET', 'LOGOUT_ALL'));

-- -----------------------------------------------------------------------------
-- 4b. audit_logs rows for things keyed by a code instead of a numeric id (rates, settings)
-- -----------------------------------------------------------------------------
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS entity_key varchar(100);
ALTER TABLE audit_logs ALTER COLUMN entity_id DROP NOT NULL;
ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS ck_audit_entity_id;
ALTER TABLE audit_logs ADD  CONSTRAINT ck_audit_entity_id
    CHECK ((entity_id IS NULL OR entity_id > 0) AND (entity_id IS NOT NULL OR entity_key IS NOT NULL));

-- -----------------------------------------------------------------------------
-- 5. Comment fix
-- -----------------------------------------------------------------------------
COMMENT ON COLUMN users.totp_secret_enc IS
  'Base64(IV || AES-256-GCM ciphertext) of the RFC 6238 secret. Key from env TOTP_ENC_KEY (32 bytes, base64). Required for OFFICER and ADMIN.';

COMMIT;
