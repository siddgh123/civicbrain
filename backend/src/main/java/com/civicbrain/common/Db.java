package com.civicbrain.common;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.regex.Pattern;

/** Small JDBC helpers: timestamptz as UTC {@link OffsetDateTime} (pgjdbc has no {@code Instant} binding), safe inet text. */
public final class Db {

    private static final Pattern INET = Pattern.compile("[0-9A-Fa-f:.]{2,45}");

    private Db() {
    }

    /** Parameter value for a timestamptz column (null stays null). */
    public static OffsetDateTime ts(Instant instant) {
        return instant == null ? null : instant.atOffset(ZoneOffset.UTC);
    }

    public static Instant instant(ResultSet rs, String column) throws SQLException {
        OffsetDateTime value = rs.getObject(column, OffsetDateTime.class);
        return value == null ? null : value.toInstant();
    }

    /**
     * A remote address that {@code CAST(:ip AS inet)} accepts, or null: IPv4/IPv6 characters only (zone id removed),
     * so a strange value can never break an insert.
     */
    public static String inet(String remoteAddress) {
        if (remoteAddress == null) {
            return null;
        }
        String address = remoteAddress.strip();
        int zone = address.indexOf('%');
        if (zone >= 0) {
            address = address.substring(0, zone);
        }
        return INET.matcher(address).matches() ? address : null;
    }
}
