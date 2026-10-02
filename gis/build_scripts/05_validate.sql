-- validation IN 4326; areas = geography (segmented to 0.0001 deg first = planar lon/lat edge semantics), plain geography shown too
with w as (select ward_number, geom g from qa.wards_clean),
b as (select geom g from qa.boundary where src='verified'),
u as (select ST_UnaryUnion(ST_Collect(g)) g from w),
ov as (select coalesce(sum(ST_Area(ST_Segmentize(ST_Intersection(a.g,c.g),0.0001)::geography)),0) a,
              coalesce(sum(ST_Area(ST_Intersection(a.g,c.g)::geography)),0) a_plain,
              count(*) filter (where ST_Area(ST_Intersection(a.g,c.g)) > 0) n
         from w a join w c on a.ward_number < c.ward_number and ST_Intersects(a.g,c.g))
select (select count(*) from w) n_wards,
       (select count(*) from w where ST_IsValid(g)) n_valid,
       (select count(*) from w where ST_IsEmpty(g) or ST_Area(g) = 0) n_empty,
       round(ov.a::numeric,6) overlap_m2, round(ov.a_plain::numeric,6) overlap_plain_m2, ov.n overlap_pairs_gt0,
       round(ST_Area(ST_Segmentize(ST_Difference(b.g, u.g),0.0001)::geography)::numeric,6) b_minus_u_m2,
       round(ST_Area(ST_Difference(b.g, u.g)::geography)::numeric,6) b_minus_u_plain_m2,
       round(ST_Area(ST_Segmentize(ST_Difference(u.g, b.g),0.0001)::geography)::numeric,6) u_minus_b_m2,
       round(ST_Area(ST_Difference(u.g, b.g)::geography)::numeric,6) u_minus_b_plain_m2,
       round(ST_Area(ST_Segmentize(u.g,0.0001)::geography)::numeric,2) union_m2, round(ST_Area(ST_Segmentize(b.g,0.0001)::geography)::numeric,2) boundary_m2,
       (select count(*) from w where ST_NumGeometries(g) > 1) n_multipart,
       (select count(*) from (select ST_CoverageInvalidEdges(g, 0) over () e from w) s where e is not null) coverage_invalid_edges,
       (select sum(ST_NPoints(g)) from w) total_vertices
  from b, u, ov;
with p as (select c.ward_number, d.geom g from qa.wards_clean c, lateral ST_Dump(c.geom) d),
r as (select ward_number, ST_Area(ST_Segmentize(g,0.0001)::geography) a, row_number() over (partition by ward_number order by ST_Area(g) desc) rn, g from p)
select ward_number, rn, round(a::numeric,2) extra_part_m2, ST_AsText(ST_PointOnSurface(g)) pos from r where rn > 1;
