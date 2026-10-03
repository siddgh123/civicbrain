package com.civicbrain.common;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneId;

/** API timestamps are ISO-8601 with the Asia/Kolkata offset (docs/04_API_CONTRACT.md conventions); UTC inside. */
public final class Times {

    public static final ZoneId KOLKATA = ZoneId.of("Asia/Kolkata");

    private Times() {
    }

    public static OffsetDateTime api(Instant instant) {
        return instant == null ? null : instant.atZone(KOLKATA).toOffsetDateTime();
    }
}
