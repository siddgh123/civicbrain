package com.civicbrain;

import java.time.ZoneOffset;
import java.util.TimeZone;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

@SpringBootApplication
@ConfigurationPropertiesScan
public class CivicbrainApplication {

    public static void main(String[] args) {
        // Everything inside the app is UTC (rule 10; Asia/Kolkata only when formatting for people). It also stops the
        // JDBC driver from sending Windows' legacy zone name "Asia/Calcutta", which PostgreSQL builds may reject.
        TimeZone.setDefault(TimeZone.getTimeZone(ZoneOffset.UTC));
        SpringApplication.run(CivicbrainApplication.class, args);
    }
}
