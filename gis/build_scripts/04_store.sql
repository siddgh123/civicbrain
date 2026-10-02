\timing on
drop table if exists qa.wards_clean, qa.wc_strip_test;
create table qa.wards_clean (
  ward_id int, ward_number int, ward_name text, geom geometry(MultiPolygon,4326),
  area_km2 numeric, area_before_m2 numeric, gained_m2 numeric, lost_m2 numeric);
-- back to 4326; strip only the (collinear) 0.0001-deg densification vertices with a coverage-safe VW pass (1e-7 deg)
insert into qa.wards_clean (ward_id, ward_number, ward_name, geom)
select ward_id, ward_number, ward_name,
       ST_Multi(ST_CollectionExtract(ST_SetSRID(ST_CoverageSimplify(g4326, 1e-7, true) over (), 4326), 3))
  from (select ward_id, ward_number, ward_name, ST_Transform(g, 4326) g4326 from qa.wc_final) s;
-- areas: geography, measured on geometries segmented to <= 0.0001 deg so edges are interpreted as straight lon/lat lines
update qa.wards_clean c set
  area_km2       = round((ST_Area(ST_Segmentize(c.geom,0.0001)::geography)/1e6)::numeric, 6),
  area_before_m2 = round(ST_Area(ST_Segmentize(w.geom,0.0001)::geography)::numeric, 2),
  gained_m2      = round(coalesce(ST_Area(ST_Segmentize(ST_Difference(c.geom, w.geom),0.0001)::geography),0)::numeric, 2),
  lost_m2        = round(coalesce(ST_Area(ST_Segmentize(ST_Difference(w.geom, c.geom),0.0001)::geography),0)::numeric, 2)
  from qa.wards w where w.src='verified' and w.ward_number = c.ward_number;
comment on table qa.wards_clean is 'CivicBrain wards topology-cleaned v2: 23 verified wards clipped to the TDMC boundary; pairwise overlaps + gaps (disputed area) split to the nearest undisputed core (Voronoi of 1 m-densified core edges, EPSG:32643); exact coverage of the boundary. ward_id = qa.wards ward_id (NOT public.wards.ward_id) - join by ward_number.';
select ward_number, ward_id, area_km2, area_before_m2, gained_m2, lost_m2, ST_NumGeometries(geom) parts, ST_NPoints(geom) npts,
       round(area_before_m2 + gained_m2 - lost_m2 - area_km2*1e6, 3) balance_check
  from qa.wards_clean order by ward_number;
