package com.civicbrain.common;

import java.util.Map;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

import tools.jackson.databind.json.JsonMapper;

/**
 * Append-only {@code audit_logs} rows for state changes (docs/04_API_CONTRACT.md conventions, 07 §6): actor, entity,
 * old/new JSON. Callers pass only non-secret fields (never passwords, tokens, codes or full phone numbers).
 */
@Component
public class AuditLog {

    private final JdbcClient jdbc;
    private final JsonMapper json;

    public AuditLog(JdbcClient jdbc, JsonMapper json) {
        this.jdbc = jdbc;
        this.json = json;
    }

    public void userAction(long userId, String entityType, long entityId, String action, Map<String, ?> oldValue,
                           Map<String, ?> newValue, String ip, String requestId) {
        jdbc.sql("""
                INSERT INTO audit_logs (user_id, entity_type, entity_id, action, old_value, new_value, actor_type,
                                        ip_address, request_id)
                VALUES (:userId, :entityType, :entityId, :action, CAST(:oldValue AS jsonb), CAST(:newValue AS jsonb), 'USER',
                        CAST(:ip AS inet), :requestId)""")
                .param("userId", userId).param("entityType", entityType).param("entityId", entityId)
                .param("action", action)
                .param("oldValue", oldValue == null ? null : json.writeValueAsString(oldValue))
                .param("newValue", newValue == null ? null : json.writeValueAsString(newValue))
                .param("ip", Db.inet(ip)).param("requestId", Masking.logSafe(requestId, 64))
                .update();
    }

    /** The same for an entity keyed by a code or UUID ({@code audit_logs.entity_key}, V5) instead of a number. */
    public void userActionByKey(long userId, String entityType, String entityKey, String action, Map<String, ?> newValue,
                                String ip, String requestId) {
        jdbc.sql("""
                INSERT INTO audit_logs (user_id, entity_type, entity_key, action, new_value, actor_type, ip_address, request_id)
                VALUES (:userId, :entityType, :entityKey, :action, CAST(:newValue AS jsonb), 'USER', CAST(:ip AS inet), :requestId)""")
                .param("userId", userId).param("entityType", entityType).param("entityKey", entityKey).param("action", action)
                .param("newValue", newValue == null ? null : json.writeValueAsString(newValue))
                .param("ip", Db.inet(ip)).param("requestId", Masking.logSafe(requestId, 64))
                .update();
    }
}
