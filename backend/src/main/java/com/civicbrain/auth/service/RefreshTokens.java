package com.civicbrain.auth.service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.Base64;
import java.util.HexFormat;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionTemplate;

import com.civicbrain.auth.repo.RefreshTokenRepository;
import com.civicbrain.auth.repo.RefreshTokenRepository.RevokeReason;
import com.civicbrain.auth.repo.RefreshTokenRepository.TokenRow;
import com.civicbrain.auth.service.AuthEvents.Client;
import com.civicbrain.common.Masking;
import com.civicbrain.users.model.UserAccount;
import com.civicbrain.users.repo.UserRepository;

/**
 * Refresh tokens of docs/07_SECURITY.md §1: 256-bit random opaque values (cookie {@code __Host-cb_rt}), stored as
 * SHA-256 hex, rotated on every use within a family. Presenting a rotated or revoked token revokes the whole family
 * and writes REFRESH_REUSE_DETECTED. Lifetimes per role (absolute / idle): citizen 30 d / 7 d, officer/admin
 * 24 h / 1 h, contractor 7 d / 3 d.
 */
@Component
public class RefreshTokens {

    public record Issued(String value, Duration maxAge, UUID familyId) {
        @Override
        public String toString() {
            return "Issued[family=" + familyId + "]";
        }
    }

    public enum Outcome { ROTATED, UNKNOWN, EXPIRED, REUSED, USER_INACTIVE }

    /** Result of a refresh: the user and the next token when {@code ROTATED}. */
    public record Rotation(Outcome outcome, UserAccount user, Issued next) {
    }

    private static final int MAX_USER_AGENT = 300;
    private static final HexFormat HEX = HexFormat.of();

    private final RefreshTokenRepository tokens;
    private final UserRepository users;
    private final AuthEvents events;
    private final TransactionTemplate tx;
    private final Clock clock;
    private final SecureRandom random = new SecureRandom();

    public RefreshTokens(RefreshTokenRepository tokens, UserRepository users, AuthEvents events, TransactionTemplate tx,
                         Clock clock) {
        this.tokens = tokens;
        this.users = users;
        this.events = events;
        this.tx = tx;
        this.clock = clock;
    }

    /** A new family at login. */
    public Issued startFamily(UserAccount user, Client client) {
        Instant now = clock.instant();
        Instant familyExpiresAt = now.plus(Duration.ofHours(user.role().refreshAbsoluteHours()));
        return insert(user, UUID.randomUUID(), familyExpiresAt, now, client).issued();
    }

    /** Rotates the presented token (one transaction; revocations are committed whatever the outcome). */
    public Rotation rotate(String raw, Client client) {
        return tx.execute(status -> {
            Instant now = clock.instant();
            TokenRow row = tokens.findByHash(hash(raw), true).orElse(null);
            if (row == null) {
                return new Rotation(Outcome.UNKNOWN, null, null);
            }
            if (row.revokedAt() != null) {
                tokens.revokeFamily(row.familyId(), RevokeReason.REUSE_DETECTED, now);
                events.record(AuthEvents.Type.REFRESH_REUSE_DETECTED, row.userId(), null, client,
                        Map.of("family", row.familyId().toString(), "previousReason", String.valueOf(row.revokeReason())));
                return new Rotation(Outcome.REUSED, null, null);
            }
            if (!row.expiresAt().isAfter(now) || (row.familyExpiresAt() != null && !row.familyExpiresAt().isAfter(now))) {
                tokens.revokeFamily(row.familyId(), RevokeReason.EXPIRED, now);
                return new Rotation(Outcome.EXPIRED, null, null);
            }
            UserAccount user = users.findById(row.userId()).filter(UserAccount::active).orElse(null);
            if (user == null) {
                tokens.revokeFamily(row.familyId(), RevokeReason.ADMIN_REVOKED, now);
                return new Rotation(Outcome.USER_INACTIVE, null, null);
            }
            Instant familyExpiresAt = row.familyExpiresAt() != null ? row.familyExpiresAt()
                    : now.plus(Duration.ofHours(user.role().refreshAbsoluteHours()));
            Inserted next = insert(user, row.familyId(), familyExpiresAt, now, client);
            tokens.markRotated(row.id(), next.id(), now);
            return new Rotation(Outcome.ROTATED, user, next.issued());
        });
    }

    /** The family of a presented token, if it is known and belongs to {@code userId}. */
    public Optional<UUID> familyOf(String raw, long userId) {
        if (raw == null || raw.isBlank()) {
            return Optional.empty();
        }
        return tokens.findByHash(hash(raw), false).filter(t -> t.userId() == userId).map(TokenRow::familyId);
    }

    /** Logout: revokes the family of the presented token; returns its user id when known. */
    public Optional<Long> revokeFamilyOf(String raw) {
        if (raw == null || raw.isBlank()) {
            return Optional.empty();
        }
        return tokens.findByHash(hash(raw), false).map(t -> {
            tokens.revokeFamily(t.familyId(), RevokeReason.LOGOUT, clock.instant());
            return t.userId();
        });
    }

    public void revokeAll(long userId, RevokeReason reason, UUID keepFamily) {
        tokens.revokeAllForUser(userId, reason, keepFamily, clock.instant());
    }

    private record Inserted(long id, Issued issued) {
    }

    private Inserted insert(UserAccount user, UUID familyId, Instant familyExpiresAt, Instant now, Client client) {
        byte[] bytes = new byte[32];
        random.nextBytes(bytes);
        String value = Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
        Instant idle = now.plus(Duration.ofHours(user.role().refreshIdleHours()));
        Instant expiresAt = idle.isBefore(familyExpiresAt) ? idle : familyExpiresAt;
        long id = tokens.insert(user.id(), hash(value), familyId, familyExpiresAt, now, expiresAt,
                Masking.logSafe(client.userAgent(), MAX_USER_AGENT), client.ip());
        return new Inserted(id, new Issued(value, Duration.between(now, expiresAt), familyId));
    }

    static String hash(String raw) {
        try {
            return HEX.formatHex(MessageDigest.getInstance("SHA-256").digest(raw.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 unavailable", e);
        }
    }
}
