package com.civicbrain.complaints.repo;

import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

import com.civicbrain.common.Db;
import com.civicbrain.common.Masking;

/**
 * {@code capture_sessions}: single-use, 10 minutes (docs/07 §8). Times come from the application clock. Lookups
 * always include the owner, so another user's session id behaves exactly like an unknown one.
 */
@Repository
public class CaptureSessionRepository {

    /** One session of the caller. */
    public record Session(UUID id, Instant expiresAt, Instant usedAt) {
        public boolean used() {
            return usedAt != null;
        }

        public boolean expiredAt(Instant now) {
            return !expiresAt.isAfter(now);
        }
    }

    private final JdbcClient jdbc;

    public CaptureSessionRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    public UUID insert(long userId, Instant issuedAt, Instant expiresAt, String ip, String userAgent) {
        return jdbc.sql("""
                INSERT INTO capture_sessions (user_id, issued_at, expires_at, client_ip, user_agent)
                VALUES (:userId, :issued, :expires, CAST(:ip AS inet), :userAgent)
                RETURNING capture_session_id""")
                .param("userId", userId).param("issued", Db.ts(issuedAt)).param("expires", Db.ts(expiresAt))
                .param("ip", Db.inet(ip)).param("userAgent", Masking.logSafe(userAgent, 500))
                .query(UUID.class).single();
    }

    public Optional<Session> find(UUID id, long userId) {
        return jdbc.sql("SELECT capture_session_id, expires_at, used_at FROM capture_sessions WHERE capture_session_id = :id AND user_id = :u")
                .param("id", id).param("u", userId).query(CaptureSessionRepository::map).optional();
    }

    /** The same lookup with a row lock, inside the submit transaction (a double tap cannot use it twice). */
    public Optional<Session> lock(UUID id, long userId) {
        return jdbc.sql("""
                SELECT capture_session_id, expires_at, used_at FROM capture_sessions
                 WHERE capture_session_id = :id AND user_id = :u FOR UPDATE""")
                .param("id", id).param("u", userId).query(CaptureSessionRepository::map).optional();
    }

    public void markUsed(UUID id, long complaintId, Instant now) {
        jdbc.sql("UPDATE capture_sessions SET used_at = :now, used_by_complaint_id = :c WHERE capture_session_id = :id")
                .param("now", Db.ts(now)).param("c", complaintId).param("id", id).update();
    }

    private static Session map(java.sql.ResultSet rs, int row) throws java.sql.SQLException {
        return new Session(rs.getObject("capture_session_id", UUID.class), Db.instant(rs, "expires_at"), Db.instant(rs, "used_at"));
    }
}
