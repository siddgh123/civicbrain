package com.civicbrain.auth.service;

import java.util.Map;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

import com.civicbrain.common.Db;
import com.civicbrain.common.Masking;

import tools.jackson.databind.json.JsonMapper;

/**
 * Append-only {@code auth_events} rows for every auth event (docs/07_SECURITY.md §1, §6; V5 type list). The
 * identifier is the e-mail or the masked phone; details never hold passwords, codes or tokens.
 */
@Component
public class AuthEvents {

    /** {@code auth_events.event_type} (CHECK list incl. V5). */
    public enum Type {
        LOGIN_SUCCESS, LOGIN_FAILED, ACCOUNT_LOCKED, LOGOUT, OTP_SENT, OTP_VERIFIED, OTP_FAILED, PASSWORD_RESET,
        PASSWORD_CHANGED, REFRESH_REUSE_DETECTED, ROLE_CHANGED, ACCOUNT_CREATED, TOTP_ENABLED, TOTP_VERIFIED,
        TOTP_FAILED, TOTP_RESET, LOGOUT_ALL
    }

    /** Who and from where (IP, user agent) - built by the controller from the request. */
    public record Client(String ip, String userAgent) {
        public static final Client SYSTEM = new Client(null, null);
    }

    private static final int MAX_USER_AGENT = 300;

    private final JdbcClient jdbc;
    private final JsonMapper json;

    public AuthEvents(JdbcClient jdbc, JsonMapper json) {
        this.jdbc = jdbc;
        this.json = json;
    }

    public void record(Type type, Long userId, String identifier, Client client, Map<String, ?> details) {
        jdbc.sql("""
                INSERT INTO auth_events (user_id, identifier, event_type, ip_address, user_agent, details)
                VALUES (:userId, :identifier, :type, CAST(:ip AS inet), :userAgent, CAST(:details AS jsonb))""")
                .param("userId", userId)
                .param("identifier", identifier == null ? null : Masking.identifier(identifier))
                .param("type", type.name())
                .param("ip", Db.inet(client.ip()))
                .param("userAgent", Masking.logSafe(client.userAgent(), MAX_USER_AGENT))
                .param("details", json.writeValueAsString(details == null ? Map.of() : details))
                .update();
    }

    public void record(Type type, Long userId, String identifier, Client client) {
        record(type, userId, identifier, client, Map.of());
    }
}
