# Ward topology QA report: TDMC analytical wards, v2

Date: 2026-09-30. Engine: PostgreSQL 16.13, PostGIS 3.4.2, GEOS 3.12.1, on the working copy `civicbrain` (schema `qa`).
Outputs: `gis/tdmc_wards_clean_v2.geojson`, `db/V3__wards_topology_clean.sql`, table `qa.wards_clean`.

## Summary

The 23 wards now tile the Talegaon Dabhade municipal boundary exactly. There are no overlaps, no gaps, and no ward area outside the boundary; every residual is under 0.01 m².

The disputed land was 1.50 km², about 6% of the town: the union of all overlaps plus all gaps. It was split with one deterministic rule. **Each disputed point goes to the ward whose undisputed core is nearest.**

Re-deriving `ward_id` from the clean geometry changes:
- 13 of 500 complaints;
- 65 of 1,113 roads;
- 22 of 25 POIs. All 22 POI changes fix an existing id bug; none is caused by the new geometry.

Four overlaps and four gaps larger than 50,000 m² are real ambiguities, not digitising slivers. They need a human check against the reference map (section 7).

## 1. Inputs checked

| Input | Check | Result |
|---|---|---|
| Ward files: verified / processed / archive | `ST_Equals` and `ward_name`, per ward_number | identical, 23/23 |
| Verified wards vs `public.wards` | `ST_Equals(ST_Multi(qa), public)`, by ward_number | identical, 23/23 |
| Boundary vs `public.municipal_boundary` | `ST_Equals` | identical (1 polygon, 14 vertices, status VERIFIED) |
| POIs vs `public.pois` | `ST_Equals`, by poi_id | identical, 25/25 |
| Roads vs `public.roads` | `ST_Equals` | identical, 1,113/1,113 |
| Ward ids | qa / GeoJSON `ward_id` equals ward_number. `public.wards.ward_id` is different (ward 1 = id 21, ward 3 = id 1, ward 13 = id 6, ...). | **Always join by `ward_number`.** |

## 2. Method

All geometric operations ran in EPSG:32643 (UTM 43N). Results were transformed back to EPSG:4326 at the end.

1. **Densify, then project.** Boundary and wards were segmented to ≤ 0.0001° (about 11 m) in 4326 before projecting. This keeps edges that are straight in lon/lat straight after the round trip.
   - Without this step, the boundary's 1–5 km edges bow by a few mm in UTM.
   - Across the whole perimeter that bowing made the 4326 check "boundary minus union" fail at 30.9 m².
2. **Clip.** Each ward was clipped to the boundary.
3. **Disputed area and cores.** D = (union of all pairwise overlaps of the clipped wards) ∪ (boundary minus union of the clipped wards). This gives 60 pieces, 1,503,413 m².
   - Core_i = clipped ward_i minus D.
   - 17 degenerate core parts under 1 m² were dropped; their total area is under 0.001 m². They were added back into D.
4. **Nearest-core split.**
   - Sample points were taken every 1 m along each core boundary: 97,004 points, labelled by ward.
   - Only the parts of a core boundary that face D or the municipal edge were sampled. This includes interior rings, because ward 11's core has a hole.
   - Core-to-core shared edges were skipped. Points there are equidistant to both cores, and with them included, ward 1 picked up 338 stray fragments.
   - `ST_VoronoiPolygons` was built over all points, with the envelope extended 2 km past the boundary.
   - The cells were dissolved per ward and intersected with D.
   - Points were snapped to a 1 cm grid and a 0.02 m Voronoi tolerance was used, because GEOS failed on near-coincident points. When two points coincide, the lowest ward_number wins.
5. **Assemble the wards as one coverage.**
   - All core and assigned-piece boundaries plus the municipal boundary were snap-rounded together on a 1 µm grid.
   - They were polygonized into 884 faces.
   - Each face was labelled by the piece covering most of it, then the faces were dissolved per ward.

   A simple per-ward `ST_Union(core, assigned)` did not work. It left gaps about 1e-10 m wide between pieces, and 7 wards came out as fake 2–7-part MultiPolygons (for example, a detached 68,411 m² part in W19). With the face-based build, neighbours share identical edges.
