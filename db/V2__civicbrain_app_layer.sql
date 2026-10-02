-- =============================================================================
-- CivicBrain  |  V2__civicbrain_app_layer.sql
-- Step 14 application layer: Citizen / Officer / Contractor web workflow
--
-- Target  : PostgreSQL 16-18 + PostGIS 3.4+  (your DB: PostgreSQL 18.6 + PostGIS 3.6.2)
-- Tested  : on a restore of civicbrain_backup (pg_dump 18.6) into PostgreSQL 16.13 + PostGIS 3.4.2
-- Run as  : the database owner, e.g.  psql -d civicbrain -f V2__civicbrain_app_layer.sql
--           (or place it in src/main/resources/db/migration and let Flyway run it after
--            baselining the existing database as V1)
--
-- Rules followed (from CIVICBRAIN_MASTER_README.md):
--   * ADDITIVE ONLY. No existing complaint / GIS / Step 9-13 row value is changed.
--     The only UPDATE is on the 8 reference rows of complaint_categories, to fill the
--     two NEW columns work_type_code and yolo_class_id (the frozen Step 13 mapping).
--   * Step 9 (YOLO classes), Step 11 (priority weights), Step 12 (300 m / 7 days /
--     0.59 / 0.55) and all step13_* tables are untouched.
--   * Idempotent: running it twice is safe.
--   * No official TDMC staff, departments, inventory or rates are invented: rate
--     columns are left NULL ("to be configured"), prototype values are labelled.
-- =============================================================================

BEGIN;

SET LOCAL search_path = public;

-- -----------------------------------------------------------------------------
-- 0. Reference: operational work types (the frozen Step 13 scope)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS work_types (
    work_type_code   varchar(30)  PRIMARY KEY,
    display_name     varchar(100) NOT NULL,
    is_operational   boolean      NOT NULL DEFAULT true,
    note             text,
    CONSTRAINT ck_work_types_code CHECK (work_type_code IN ('ROAD','WATER','GARBAGE','ELECTRICITY','REVIEW_REQUIRED'))
);

INSERT INTO work_types (work_type_code, display_name, is_operational, note) VALUES
  ('ROAD',            'Road',                      true,  'CivicBrain project-level work type (not an official TDMC department)'),
  ('WATER',           'Water / Drainage',          true,  'CivicBrain project-level work type (not an official TDMC department)'),
  ('GARBAGE',         'Garbage / Sanitation',      true,  'CivicBrain project-level work type (not an official TDMC department)'),
  ('ELECTRICITY',     'Electricity / Streetlight', true,  'CivicBrain project-level work type (not an official TDMC department)'),
  ('REVIEW_REQUIRED', 'Needs officer review',      false, 'Category "Other" - officer must reclassify before planning')
ON CONFLICT (work_type_code) DO NOTHING;

-- complaint_categories -> work type + YOLO class (Step 9 / Step 13 frozen mapping)
ALTER TABLE complaint_categories
    ADD COLUMN IF NOT EXISTS work_type_code     varchar(30) REFERENCES work_types(work_type_code),
    ADD COLUMN IF NOT EXISTS yolo_class_id      smallint,
    ADD COLUMN IF NOT EXISTS citizen_selectable boolean NOT NULL DEFAULT true,
    ADD COLUMN IF NOT EXISTS display_order      smallint;

ALTER TABLE complaint_categories DROP CONSTRAINT IF EXISTS ck_complaint_categories_yolo_class;
ALTER TABLE complaint_categories ADD  CONSTRAINT ck_complaint_categories_yolo_class
    CHECK (yolo_class_id IS NULL OR yolo_class_id BETWEEN 0 AND 3);

UPDATE complaint_categories c
   SET work_type_code = m.wt,
       yolo_class_id  = m.yc,
       display_order  = m.ord
  FROM (VALUES ('Pothole',              'ROAD',            0::smallint,    1::smallint),
               ('Road Damage',          'ROAD',            3::smallint,    2::smallint),
               ('Waterlogging',         'WATER',           2::smallint,    3::smallint),
               ('Water Leakage',        'WATER',           NULL::smallint, 4::smallint),
               ('Blocked Drain',        'WATER',           NULL::smallint, 5::smallint),
               ('Garbage Accumulation', 'GARBAGE',         1::smallint,    6::smallint),
               ('Streetlight',          'ELECTRICITY',     NULL::smallint, 7::smallint),
               ('Other',                'REVIEW_REQUIRED', NULL::smallint, 8::smallint)) AS m(name, wt, yc, ord)
 WHERE c.category_name = m.name
   AND c.work_type_code IS NULL;

COMMENT ON COLUMN complaint_categories.yolo_class_id IS
  'Step 9 frozen YOLO class id (0 Pothole, 1 Garbage Accumulation, 2 Waterlogging, 3 Road Damage). NULL = category has no visual model; image is stored as evidence only.';

-- wards: make the 23-unit scheme explicit (README: 23 analytical GIS units != 14 electoral wards)
ALTER TABLE wards ADD COLUMN IF NOT EXISTS ward_scheme varchar(30) NOT NULL DEFAULT 'ANALYTICAL_GIS_23';
COMMENT ON COLUMN wards.ward_scheme IS
  'ANALYTICAL_GIS_23 = the 23 analytical GIS units used by CivicBrain. Not the 2025 electoral structure (14 wards / 28 seats).';

-- -----------------------------------------------------------------------------
-- 1. Users, roles and authentication
-- -----------------------------------------------------------------------------
ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_role;
ALTER TABLE users ADD  CONSTRAINT ck_users_role
    CHECK (role IN ('CITIZEN','OFFICER','ADMIN','CONTRACTOR','CONTRACTOR_STAFF','FIELD_TEAM'));

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS email_verified_at    timestamptz,
    ADD COLUMN IF NOT EXISTS phone_verified_at    timestamptz,
    ADD COLUMN IF NOT EXISTS whatsapp_opt_in      boolean      NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS email_opt_in         boolean      NOT NULL DEFAULT true,
    ADD COLUMN IF NOT EXISTS preferred_language   varchar(5)   NOT NULL DEFAULT 'en',
    ADD COLUMN IF NOT EXISTS trust_score          numeric(5,2) NOT NULL DEFAULT 50.00,
    ADD COLUMN IF NOT EXISTS failed_login_count   integer      NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS locked_until         timestamptz,
    ADD COLUMN IF NOT EXISTS last_login_at        timestamptz,
    ADD COLUMN IF NOT EXISTS password_changed_at  timestamptz,
    ADD COLUMN IF NOT EXISTS must_change_password boolean      NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS created_by_user_id   bigint REFERENCES users(user_id) ON DELETE SET NULL;

ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_trust_score;
ALTER TABLE users ADD  CONSTRAINT ck_users_trust_score CHECK (trust_score BETWEEN 0 AND 100);
ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_language;
ALTER TABLE users ADD  CONSTRAINT ck_users_language CHECK (preferred_language IN ('en','mr','hi'));
ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_failed_logins;
ALTER TABLE users ADD  CONSTRAINT ck_users_failed_logins CHECK (failed_login_count >= 0);
ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_phone_format;
ALTER TABLE users ADD  CONSTRAINT ck_users_phone_format CHECK (phone IS NULL OR phone ~ '^\+?[0-9]{10,15}$');
ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_contact_present;
ALTER TABLE users ADD  CONSTRAINT ck_users_contact_present CHECK (email IS NOT NULL OR phone IS NOT NULL);

-- e-mail must be unique ignoring case (existing uq_users_email is case-sensitive)
CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email_lower ON users (lower(email)) WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);

