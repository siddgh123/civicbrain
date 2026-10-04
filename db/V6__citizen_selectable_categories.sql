-- =============================================================================
-- CivicBrain | V6__citizen_selectable_categories.sql
-- MVP scope decision of 2026-10-04 (docs/PROGRESS.md, approved by the team): citizens report only 5 categories -
-- Pothole, Road Damage, Waterlogging, Garbage Accumulation and Other. Water Leakage, Blocked Drain and Streetlight
-- stay in the data model (synthetic research data and the priority golden dataset use them; officers still see
-- them on existing complaints) but are no longer offered to citizens (GET /public/categories citizenSelectable,
-- POST /citizen/complaints rejects them).
-- Order   : run AFTER V5 (no new tables, no grant change)
-- Target  : PostgreSQL 16-18 + PostGIS 3.4+
-- Rules   : data only, idempotent, one transaction. Only complaint_categories.citizen_selectable of exactly these
--           3 rows changes: no delete, no rename, no work-type or YOLO-class change.
-- =============================================================================
BEGIN;
SET LOCAL search_path = public;

DO $$
BEGIN
    IF (SELECT count(*) FROM complaint_categories
         WHERE category_name IN ('Water Leakage', 'Blocked Drain', 'Streetlight')) <> 3 THEN
        RAISE EXCEPTION 'V6: the categories Water Leakage, Blocked Drain and Streetlight (V1 seed) were not all found';
    END IF;
END $$;

UPDATE complaint_categories SET citizen_selectable = false
 WHERE category_name IN ('Water Leakage', 'Blocked Drain', 'Streetlight')
   AND citizen_selectable;

COMMENT ON COLUMN complaint_categories.citizen_selectable IS
  'true = offered in the citizen report wizard and accepted by POST /citizen/complaints. false = kept for existing, synthetic and research rows only (V6: Water Leakage, Blocked Drain, Streetlight).';

COMMIT;
