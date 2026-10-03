package com.civicbrain.config;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.annotation.Profile;
import org.springframework.context.event.EventListener;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

/**
 * After start-up on a real database, read the wards through the API's own connection (civicbrain_app). Proves that
 * R__civicbrain_grants.sql gave the role its rights (docs/03_DATABASE.md §5); stops the app if it cannot read them.
 */
@Component
@Profile({"dev", "demo", "e2e"})
public class DatabaseStartupCheck {

    private static final Logger log = LoggerFactory.getLogger(DatabaseStartupCheck.class);
    private static final int EXPECTED_WARDS = 23;

    private final JdbcClient jdbc;

    public DatabaseStartupCheck(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @EventListener(ApplicationReadyEvent.class)
    public void checkWardsVisible() {
        record Visible(String role, long wards) {
        }
        Visible visible;
        try {
            visible = jdbc.sql("SELECT current_user AS role_name, (SELECT count(*) FROM wards) AS ward_count")
                    .query((rs, n) -> new Visible(rs.getString("role_name"), rs.getLong("ward_count")))
                    .single();
        } catch (DataAccessException e) {
            throw new IllegalStateException("DB check failed: the API role cannot read table wards - were the grants of "
                    + "R__civicbrain_grants.sql applied after the roles existed? (docs/03_DATABASE.md §5)", e);
        }
        log.info("DB check: {} wards visible to {}", visible.wards(), visible.role());
        if (visible.wards() != EXPECTED_WARDS) {
            log.warn("DB check: expected {} wards, found {} - check the V3 migration", EXPECTED_WARDS, visible.wards());
        }
    }
}
