\timing on
\set gs 0.000001
drop table if exists qa.wc_final, qa.wc_extra, qa.wc_pieces, qa.wc_faces, qa.wc_dcov, qa.wc_merge_log cascade;
-- 5a. pieces = undisputed cores + assigned disputed parts
create table qa.wc_pieces as
select ward_number, 'core'::text kind, (ST_Dump(g)).geom g from qa.wc_core
union all
select ward_number, 'assigned', (ST_Dump(g)).geom g from qa.wc_assigned where not ST_IsEmpty(g);
create index on qa.wc_pieces using gist(g);

-- 5b. ONE snap-rounded (1 µm grid) noding of all piece rings + municipal boundary, polygonize => exact coverage faces
create table qa.wc_faces as
with lines as (
  select ST_UnaryUnion(ST_Collect(l), :gs) g
    from (select ST_Boundary(g) l from qa.wc_pieces union all select ST_Boundary(g) from qa.wc_b) s),
poly as (select ST_Polygonize(g) g from lines)
select row_number() over (order by ST_XMin(d.geom), ST_YMin(d.geom), ST_Area(d.geom)) face_id, d.geom g
  from poly, lateral ST_Dump(poly.g) d;
create index on qa.wc_faces using gist(g);
alter table qa.wc_faces add column ward_number int, add column kind text, add column cover_m2 double precision;
delete from qa.wc_faces f using qa.wc_b b where ST_Area(ST_Intersection(f.g, b.g)) <= 0.5*ST_Area(f.g);
-- label each face with the piece covering most of it (ties: lowest ward_number, core before assigned)
update qa.wc_faces f set ward_number = x.ward_number, kind = x.kind, cover_m2 = x.a
  from (select distinct on (f2.face_id) f2.face_id, p.ward_number, p.kind, ST_Area(ST_Intersection(f2.g, p.g)) a
          from qa.wc_faces f2 join qa.wc_pieces p on ST_Intersects(f2.g, p.g)
         order by f2.face_id, ST_Area(ST_Intersection(f2.g, p.g)) desc, p.ward_number, p.kind desc) x
 where x.face_id = f.face_id and x.a > 0;
select count(*) n_faces, count(ward_number) labelled, round(sum(ST_Area(g))::numeric,4) area,
       round(sum(abs(ST_Area(g) - cover_m2))::numeric,6) label_mismatch_m2 from qa.wc_faces;

-- 5c. disputed-area coverage per ward; simplify ONLY its internal split lines (Voronoi zig-zag), outline of D fixed
create table qa.wc_dcov as
select ward_number, (ST_Dump(ST_UnaryUnion(ST_Collect(g), :gs))).geom g0
  from qa.wc_faces where kind = 'assigned' group by ward_number;
alter table qa.wc_dcov add column g geometry;
update qa.wc_dcov d set g = s.g from (
  select ctid c, ST_SetSRID(ST_CoverageSimplify(g0, 1.0, false) over (), 32643) g from qa.wc_dcov) s where s.c = d.ctid;
select count(*) n, sum(ST_NPoints(g0)) pts_before, sum(ST_NPoints(g)) pts_after, bool_and(ST_IsValid(g)) valid,
       round(max(ST_HausdorffDistance(g0,g))::numeric,3) max_shift_m,
       round((sum(ST_Area(ST_SymDifference(g0,g)))/2)::numeric,1) area_moved_m2,
       round(ST_Area(ST_SymDifference(ST_UnaryUnion(ST_Collect(g0)), ST_UnaryUnion(ST_Collect(g))))::numeric,6) outline_change_m2
  from qa.wc_dcov;

-- 5d. Ward_final_i = core faces_i ∪ simplified assigned_i, clipped to boundary, valid polygons, holes < 1 m2 removed
create table qa.wc_final as
with u as (
  select w.ward_id, w.ward_number, w.ward_name,
         ST_CollectionExtract(ST_MakeValid(ST_Intersection(ST_UnaryUnion(ST_Collect(x.g), :gs), b.g, :gs)),3) g
    from qa.wc_w w
    join (select ward_number, g from qa.wc_faces where kind = 'core'
          union all select ward_number, g from qa.wc_dcov) x using (ward_number)
    cross join qa.wc_b b
   group by w.ward_id, w.ward_number, w.ward_name, b.g),