6. **Smooth the split lines only.**
   - The 1 m Voronoi produces zig-zag split lines: 135,932 vertices, against 134 in the whole input.
   - These were smoothed with `ST_CoverageSimplify(tolerance 1 m, simplifyBoundary = false)`, run on the coverage of D only.
   - D's outline and every undisputed edge are untouched.
   - Maximum shift is 0.46 m, and about 297 m² moved between neighbours along split lines.
7. **Finish.**
   - Clipped to the boundary, `ST_MakeValid`, polygons extracted, MultiPolygon. Holes under 1 m² were removed; none remained.
   - Extra parts under 50 m²: none, so nothing was merged.
   - Transformed to 4326. The collinear densification vertices were stripped with a coverage-safe `ST_CoverageSimplify(1e-7°)`: 8,417 → 4,411 vertices, maximum shift 4.8 mm.

**Areas** are geography areas measured on geometry segmented to ≤ 0.0001°; see section 8.3 for why. The brief's figures used plain `::geography`: 929,943 / 574,799 / 146,803 m², largest gap 137,899 m². They differ from the figures below by less than 0.01%.

## 3. Before

| Quantity | Value |
|---|---|
| Sum of the 23 ward areas | 25,765,646 m² |
| Union of wards | 24,836,371 m² |
| Municipal boundary | 25,264,369 m² |
| Overlapping pairs | 40 with positive area: 39 of at least 1 m², plus a 0.6 m² touch between 20 and 21. Sum 929,937 m²; union of overlaps 928,613 m². |
| Gaps inside the boundary | 28 pieces, 574,800 m² |
| Ward area outside the boundary | 9 pieces, 146,802 m² |

### 3.1 Overlap pairs > 1,000 m² (25 of 40)

Average width ≈ 2 × area / perimeter; length ≈ perimeter / 2.

| Wards | Area m² | Avg width m | Length m |
|---|---:|---:|---:|
| 13 / 16 | 311,060 | 216.6 | 1,436 |
| 19 / 20 | 146,337 | 150.4 | 973 |
| 18 / 19 | 127,993 | 123.2 | 1,038 |
| 17 / 18 | 89,693 | 98.6 | 910 |
| 2 / 3 | 35,779 | 32.7 | 1,094 |
| 5 / 6 | 24,939 | 20.8 | 1,198 |
| 4 / 12 | 23,379 | 24.2 | 965 |
| 3 / 6 | 22,709 | 19.9 | 1,140 |
| 4 / 5 | 16,833 | 13.8 | 1,222 |
| 18 / 21 | 15,147 | 33.8 | 448 |
| 16 / 19 | 14,079 | 30.1 | 468 |
| 7 / 10 | 12,936 | 32.2 | 402 |
| 14 / 15 | 10,515 | 13.7 | 765 |
| 2 / 14 | 9,318 | 25.6 | 364 |
| 13 / 15 | 9,128 | 14.8 | 617 |
| 21 / 22 | 7,918 | 26.9 | 294 |
| 8 / 23 | 7,370 | 20.0 | 368 |
| 1 / 15 | 7,277 | 10.8 | 671 |
| 20 / 23 | 6,302 | 12.5 | 506 |
| 7 / 9 | 6,248 | 25.6 | 244 |
| 19 / 23 | 6,194 | 11.0 | 560 |
| 10 / 17 | 5,389 | 10.7 | 504 |
| 12 / 16 | 3,857 | 6.7 | 572 |
| 16 / 18 | 2,812 | 9.8 | 287 |
| 7 / 11 | 1,133 | 5.6 | 203 |

The other 15 pairs are between 0.6 and 893 m².

### 3.2 Gap pieces > 1,000 m² (24 of 28)

"On boundary" means the gap lies along the municipal boundary.

