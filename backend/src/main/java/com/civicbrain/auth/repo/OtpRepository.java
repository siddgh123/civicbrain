package com.civicbrain.auth.repo;

import java.time.Instant;
import java.util.Optional;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

import com.civicbrain.common.Db;

/** {@code auth_otp_codes}: one row per code (decoy rows have {@code user_id} NULL); the code itself is never stored. */
@Repository
public class OtpRepository {

    /** {@code purpose} CHECK list. */
    public enum Purpose {
        REGISTER, LOGIN, RESET_PASSWORD, VERIFY_EMAIL, VERIFY_PHONE
    }

    public record OtpRow(long id, Long userId, String destination, Purpose purpose, String codeHmac, Instant expiresAt,
                         int attemptCount, int maxAttempts, Instant consumedAt) {
        @Override
        public String toString() {
            return "OtpRow[id=" + id + ", purpose=" + purpose + "]";
        }
    }

    private final JdbcClient jdbc;

    public OtpRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    /** The id is taken first: the HMAC covers {@code otpId || code} (docs/07_SECURITY.md §1). */
    public long nextId() {
        return jdbc.sql("SELECT nextval(pg_get_serial_sequence('auth_otp_codes', 'otp_id'))").query(Long.class).single();
    }

    public void insert(long id, Long userId, String destination, Purpose purpose, String codeHmac, Instant now,
                       Instant expiresAt, int maxAttempts, String ip) {
        jdbc.sql("""
                INSERT INTO auth_otp_codes (otp_id, user_id, destination, channel, purpose, code_hmac, expires_at,
                                            max_attempts, request_ip, created_at)
                VALUES (:id, :userId, :destination, 'EMAIL', :purpose, :hmac, :expiresAt, :maxAttempts, CAST(:ip AS inet), :now)""")
                .param("id", id).param("userId", userId).param("destination", destination)
                .param("purpose", purpose.name()).param("hmac", codeHmac).param("expiresAt", Db.ts(expiresAt))
                .param("maxAttempts", maxAttempts).param("ip", Db.inet(ip)).param("now", Db.ts(now))
                .update();
    }

    public Optional<OtpRow> findForUpdate(long id) {
        return jdbc.sql("""
                SELECT otp_id, user_id, destination, purpose, code_hmac, expires_at, attempt_count, max_attempts, consumed_at
                  FROM auth_otp_codes WHERE otp_id = :id FOR UPDATE""")
                .param("id", id)
                .query((rs, n) -> new OtpRow(rs.getLong("otp_id"), (Long) rs.getObject("user_id", Long.class),
                        rs.getString("destination"), Purpose.valueOf(rs.getString("purpose")), rs.getString("code_hmac"),
                        Db.instant(rs, "expires_at"), rs.getInt("attempt_count"), rs.getInt("max_attempts"),
                        Db.instant(rs, "consumed_at")))
                .optional();
    }

    /** The newest unused, unexpired code of a user for one of {@code purposes} (its code was already sent). */
    public Optional<Long> latestActiveId(long userId, Instant now, Purpose... purposes) {
        return jdbc.sql("""
                SELECT otp_id FROM auth_otp_codes
                 WHERE user_id = :userId AND purpose IN (:purposes) AND consumed_at IS NULL
                   AND expires_at > :now AND attempt_count < max_attempts
                 ORDER BY created_at DESC, otp_id DESC LIMIT 1""")
                .param("userId", userId).param("now", Db.ts(now))
                .param("purposes", java.util.Arrays.stream(purposes).map(Purpose::name).toList())
                .query(Long.class).optional();
    }

    public void incrementAttempts(long id) {
        jdbc.sql("UPDATE auth_otp_codes SET attempt_count = attempt_count + 1 WHERE otp_id = :id").param("id", id).update();
    }

    public void consume(long id, Instant now) {
        jdbc.sql("UPDATE auth_otp_codes SET consumed_at = COALESCE(consumed_at, :now) WHERE otp_id = :id")
                .param("now", Db.ts(now)).param("id", id).update();
    }

    /** Resend: same otpId, new code, new expiry, attempts from 0. */
    public void renew(long id, String codeHmac, Instant expiresAt) {
        jdbc.sql("UPDATE auth_otp_codes SET code_hmac = :hmac, expires_at = :expiresAt, attempt_count = 0 WHERE otp_id = :id")
                .param("hmac", codeHmac).param("expiresAt", Db.ts(expiresAt)).param("id", id).update();
    }
}