parts as (select u.ward_id, u.ward_number, u.ward_name, d.path[1] pn, d.geom g from u, lateral ST_Dump(u.g) d
           where ST_Area(d.geom) > 0)
select ward_id, ward_number, ward_name,
       ST_Multi(ST_Collect(ST_MakePolygon(ST_ExteriorRing(p.g),
            coalesce((select array_agg(ST_ExteriorRing(r.geom) order by r.path[1])
                        from ST_DumpRings(p.g) r where r.path[1] > 0 and ST_Area(r.geom) >= 1), '{}'::geometry[]))
            order by pn)) g,
       sum(ST_NRings(p.g) - 1) holes_in
  from parts p group by ward_id, ward_number, ward_name;

-- 6-pre. extra parts; parts < 50 m2 are merged into the neighbour with the longest shared border
create table qa.wc_merge_log (ward_from int, ward_to int, area_m2 double precision, shared_len_m double precision);
create table qa.wc_extra as
with p as (select f.ward_number, d.geom g from qa.wc_final f, lateral ST_Dump(f.g) d),
r as (select *, row_number() over (partition by ward_number order by ST_Area(g) desc) rn from p)
select ward_number, rn, g, ST_Area(g) area_m2 from r where rn > 1;
select ward_number, rn, round(area_m2::numeric,4) area_m2 from qa.wc_extra order by area_m2 desc;

insert into qa.wc_merge_log
select e.ward_number, n.ward_number, e.area_m2, ST_Length(ST_Intersection(ST_Boundary(e.g), n.g))
  from qa.wc_extra e
  join lateral (select f.ward_number, f.g from qa.wc_final f
                 where f.ward_number <> e.ward_number and ST_Intersects(f.g, e.g)
                 order by ST_Length(ST_Intersection(ST_Boundary(e.g), f.g)) desc, f.ward_number limit 1) n on true
 where e.area_m2 < 50;
select * from qa.wc_merge_log;
update qa.wc_final f set g = ST_Multi(ST_CollectionExtract(ST_Difference(f.g, (select ST_Collect(e.g) from qa.wc_extra e join qa.wc_merge_log m on m.ward_from=e.ward_number and m.area_m2=e.area_m2 where e.ward_number=f.ward_number), :gs),3))
 where f.ward_number in (select ward_from from qa.wc_merge_log);
update qa.wc_final f set g = ST_Multi(ST_CollectionExtract(ST_UnaryUnion(ST_Collect(f.g, (select ST_Collect(e.g) from qa.wc_extra e join qa.wc_merge_log m on m.ward_from=e.ward_number and m.area_m2=e.area_m2 where m.ward_to=f.ward_number)), :gs),3))
 where f.ward_number in (select ward_to from qa.wc_merge_log);

-- UTM checks
select ward_number, ST_NumGeometries(g) nparts, ST_NRings(g)-ST_NumGeometries(g) nholes, holes_in, ST_NPoints(g) npts, ST_IsValid(g) valid,
       round(ST_Area(g)::numeric) area_utm from qa.wc_final order by 1;
select (select count(*) from (select ST_CoverageInvalidEdges(g, 0) over () e from qa.wc_final) s where e is not null) coverage_invalid_edges,
       (select ST_Area(ST_Difference(b.g, ST_UnaryUnion(ST_Collect(f.g)))) from qa.wc_final f, qa.wc_b b group by b.g) gap_utm,
       (select ST_Area(ST_Difference(ST_UnaryUnion(ST_Collect(f.g)), b.g)) from qa.wc_final f, qa.wc_b b group by b.g) outside_utm,
       (select sum(ST_Area(ST_Intersection(a.g,c.g))) from qa.wc_final a join qa.wc_final c on a.ward_number<c.ward_number and ST_Intersects(a.g,c.g)) overlap_utm;
