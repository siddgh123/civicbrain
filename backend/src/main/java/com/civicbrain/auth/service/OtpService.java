package com.civicbrain.auth.service;

import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.HexFormat;
import java.util.Optional;
import java.util.Set;
import java.util.function.Consumer;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.mail.MailException;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionTemplate;

import com.civicbrain.auth.repo.OtpRepository;
import com.civicbrain.auth.repo.OtpRepository.OtpRow;
import com.civicbrain.auth.repo.OtpRepository.Purpose;
import com.civicbrain.common.ApiException;
import com.civicbrain.common.ErrorCode;
import com.civicbrain.common.RateLimiter;
import com.civicbrain.config.AuthProperties;

/**
 * E-mail OTP of docs/07_SECURITY.md §1: 6 digits from {@link SecureRandom}, 10 minutes, single use, 5 attempts per
 * code, stored as hex {@code HMAC-SHA256(OTP_HMAC_KEY, otpId || code)}, compared in constant time, sent synchronously
 * (SMTP failure → that row is marked used and 503 DEPENDENCY_UNAVAILABLE). Send/resend: 1 / 60 s and 5 / hour per
 * destination (04 §11). The code is never logged or stored in clear.
 */
@Component
public class OtpService {

    public static final Duration TTL = Duration.ofMinutes(10);
    public static final int MAX_ATTEMPTS = 5;

    private static final Logger log = LoggerFactory.getLogger(OtpService.class);
    private static final HexFormat HEX = HexFormat.of();

    public record Issued(long otpId, long expiresInSeconds) {
    }

    public enum Check { VERIFIED, INVALID, EXPIRED, ATTEMPTS_EXCEEDED }

    /** Outcome of a code check; user and destination are null for unknown ids. */
    public record Verification(Check check, Long userId, String destination) {
    }

    /** A code that was really sent (resend). */
    public record Sent(long userId, String destination) {
    }

    private final OtpRepository otps;
    private final AuthMailer mailer;
    private final RateLimiter limits;
    private final TransactionTemplate tx;
    private final Clock clock;
    private final byte[] hmacKey;
    private final SecureRandom random = new SecureRandom();

    public OtpService(OtpRepository otps, AuthMailer mailer, RateLimiter limits, TransactionTemplate tx, Clock clock,
                      AuthProperties auth) {
        this.otps = otps;
        this.mailer = mailer;
        this.limits = limits;
        this.tx = tx;
        this.clock = clock;
        this.hmacKey = auth.otpHmacKey().bytes();
    }

    /** New code for a user, e-mailed now. Counts against the destination limit (429 when exhausted). */
    public Issued issue(long userId, String email, Purpose purpose, String ip) {
        limits.consume(RateLimiter.Kind.OTP_SEND, email);
        return createAndSend(userId, email, purpose, ip);
    }

    /** Like {@link #issue} but returns null instead of 429 when the destination limit is exhausted. */
    public Issued issueIfAllowed(long userId, String email, Purpose purpose, String ip) {
        return limits.tryConsume(RateLimiter.Kind.OTP_SEND, email) ? createAndSend(userId, email, purpose, ip) : null;
    }

    /** A real row with {@code user_id} NULL whose random code is never sent (register with an existing account). */
    public Issued decoy(String destination, Purpose purpose, String ip) {
        Instant now = clock.instant();
        long id = otps.nextId();
        otps.insert(id, null, destination, purpose, hmac(id, newCode()), now, now.plus(TTL), MAX_ATTEMPTS, ip);
        return new Issued(id, TTL.toSeconds());
    }

    /**
     * Checks a code for one of {@code purposes} (a code of another purpose counts as wrong). Wrong codes count
     * (committed even though the caller then answers 422). On success the row is consumed and {@code onVerified} runs
     * in the same transaction (e.g. mark the e-mail verified); if it throws, nothing is consumed.
     */
    public Verification verify(long otpId, String code, Set<Purpose> purposes, Consumer<OtpRow> onVerified) {
        return tx.execute(status -> {
            OtpRow row = otps.findForUpdate(otpId).orElse(null);
            if (row == null || row.consumedAt() != null) {
                return new Verification(Check.INVALID, row == null ? null : row.userId(), row == null ? null : row.destination());
            }
            // 20 / hour per account (04 §11), before anything is written: a 429 rolls back nothing
            limits.consume(RateLimiter.Kind.OTP_VERIFY_ACCOUNT, row.destination());
            if (!row.expiresAt().isAfter(clock.instant())) {
                return new Verification(Check.EXPIRED, row.userId(), row.destination());
            }
            if (row.attemptCount() >= row.maxAttempts()) {
                return new Verification(Check.ATTEMPTS_EXCEEDED, row.userId(), row.destination());
            }
            boolean match = MessageDigest.isEqual(hmac(otpId, code).getBytes(StandardCharsets.US_ASCII),
                    row.codeHmac().strip().getBytes(StandardCharsets.US_ASCII));
            if (!match || row.userId() == null || !purposes.contains(row.purpose())) {
                otps.incrementAttempts(otpId);
                return new Verification(Check.INVALID, row.userId(), row.destination());
            }
            otps.consume(otpId, clock.instant());
            onVerified.accept(row);
            return new Verification(Check.VERIFIED, row.userId(), row.destination());
        });
    }

    /**
     * Resend (04 §1): same otpId, new code and expiry, attempts from 0. Unknown, used or decoy ids are answered the
     * same way (202) without sending anything, so otpIds cannot be probed.
     */
    public Optional<Sent> resend(long otpId, String ip) {
        OtpRow row = tx.execute(status -> otps.findForUpdate(otpId).orElse(null));
        if (row == null || row.consumedAt() != null) {
            return Optional.empty();
        }
        limits.consume(RateLimiter.Kind.OTP_SEND, row.destination());
        if (row.userId() == null) {
            return Optional.empty();
        }
        String code = newCode();
        otps.renew(otpId, hmac(otpId, code), clock.instant().plus(TTL));
        send(otpId, row.destination(), row.purpose(), code);
        return Optional.of(new Sent(row.userId(), row.destination()));
    }

    private Issued createAndSend(long userId, String email, Purpose purpose, String ip) {
        Instant now = clock.instant();
        long id = otps.nextId();
        String code = newCode();
        otps.insert(id, userId, email, purpose, hmac(id, code), now, now.plus(TTL), MAX_ATTEMPTS, ip);
        send(id, email, purpose, code);
        return new Issued(id, TTL.toSeconds());
    }

    private void send(long otpId, String email, Purpose purpose, String code) {
        try {
            if (purpose == Purpose.RESET_PASSWORD) {
                mailer.sendResetCode(email, code);
            } else {
                mailer.sendCode(email, code);
            }
        } catch (MailException e) {
            otps.consume(otpId, clock.instant());
            log.warn("OTP e-mail for otp {} could not be sent: {}", otpId, e.getClass().getSimpleName());
            throw new ApiException(ErrorCode.DEPENDENCY_UNAVAILABLE, "The e-mail could not be sent. Please try again later.");
        }
    }

    private String newCode() {
        return "%06d".formatted(random.nextInt(1_000_000));
    }

    String hmac(long otpId, String code) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(hmacKey, "HmacSHA256"));
            return HEX.formatHex(mac.doFinal((otpId + code).getBytes(StandardCharsets.UTF_8)));
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException("HmacSHA256 unavailable", e);
        }
    }
}
