select json_build_object(
  'type', 'FeatureCollection',
  'name', 'tdmc_wards_clean_v2',
  'features', json_agg(json_build_object(
      'type', 'Feature',
      'properties', json_build_object(
          'ward_id', ward_id, 'ward_number', ward_number, 'ward_name', ward_name,
          'ward_scheme', 'ANALYTICAL_GIS_23',
          'source', 'CivicBrain analytical GIS units, topology-cleaned v2 (from tdmc_wards_verified.geojson; disputed areas split to nearest undisputed core)',
          'area_km2', area_km2),
      'geometry', ST_AsGeoJSON(ST_ForcePolygonCCW(geom), :prec)::json) order by ward_number))
from qa.wards_clean;
