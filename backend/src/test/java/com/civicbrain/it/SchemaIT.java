package com.civicbrain.it;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.transaction.support.TransactionTemplate;

import com.civicbrain.it.support.IntegrationTest;

/**
 * Flyway builds the schema from the kit's migrations (docs/03_DATABASE.md §1, 09_BUILD_PLAN_7DAY §4
 * "context + Flyway V1-V5 (74 tables, fn_locate_point ward 1)").
 */
@IntegrationTest
class SchemaIT {

    /** The reference schema the kit tested (74 application tables, PostGIS's spatial_ref_sys not included). */
    private static final Path SCHEMA_REFERENCE = Path.of("..", "db", "SCHEMA_REFERENCE_after_V5.sql");

    @Autowired
    JdbcClient jdbc;

    @Autowired
    TransactionTemplate tx;

    @Test
    void flywayAppliedV1ToV5AndTheGrantsMigration() {
        List<String> applied = jdbc.sql("""
                SELECT coalesce(version, 'R') || ':' || script
                  FROM flyway_schema_history WHERE success ORDER BY installed_rank""")
                .query(String.class).list();
        assertThat(applied).containsExactly(
                "1:V1__baseline.sql",
                "2:V2__civicbrain_app_layer.sql",
                "3:V3__wards_topology_clean.sql",
                "4:V4__security_privacy_jobs.sql",
                "5:V5__capture_answers_plan_release.sql",
                "R:R__civicbrain_grants.sql");
        assertThat(jdbc.sql("SELECT count(*) FROM flyway_schema_history WHERE NOT success").query(Long.class).single())
                .isZero();
    }

    @Test
    void theApplicationTablesOfTheSchemaReferenceExist() throws IOException {
        Set<String> expected = tablesOfSchemaReference();
        assertThat(expected).hasSize(74);

        Set<String> actual = new TreeSet<>(jdbc.sql("""
                SELECT table_name FROM information_schema.tables
                 WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                   AND table_name NOT IN ('spatial_ref_sys', 'flyway_schema_history')""")
                .query(String.class).list());
        assertThat(actual).isEqualTo(expected);
    }

    @Test
    void twentyThreeWardsNumberedOneToTwentyThree() {
        assertThat(jdbc.sql("SELECT count(*) FROM wards").query(Long.class).single()).isEqualTo(23L);
        assertThat(jdbc.sql("SELECT ward_number FROM wards ORDER BY ward_number").query(Integer.class).list())
                .containsExactlyElementsOf(java.util.stream.IntStream.rangeClosed(1, 23).boxed().toList());
    }

    @Test
    void locatePointFindsWardOneInsideTheBoundary() {
        var located = jdbc.sql("""
                SELECT f.inside_boundary, w.ward_number, f.ward_id
                  FROM fn_locate_point(18.7440, 73.6760) f JOIN wards w ON w.ward_id = f.ward_id""")
                .query((rs, n) -> new Object[] {rs.getBoolean(1), rs.getInt(2), rs.getLong(3)})
                .single();
        assertThat(located[0]).isEqualTo(true);
        assertThat(located[1]).isEqualTo(1);
        assertThat(located[2]).isEqualTo(21L);
    }

    @Test
    void insertingAComplaintEnqueuesExactlyOneAnalysisJob() {
        tx.executeWithoutResult(status -> {
            long userId = jdbc.sql("""
                    INSERT INTO users (full_name, email, password_hash, role)
                    VALUES ('Schema IT', 'schema-it@it.local', '$argon2id$dummy', 'CITIZEN') RETURNING user_id""")
                    .query(Long.class).single();
            long complaintId = jdbc.sql("""
                    INSERT INTO complaints (user_id, category_id, title, description, location)
                    VALUES (:user, 1, 'Schema IT pothole', 'test', ST_SetSRID(ST_MakePoint(73.676, 18.744), 4326))
                    RETURNING complaint_id""")
                    .param("user", userId).query(Long.class).single();

            List<String> jobs = jdbc.sql("SELECT job_type || ':' || status FROM jobs WHERE ref_id = :id")
                    .param("id", complaintId).query(String.class).list();
            assertThat(jobs).containsExactly("ANALYZE_COMPLAINT:QUEUED");
            assertThat(jdbc.sql("SELECT public_ref FROM complaints WHERE complaint_id = :id")
                    .param("id", complaintId).query(String.class).single())
                    .isEqualTo("CB-%06d".formatted(complaintId));
            status.setRollbackOnly();   // the test leaves no rows behind
        });
    }

    private static Set<String> tablesOfSchemaReference() throws IOException {
        Matcher m = Pattern.compile("(?m)^CREATE TABLE public\\.([a-z0-9_]+) \\(").matcher(Files.readString(SCHEMA_REFERENCE));
        Set<String> tables = new TreeSet<>();
        while (m.find()) {
            tables.add(m.group(1));
        }
        return tables;
    }
}
