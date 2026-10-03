package com.civicbrain;

import java.time.ZoneOffset;
import java.util.TimeZone;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;
import org.springframework.context.ConfigurableApplicationContext;

@SpringBootApplication
@ConfigurationPropertiesScan
public class CivicbrainApplication {

    /** Non-web profiles whose runner does one job (AdminBootstrapRunner, E2eSeedRunner); the JVM exits after it. */
    static final String ONE_SHOT_PROFILES = "e2e-seed | bootstrap-admin";

    public static void main(String[] args) {
        // Everything inside the app is UTC (rule 10; Asia/Kolkata only when formatting for people). It also stops the
        // JDBC driver from sending Windows' legacy zone name "Asia/Calcutta", which PostgreSQL builds may reject.
        TimeZone.setDefault(TimeZone.getTimeZone(ZoneOffset.UTC));
        ConfigurableApplicationContext context = SpringApplication.run(CivicbrainApplication.class, args);
        // a failing runner already ended run() with an exception (exit code 1); success closes the context, exit 0
        if (context.getEnvironment().matchesProfiles(ONE_SHOT_PROFILES)) {
            System.exit(SpringApplication.exit(context));
        }
    }
}