| # | Area m² | Avg width m | Touching wards | On boundary | Point (lon, lat) |
|---:|---:|---:|---|---|---|
| 1 | 137,908 | 23.6 | 1, 15, 16 | yes | 73.65463, 18.72836 |
| 2 | 69,380 | 18.0 | 5, 6 | yes | 73.70971, 18.74043 |
| 3 | 62,300 | 21.5 | 5, 7, 11, 16, 17 | yes | 73.70220, 18.72294 |
| 4 | 61,717 | 15.7 | 1, 2, 3, 14 | yes | 73.68386, 18.74200 |
| 5 | 43,861 | 16.1 | 7, 8, 9, 10, 22 | yes | 73.71210, 18.71606 |
| 6 | 43,830 | 31.6 | 23 | yes | 73.70955, 18.69805 |
| 7 | 28,922 | 17.6 | 16, 17, 18 | no | 73.68935, 18.71896 |
| 8 | 20,734 | 22.1 | 2, 3, 4, 5, 6 | no | 73.69358, 18.73816 |
| 9 | 19,741 | 22.1 | 19, 23 | yes | 73.69971, 18.70047 |
| 10 | 14,402 | 11.1 | 1, 14, 15 | no | 73.67163, 18.73935 |
| 11 | 9,917 | 13.4 | 18, 19, 20, 21 | no | 73.69853, 18.71211 |
| 12 | 8,978 | 27.4 | 4, 5, 16 | no | 73.69379, 18.72685 |
| 13 | 8,898 | 8.2 | 8, 23 | yes | 73.70982, 18.70785 |
| 14 | 8,760 | 10.6 | 12, 13, 14, 15 | no | 73.67662, 18.73196 |
| 15 | 7,199 | 8.6 | 10, 11, 17 | no | 73.69415, 18.72259 |
| 16 | 5,826 | 16.4 | 4, 12, 14 | no | 73.68359, 18.73573 |
| 17 | 5,042 | 9.0 | 8, 18, 21, 22, 23 | no | 73.70079, 18.71505 |
| 18 | 3,133 | 8.9 | 20, 23 | no | 73.70342, 18.70760 |
| 19 | 2,871 | 14.6 | 10, 21, 22 | no | 73.69814, 18.71695 |
| 20 | 2,816 | 7.8 | 3, 6 | no | 73.69618, 18.74855 |
| 21 | 2,671 | 9.6 | 10, 17, 18, 21 | no | 73.69713, 18.71528 |
| 22 | 1,987 | 4.6 | 4, 12, 16 | no | 73.69051, 18.72938 |
| 23 | 1,188 | 5.9 | 18, 20, 21, 23 | no | 73.70155, 18.71362 |
| 24 | 1,016 | 7.9 | 2, 4, 14 | no | 73.68573, 18.73725 |

The other 4 gaps are 790, 496, 370 and 47 m².

### 3.3 Ward area outside the boundary (all pieces ≥ 1 m²)

| Ward | 16 | 23 | 8 | 19 | 5 | 3 | 1 | 6 | 23 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Area m² | 64,746 | 27,996 | 22,426 | 11,911 | 7,658 | 5,133 | 3,939 | 2,069 | 923 |
| Avg width m | 45.2 | 36.2 | 29.6 | 9.0 | 14.3 | 10.6 | 6.8 | 3.6 | 5.0 |

## 4. After: checks in EPSG:4326 (geography areas)

| Check | Value | Required | Result |
|---|---|---|---|
| Wards / non-empty | 23 / 23 | 23 | PASS |
| `ST_IsValid` | 23 / 23 | all | PASS |
| Pairwise overlap total | 0.000000 m² (0 pairs with area) | < 1 m² | PASS |
| Boundary minus union | 0.005 m² | < 1 m² | PASS |
| Union minus boundary | 0.004 m² | < 1 m² | PASS |
| Coverage (`ST_CoverageInvalidEdges`) | 0 invalid edges | 0 | PASS |
| Union area vs boundary area | 25,264,368.95 vs 25,264,368.95 m² | equal | PASS |
| MultiPolygons with > 1 part | 1: ward 18, extra part 210.6 m² | merge if < 50 m² | PASS (≥ 50 m², kept; see section 7) |
| Holes | 0 | — | — |
| GeoJSON file reloaded with `ST_GeomFromGeoJSON` | identical to `qa.wards_clean`; same checks pass | — | PASS |
| V3 applied to fresh DBs, with and without V2 | EWKB identical to `qa.wards_clean`, 23/23 | — | PASS |

