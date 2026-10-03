package com.civicbrain.complaints.repo;

import java.util.List;
import java.util.Optional;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/** Read-only reference data for the citizen portal: categories and the 23 analytical wards (docs/03 §2). */
@Repository
public class ReferenceRepository {

    /** One {@code complaint_categories} row. */
    public record Category(long id, String name, String workTypeCode, boolean citizenSelectable, boolean needsDepthAnswer,
                           boolean active) {
    }

    /**
     * The wards as one GeoJSON FeatureCollection, simplified with a 5 m tolerance in UTM zone 43N (EPSG:32643, metres)
     * and written with 6 decimals; properties {@code wardNumber}, {@code wardName}.
     */
    private static final String WARDS_GEOJSON = """
            SELECT json_build_object(
                     'type', 'FeatureCollection',
                     'features', coalesce(json_agg(json_build_object(
                         'type', 'Feature',
                         'geometry', ST_AsGeoJSON(ST_Transform(ST_SimplifyPreserveTopology(ST_Transform(w.geometry, 32643), 5), 4326), 6)::json,
                         'properties', json_build_object('wardNumber', w.ward_number, 'wardName', w.ward_name))
                       ORDER BY w.ward_number), '[]'::json))::text
              FROM wards w""";

    private final JdbcClient jdbc;

    public ReferenceRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    public List<Category> activeCategories() {
        return jdbc.sql("""
                SELECT category_id, category_name, work_type_code, citizen_selectable, needs_depth_answer, is_active
                  FROM complaint_categories WHERE is_active
                 ORDER BY display_order NULLS LAST, category_id""")
                .query(ReferenceRepository::category).list();
    }

    public Optional<Category> category(long id) {
        return jdbc.sql("""
                SELECT category_id, category_name, work_type_code, citizen_selectable, needs_depth_answer, is_active
                  FROM complaint_categories WHERE category_id = :id""")
                .param("id", id).query(ReferenceRepository::category).optional();
    }

    public String wardsGeoJson() {
        return jdbc.sql(WARDS_GEOJSON).query(String.class).single();
    }

    private static Category category(java.sql.ResultSet rs, int row) throws java.sql.SQLException {
        return new Category(rs.getLong("category_id"), rs.getString("category_name"), rs.getString("work_type_code"),
                rs.getBoolean("citizen_selectable"), rs.getBoolean("needs_depth_answer"), rs.getBoolean("is_active"));
    }
}