-- Refresh tokens: only the SHA-256 hash of the opaque token is stored; rotated on every use.
CREATE TABLE IF NOT EXISTS auth_refresh_tokens (
    refresh_token_id      bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    user_id               bigint      NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    token_hash            char(64)    NOT NULL,
    family_id             uuid        NOT NULL,
    family_expires_at     timestamptz,                -- absolute cap for the whole login session
    issued_at             timestamptz NOT NULL DEFAULT now(),
    expires_at            timestamptz NOT NULL,
    last_used_at          timestamptz,
    revoked_at            timestamptz,
    revoke_reason         varchar(40),
    replaced_by_token_id  bigint REFERENCES auth_refresh_tokens(refresh_token_id) ON DELETE SET NULL,
    user_agent            text,
    ip_address            inet,
    CONSTRAINT uq_refresh_token_hash UNIQUE (token_hash),
    CONSTRAINT ck_refresh_hash   CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_refresh_expiry CHECK (expires_at > issued_at),
    CONSTRAINT ck_refresh_reason CHECK (revoke_reason IS NULL OR revoke_reason IN
        ('LOGOUT','ROTATED','REUSE_DETECTED','PASSWORD_CHANGED','ADMIN_REVOKED','EXPIRED'))
);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user   ON auth_refresh_tokens (user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_family ON auth_refresh_tokens (family_id);

-- OTP codes: stored as HMAC-SHA256(server secret, code); single use; short expiry; attempt limit.
CREATE TABLE IF NOT EXISTS auth_otp_codes (
    otp_id         bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    user_id        bigint REFERENCES users(user_id) ON DELETE CASCADE,   -- NULL before the account exists
    destination    varchar(255) NOT NULL,                                 -- e-mail or +91 phone
    channel        varchar(20)  NOT NULL,
    purpose        varchar(30)  NOT NULL,
    code_hmac      char(64)     NOT NULL,
    expires_at     timestamptz  NOT NULL,
    attempt_count  smallint     NOT NULL DEFAULT 0,
    max_attempts   smallint     NOT NULL DEFAULT 5,
    consumed_at    timestamptz,
    request_ip     inet,
    created_at     timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT ck_otp_channel  CHECK (channel IN ('EMAIL','WHATSAPP','SMS')),
    CONSTRAINT ck_otp_purpose  CHECK (purpose IN ('REGISTER','LOGIN','RESET_PASSWORD','VERIFY_EMAIL','VERIFY_PHONE')),
    CONSTRAINT ck_otp_hmac     CHECK (code_hmac ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_otp_expiry   CHECK (expires_at > created_at),
    CONSTRAINT ck_otp_attempts CHECK (attempt_count >= 0 AND max_attempts > 0)
);
CREATE INDEX IF NOT EXISTS idx_otp_destination ON auth_otp_codes (destination, purpose, created_at DESC);

-- Security events (login failures for unknown users cannot go to audit_logs, which needs a user)
CREATE TABLE IF NOT EXISTS auth_events (
    auth_event_id  bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    user_id        bigint REFERENCES users(user_id) ON DELETE SET NULL,
    identifier     varchar(255),
    event_type     varchar(40) NOT NULL,
    ip_address     inet,
    user_agent     text,
    details        jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at     timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_auth_event_type CHECK (event_type IN
        ('LOGIN_SUCCESS','LOGIN_FAILED','ACCOUNT_LOCKED','LOGOUT','OTP_SENT','OTP_VERIFIED','OTP_FAILED',
         'PASSWORD_RESET','PASSWORD_CHANGED','REFRESH_REUSE_DETECTED','ROLE_CHANGED','ACCOUNT_CREATED'))
);
CREATE INDEX IF NOT EXISTS idx_auth_events_user    ON auth_events (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_auth_events_created ON auth_events (created_at);

-- audit_logs: allow SYSTEM / AI actions (no human user)
ALTER TABLE audit_logs ALTER COLUMN user_id DROP NOT NULL;
ALTER TABLE audit_logs
    ADD COLUMN IF NOT EXISTS actor_type varchar(20) NOT NULL DEFAULT 'USER',
    ADD COLUMN IF NOT EXISTS ip_address inet,
    ADD COLUMN IF NOT EXISTS request_id varchar(64);
ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS ck_audit_actor_type;
ALTER TABLE audit_logs ADD  CONSTRAINT ck_audit_actor_type CHECK (actor_type IN ('USER','SYSTEM','AI'));
ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS ck_audit_user_actor;
ALTER TABLE audit_logs ADD  CONSTRAINT ck_audit_user_actor CHECK (actor_type <> 'USER' OR user_id IS NOT NULL);

-- Officer data scope (which wards / work types an officer may see). No row = no scope.
CREATE TABLE IF NOT EXISTS officer_scopes (
    officer_scope_id  bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    officer_id        bigint NOT NULL REFERENCES officers(officer_id) ON DELETE CASCADE,
    ward_id           bigint REFERENCES wards(ward_id) ON DELETE CASCADE,          -- NULL = all wards
    work_type_code    varchar(30) REFERENCES work_types(work_type_code),           -- NULL = all work types
    created_at        timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_officer_scope UNIQUE NULLS NOT DISTINCT (officer_id, ward_id, work_type_code)
);
CREATE INDEX IF NOT EXISTS idx_officer_scopes_officer ON officer_scopes (officer_id);

ALTER TABLE officers ADD COLUMN IF NOT EXISTS created_by_user_id bigint REFERENCES users(user_id) ON DELETE SET NULL;

-- -----------------------------------------------------------------------------
-- 2. Contractors, their employees and equipment (officer manages these)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS equipment_catalog (
    equipment_code           varchar(60)  PRIMARY KEY,
    display_name             varchar(150) NOT NULL,
    unit                     varchar(30)  NOT NULL DEFAULT 'day',
    rate_per_unit            numeric(12,2),
    rate_source              text,
    is_prototype_assumption  boolean NOT NULL DEFAULT true,
    CONSTRAINT ck_equipment_rate CHECK (rate_per_unit IS NULL OR rate_per_unit >= 0)
);
-- The 7 normalized equipment types from Step 13.2 (rates intentionally NULL = TO_BE_CONFIGURED)
INSERT INTO equipment_catalog (equipment_code, display_name, unit) VALUES
  ('drain_cleaning_tools',            'Drain cleaning tools',               'set-day'),
  ('electrical_maintenance_tools',    'Electrical maintenance tools',       'set-day'),
  ('joint_cutting_machine',           'Joint cutting machine',              'day'),
  ('manual_garbage_collection_tools', 'Manual garbage collection tools',    'set-day'),
  ('plate_compactor',                 'Plate compactor',                    'day'),
  ('truck_5_5_cum_per_10_mt',         'Truck 5.5 cum / 10 MT',              'trip'),
  ('water_leakage_repair_tools',      'Water leakage repair tools',         'set-day')
ON CONFLICT (equipment_code) DO NOTHING;

CREATE TABLE IF NOT EXISTS contractors (
    contractor_id          bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    user_id                bigint UNIQUE REFERENCES users(user_id) ON DELETE SET NULL,   -- login (role CONTRACTOR)
    firm_name              varchar(200) NOT NULL,
    contact_person         varchar(150) NOT NULL,
    phone                  varchar(20)  NOT NULL,
    email                  varchar(255),
    address                text,
    registration_no        varchar(100),
    crew_capacity          integer      NOT NULL DEFAULT 4,
    shift_start            time         NOT NULL DEFAULT '08:00',
    shift_end              time         NOT NULL DEFAULT '17:00',
    status                 varchar(20)  NOT NULL DEFAULT 'ACTIVE',
    rating                 numeric(3,2),
    created_by_officer_id  bigint REFERENCES officers(officer_id) ON DELETE SET NULL,
    created_at             timestamptz  NOT NULL DEFAULT now(),
    updated_at             timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT ck_contractors_firm     CHECK (btrim(firm_name) <> ''),
    CONSTRAINT ck_contractors_phone    CHECK (phone ~ '^\+?[0-9]{10,15}$'),
    CONSTRAINT ck_contractors_capacity CHECK (crew_capacity > 0),
    CONSTRAINT ck_contractors_shift    CHECK (shift_end > shift_start),
    CONSTRAINT ck_contractors_status   CHECK (status IN ('ACTIVE','INACTIVE','SUSPENDED')),
    CONSTRAINT ck_contractors_rating   CHECK (rating IS NULL OR rating BETWEEN 0 AND 5)
);
CREATE INDEX IF NOT EXISTS idx_contractors_status ON contractors (status);
CREATE OR REPLACE TRIGGER trg_contractors_updated_at BEFORE UPDATE ON contractors
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS contractor_work_types (
    contractor_id   bigint      NOT NULL REFERENCES contractors(contractor_id) ON DELETE CASCADE,
    work_type_code  varchar(30) NOT NULL REFERENCES work_types(work_type_code),
    PRIMARY KEY (contractor_id, work_type_code)
);

-- Contractor employees ("employee add" requirement). Optional login via user_id (role CONTRACTOR_STAFF).
CREATE TABLE IF NOT EXISTS contractor_workers (
    worker_id           bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    contractor_id       bigint       NOT NULL REFERENCES contractors(contractor_id) ON DELETE CASCADE,
    user_id             bigint UNIQUE REFERENCES users(user_id) ON DELETE SET NULL,
    full_name           varchar(150) NOT NULL,
    phone               varchar(20),
    skill               varchar(30)  NOT NULL,
    is_active           boolean      NOT NULL DEFAULT true,
    created_by_user_id  bigint REFERENCES users(user_id) ON DELETE SET NULL,
    created_at          timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT ck_workers_name  CHECK (btrim(full_name) <> ''),
    CONSTRAINT ck_workers_phone CHECK (phone IS NULL OR phone ~ '^\+?[0-9]{10,15}$'),
    CONSTRAINT ck_workers_skill CHECK (skill IN ('SUPERVISOR','MASON','LABOURER','ELECTRICIAN','PLUMBER',
                                                 'MACHINE_OPERATOR','DRIVER','SANITATION_WORKER','OTHER'))
);
CREATE INDEX IF NOT EXISTS idx_contractor_workers_contractor ON contractor_workers (contractor_id);

CREATE TABLE IF NOT EXISTS contractor_equipment (
    contractor_id   bigint      NOT NULL REFERENCES contractors(contractor_id) ON DELETE CASCADE,
    equipment_code  varchar(60) NOT NULL REFERENCES equipment_catalog(equipment_code),
    quantity        integer     NOT NULL DEFAULT 1,
    PRIMARY KEY (contractor_id, equipment_code),
    CONSTRAINT ck_contractor_equipment_qty CHECK (quantity >= 0)
);

-- Materials used by the quantity-takeoff engine. Rates NULL until taken from Maharashtra PWD SSR.
CREATE TABLE IF NOT EXISTS material_catalog (
    material_code          varchar(60)  PRIMARY KEY,
    display_name           varchar(150) NOT NULL,
    unit                   varchar(20)  NOT NULL,
    work_type_code         varchar(30)  REFERENCES work_types(work_type_code),
    density_t_per_m3       numeric(6,3),
    application_rate       numeric(10,4),
    application_rate_unit  varchar(40),
    rate_per_unit          numeric(12,2),
    rate_source            text,
    notes                  text,
    CONSTRAINT ck_material_rate CHECK (rate_per_unit IS NULL OR rate_per_unit >= 0)
);
INSERT INTO material_catalog (material_code, display_name, unit, work_type_code, density_t_per_m3,
                              application_rate, application_rate_unit, notes) VALUES
  ('BITUMINOUS_HOT_MIX',  'Bituminous hot premix / BC for patching', 'tonne', 'ROAD', 2.350, NULL, NULL,
   'Compacted density ~2.3-2.4 t/m3 from a secondary AASHTO-based chart; confirm with MoRTH Sec 500 / contractor job-mix formula.'),
  ('BITUMINOUS_COLD_MIX', 'Bituminous cold mix for patching',        'tonne', 'ROAD', 2.150, NULL, NULL,
   'Compacted density ~2.1-2.2 t/m3 (secondary source). IRC:116-2014 governs cold-mix patching.'),
  ('TACK_COAT_EMULSION',  'Bitumen emulsion tack coat',              'kg',    'ROAD', NULL,  0.2500, 'kg per m2 of repair area',
   'IRC:82-2015: 2.5 kg per 10 sq m.'),
  ('CRACK_SEALANT',       'Crack sealing compound',                  'litre', 'ROAD', NULL,  NULL, NULL,
   'Consumption per metre of crack to be configured.')
ON CONFLICT (material_code) DO NOTHING;

-- Prototype depot from Step 13.8 (user-verified map location, NOT an official TDMC depot)
CREATE TABLE IF NOT EXISTS depots (
    depot_id      varchar(20)  PRIMARY KEY,
    depot_name    varchar(150) NOT NULL,
    location      geometry(Point,4326) NOT NULL,
    source        text NOT NULL,
    is_prototype  boolean NOT NULL DEFAULT true
);
INSERT INTO depots (depot_id, depot_name, location, source, is_prototype) VALUES
  ('D001', 'Morkhala Kachara Depo (prototype)', ST_SetSRID(ST_MakePoint(73.699489, 18.729411), 4326),
   'User-provided map location; user_verified_map (Step 13.8)', true)
ON CONFLICT (depot_id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 3. Complaint lifecycle: statuses, new columns, transition table
-- -----------------------------------------------------------------------------
-- Lifecycle used by the web app:
--   SUBMITTED -> VERIFIED (authenticity + AI done, visible in officer "New")
--   VERIFIED  -> SCHEDULED (in an approved action plan) -> ASSIGNED (contractor assigned)
--   ASSIGNED  -> INSPECTED (contractor site visit) -> IN_PROGRESS -> COMPLETED (proof photo)
--   COMPLETED -> CLOSED (officer verified) | REOPENED
--   side exits: REJECTED (fake / invalid), MERGED (duplicate child follows its master)
ALTER TABLE complaints DROP CONSTRAINT IF EXISTS ck_complaints_status;
ALTER TABLE complaints ADD  CONSTRAINT ck_complaints_status CHECK (status IN
    ('SUBMITTED','VERIFIED','REJECTED','MERGED','SCHEDULED','ASSIGNED','INSPECTED',
     'IN_PROGRESS','COMPLETED','CLOSED','REOPENED'));

ALTER TABLE complaint_status_history DROP CONSTRAINT IF EXISTS ck_status_history_new_status;
ALTER TABLE complaint_status_history ADD  CONSTRAINT ck_status_history_new_status CHECK (new_status IN
    ('SUBMITTED','VERIFIED','REJECTED','MERGED','SCHEDULED','ASSIGNED','INSPECTED',
     'IN_PROGRESS','COMPLETED','CLOSED','REOPENED'));
ALTER TABLE complaint_status_history DROP CONSTRAINT IF EXISTS ck_status_history_old_status;
ALTER TABLE complaint_status_history ADD  CONSTRAINT ck_status_history_old_status CHECK (old_status IS NULL OR old_status IN
    ('SUBMITTED','VERIFIED','REJECTED','MERGED','SCHEDULED','ASSIGNED','INSPECTED',
     'IN_PROGRESS','COMPLETED','CLOSED','REOPENED'));

ALTER TABLE complaint_status_history
    ADD COLUMN IF NOT EXISTS actor_role varchar(20),
    ADD COLUMN IF NOT EXISTS source     varchar(20) NOT NULL DEFAULT 'WEB',
    ADD COLUMN IF NOT EXISTS metadata   jsonb       NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE complaint_status_history DROP CONSTRAINT IF EXISTS ck_status_history_source;
ALTER TABLE complaint_status_history ADD  CONSTRAINT ck_status_history_source
    CHECK (source IN ('WEB','SYSTEM','AI','MIGRATION'));

-- New complaint columns. Existing 500 rows keep all their values; new columns are NULL/default.
ALTER TABLE complaints
    ADD COLUMN IF NOT EXISTS public_ref varchar(20)
        GENERATED ALWAYS AS ('CB-' || lpad(complaint_id::text, 6, '0')) STORED,
    -- DEFAULT true only while adding, so the existing 500 synthetic rows are flagged without an UPDATE
    ADD COLUMN IF NOT EXISTS is_synthetic          boolean NOT NULL DEFAULT true,
    ADD COLUMN IF NOT EXISTS landmark              text,
    ADD COLUMN IF NOT EXISTS address_text          text,
    ADD COLUMN IF NOT EXISTS location_accuracy_m   numeric(8,2),
    ADD COLUMN IF NOT EXISTS location_captured_at  timestamptz,
    ADD COLUMN IF NOT EXISTS location_source       varchar(20),
    ADD COLUMN IF NOT EXISTS capture_session_id    uuid,
    ADD COLUMN IF NOT EXISTS authenticity_status   varchar(20) NOT NULL DEFAULT 'NOT_CHECKED',
    ADD COLUMN IF NOT EXISTS authenticity_score    numeric(5,2),
    ADD COLUMN IF NOT EXISTS ai_status             varchar(20) NOT NULL DEFAULT 'PENDING',
    ADD COLUMN IF NOT EXISTS ai_processed_at       timestamptz,
    ADD COLUMN IF NOT EXISTS current_priority_score numeric(6,2),
    ADD COLUMN IF NOT EXISTS current_priority_level varchar(10),
    ADD COLUMN IF NOT EXISTS current_action_plan_id bigint,
    ADD COLUMN IF NOT EXISTS assigned_contractor_id bigint REFERENCES contractors(contractor_id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS rejection_reason      text;
ALTER TABLE complaints ALTER COLUMN is_synthetic SET DEFAULT false;   -- new (real) complaints

ALTER TABLE complaints DROP CONSTRAINT IF EXISTS ck_complaints_location_accuracy;
ALTER TABLE complaints ADD  CONSTRAINT ck_complaints_location_accuracy CHECK (location_accuracy_m IS NULL OR location_accuracy_m >= 0);
ALTER TABLE complaints DROP CONSTRAINT IF EXISTS ck_complaints_location_source;
ALTER TABLE complaints ADD  CONSTRAINT ck_complaints_location_source CHECK (location_source IS NULL OR location_source IN
    ('BROWSER_GPS','EXIF','OFFICER_CORRECTED','SYNTHETIC'));
ALTER TABLE complaints DROP CONSTRAINT IF EXISTS ck_complaints_authenticity_status;
ALTER TABLE complaints ADD  CONSTRAINT ck_complaints_authenticity_status CHECK (authenticity_status IN
    ('NOT_CHECKED','PASSED','FLAGGED','REJECTED'));
ALTER TABLE complaints DROP CONSTRAINT IF EXISTS ck_complaints_authenticity_score;
ALTER TABLE complaints ADD  CONSTRAINT ck_complaints_authenticity_score CHECK (authenticity_score IS NULL OR authenticity_score BETWEEN 0 AND 100);
ALTER TABLE complaints DROP CONSTRAINT IF EXISTS ck_complaints_ai_status;
ALTER TABLE complaints ADD  CONSTRAINT ck_complaints_ai_status CHECK (ai_status IN
    ('PENDING','PROCESSING','COMPLETED','FAILED','SKIPPED'));
ALTER TABLE complaints DROP CONSTRAINT IF EXISTS ck_complaints_priority_level;
ALTER TABLE complaints ADD  CONSTRAINT ck_complaints_priority_level CHECK (current_priority_level IS NULL OR current_priority_level IN
    ('LOW','MEDIUM','HIGH','CRITICAL'));

CREATE UNIQUE INDEX IF NOT EXISTS uq_complaints_public_ref ON complaints (public_ref);
CREATE INDEX IF NOT EXISTS idx_complaints_location_geog ON complaints USING gist ((location::geography));
CREATE INDEX IF NOT EXISTS idx_complaints_ai_status   ON complaints (ai_status) WHERE ai_status IN ('PENDING','PROCESSING');
CREATE INDEX IF NOT EXISTS idx_complaints_contractor  ON complaints (assigned_contractor_id);
CREATE INDEX IF NOT EXISTS idx_complaints_action_plan ON complaints (current_action_plan_id);

COMMENT ON COLUMN complaints.is_synthetic IS 'true for the 500 Step 8 synthetic complaints; false for real web submissions.';
COMMENT ON COLUMN complaints.public_ref   IS 'Citizen-facing complaint number used in e-mail / WhatsApp, e.g. CB-000123.';

-- Allowed transitions (data-driven state machine; enforced by trigger below)
CREATE TABLE IF NOT EXISTS complaint_status_transitions (
    from_status     varchar(30) NOT NULL,
    to_status       varchar(30) NOT NULL,
    allowed_roles   text[]      NOT NULL,
    notify_citizen  boolean     NOT NULL DEFAULT true,
    description     text,
    PRIMARY KEY (from_status, to_status)
);
INSERT INTO complaint_status_transitions (from_status, to_status, allowed_roles, notify_citizen, description) VALUES
  ('SUBMITTED',  'VERIFIED',    ARRAY['SYSTEM','OFFICER','ADMIN'], false, 'Authenticity + AI analysis done; appears in officer New tab'),
  ('SUBMITTED',  'REJECTED',    ARRAY['SYSTEM','OFFICER','ADMIN'], true,  'Fake / outside boundary / invalid'),
  ('SUBMITTED',  'MERGED',      ARRAY['SYSTEM','OFFICER','ADMIN'], true,  'Duplicate of an existing complaint; citizen follows the master complaint'),
  ('VERIFIED',   'REJECTED',    ARRAY['OFFICER','ADMIN'],          true,  'Officer rejected after review'),
  ('VERIFIED',   'MERGED',      ARRAY['OFFICER','ADMIN'],          true,  'Officer merged duplicate'),
  ('VERIFIED',   'SCHEDULED',   ARRAY['OFFICER','ADMIN'],          false, 'Included in an approved action plan'),
  ('SCHEDULED',  'ASSIGNED',    ARRAY['OFFICER','ADMIN'],          true,  'Contractor assigned (citizen gets contractor name)'),
  ('SCHEDULED',  'VERIFIED',    ARRAY['OFFICER','ADMIN'],          false, 'Removed from action plan'),
  ('ASSIGNED',   'INSPECTED',   ARRAY['CONTRACTOR','CONTRACTOR_STAFF'], true, 'Contractor site inspection done (notes shared)'),
  ('ASSIGNED',   'VERIFIED',    ARRAY['OFFICER','ADMIN'],          true,  'Contractor unassigned / re-planning'),
  ('INSPECTED',  'IN_PROGRESS', ARRAY['CONTRACTOR','CONTRACTOR_STAFF'], true, 'Work started'),
  ('INSPECTED',  'VERIFIED',    ARRAY['OFFICER','ADMIN'],          true,  'Re-planning after inspection'),
  ('IN_PROGRESS','COMPLETED',   ARRAY['CONTRACTOR','CONTRACTOR_STAFF'], true, 'Work completed with proof photo'),
  ('COMPLETED',  'CLOSED',      ARRAY['OFFICER','ADMIN','SYSTEM'], true,  'Officer verified completion'),
  ('COMPLETED',  'REOPENED',    ARRAY['OFFICER','ADMIN','CITIZEN'],true,  'Completion rejected'),
  ('CLOSED',     'REOPENED',    ARRAY['OFFICER','ADMIN','CITIZEN'],true,  'Issue came back'),
  ('REOPENED',   'SCHEDULED',   ARRAY['OFFICER','ADMIN'],          false, 'Re-planned'),
  ('REOPENED',   'ASSIGNED',    ARRAY['OFFICER','ADMIN'],          true,  'Re-assigned to contractor'),
  ('REJECTED',   'VERIFIED',    ARRAY['OFFICER','ADMIN'],          true,  'Rejection reversed on review'),
  ('MERGED',     'VERIFIED',    ARRAY['OFFICER','ADMIN'],          true,  'Un-merged')
ON CONFLICT (from_status, to_status) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 4. Notifications (transactional outbox -> dispatcher -> per-channel log)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notification_templates (
    template_id             bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    template_code           varchar(60) NOT NULL,
    channel                 varchar(20) NOT NULL,
    locale                  varchar(5)  NOT NULL DEFAULT 'en',
    event_status            varchar(30),
    subject                 text,
    body                    text        NOT NULL,
    provider_template_name  varchar(100),
    include_photo           boolean     NOT NULL DEFAULT false,
    is_active               boolean     NOT NULL DEFAULT true,
    CONSTRAINT uq_notification_template UNIQUE (template_code, channel, locale),
    CONSTRAINT ck_template_channel CHECK (channel IN ('EMAIL','WHATSAPP','SMS','IN_APP')),
    CONSTRAINT ck_template_locale  CHECK (locale IN ('en','mr','hi'))
);

CREATE TABLE IF NOT EXISTS notification_outbox (
    outbox_id       bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    event_type      varchar(40) NOT NULL,
    complaint_id    bigint REFERENCES complaints(complaint_id) ON DELETE CASCADE,
    action_plan_id  bigint,
    event_status    varchar(30),
    payload         jsonb       NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now(),
    processed_at    timestamptz,
    attempt_count   integer     NOT NULL DEFAULT 0,
    last_error      text,
    CONSTRAINT ck_outbox_event_type CHECK (event_type IN
        ('COMPLAINT_STATUS_CHANGED','ACTION_PLAN_ASSIGNED','COMPLETION_SUBMITTED','ACCOUNT_CREATED','OTP','GENERIC'))
);
CREATE INDEX IF NOT EXISTS idx_outbox_pending ON notification_outbox (created_at) WHERE processed_at IS NULL;

CREATE TABLE IF NOT EXISTS notifications (
    notification_id      bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    outbox_id            bigint REFERENCES notification_outbox(outbox_id) ON DELETE SET NULL,
    user_id              bigint NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    complaint_id         bigint REFERENCES complaints(complaint_id) ON DELETE CASCADE,
    channel              varchar(20)  NOT NULL,
    template_code        varchar(60),
    destination          varchar(255),
    rendered_subject     text,
    rendered_body        text,
    media_url            text,
    status               varchar(20)  NOT NULL DEFAULT 'QUEUED',
    provider             varchar(30),
    provider_message_id  varchar(128),
    attempt_count        smallint     NOT NULL DEFAULT 0,
    next_attempt_at      timestamptz,
    last_error           text,
    dedupe_key           varchar(200) NOT NULL,
    created_at           timestamptz  NOT NULL DEFAULT now(),
    sent_at              timestamptz,
    delivered_at         timestamptz,
    read_at              timestamptz,
    CONSTRAINT uq_notifications_dedupe UNIQUE (dedupe_key),
    CONSTRAINT ck_notifications_channel CHECK (channel IN ('EMAIL','WHATSAPP','SMS','IN_APP')),
    CONSTRAINT ck_notifications_status  CHECK (status IN ('QUEUED','SENDING','SENT','DELIVERED','READ','FAILED','SKIPPED')),
    CONSTRAINT ck_notifications_provider CHECK (provider IS NULL OR provider IN
        ('GMAIL_SMTP','BREVO','RESEND','META_CLOUD_API','TWILIO_SANDBOX','INTERNAL'))
);
CREATE INDEX IF NOT EXISTS idx_notifications_user       ON notifications (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_retry      ON notifications (status, next_attempt_at) WHERE status IN ('QUEUED','FAILED');
CREATE INDEX IF NOT EXISTS idx_notifications_provider   ON notifications (provider_message_id);
CREATE INDEX IF NOT EXISTS idx_notifications_complaint  ON notifications (complaint_id);

-- English seed templates. Placeholders are filled by the dispatcher.
INSERT INTO notification_templates (template_code, channel, event_status, subject, body, include_photo) VALUES
  ('COMPLAINT_SUBMITTED','EMAIL','SUBMITTED','CivicBrain: complaint {{public_ref}} received',
   'Dear {{citizen_name}}, your complaint {{public_ref}} ({{category}}) at {{location_text}} was received on {{submitted_at}}. We will notify you when a contractor is assigned.', false),
  ('COMPLAINT_SUBMITTED','WHATSAPP','SUBMITTED',NULL,
   'Complaint {{public_ref}} ({{category}}) received. Track: {{track_url}}', false),
  ('COMPLAINT_REJECTED','EMAIL','REJECTED','CivicBrain: complaint {{public_ref}} could not be accepted',
   'Dear {{citizen_name}}, complaint {{public_ref}} could not be accepted. Reason: {{remarks}}.', false),
  ('COMPLAINT_REJECTED','WHATSAPP','REJECTED',NULL,
   'Complaint {{public_ref}} was not accepted. Reason: {{remarks}}', false),
  ('COMPLAINT_MERGED','EMAIL','MERGED','CivicBrain: complaint {{public_ref}} linked to an existing complaint',
   'Dear {{citizen_name}}, the issue you reported is already registered as {{master_ref}}. You will receive every update for it.', false),
  ('COMPLAINT_MERGED','WHATSAPP','MERGED',NULL,
   'Your complaint {{public_ref}} is linked to existing complaint {{master_ref}}. You will get all its updates.', false),
  ('COMPLAINT_ASSIGNED','EMAIL','ASSIGNED','CivicBrain: contractor assigned to {{public_ref}}',
   'Dear {{citizen_name}}, contractor {{contractor_name}} has been assigned to complaint {{public_ref}}. Planned date: {{planned_date}}.', false),
  ('COMPLAINT_ASSIGNED','WHATSAPP','ASSIGNED',NULL,
   'Complaint {{public_ref}}: contractor {{contractor_name}} assigned. Planned date {{planned_date}}.', false),
  ('COMPLAINT_INSPECTED','EMAIL','INSPECTED','CivicBrain: site inspection done for {{public_ref}}',
   'Dear {{citizen_name}}, the contractor inspected the site for {{public_ref}}. Notes: {{inspection_notes}}. Expected completion: {{expected_completion}}.', true),
  ('COMPLAINT_INSPECTED','WHATSAPP','INSPECTED',NULL,
   'Complaint {{public_ref}}: site inspected. {{inspection_notes}}', true),
  ('COMPLAINT_IN_PROGRESS','EMAIL','IN_PROGRESS','CivicBrain: work started on {{public_ref}}',
   'Dear {{citizen_name}}, work has started on complaint {{public_ref}}.', false),
  ('COMPLAINT_IN_PROGRESS','WHATSAPP','IN_PROGRESS',NULL,
   'Complaint {{public_ref}}: work started.', false),
  ('COMPLAINT_COMPLETED','EMAIL','COMPLETED','CivicBrain: work completed for {{public_ref}}',
   'Dear {{citizen_name}}, the work for complaint {{public_ref}} is completed. The proof photo is attached. If the problem is not fixed, reopen it here: {{track_url}}', true),
  ('COMPLAINT_COMPLETED','WHATSAPP','COMPLETED',NULL,
   'Complaint {{public_ref}} completed. Proof photo attached. Not fixed? {{track_url}}', true),
  ('COMPLAINT_CLOSED','EMAIL','CLOSED','CivicBrain: complaint {{public_ref}} closed',
   'Dear {{citizen_name}}, complaint {{public_ref}} was verified and closed. Please rate the work: {{track_url}}', false),
  ('COMPLAINT_CLOSED','WHATSAPP','CLOSED',NULL,
   'Complaint {{public_ref}} closed. Rate the work: {{track_url}}', false),
  ('COMPLAINT_REOPENED','EMAIL','REOPENED','CivicBrain: complaint {{public_ref}} reopened',
   'Complaint {{public_ref}} has been reopened. Reason: {{remarks}}.', false),
  ('COMPLAINT_REOPENED','WHATSAPP','REOPENED',NULL,
   'Complaint {{public_ref}} reopened. {{remarks}}', false),
  ('ACTION_PLAN_ASSIGNED','EMAIL',NULL,'CivicBrain: new action plan {{plan_code}}',
   'Dear {{contractor_name}}, action plan {{plan_code}} ({{job_count}} jobs, {{planned_date}}) has been assigned to you. Open it: {{plan_url}}', false),
  ('ACTION_PLAN_ASSIGNED','WHATSAPP',NULL,NULL,
   'New action plan {{plan_code}}: {{job_count}} jobs on {{planned_date}}. {{plan_url}}', false),
  ('COMPLETION_SUBMITTED','EMAIL',NULL,'CivicBrain: completion proof submitted for {{public_ref}}',
   'Contractor {{contractor_name}} submitted completion proof for {{public_ref}}. Verify: {{review_url}}', true)
ON CONFLICT (template_code, channel, locale) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 5. Photo evidence, capture sessions and authenticity checks
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS capture_sessions (
    capture_session_id    uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id               bigint      NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    issued_at             timestamptz NOT NULL DEFAULT now(),
    expires_at            timestamptz NOT NULL DEFAULT (now() + interval '10 minutes'),
    used_at               timestamptz,
    used_by_complaint_id  bigint REFERENCES complaints(complaint_id) ON DELETE SET NULL,
    client_ip             inet,
    user_agent            text,
    CONSTRAINT ck_capture_session_expiry CHECK (expires_at > issued_at)
);
CREATE INDEX IF NOT EXISTS idx_capture_sessions_user ON capture_sessions (user_id, issued_at DESC);

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_complaints_capture_session') THEN
    ALTER TABLE complaints ADD CONSTRAINT fk_complaints_capture_session
      FOREIGN KEY (capture_session_id) REFERENCES capture_sessions(capture_session_id) ON DELETE SET NULL;
  END IF;
END $$;

ALTER TABLE complaint_images
    ADD COLUMN IF NOT EXISTS image_role            varchar(30)  NOT NULL DEFAULT 'CITIZEN_EVIDENCE',
    ADD COLUMN IF NOT EXISTS uploaded_by           bigint REFERENCES users(user_id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS storage_key           text,
    ADD COLUMN IF NOT EXISTS sha256                char(64),
    ADD COLUMN IF NOT EXISTS phash                 bigint,          -- 64-bit perceptual hash (imagehash), signed int64
    ADD COLUMN IF NOT EXISTS width_px              integer,
    ADD COLUMN IF NOT EXISTS height_px             integer,
    ADD COLUMN IF NOT EXISTS file_size_bytes       bigint,
    ADD COLUMN IF NOT EXISTS capture_method        varchar(20),
    ADD COLUMN IF NOT EXISTS client_captured_at    timestamptz,
    ADD COLUMN IF NOT EXISTS capture_location      geometry(Point,4326),
    ADD COLUMN IF NOT EXISTS capture_accuracy_m    numeric(8,2),
    ADD COLUMN IF NOT EXISTS device_pitch_deg      numeric(6,2),
    ADD COLUMN IF NOT EXISTS device_roll_deg       numeric(6,2),
    ADD COLUMN IF NOT EXISTS focal_length_35mm_eq  numeric(6,2),
    ADD COLUMN IF NOT EXISTS exif_extracted        jsonb,
    ADD COLUMN IF NOT EXISTS inspection_id         bigint,
    ADD COLUMN IF NOT EXISTS completion_id         bigint;

ALTER TABLE complaint_images DROP CONSTRAINT IF EXISTS ck_complaint_images_role;
ALTER TABLE complaint_images ADD  CONSTRAINT ck_complaint_images_role CHECK (image_role IN
    ('CITIZEN_EVIDENCE','INSPECTION','WORK_IN_PROGRESS','COMPLETION_PROOF'));
ALTER TABLE complaint_images DROP CONSTRAINT IF EXISTS ck_complaint_images_capture_method;
ALTER TABLE complaint_images ADD  CONSTRAINT ck_complaint_images_capture_method CHECK (capture_method IS NULL OR capture_method IN
    ('IN_APP_CAMERA','FILE_CAPTURE','FILE_UPLOAD'));
ALTER TABLE complaint_images DROP CONSTRAINT IF EXISTS ck_complaint_images_hashes;
ALTER TABLE complaint_images ADD  CONSTRAINT ck_complaint_images_hashes CHECK (
    sha256 IS NULL OR sha256 ~ '^[0-9a-f]{64}$');
ALTER TABLE complaint_images DROP CONSTRAINT IF EXISTS ck_complaint_images_dimensions;
ALTER TABLE complaint_images ADD  CONSTRAINT ck_complaint_images_dimensions CHECK (
    (width_px IS NULL OR width_px > 0) AND (height_px IS NULL OR height_px > 0) AND (file_size_bytes IS NULL OR file_size_bytes > 0));
ALTER TABLE complaint_images DROP CONSTRAINT IF EXISTS ck_complaint_images_angles;
ALTER TABLE complaint_images ADD  CONSTRAINT ck_complaint_images_angles CHECK (
    (device_pitch_deg IS NULL OR device_pitch_deg BETWEEN -180 AND 180) AND
    (device_roll_deg  IS NULL OR device_roll_deg  BETWEEN -180 AND 180));

CREATE INDEX IF NOT EXISTS idx_complaint_images_sha256   ON complaint_images (sha256);
CREATE INDEX IF NOT EXISTS idx_complaint_images_phash    ON complaint_images (phash);
CREATE INDEX IF NOT EXISTS idx_complaint_images_role     ON complaint_images (complaint_id, image_role);
CREATE INDEX IF NOT EXISTS idx_complaint_images_capture  ON complaint_images USING gist (capture_location);

CREATE TABLE IF NOT EXISTS authenticity_checks (
    check_id      bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    complaint_id  bigint      NOT NULL REFERENCES complaints(complaint_id) ON DELETE CASCADE,
    image_id      bigint REFERENCES complaint_images(image_id) ON DELETE CASCADE,
    check_code    varchar(40) NOT NULL,
    result        varchar(10) NOT NULL,
    score_delta   numeric(6,2) NOT NULL DEFAULT 0,
    details       jsonb       NOT NULL DEFAULT '{}'::jsonb,
    created_at    timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_authenticity_check UNIQUE NULLS NOT DISTINCT (complaint_id, image_id, check_code),
    CONSTRAINT ck_authenticity_code CHECK (check_code IN
        ('BOUNDARY','GPS_ACCURACY','GPS_FRESHNESS','CAPTURE_SESSION','IMAGE_REUSE_SHA256','IMAGE_REUSE_PHASH',
         'EXIF_CONSISTENCY','SUBMISSION_RATE','IMPOSSIBLE_TRAVEL','ACCOUNT_TRUST','CATEGORY_IMAGE_MISMATCH')),
    CONSTRAINT ck_authenticity_result CHECK (result IN ('PASS','WARN','FAIL','SKIPPED'))
);
CREATE INDEX IF NOT EXISTS idx_authenticity_checks_complaint ON authenticity_checks (complaint_id);

-- -----------------------------------------------------------------------------
-- 6. AI outputs: classification, measurement, priority, resource estimate
-- -----------------------------------------------------------------------------
ALTER TABLE ai_classifications
    ADD COLUMN IF NOT EXISTS model_type            varchar(20) NOT NULL DEFAULT 'TEXT',
    ADD COLUMN IF NOT EXISTS predicted_category_id bigint REFERENCES complaint_categories(category_id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS top_k                 jsonb,
    ADD COLUMN IF NOT EXISTS is_accepted           boolean;
ALTER TABLE ai_classifications DROP CONSTRAINT IF EXISTS ck_ai_classifications_model_type;
ALTER TABLE ai_classifications ADD  CONSTRAINT ck_ai_classifications_model_type CHECK (model_type IN ('TEXT','IMAGE','FUSION'));

-- Real-world size estimate. Separate from yolo_detections (Step 9 = visual evidence only).
-- AI and contractor measurements are stored as separate rows so they can be compared.
CREATE TABLE IF NOT EXISTS defect_measurements (
    measurement_id      bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    complaint_id        bigint      NOT NULL REFERENCES complaints(complaint_id) ON DELETE CASCADE,
    image_id            bigint REFERENCES complaint_images(image_id) ON DELETE SET NULL,
    detection_id        bigint REFERENCES yolo_detections(detection_id) ON DELETE SET NULL,
    source              varchar(20) NOT NULL,
    method              varchar(40) NOT NULL,
    mask_area_px        numeric(14,2),
    length_m            numeric(8,3),
    width_m             numeric(8,3),
    area_m2             numeric(10,3),
    depth_m             numeric(6,3),
    depth_source        varchar(30),
    volume_m3           numeric(10,4),
    severity_class      varchar(10),
    confidence          numeric(4,3),
    error_band_pct      numeric(5,1),
    assumptions         jsonb       NOT NULL DEFAULT '{}'::jsonb,
    model_name          varchar(150),
    model_version       varchar(50),
    measured_by         bigint REFERENCES users(user_id) ON DELETE SET NULL,
    created_at          timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_measure_source   CHECK (source IN ('AI','CONTRACTOR','OFFICER')),
    CONSTRAINT ck_measure_method   CHECK (method IN ('GROUND_PLANE_HOMOGRAPHY','REFERENCE_OBJECT','MONOCULAR_DEPTH',
                                                     'CATEGORY_DEFAULT','MANUAL_TAPE')),
    CONSTRAINT ck_measure_depth_src CHECK (depth_source IS NULL OR depth_source IN
                                          ('ASSUMED_FROM_SEVERITY_CLASS','MEASURED_ON_SITE','MODEL_ESTIMATE')),
    CONSTRAINT ck_measure_severity CHECK (severity_class IS NULL OR severity_class IN ('SMALL','MEDIUM','LARGE')),
    CONSTRAINT ck_measure_values   CHECK ((length_m IS NULL OR length_m > 0) AND (width_m IS NULL OR width_m > 0)
                                      AND (area_m2 IS NULL OR area_m2 > 0) AND (depth_m IS NULL OR depth_m >= 0)
                                      AND (volume_m3 IS NULL OR volume_m3 >= 0)),
    CONSTRAINT ck_measure_confidence CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1)
);
CREATE INDEX IF NOT EXISTS idx_defect_measurements_complaint ON defect_measurements (complaint_id, source);
COMMENT ON TABLE defect_measurements IS
  'Real-world size estimates. AI rows are preliminary (single photo; depth cannot be measured from one RGB photo and is assumed from IRC:82 class: SMALL <=25 mm, MEDIUM 25-50 mm, LARGE >50 mm). CONTRACTOR rows are tape measurements at inspection and override AI for costing.';

-- priority_assessments: store all 7 frozen Step 11 factors
ALTER TABLE priority_assessments
    ADD COLUMN IF NOT EXISTS frequency_score        numeric(6,2),
    ADD COLUMN IF NOT EXISTS infrastructure_score   numeric(6,2),
    ADD COLUMN IF NOT EXISTS historical_risk_score  numeric(6,2),
    ADD COLUMN IF NOT EXISTS formula_version        varchar(40) NOT NULL DEFAULT 'STEP11_FROZEN_V1',
    ADD COLUMN IF NOT EXISTS weights                jsonb NOT NULL DEFAULT
        '{"severity":0.25,"population_impact":0.15,"location_risk":0.15,"frequency":0.10,"wait_time":0.10,"infrastructure_importance":0.15,"historical_risk":0.10}'::jsonb,
    ADD COLUMN IF NOT EXISTS explanation            jsonb,
    ADD COLUMN IF NOT EXISTS is_current             boolean NOT NULL DEFAULT true;
ALTER TABLE priority_assessments DROP CONSTRAINT IF EXISTS ck_priority_extra_factors;
ALTER TABLE priority_assessments ADD  CONSTRAINT ck_priority_extra_factors CHECK (
    (frequency_score IS NULL OR frequency_score >= 0) AND (infrastructure_score IS NULL OR infrastructure_score >= 0)
    AND (historical_risk_score IS NULL OR historical_risk_score >= 0));
CREATE UNIQUE INDEX IF NOT EXISTS uq_priority_current ON priority_assessments (complaint_id) WHERE is_current;
COMMENT ON COLUMN priority_assessments.severity_score IS 'Step 11 factor S (weight 0.25)';
COMMENT ON COLUMN priority_assessments.impact_score   IS 'Step 11 factor Ipop - population impact (weight 0.15)';
COMMENT ON COLUMN priority_assessments.location_score IS 'Step 11 factor Rloc - location risk (weight 0.15)';
COMMENT ON COLUMN priority_assessments.urgency_score  IS 'Step 11 factor Twait - wait time (weight 0.10)';
COMMENT ON COLUMN priority_assessments.frequency_score       IS 'Step 11 factor F (weight 0.10)';
COMMENT ON COLUMN priority_assessments.infrastructure_score  IS 'Step 11 factor Iinfra (weight 0.15)';
COMMENT ON COLUMN priority_assessments.historical_risk_score IS 'Step 11 factor H (weight 0.10)';

CREATE TABLE IF NOT EXISTS resource_estimates (
    estimate_id          bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    complaint_id         bigint      NOT NULL REFERENCES complaints(complaint_id) ON DELETE CASCADE,
    measurement_id       bigint REFERENCES defect_measurements(measurement_id) ON DELETE SET NULL,
    estimate_source      varchar(30) NOT NULL,
    workers_required     numeric(6,2),
    duration_hours       numeric(8,2),
    labour_cost          numeric(12,2),
    material_cost        numeric(12,2),
    equipment_cost       numeric(12,2),
    total_cost_min       numeric(12,2),
    total_cost_expected  numeric(12,2),
    total_cost_max       numeric(12,2),
    rate_reference       text,
    model_name           varchar(150),
    model_version        varchar(50),
    input_features       jsonb NOT NULL DEFAULT '{}'::jsonb,
    is_current           boolean NOT NULL DEFAULT true,
    created_by           bigint REFERENCES users(user_id) ON DELETE SET NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_estimate_source CHECK (estimate_source IN
        ('AI_MODEL','RULE_BASED','STEP10_PRECOMPUTED','CONTRACTOR_INSPECTION','OFFICER_OVERRIDE')),
    CONSTRAINT ck_estimate_values CHECK ((workers_required IS NULL OR workers_required > 0)
        AND (duration_hours IS NULL OR duration_hours > 0)
        AND (total_cost_expected IS NULL OR total_cost_expected >= 0)),
    CONSTRAINT ck_estimate_range CHECK (total_cost_min IS NULL OR total_cost_max IS NULL OR total_cost_min <= total_cost_max)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_resource_estimate_current ON resource_estimates (complaint_id) WHERE is_current;

CREATE TABLE IF NOT EXISTS resource_estimate_materials (
    estimate_id    bigint        NOT NULL REFERENCES resource_estimates(estimate_id) ON DELETE CASCADE,
    material_code  varchar(60)   NOT NULL REFERENCES material_catalog(material_code),
    quantity       numeric(12,4) NOT NULL,
    unit           varchar(20)   NOT NULL,
    rate           numeric(12,2),
    amount         numeric(12,2),
    PRIMARY KEY (estimate_id, material_code),
    CONSTRAINT ck_estimate_material_qty CHECK (quantity >= 0)
);

CREATE TABLE IF NOT EXISTS resource_estimate_equipment (
    estimate_id     bigint       NOT NULL REFERENCES resource_estimates(estimate_id) ON DELETE CASCADE,
    equipment_code  varchar(60)  NOT NULL REFERENCES equipment_catalog(equipment_code),
    quantity        numeric(10,2) NOT NULL,
    unit            varchar(30)  NOT NULL,
    rate            numeric(12,2),
    amount          numeric(12,2),
    PRIMARY KEY (estimate_id, equipment_code),
    CONSTRAINT ck_estimate_equipment_qty CHECK (quantity >= 0)
);

-- -----------------------------------------------------------------------------
-- 7. Action plans (officer-only, editable, downloadable) and optimizer runs
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS optimizer_runs (
    run_id          bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    requested_by    bigint REFERENCES users(user_id) ON DELETE SET NULL,
    request         jsonb       NOT NULL,                 -- filters + selected complaint ids
    solver          varchar(30) NOT NULL DEFAULT 'ORTOOLS_ROUTING',
    status          varchar(20) NOT NULL DEFAULT 'QUEUED',
    started_at      timestamptz,
    finished_at     timestamptz,
    result_summary  jsonb,
    dropped_jobs    jsonb,                                -- job id + human-readable reason
    error_message   text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_optimizer_solver CHECK (solver IN ('ORTOOLS_ROUTING','ORTOOLS_CPSAT','MANUAL')),
    CONSTRAINT ck_optimizer_status CHECK (status IN ('QUEUED','RUNNING','SUCCEEDED','FAILED','CANCELLED'))
);

CREATE TABLE IF NOT EXISTS action_plans (
    action_plan_id        bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    plan_code             varchar(60)  NOT NULL,
    work_type_code        varchar(30)  REFERENCES work_types(work_type_code),
    planned_date          date         NOT NULL,
    status                varchar(20)  NOT NULL DEFAULT 'DRAFT',
    depot_id              varchar(20)  REFERENCES depots(depot_id),
    contractor_id         bigint REFERENCES contractors(contractor_id) ON DELETE SET NULL,
    optimizer_run_id      bigint REFERENCES optimizer_runs(run_id) ON DELETE SET NULL,
    generation_source     varchar(20)  NOT NULL DEFAULT 'OPTIMIZER',
    version               integer      NOT NULL DEFAULT 1,
    job_count             integer      NOT NULL DEFAULT 0,
    total_workers         numeric(8,2),
    est_service_hours     numeric(10,3),
    est_travel_hours      numeric(10,3),
    total_distance_km     numeric(12,3),
    est_total_cost        numeric(14,2),
    planned_start         time,
    planned_end           time,
    route_geometry        geometry(Geometry,4326),
    notes                 text,
    export_pdf_key        text,
    export_xlsx_key       text,
    created_by_user_id    bigint REFERENCES users(user_id) ON DELETE SET NULL,
    approved_by_user_id   bigint REFERENCES users(user_id) ON DELETE SET NULL,
    approved_at           timestamptz,
    assigned_by_user_id   bigint REFERENCES users(user_id) ON DELETE SET NULL,
    assigned_at           timestamptz,
    created_at            timestamptz  NOT NULL DEFAULT now(),
    updated_at            timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT uq_action_plans_code UNIQUE (plan_code),
    CONSTRAINT ck_action_plans_status CHECK (status IN
        ('DRAFT','APPROVED','ASSIGNED','IN_PROGRESS','COMPLETED','CANCELLED')),
    CONSTRAINT ck_action_plans_source CHECK (generation_source IN ('OPTIMIZER','MANUAL')),
    CONSTRAINT ck_action_plans_numbers CHECK (job_count >= 0 AND version >= 1
        AND (est_total_cost IS NULL OR est_total_cost >= 0) AND (total_distance_km IS NULL OR total_distance_km >= 0)),
    CONSTRAINT ck_action_plans_times CHECK (planned_start IS NULL OR planned_end IS NULL OR planned_end > planned_start),
    CONSTRAINT ck_action_plans_assigned CHECK (status NOT IN ('ASSIGNED','IN_PROGRESS','COMPLETED') OR contractor_id IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_action_plans_status     ON action_plans (status, planned_date);
CREATE INDEX IF NOT EXISTS idx_action_plans_contractor ON action_plans (contractor_id);
CREATE INDEX IF NOT EXISTS idx_action_plans_route      ON action_plans USING gist (route_geometry);
CREATE OR REPLACE TRIGGER trg_action_plans_updated_at BEFORE UPDATE ON action_plans
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS action_plan_items (
    item_id               bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    action_plan_id        bigint      NOT NULL REFERENCES action_plans(action_plan_id) ON DELETE CASCADE,
    complaint_id          bigint      NOT NULL REFERENCES complaints(complaint_id) ON DELETE RESTRICT,
    sequence_no           integer     NOT NULL,
    item_status           varchar(25) NOT NULL DEFAULT 'ACTIVE',
    planned_start         timestamp,
    planned_end           timestamp,
    service_duration_h    numeric(8,3),
    travel_from_prev_km   numeric(10,3),
    travel_from_prev_min  numeric(10,2),
    est_workers           numeric(6,2),
    est_cost              numeric(12,2),
    priority_score        numeric(6,2),
    drop_reason           text,
    CONSTRAINT uq_action_plan_item UNIQUE (action_plan_id, complaint_id),
    CONSTRAINT uq_action_plan_sequence UNIQUE (action_plan_id, sequence_no) DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT ck_action_plan_item_status CHECK (item_status IN ('ACTIVE','REMOVED','DROPPED_BY_OPTIMIZER')),
    CONSTRAINT ck_action_plan_item_seq CHECK (sequence_no > 0),
    CONSTRAINT ck_action_plan_item_times CHECK (planned_start IS NULL OR planned_end IS NULL OR planned_end > planned_start)
);
CREATE INDEX IF NOT EXISTS idx_action_plan_items_complaint ON action_plan_items (complaint_id);

-- Every officer edit is versioned (snapshot of the plan + items)
CREATE TABLE IF NOT EXISTS action_plan_revisions (
    revision_id     bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    action_plan_id  bigint      NOT NULL REFERENCES action_plans(action_plan_id) ON DELETE CASCADE,
    version         integer     NOT NULL,
    changed_by      bigint REFERENCES users(user_id) ON DELETE SET NULL,
    change_summary  text,
    snapshot        jsonb       NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_action_plan_revision UNIQUE (action_plan_id, version)
);

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_complaints_current_action_plan') THEN
    ALTER TABLE complaints ADD CONSTRAINT fk_complaints_current_action_plan
      FOREIGN KEY (current_action_plan_id) REFERENCES action_plans(action_plan_id) ON DELETE SET NULL;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_outbox_action_plan') THEN
    ALTER TABLE notification_outbox ADD CONSTRAINT fk_outbox_action_plan
      FOREIGN KEY (action_plan_id) REFERENCES action_plans(action_plan_id) ON DELETE CASCADE;
  END IF;
END $$;

-- -----------------------------------------------------------------------------
-- 8. Field execution: inspection, completion, citizen feedback, votes
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS site_inspections (
    inspection_id              bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    complaint_id               bigint      NOT NULL REFERENCES complaints(complaint_id) ON DELETE CASCADE,
    action_plan_id             bigint REFERENCES action_plans(action_plan_id) ON DELETE SET NULL,
    contractor_id              bigint      NOT NULL REFERENCES contractors(contractor_id) ON DELETE RESTRICT,
    inspected_by_user_id       bigint REFERENCES users(user_id) ON DELETE SET NULL,
    inspected_at               timestamptz NOT NULL DEFAULT now(),
    inspector_location         geometry(Point,4326),
    inspector_accuracy_m       numeric(8,2),
    distance_from_complaint_m  numeric(10,2),
    issue_confirmed            boolean     NOT NULL,
    findings                   text        NOT NULL,
    measurement_id             bigint REFERENCES defect_measurements(measurement_id) ON DELETE SET NULL,
    revised_estimate_id        bigint REFERENCES resource_estimates(estimate_id) ON DELETE SET NULL,
    expected_completion_date   date,
    created_at                 timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_inspection_findings CHECK (btrim(findings) <> '')
);
CREATE INDEX IF NOT EXISTS idx_site_inspections_complaint ON site_inspections (complaint_id);

CREATE TABLE IF NOT EXISTS work_completions (
    completion_id               bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    complaint_id                bigint      NOT NULL REFERENCES complaints(complaint_id) ON DELETE CASCADE,
    action_plan_id              bigint REFERENCES action_plans(action_plan_id) ON DELETE SET NULL,
    contractor_id               bigint      NOT NULL REFERENCES contractors(contractor_id) ON DELETE RESTRICT,
    submitted_by_user_id        bigint REFERENCES users(user_id) ON DELETE SET NULL,
    completed_at                timestamptz NOT NULL DEFAULT now(),
    completion_location         geometry(Point,4326),
    completion_accuracy_m       numeric(8,2),
    distance_from_complaint_m   numeric(10,2),
    work_summary                text        NOT NULL,
    actual_workers              numeric(6,2),
    actual_hours                numeric(8,2),
    actual_cost                 numeric(12,2),
    materials_used              jsonb       NOT NULL DEFAULT '[]'::jsonb,
    verification_status         varchar(20) NOT NULL DEFAULT 'PENDING',
    verified_by_user_id         bigint REFERENCES users(user_id) ON DELETE SET NULL,
    verified_at                 timestamptz,
    verification_remarks        text,
    CONSTRAINT ck_completion_summary CHECK (btrim(work_summary) <> ''),
    CONSTRAINT ck_completion_verification CHECK (verification_status IN ('PENDING','APPROVED','REJECTED')),
    CONSTRAINT ck_completion_verified_meta CHECK (verification_status = 'PENDING'
        OR (verified_by_user_id IS NOT NULL AND verified_at IS NOT NULL)),
    CONSTRAINT ck_completion_actuals CHECK ((actual_cost IS NULL OR actual_cost >= 0)
        AND (actual_hours IS NULL OR actual_hours >= 0) AND (actual_workers IS NULL OR actual_workers > 0))
);
CREATE INDEX IF NOT EXISTS idx_work_completions_complaint ON work_completions (complaint_id);

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_complaint_images_inspection') THEN
    ALTER TABLE complaint_images ADD CONSTRAINT fk_complaint_images_inspection
      FOREIGN KEY (inspection_id) REFERENCES site_inspections(inspection_id) ON DELETE SET NULL;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_complaint_images_completion') THEN
    ALTER TABLE complaint_images ADD CONSTRAINT fk_complaint_images_completion
      FOREIGN KEY (completion_id) REFERENCES work_completions(completion_id) ON DELETE SET NULL;
  END IF;
END $$;

-- Citizen confirms the fix and rates it (counters fake "resolved" photos)
CREATE TABLE IF NOT EXISTS complaint_feedback (
    feedback_id       bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    complaint_id      bigint      NOT NULL REFERENCES complaints(complaint_id) ON DELETE CASCADE,
    user_id           bigint      NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    is_resolved       boolean     NOT NULL,
    rating            smallint,
    comment           text,
    created_at        timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_complaint_feedback UNIQUE (complaint_id, user_id),
    CONSTRAINT ck_feedback_rating CHECK (rating IS NULL OR rating BETWEEN 1 AND 5)
);

-- "Me too" support on nearby complaints (blueprint like/dislike)
CREATE TABLE IF NOT EXISTS complaint_votes (
    complaint_id  bigint      NOT NULL REFERENCES complaints(complaint_id) ON DELETE CASCADE,
    user_id       bigint      NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    vote_type     varchar(10) NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (complaint_id, user_id),
    CONSTRAINT ck_vote_type CHECK (vote_type IN ('UP','DOWN'))
);

-- -----------------------------------------------------------------------------
-- 9. Functions and triggers
-- -----------------------------------------------------------------------------
-- The web backend sets these per transaction before changing a complaint status:
--   SELECT set_config('civicbrain.actor_user_id', '42', true);
--   SELECT set_config('civicbrain.actor_role',   'OFFICER', true);
--   SELECT set_config('civicbrain.status_remarks', 'Pothole filled', true);   -- optional

CREATE OR REPLACE FUNCTION fn_complaint_status_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
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

CREATE OR REPLACE FUNCTION fn_complaint_status_log() RETURNS trigger
LANGUAGE plpgsql AS $$
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

CREATE OR REPLACE TRIGGER trg_complaints_status_guard
    BEFORE INSERT OR UPDATE OF status ON complaints
    FOR EACH ROW EXECUTE FUNCTION fn_complaint_status_guard();

CREATE OR REPLACE TRIGGER trg_complaints_status_log
    AFTER INSERT OR UPDATE OF status ON complaints
    FOR EACH ROW EXECUTE FUNCTION fn_complaint_status_log();

-- Who gets a complaint notification: the owner + owners of duplicate children merged into it
CREATE OR REPLACE FUNCTION fn_complaint_notification_recipients(p_complaint_id bigint)
RETURNS TABLE (user_id bigint, complaint_id bigint, relation text)
LANGUAGE sql STABLE AS $$
    SELECT c.user_id, c.complaint_id, 'OWNER'::text
      FROM complaints c
     WHERE c.complaint_id = p_complaint_id
    UNION
    SELECT ch.user_id, ch.complaint_id, 'MERGED_CHILD_OWNER'::text
      FROM complaints ch
     WHERE ch.master_complaint_id = p_complaint_id
       AND ch.status = 'MERGED';
$$;

-- Inspection / completion: how far was the contractor from the complaint point?
CREATE OR REPLACE FUNCTION fn_set_distance_from_complaint() RETURNS trigger
LANGUAGE plpgsql AS $$
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

CREATE OR REPLACE TRIGGER trg_site_inspections_distance
    BEFORE INSERT OR UPDATE OF inspector_location ON site_inspections
    FOR EACH ROW EXECUTE FUNCTION fn_set_distance_from_complaint();
CREATE OR REPLACE TRIGGER trg_work_completions_distance
    BEFORE INSERT OR UPDATE OF completion_location ON work_completions
    FOR EACH ROW EXECUTE FUNCTION fn_set_distance_from_complaint();

-- GPS point -> boundary / ward / nearest road / nearest POI (used on complaint submit)
CREATE OR REPLACE FUNCTION fn_locate_point(p_lat double precision, p_lon double precision)
RETURNS TABLE (inside_boundary boolean, ward_id bigint, ward_match text,
               road_id bigint, road_distance_m double precision,
               poi_id bigint, poi_distance_m double precision)
LANGUAGE sql STABLE AS $$
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

-- Step 12 candidate pre-filter with the FROZEN parameters (300 m, 7 days).
-- Text similarity (all-MiniLM-L6-v2) + the 0.70/0.20/0.10 score stay in the Python service.
CREATE OR REPLACE FUNCTION fn_duplicate_candidates(p_complaint_id bigint)
RETURNS TABLE (candidate_id bigint, distance_m double precision, hours_apart double precision,
               same_work_type boolean, candidate_status varchar)
LANGUAGE sql STABLE AS $$
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

-- Hamming distance between two 64-bit perceptual hashes (0 = identical, <=4 duplicate, 5-10 review)
CREATE OR REPLACE FUNCTION fn_phash_distance(a bigint, b bigint)
RETURNS integer LANGUAGE sql IMMUTABLE STRICT AS $$
    SELECT bit_count((a # b)::bit(64))::integer;
$$;

-- Earlier photos that look like this one (image reuse check; use for contractor proof photos too)
CREATE OR REPLACE FUNCTION fn_similar_images(p_image_id bigint, p_max_bits integer DEFAULT 10)
RETURNS TABLE (image_id bigint, complaint_id bigint, image_role varchar, hamming_bits integer,
               same_complaint boolean, distance_m double precision)
LANGUAGE sql STABLE AS $$
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

-- Live "2 km, same work type, max 10 jobs" grouping for the Generate Action Plan button.
-- Same rules as the frozen Step 13 clustering, computed on demand in PostGIS:
--   DBSCAN (eps 2000 m, UTM 43N) per work type -> KMeans with max_radius = diameter/2
--   -> split any group that still has more than p_max_jobs members.
CREATE OR REPLACE FUNCTION fn_cluster_jobs(p_complaint_ids bigint[],
                                           p_max_diameter_m double precision DEFAULT 2000,
                                           p_max_jobs integer DEFAULT 10)
RETURNS TABLE (complaint_id bigint, work_type_code varchar, cluster_key text, cluster_size integer)
LANGUAGE sql STABLE AS $$
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

-- Officer approves a DRAFT plan: plan -> APPROVED, its complaints VERIFIED/REOPENED -> SCHEDULED
CREATE OR REPLACE FUNCTION fn_approve_action_plan(p_action_plan_id bigint, p_officer_user_id bigint)
RETURNS integer
LANGUAGE plpgsql AS $$
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

-- Officer assigns an APPROVED plan to a contractor: every complaint owner is notified
CREATE OR REPLACE FUNCTION fn_assign_action_plan(p_action_plan_id bigint, p_contractor_id bigint, p_officer_user_id bigint)
RETURNS integer
LANGUAGE plpgsql AS $$
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

-- -----------------------------------------------------------------------------
-- 10. Views for the dashboards
-- -----------------------------------------------------------------------------
-- Officer queue: one row per master complaint (duplicate children are counted, not listed)
CREATE OR REPLACE VIEW v_officer_complaint_queue AS
SELECT c.complaint_id,
       c.public_ref,
       c.title,
       c.status,
       CASE WHEN c.status IN ('SUBMITTED','VERIFIED','REOPENED')                  THEN 'NEW'
            WHEN c.status IN ('SCHEDULED','ASSIGNED','INSPECTED','IN_PROGRESS')   THEN 'IN_PROGRESS'
            WHEN c.status IN ('COMPLETED','CLOSED')                               THEN 'COMPLETED'
            ELSE 'CLOSED_OUT' END                                                  AS dashboard_tab,
       cat.category_name,
       cat.work_type_code,
       c.ward_id,
       w.ward_number,
       ST_Y(c.location)                                                          AS latitude,
       ST_X(c.location)                                                          AS longitude,
       c.submitted_at,
       c.duplicate_status,
       (SELECT count(*) FROM complaints ch WHERE ch.master_complaint_id = c.complaint_id) AS linked_duplicates,
       coalesce(c.current_priority_score, pa.final_score)                        AS priority_score,
       coalesce(c.current_priority_level, pa.priority_level)                     AS priority_level,
       re.workers_required,
       re.duration_hours,
       re.total_cost_expected,
       c.authenticity_status,
       c.authenticity_score,
       c.ai_status,
       c.current_action_plan_id,
       ap.plan_code,
       ct.firm_name                                                              AS contractor_name,
       c.is_synthetic
  FROM complaints c
  LEFT JOIN complaint_categories cat ON cat.category_id = c.category_id
  LEFT JOIN wards w                  ON w.ward_id = c.ward_id
  LEFT JOIN LATERAL (SELECT p.final_score, p.priority_level
                       FROM priority_assessments p
                      WHERE p.complaint_id = c.complaint_id AND p.is_current
                      ORDER BY p.calculated_at DESC LIMIT 1) pa ON true
  LEFT JOIN LATERAL (SELECT r.workers_required, r.duration_hours, r.total_cost_expected
                       FROM resource_estimates r
                      WHERE r.complaint_id = c.complaint_id AND r.is_current
                      ORDER BY r.created_at DESC LIMIT 1) re ON true
  LEFT JOIN action_plans ap ON ap.action_plan_id = c.current_action_plan_id
  LEFT JOIN contractors ct  ON ct.contractor_id  = c.assigned_contractor_id
 WHERE c.master_complaint_id IS NULL;

-- Citizen tracking timeline
CREATE OR REPLACE VIEW v_complaint_timeline AS
SELECT h.complaint_id,
       c.public_ref,
       c.user_id        AS owner_user_id,
       h.old_status,
       h.new_status,
       h.remarks,
       h.actor_role,
       h.changed_at,
       h.status_history_id
  FROM complaint_status_history h
  JOIN complaints c ON c.complaint_id = h.complaint_id;

-- Contractor work list
CREATE OR REPLACE VIEW v_contractor_worklist AS
SELECT ap.contractor_id,
       ap.action_plan_id,
       ap.plan_code,
       ap.planned_date,
       ap.status             AS plan_status,
       i.sequence_no,
       c.complaint_id,
       c.public_ref,
       c.title,
       c.status              AS complaint_status,
       cat.category_name,
       ST_Y(c.location)      AS latitude,
       ST_X(c.location)      AS longitude,
       c.landmark,
       i.planned_start,
       i.planned_end,
       i.est_workers,
       i.est_cost
  FROM action_plans ap
  JOIN action_plan_items i ON i.action_plan_id = ap.action_plan_id AND i.item_status = 'ACTIVE'
  JOIN complaints c        ON c.complaint_id   = i.complaint_id
  LEFT JOIN complaint_categories cat ON cat.category_id = c.category_id
 WHERE ap.status IN ('ASSIGNED','IN_PROGRESS');

-- -----------------------------------------------------------------------------
-- 11. Fix identity sequences that are behind the data
--     In the backup, complaints_complaint_id_seq is at 1 while complaint_id goes to 500,
--     and pois_poi_id_seq is at 1 while poi_id goes to 26 (rows were loaded with explicit ids).
--     Without this, the FIRST web complaint insert fails with "duplicate key ... (complaint_id)=(1)".
--     Only moves a sequence forward, never backward. No row data is touched.
-- -----------------------------------------------------------------------------
DO $$
DECLARE
    r        record;
    v_max    bigint;
    v_last   bigint;
    v_called boolean;
BEGIN
    FOR r IN
        SELECT c.relname AS tbl, a.attname AS col,
               pg_get_serial_sequence(format('public.%I', c.relname), a.attname) AS seq
          FROM pg_attribute a
          JOIN pg_class c     ON c.oid = a.attrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'public' AND c.relkind = 'r' AND a.attnum > 0 AND NOT a.attisdropped
           AND pg_get_serial_sequence(format('public.%I', c.relname), a.attname) IS NOT NULL
    LOOP
        EXECUTE format('SELECT max(%I) FROM public.%I', r.col, r.tbl) INTO v_max;
        EXECUTE format('SELECT last_value, is_called FROM %s', r.seq) INTO v_last, v_called;
        IF v_max IS NOT NULL AND v_max > (CASE WHEN v_called THEN v_last ELSE v_last - 1 END) THEN
            PERFORM setval(r.seq, v_max, true);
            RAISE NOTICE 'Sequence % moved to % (max %.%)', r.seq, v_max, r.tbl, r.col;
        END IF;
    END LOOP;
END $$;

COMMIT;

-- =============================================================================
-- Optional (run separately, adjust password): least-privilege login for Spring Boot
-- =============================================================================
-- CREATE ROLE civicbrain_app LOGIN PASSWORD 'change-me';
-- GRANT CONNECT ON DATABASE civicbrain TO civicbrain_app;
-- GRANT USAGE ON SCHEMA public TO civicbrain_app;
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO civicbrain_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO civicbrain_app;
-- REVOKE INSERT, UPDATE, DELETE ON step13_teams, step13_team_equipment, step13_clusters,
--        step13_cluster_complaint, step13_schedules, step13_schedule_job, step13_routes,
--        step13_route_stops, step13_action_plans, duplicate_relation FROM civicbrain_app;
