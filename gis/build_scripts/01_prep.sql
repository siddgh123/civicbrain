\timing on
-- ---------- inputs in UTM 43N
drop table if exists qa.wc_b, qa.wc_w, qa.wc_ov, qa.wc_gap, qa.wc_d, qa.wc_core, qa.wc_pts, qa.wc_cells, qa.wc_vor, qa.wc_assigned, qa.wc_final cascade;
-- inputs densified to <= 0.0001 deg in 4326 first, so lon/lat-straight edges stay straight after the UTM round trip
create table qa.wc_b as select ST_Transform(ST_Segmentize(geom, 0.0001),32643) g from qa.boundary where src='verified';
create table qa.wc_w as
select ward_id, ward_number, ward_name, ST_Transform(ST_Segmentize(geom, 0.0001),32643) g_raw, null::geometry g_clip
  from qa.wards where src='verified';
update qa.wc_w set g_clip = ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_Intersection(g_raw,(select g from qa.wc_b))),3));
select ward_number, ST_NumGeometries(g_clip) nparts, round(ST_Area(g_raw)::numeric) a_raw, round(ST_Area(g_clip)::numeric) a_clip from qa.wc_w where ST_NumGeometries(g_clip)<>1 or true order by 1;

-- ---------- pairwise overlaps (of clipped wards)
create table qa.wc_ov as
select a.ward_number wa, c.ward_number wb, ST_CollectionExtract(ST_Intersection(a.g_clip,c.g_clip),3) g
  from qa.wc_w a join qa.wc_w c on a.ward_number<c.ward_number and ST_Intersects(a.g_clip,c.g_clip);
delete from qa.wc_ov where ST_IsEmpty(g) or ST_Area(g)=0;
select count(*) n_pairs, round(sum(ST_Area(g))::numeric) sum_area from qa.wc_ov;

-- ---------- gaps inside boundary
create table qa.wc_gap as
select ST_CollectionExtract(ST_Difference(b.g, (select ST_Union(g_clip) from qa.wc_w)),3) g from qa.wc_b b;
select ST_NumGeometries(g) n, round(ST_Area(g)::numeric) a from qa.wc_gap;

-- ---------- disputed area D
create table qa.wc_d as
select ST_CollectionExtract(ST_UnaryUnion(ST_Collect(g)),3) g
  from (select g from qa.wc_ov union all select g from qa.wc_gap) s;
select ST_NumGeometries(g) n, round(ST_Area(g)::numeric) a, ST_IsValid(g) from qa.wc_d;

-- ---------- cores: clipped ward minus D, parts < 1 m2 dropped (dropped parts go back into D)
create table qa.wc_core as
with parts as (
  select w.ward_number, (ST_Dump(ST_CollectionExtract(ST_Difference(w.g_clip, d.g),3))).geom g
    from qa.wc_w w, qa.wc_d d)
select ward_number, ST_Multi(ST_Collect(g) filter (where ST_Area(g) >= 1)) g,
       ST_Collect(g) filter (where ST_Area(g) < 1) g_dropped,
       count(*) filter (where ST_Area(g) >= 1) n_parts,
       count(*) filter (where ST_Area(g) < 1) n_dropped
  from parts group by ward_number;
select ward_number, n_parts, n_dropped, round(ST_Area(g)::numeric) a_core, ST_NRings(g)-ST_NumGeometries(g) n_holes from qa.wc_core order by 1;
update qa.wc_d set g = ST_CollectionExtract(ST_UnaryUnion(ST_Collect(qa.wc_d.g, x.g)),3)
  from (select ST_Collect(g_dropped) g from qa.wc_core where g_dropped is not null) x where x.g is not null;
select ST_NumGeometries(g) n, ST_Area(g) a from qa.wc_d;