## 5. Per-ward areas

| Ward | Before km² | After km² | Gained m² | Lost m² | Net m² |
|---:|---:|---:|---:|---:|---:|
| 1 | 2.346296 | 2.384960 | 46,508 | 7,844 | +38,664 |
| 2 | 0.805173 | 0.806195 | 24,502 | 23,480 | +1,022 |
| 3 | 0.759894 | 0.736982 | 11,457 | 34,369 | −22,912 |
| 4 | 0.629081 | 0.614021 | 6,586 | 21,645 | −15,060 |
| 5 | 1.510580 | 1.504681 | 22,639 | 28,538 | −5,899 |
| 6 | 2.522009 | 2.565612 | 69,406 | 25,802 | +43,603 |
| 7 | 0.292885 | 0.315648 | 33,081 | 10,318 | +22,763 |
| 8 | 0.867726 | 0.876764 | 34,962 | 25,924 | +9,038 |
| 9 | 0.053038 | 0.051717 | 2,171 | 3,493 | −1,321 |
| 10 | 0.170899 | 0.164001 | 2,699 | 9,597 | −6,898 |
| 11 | 0.319881 | 0.342973 | 23,780 | 689 | +23,092 |
| 12 | 0.447680 | 0.436393 | 2,301 | 13,588 | −11,287 |
| 13 | 0.903023 | 0.726545 | 4,271 | 180,749 | −176,478 |
| 14 | 0.446910 | 0.446275 | 9,737 | 10,372 | −635 |
| 15 | 4.244030 | 4.358660 | 128,189 | 13,559 | +114,630 |
| 16 | 3.760046 | 3.589299 | 40,209 | 210,956 | −170,747 |
| 17 | 0.937310 | 0.900672 | 16,596 | 53,233 | −36,638 |
| 18 | 0.667766 | 0.558294 | 7,410 | 116,881 | −109,472 |
| 19 | 1.678318 | 1.548468 | 16,943 | 146,793 | −129,850 |
| 20 | 0.522354 | 0.445008 | 6,954 | 84,301 | −77,346 |
| 21 | 0.119046 | 0.110420 | 3,350 | 11,976 | −8,626 |
| 22 | 0.128671 | 0.131033 | 6,041 | 3,678 | +2,362 |
| 23 | 1.633029 | 1.649747 | 55,467 | 38,750 | +16,718 |
| **Total** | **25.765646** | **25.264368** | **575,258** | **1,076,535** | **−501,278** |

- "Before" is the unclipped verified ward.
- "Gained" is area the ward did not have before: gaps, or overlap land that went to a third ward.
- "Lost" is area it gave up: the side of an overlap it did not win, plus anything outside the boundary.
- Before + gained − lost = after, to within 0.5 m² per ward.

## 6. Re-assignment of complaints, POIs and roads (V3 migration)

Rules:
- **Complaints and POIs:** the ward whose geometry `ST_Covers` the point. Ties on a shared edge go to the smallest ward, then the lowest ward_number, which is the same order as V2's `fn_locate_point`. If no ward covers the point, the nearest ward by geography distance.
- **Roads:** the ward holding the largest share of the road's length, with ties going to the lowest ward_number.
- Every change is written to `ward_reassignment_log` before the update.

| Entity | Changed | Notes |
|---|---:|---|
| Complaints | **13 / 500** | All 13 sat in an overlap, so two old wards covered them. After V3, all 500 are covered by exactly one ward (0 outside, 0 in two or more). |
| POIs | 22 / 25 | All are id corrections, not geometry changes: `pois.ward_id` held ward **numbers** (see section 8.1). Every POI keeps its ward number. |
| Roads | 65 / 1,113 | 61 run through the disputed area. The other 4 (roads 257, 644, 897, 1081) did not follow the largest-length rule before either. |

Complaints that change ward (the old ward is the one stored before; "covered by" uses the old geometry):

