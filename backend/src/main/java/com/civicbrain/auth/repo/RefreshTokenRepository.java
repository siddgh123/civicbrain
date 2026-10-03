package com.civicbrain.auth.repo;

import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

import com.civicbrain.common.Db;

/** {@code auth_refresh_tokens}: SHA-256 hex of each opaque token, grouped in rotation families. */
@Repository
public class RefreshTokenRepository {

    /** {@code revoke_reason} CHECK list. */
    public enum RevokeReason {
        LOGOUT, ROTATED, REUSE_DETECTED, PASSWORD_CHANGED, ADMIN_REVOKED, EXPIRED
    }

    public record TokenRow(long id, long userId, UUID familyId, Instant familyExpiresAt, Instant expiresAt,
                           Instant revokedAt, String revokeReason) {
    }

    private final JdbcClient jdbc;

    public RefreshTokenRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    public long insert(long userId, String tokenHash, UUID familyId, Instant familyExpiresAt, Instant now, Instant expiresAt,
                       String userAgent, String ip) {
        return jdbc.sql("""
                INSERT INTO auth_refresh_tokens (user_id, token_hash, family_id, family_expires_at, issued_at, expires_at,
                                                 user_agent, ip_address)
                VALUES (:userId, :hash, :family, :familyExpiresAt, :now, :expiresAt, :userAgent, CAST(:ip AS inet))
                RETURNING refresh_token_id""")
                .param("userId", userId).param("hash", tokenHash).param("family", familyId)
                .param("familyExpiresAt", Db.ts(familyExpiresAt)).param("now", Db.ts(now))
                .param("expiresAt", Db.ts(expiresAt)).param("userAgent", userAgent).param("ip", Db.inet(ip))
                .query(Long.class).single();
    }

    public Optional<TokenRow> findByHash(String tokenHash, boolean forUpdate) {
        return jdbc.sql("""
                SELECT refresh_token_id, user_id, family_id, family_expires_at, expires_at, revoked_at, revoke_reason
                  FROM auth_refresh_tokens WHERE token_hash = :hash""" + (forUpdate ? " FOR UPDATE" : ""))
                .param("hash", tokenHash)
                .query((rs, n) -> new TokenRow(rs.getLong("refresh_token_id"), rs.getLong("user_id"),
                        rs.getObject("family_id", UUID.class), Db.instant(rs, "family_expires_at"),
                        Db.instant(rs, "expires_at"), Db.instant(rs, "revoked_at"), rs.getString("revoke_reason")))
                .optional();
    }

    public void markRotated(long id, long replacedBy, Instant now) {
        jdbc.sql("""
                UPDATE auth_refresh_tokens SET revoked_at = :now, revoke_reason = 'ROTATED', last_used_at = :now,
                                               replaced_by_token_id = :replacedBy
                 WHERE refresh_token_id = :id""")
                .param("now", Db.ts(now)).param("replacedBy", replacedBy).param("id", id).update();
    }

    /** Revokes every still-valid token of a family. */
    public int revokeFamily(UUID familyId, RevokeReason reason, Instant now) {
        return jdbc.sql("""
                UPDATE auth_refresh_tokens SET revoked_at = :now, revoke_reason = :reason
                 WHERE family_id = :family AND revoked_at IS NULL""")
                .param("now", Db.ts(now)).param("reason", reason.name()).param("family", familyId).update();
    }

    /** Revokes every still-valid token of a user, except one family (null = all). */
    public int revokeAllForUser(long userId, RevokeReason reason, UUID keepFamily, Instant now) {
        return jdbc.sql("""
                UPDATE auth_refresh_tokens SET revoked_at = :now, revoke_reason = :reason
                 WHERE user_id = :userId AND revoked_at IS NULL
                   AND (CAST(:keep AS uuid) IS NULL OR family_id <> CAST(:keep AS uuid))""")
                .param("now", Db.ts(now)).param("reason", reason.name()).param("userId", userId)
                .param("keep", keepFamily == null ? null : keepFamily.toString())
                .update();
    }
}
