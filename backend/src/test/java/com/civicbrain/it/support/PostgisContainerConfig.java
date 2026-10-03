package com.civicbrain.it.support;

import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.context.annotation.Bean;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.DockerImageName;

/**
 * One PostGIS container for every integration test (the Spring test context, and with it the container, is cached
 * and shared by all classes annotated with {@link IntegrationTest}). Flyway applies V1-V5 + R__ to it on start-up;
 * the login roles do not exist there, so R__civicbrain_grants.sql only logs a NOTICE (docs/03_DATABASE.md §1).
 */
@TestConfiguration(proxyBeanMethods = false)
public class PostgisContainerConfig {

    public static final DockerImageName POSTGIS = DockerImageName.parse("postgis/postgis:18-3.6")
            .asCompatibleSubstituteFor("postgres");

    @Bean
    @ServiceConnection
    PostgreSQLContainer postgis() {
        return new PostgreSQLContainer(POSTGIS);
    }
}