| complaint_id | public_ref | Old ward (ward_id) | New ward (ward_id) | Old geometry covered by |
|---:|---|---:|---:|---|
| 34 | CB-000034 | 13 (6) | 16 (7) | 13 & 16 |
| 70 | CB-000070 | 17 (8) | 10 (11) | 10 & 17 |
| 104 | CB-000104 | 20 (17) | 19 (19) | 19 & 20 |
| 181 | CB-000181 | 3 (1) | 2 (2) | 2 & 3 |
| 247 | CB-000247 | 16 (7) | 19 (19) | 16 & 19 |
| 254 | CB-000254 | 13 (6) | 16 (7) | 13 & 16 |
| 297 | CB-000297 | 13 (6) | 16 (7) | 13 & 16 |
| 393 | CB-000393 | 13 (6) | 16 (7) | 13 & 16 |
| 417 | CB-000417 | 13 (6) | 16 (7) | 13 & 16 |
| 423 | CB-000423 | 13 (6) | 16 (7) | 13 & 16 |
| 435 | CB-000435 | 3 (1) | 2 (2) | 2 & 3 |
| 463 | CB-000463 | 18 (18) | 19 (19) | 18 & 19 |
| 486 | CB-000486 | 18 (18) | 19 (19) | 18 & 19 |

Road changes, by ward number (old → new):
- 13→16: 12; 13→15: 6; 12→4: 5
- 1→15, 12→16, 14→13, 19→16, 23→8: 3 each
- 4→12, 4→16, 5→6, 11→5, 12→13, 14→1, 14→15, 16→15, 20→23: 2 each
- 2→1, 2→4, 3→6, 4→5, 7→11, 13→12, 18→19, 19→23, 20→19: 1 each

Six of the 13 complaint changes (13 → 16) and 12 of the road changes (13 → 16) come from the 13/16 overlap. They depend on the human confirmation below.

## 7. Needs human confirmation

These are not digitising slivers: they are 99–217 m wide. The nearest-core rule gives a defensible, reproducible split, but only the reference map can say where the real ward line is.

| Area | Size m² | How it was split (nearest undisputed core) |
|---|---:|---|
| Overlap 13 / 16 | 311,060 | W16 175,977 (57%) · W13 135,083 (43%) |
| Overlap 19 / 20 | 146,337 | W19 81,131 (55%) · W20 65,165 (45%) · W23 41 |
| Overlap 18 / 19 | 127,993 | W19 68,432 (53%) · W18 59,561 (47%) |
| Overlap 17 / 18 | 89,693 | W18 50,209 (56%) · W17 39,484 (44%) |
| Gap 1 (73.65463, 18.72836), on the boundary | 137,908 | W15 122,950 (89%) · W16 14,659 (11%) · W1 298 |
| Gap 2 (73.70971, 18.74043), on the boundary | 69,380 | W6 68,593 (99%) · W5 786 (1%) |
| Gap 3 (73.70220, 18.72294), on the boundary | 62,300 | W7 26,021 (42%) · W11 19,761 (32%) · W5 10,269 (16%) · W16 6,225 (10%) · W17 25 |
| Gap 4 (73.68386, 18.74200), on the boundary | 61,717 | W1 39,033 (63%) · W2 22,553 (37%) · W3 88 · W14 43 |
| Ward 18 detached part (73.70106, 18.71453) | 210.6 | Kept as a second part of ward 18. 78 m² of it was inside ward 18's original polygon (25 m² of that also inside ward 21); the rest was gap. It lies 27 m from ward 18's main part and is surrounded by W21 (34.9 m of shared border), W23 (17.4 m) and W22 (7.5 m). If the map shows it belongs to W21, merge it there. |

**How to review in QGIS**

1. Add the raster `gis/raw/official_sources/tdmc_boundary_georeferenced.tif`.
2. Add `gis/tdmc_wards_clean_v2.geojson`. Style it with no fill and a 1.5 px outline, labelled with `ward_number`.
3. Optional: add the original `gis/verified/tdmc_wards_verified.geojson` with a red dashed outline, so the disputed zones stand out.
4. For each row above, zoom to the point (Locator: type the lon, lat) and compare the new ward line with the ward line on the reference map.
5. If a split is wrong, fix it in a new migration (V4), not in V3:
   - Edit with **Topological editing** on and snapping to the layer, so that moving a shared edge moves it in both wards.
   - Re-check with Vector › Geometry Tools › Check Validity and the Topology Checker rules "must not overlap" and "must not have gaps".
   - Re-run section 6 so complaints, POIs and roads follow the new lines.

