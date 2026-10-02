\timing on
\set spacing 1.0
drop table if exists qa.wc_pts, qa.wc_cells, qa.wc_vor, qa.wc_assigned cascade;
-- Sample ring points (exterior AND interior rings) of each core, EXCLUDING boundary portions shared with
-- another core (points there are equidistant to both cores and can never be the nearest-core witness of
-- a disputed point; keeping them only produces interleaved label fans). Spacing :spacing m, 1 cm grid.
create table qa.wc_pts as
with facing as (
  select c.ward_number,
         ST_Difference(ST_Boundary(c.g),
                       coalesce((select ST_Buffer(ST_Union(o.g), 0.01) from qa.wc_core o
                                  where o.ward_number <> c.ward_number and ST_DWithin(o.g, c.g, 0.02)),
                                'POLYGON EMPTY'::geometry)) g
    from qa.wc_core c)
select distinct on (ST_X(p), ST_Y(p)) ward_number, p g
  from (select ward_number, ST_SnapToGrid((ST_DumpPoints(ST_Segmentize(g, :spacing))).geom, 0.01) p from facing) s
 order by ST_X(p), ST_Y(p), ward_number;          -- exact duplicate coords: lowest ward_number wins (deterministic)
create index on qa.wc_pts using gist(g);
select count(*) n_pts from qa.wc_pts;

create table qa.wc_cells as
select (ST_Dump(ST_VoronoiPolygons(ST_Collect(g), 0.02,
        (select ST_Expand(ST_Envelope(g), 2000) from qa.wc_b)))).geom g
  from qa.wc_pts;
create index on qa.wc_cells using gist(g);
alter table qa.wc_cells add column ward_number int;
update qa.wc_cells c set ward_number = (select p.ward_number from qa.wc_pts p where ST_Intersects(c.g, p.g) order by p.ward_number limit 1);
update qa.wc_cells c set ward_number = (select p.ward_number from qa.wc_pts p order by p.g <-> ST_PointOnSurface(c.g), p.ward_number limit 1) where ward_number is null;
select count(*) n_cells, count(ward_number) labelled from qa.wc_cells;

create table qa.wc_vor as
select ward_number, ST_UnaryUnion(ST_Collect(g)) g from qa.wc_cells group by ward_number;

create table qa.wc_assigned as
select v.ward_number, ST_CollectionExtract(ST_Intersection(v.g, d.g),3) g
  from qa.wc_vor v, qa.wc_d d;
select round(sum(ST_Area(g))::numeric,3) sum_assigned, (select round(ST_Area(g)::numeric,3) from qa.wc_d) d_area from qa.wc_assigned;