## 8. Other findings

1. **POI ward ids were wrong.** `public.pois.ward_id` holds the source-file ward id, which equals ward_number, instead of `public.wards.ward_id`. The foreign key still passes, because ids 1–23 exist, so nothing flagged it. As a result, 22 of 25 POIs point at the wrong ward: for example, MIMER Medical College, in ward 14, is stored as 14, which is ward_id 14 = ward 22. V3 corrects this. The POI import should be fixed so the bug does not come back.
2. **V2's `fn_cluster_jobs` depends on row order.** `ST_ClusterKMeans ... OVER (PARTITION BY ...)` has no ORDER BY, so K-means seeding follows physical row order. After V3, the "live clustering" row of `test_V2_workflow.sql` reads ELECTRICITY 11 clusters / max 9 and GARBAGE 13 / max 8, instead of 11 / 10 and 11 / 8. On a V2-only copy, a no-op `UPDATE complaints SET ward_id = ward_id` on the same 13 rows reproduces exactly those numbers. So this is not a V3 effect, but the Generate Action Plan clusters are not deterministic. Consider adding `ORDER BY complaint_id` to that window.
3. **How areas are measured.** Plain `ST_Area(geom::geography)` treats every edge as a geodesic, but GeoJSON and PostGIS geometry treat an edge as a straight lon/lat line. With the 14-vertex boundary this is visible:
   - `ST_Area(boundary::geography)` = 25,263,771 m², while the same polygon with extra collinear vertices measures 25,264,369 m².
   - Plain-cast "boundary minus union" shows 2.1 m² and "union minus boundary" shows 2.0 m². This is only edge semantics; it is not a gap.
   - All areas in this report are therefore geography areas of geometry segmented to ≤ 0.0001°.
4. **GeoJSON precision.** The file uses full precision (up to 15 decimals, 178 KB) instead of 7 decimals. Rounding to 7 decimals (about 1 cm) moves boundary vertices by up to 5 mm; over about 25 km of perimeter that gives a 30.9 m² gap, 21.6 m² outside, and 2 invalid coverage edges. 9 or 10 decimals still left invalid coverage edges. Full precision round-trips exactly to the database geometry.
5. **Side effect of the complaint update.** `trg_complaints_updated_at` sets `updated_at` on the 13 re-assigned complaints. Triggers were not disabled. `status` is not touched, so the status guard and status log do not fire.

## 9. Tests run

| Test | Result |
|---|---|
| `cb_v3test` = copy of `civicbrain_pristine`, then V2, then V3 | V2 OK. V3 OK: "23 ward geometries replaced (v2); re-assigned 13 complaints, 22 pois, 65 roads" |
| V3 run a second time | no-op: "already applied ... nothing to do", no errors |
| Checks on `public.wards` in `cb_v3test` | 23 rows, 23 valid MultiPolygons, overlap 0 m², gap 0.005 m², outside 0.004 m², 0 invalid coverage edges |
| Every complaint covered by exactly one ward | 500 / 500, and each is assigned to that ward |
| `ward_geometry_history` / `ward_reassignment_log` | 23 rows (version v2) / 13 complaint + 22 poi + 65 road |
| `test_V2_workflow.sql` on `cb_v3test` | "NEGATIVE TESTS PASSED: 6 / 6", 0 ERROR lines, ends in ROLLBACK. Only ids and the K-means row differ from the stored output (section 8.2). |
| `cb_v3solo` = copy of `civicbrain_pristine`, then V3 only (no V2) | OK; run twice (second run is a no-op); same checks and counts; geometry identical |
| `civicbrain` public schema and `civicbrain_pristine` | unchanged (complaints ward hash identical, no V3 tables) |

The test databases were dropped afterwards.
