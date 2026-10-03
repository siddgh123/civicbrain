package com.civicbrain.auth.service;

import java.security.SecureRandom;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.EnumSet;
import java.util.HexFormat;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.mail.MailException;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;

import com.civicbrain.auth.repo.OtpRepository;
import com.civicbrain.auth.repo.OtpRepository.Purpose;
import com.civicbrain.auth.repo.RefreshTokenRepository.RevokeReason;
import com.civicbrain.auth.service.AuthEvents.Client;
import com.civicbrain.auth.service.AuthEvents.Type;
import com.civicbrain.common.ApiException;
import com.civicbrain.common.ErrorCode;
import com.civicbrain.common.FieldErrorItem;
import com.civicbrain.common.RateLimitedException;
import com.civicbrain.common.RateLimiter;
import com.civicbrain.config.AuthProperties;
import com.civicbrain.privacy.repo.PrivacyRepository;
import com.civicbrain.users.model.Role;
import com.civicbrain.users.model.UserAccount;
import com.civicbrain.users.repo.UserRepository;
import com.civicbrain.users.service.UserAccounts;

/**
 * Register, OTP, login, refresh, logout, password change (docs/04_API_CONTRACT.md §1, docs/07_SECURITY.md §1).
 * Account enumeration is avoided: register always answers 202 (existing e-mail/phone → decoy otpId + owner mail),
 * unknown account and wrong password give the same 401 after the same Argon2 work. Lockout: the 10th failure locks
 * for 15 min; while locked only the correct password answers 423. Every step writes {@code auth_events}.
 */
@Service
public class AuthService {

    public static final int MAX_FAILED_LOGINS = 10;
    public static final Duration LOCK_DURATION = Duration.ofMinutes(15);
    private static final Set<Purpose> EMAIL_PURPOSES = EnumSet.of(Purpose.REGISTER, Purpose.VERIFY_EMAIL);

    private static final Logger log = LoggerFactory.getLogger(AuthService.class);

    public record RegisterCommand(String fullName, String email, String phone, String password,
                                  String privacyNoticeVersion, UserAccounts.Consents consents) {
        @Override
        public String toString() {
            return "RegisterCommand[]";
        }
    }

    public record Registered(long otpId, long expiresInSeconds) {
    }

    public record Session(UserAccount user, AccessTokens.Issued access, RefreshTokens.Issued refresh) {
    }

    private final UserRepository users;
    private final UserAccounts accounts;
    private final PrivacyRepository privacy;
    private final OtpService otps;
    private final OtpRepository otpRows;
    private final AccessTokens accessTokens;
    private final RefreshTokens refreshTokens;
    private final AuthEvents events;
    private final AuthMailer mailer;
    private final PasswordPolicy policy;
    private final PasswordEncoder encoder;
    private final RateLimiter limits;
    private final TransactionTemplate tx;
    private final AuthProperties auth;
    private final Clock clock;
    private final String dummyHash;

    public AuthService(UserRepository users, UserAccounts accounts, PrivacyRepository privacy, OtpService otps,
                       OtpRepository otpRows, AccessTokens accessTokens, RefreshTokens refreshTokens, AuthEvents events,
                       AuthMailer mailer, PasswordPolicy policy, PasswordEncoder encoder, RateLimiter limits,
                       TransactionTemplate tx, AuthProperties auth, Clock clock) {
        this.users = users;
        this.accounts = accounts;
        this.privacy = privacy;
        this.otps = otps;
        this.otpRows = otpRows;
        this.accessTokens = accessTokens;
        this.refreshTokens = refreshTokens;
        this.events = events;
        this.mailer = mailer;
        this.policy = policy;
        this.encoder = encoder;
        this.limits = limits;
        this.tx = tx;
        this.auth = auth;
        this.clock = clock;
        byte[] random = new byte[24];
        new SecureRandom().nextBytes(random);
        this.dummyHash = encoder.encode("timing-only-" + HexFormat.of().formatHex(random));
    }

    // ------------------------------------------------------------------ register / OTP

    public Registered register(RegisterCommand cmd, Client client) {
        limits.consume(RateLimiter.Kind.REGISTER_IP, client.ip());
        String email = normalizeEmail(cmd.email());
        String current = privacy.currentNotice()
                .orElseThrow(() -> new ApiException(ErrorCode.INTERNAL_ERROR, "No current privacy notice."))
                .version();
        if (!current.equals(cmd.privacyNoticeVersion())) {
            throw ApiException.validation("privacyNoticeVersion", "NOT_CURRENT", "is not the current privacy notice");
        }
        policy.check("password", cmd.password(), email, cmd.fullName());

        List<UserAccount> existing = users.findByEmailOrPhone(email, cmd.phone());
        if (!existing.isEmpty()) {
            return decoy(existing, email, cmd.password(), client);
        }
        UserAccount user;
        try {
            user = accounts.create(new UserAccounts.NewAccount(cmd.fullName(), email, cmd.phone(), cmd.password(),
                    Role.CITIZEN, false, false, null, cmd.consents(), client.ip()));
        } catch (DataIntegrityViolationException race) {   // the same e-mail/phone registered a moment ago
            return decoy(users.findByEmailOrPhone(email, cmd.phone()), email, cmd.password(), client);
        }
        events.record(Type.ACCOUNT_CREATED, user.id(), email, client);
        OtpService.Issued otp = otps.issue(user.id(), email, Purpose.REGISTER, client.ip());
        events.record(Type.OTP_SENT, user.id(), email, client, Map.of("purpose", Purpose.REGISTER.name()));
        return new Registered(otp.otpId(), otp.expiresInSeconds());
    }

    /** Existing e-mail or phone: nothing is created; a decoy otpId; the owner is told (silently rate-limited). */
    private Registered decoy(List<UserAccount> owners, String email, String password, Client client) {
        encoder.encode(password);   // same Argon2 work as a real registration
        OtpService.Issued otp = otps.decoy(email, Purpose.REGISTER, client.ip());
        for (UserAccount owner : owners) {
            boolean notified = false;
            // own bucket (same limits as OTP sends): no mail bombing, and not blocked by the owner's own code mails
            if (owner.email() != null && limits.tryConsume(RateLimiter.Kind.OTP_SEND, "registration-attempt:" + owner.email())) {
                try {
                    mailer.sendRegistrationAttempt(owner.email());
                    notified = true;
                } catch (MailException e) {
                    log.warn("registration-attempt e-mail to user {} failed: {}", owner.id(), e.getClass().getSimpleName());
                }
            }
            events.record(Type.OTP_SENT, owner.id(), email, client,
                    Map.of("decoy", true, "reason", "register with an existing e-mail or phone", "ownerNotified", notified));
        }
        return new Registered(otp.otpId(), otp.expiresInSeconds());
    }

    public void verifyOtp(long otpId, String code, Client client) {
        var result = otps.verify(otpId, code, EMAIL_PURPOSES, row -> users.markEmailVerified(row.userId(), clock.instant()));
        throwIfNotVerified(result, client);
    }

    private void throwIfNotVerified(OtpService.Verification result, Client client) {
        switch (result.check()) {
            case VERIFIED -> events.record(Type.OTP_VERIFIED, result.userId(), result.destination(), client);
            case INVALID -> {
                events.record(Type.OTP_FAILED, result.userId(), result.destination(), client, Map.of("reason", "invalid"));
                throw new ApiException(ErrorCode.OTP_INVALID, "The code is incorrect.");
            }
            case EXPIRED -> {
                events.record(Type.OTP_FAILED, result.userId(), result.destination(), client, Map.of("reason", "expired"));
                throw new ApiException(ErrorCode.OTP_EXPIRED, "The code has expired. Request a new one.");
            }
            case ATTEMPTS_EXCEEDED -> {
                events.record(Type.OTP_FAILED, result.userId(), result.destination(), client, Map.of("reason", "attempts"));
                throw new ApiException(ErrorCode.OTP_ATTEMPTS_EXCEEDED, "Too many wrong codes. Request a new one.");
            }
        }
    }

    public void resendOtp(long otpId, Client client) {
        otps.resend(otpId, client.ip()).ifPresent(sent ->
                events.record(Type.OTP_SENT, sent.userId(), sent.destination(), client, Map.of("resend", true)));
    }

    // ------------------------------------------------------------------ login / session

    public Session login(String identifier, String password, Client client) {
        String normalized = normalizeIdentifier(identifier);
        limits.consume(RateLimiter.Kind.LOGIN_IP, client.ip());
        limits.consume(RateLimiter.Kind.LOGIN_IDENTIFIER, normalized);

        Optional<UserAccount> found = normalized.contains("@") ? users.findByEmail(normalized) : users.findByPhone(normalized);
        if (found.isEmpty() || !found.get().active()) {
            encoder.matches(password, dummyHash);   // same work as a real check
            events.record(Type.LOGIN_FAILED, found.map(UserAccount::id).orElse(null), normalized, client,
                    Map.of("reason", found.isEmpty() ? "unknown account" : "inactive account"));
            throw invalidCredentials();
        }
        UserAccount user = found.get();
        Instant now = clock.instant();
        boolean correct = encoder.matches(password, user.passwordHash());
        if (user.lockedAt(now)) {
            events.record(Type.LOGIN_FAILED, user.id(), normalized, client, Map.of("reason", "locked"));
            if (correct) {
                throw new ApiException(ErrorCode.ACCOUNT_LOCKED, "Too many attempts. Try again in 15 minutes.");
            }
            throw invalidCredentials();
        }
        if (!correct) {
            boolean locked = users.recordFailedLogin(user.id(), MAX_FAILED_LOGINS, now.plus(LOCK_DURATION));
            events.record(Type.LOGIN_FAILED, user.id(), normalized, client, Map.of("reason", "wrong password"));
            if (locked) {
                events.record(Type.ACCOUNT_LOCKED, user.id(), normalized, client, Map.of("minutes", LOCK_DURATION.toMinutes()));
            }
            throw invalidCredentials();
        }
        if (!user.emailVerified()) {
            events.record(Type.LOGIN_FAILED, user.id(), normalized, client, Map.of("reason", "e-mail not verified"));
            throw emailNotVerified(user, client);
        }
        if (auth.mfaRequired() && (user.role() == Role.OFFICER || user.role() == Role.ADMIN)) {
            // TOTP sign-in is the optional P25; with the flag on and no TOTP flow yet, fail closed
            throw new ApiException(ErrorCode.MFA_REQUIRED, "Two-factor sign-in is required for this account.");
        }
        users.recordLoginSuccess(user.id(), now);
        events.record(Type.LOGIN_SUCCESS, user.id(), normalized, client);
        return new Session(user, accessTokens.issue(user), refreshTokens.startFamily(user, client));
    }

    /** 403 EMAIL_NOT_VERIFIED with a fresh otpId (or the newest code already sent, inside the 60-s resend limit). */
    private ApiException emailNotVerified(UserAccount user, Client client) {
        ApiException e = new ApiException(ErrorCode.EMAIL_NOT_VERIFIED, "Please verify your e-mail with the code we sent you.");
        if (user.email() == null) {
            return e;
        }
        OtpService.Issued otp = otps.issueIfAllowed(user.id(), user.email(), Purpose.VERIFY_EMAIL, client.ip());
        if (otp != null) {
            events.record(Type.OTP_SENT, user.id(), user.email(), client, Map.of("purpose", Purpose.VERIFY_EMAIL.name()));
            return e.with("otpId", otp.otpId()).with("expiresInSec", otp.expiresInSeconds());
        }
        return otpRows.latestActiveId(user.id(), clock.instant(), Purpose.REGISTER, Purpose.VERIFY_EMAIL).map(id -> e.with("otpId", id))
                .orElseThrow(() -> new RateLimitedException(60));
    }

    public Session refresh(String raw, Client client) {
        if (raw == null || raw.isBlank()) {
            throw new ApiException(ErrorCode.UNAUTHENTICATED, "Please log in again.");
        }
        RefreshTokens.Rotation rotation = refreshTokens.rotate(raw, client);
        return switch (rotation.outcome()) {
            case ROTATED -> new Session(rotation.user(), accessTokens.issue(rotation.user()), rotation.next());
            case REUSED, USER_INACTIVE -> throw new ApiException(ErrorCode.SESSION_REVOKED, "You were signed out. Please log in again.");
            case UNKNOWN, EXPIRED -> throw new ApiException(ErrorCode.UNAUTHENTICATED, "Please log in again.");
        };
    }

    public void logout(String raw, Client client) {
        refreshTokens.revokeFamilyOf(raw).ifPresent(userId -> events.record(Type.LOGOUT, userId, null, client));
    }

    /** Revokes every access token (token_valid_after) and every refresh family of the user. */
    public void logoutAll(long userId, Client client) {
        tx.executeWithoutResult(status -> {
            users.revokeAccessTokens(userId, clock.instant());
            refreshTokens.revokeAll(userId, RevokeReason.LOGOUT, null);
            events.record(Type.LOGOUT_ALL, userId, null, client);
        });
    }

    /**
     * Re-authenticated password change: clears must_change_password, revokes every access token and every other
     * refresh family (the caller's own family, from its cookie, stays usable for the next refresh).
     */
    public void changePassword(long userId, String currentPassword, String newPassword, String refreshCookie, Client client) {
        UserAccount user = users.findById(userId).filter(UserAccount::active)
                .orElseThrow(() -> new ApiException(ErrorCode.SESSION_REVOKED, "You were signed out. Please log in again."));
        Instant now = clock.instant();
        if (user.lockedAt(now)) {
            throw new ApiException(ErrorCode.ACCOUNT_LOCKED, "Too many attempts. Try again in 15 minutes.");
        }
        if (!encoder.matches(currentPassword, user.passwordHash())) {
            boolean locked = users.recordFailedLogin(user.id(), MAX_FAILED_LOGINS, now.plus(LOCK_DURATION));
            events.record(Type.LOGIN_FAILED, user.id(), null, client, Map.of("reason", "wrong current password"));
            if (locked) {
                events.record(Type.ACCOUNT_LOCKED, user.id(), null, client, Map.of("minutes", LOCK_DURATION.toMinutes()));
            }
            throw ApiException.validation("currentPassword", "INCORRECT", "is not correct");
        }
        policy.check("newPassword", newPassword, user.email(), user.fullName());
        if (encoder.matches(newPassword, user.passwordHash())) {
            throw new ApiException(ErrorCode.PASSWORD_POLICY, "Choose a password different from the current one.",
                    List.of(new FieldErrorItem("newPassword", "PASSWORD_POLICY",
                            "Choose a password different from the current one.")));
        }
        String hash = encoder.encode(newPassword);
        UUID keep = refreshTokens.familyOf(refreshCookie, userId).orElse(null);
        tx.executeWithoutResult(status -> {
            users.updatePassword(userId, hash, now);
            users.revokeAccessTokens(userId, now);
            refreshTokens.revokeAll(userId, RevokeReason.PASSWORD_CHANGED, keep);
            events.record(Type.PASSWORD_CHANGED, userId, null, client);
        });
    }

    // ------------------------------------------------------------------ forgot / reset (FR-03)

    /**
     * Always 202 with an otpId (04 §1): a known active e-mail gets a reset code (inside the 60-s resend limit: the
     * newest code already sent), an unknown one a decoy row whose code is never sent.
     */
    public Registered forgotPassword(String email, Client client) {
        limits.consume(RateLimiter.Kind.REGISTER_IP, "forgot:" + client.ip());
        String normalized = normalizeEmail(email);
        Optional<UserAccount> user = users.findByEmail(normalized).filter(UserAccount::active);
        if (user.isPresent()) {
            long userId = user.get().id();
            OtpService.Issued otp = otps.issueIfAllowed(userId, normalized, Purpose.RESET_PASSWORD, client.ip());
            if (otp != null) {
                events.record(Type.OTP_SENT, userId, normalized, client, Map.of("purpose", Purpose.RESET_PASSWORD.name()));
                return new Registered(otp.otpId(), otp.expiresInSeconds());
            }
            Optional<Long> latest = otpRows.latestActiveId(userId, clock.instant(), Purpose.RESET_PASSWORD);
            if (latest.isPresent()) {
                return new Registered(latest.get(), OtpService.TTL.toSeconds());
            }
        }
        OtpService.Issued decoy = otps.decoy(normalized, Purpose.RESET_PASSWORD, client.ip());
        return new Registered(decoy.otpId(), decoy.expiresInSeconds());
    }

    /**
     * Sets a new password with a reset code: policy first (a refused password keeps the code usable), then the
     * password, unlock, e-mail verified, and every access token and refresh family revoked (FR-03).
     */
    public void resetPassword(long otpId, String code, String newPassword, Client client) {
        var result = otps.verify(otpId, code, EnumSet.of(Purpose.RESET_PASSWORD), row -> {
            UserAccount user = users.findById(row.userId()).orElseThrow();
            policy.check("newPassword", newPassword, user.email(), user.fullName());
            Instant now = clock.instant();
            users.updatePassword(user.id(), encoder.encode(newPassword), now);
            users.markEmailVerified(user.id(), now);
            users.revokeAccessTokens(user.id(), now);
            refreshTokens.revokeAll(user.id(), RevokeReason.PASSWORD_CHANGED, null);
            events.record(Type.PASSWORD_RESET, user.id(), user.email(), client);
        });
        throwIfNotVerified(result, client);
    }

    // ------------------------------------------------------------------ helpers

    private static ApiException invalidCredentials() {
        return new ApiException(ErrorCode.INVALID_CREDENTIALS, "E-mail/phone or password is incorrect.");
    }

    public static String normalizeEmail(String email) {
        return email == null ? null : email.strip().toLowerCase(Locale.ROOT);
    }

    /** E-mail (lower case) or an Indian mobile number in +91 form ("98765 43210", "09876543210", "919876543210"). */
    public static String normalizeIdentifier(String identifier) {
        String s = identifier == null ? "" : identifier.strip();
        if (s.contains("@")) {
            return normalizeEmail(s);
        }
        String digits = s.replaceAll("[\\s()-]", "");
        if (digits.matches("[6-9]\\d{9}")) {
            return "+91" + digits;
        }
        if (digits.matches("0[6-9]\\d{9}")) {
            return "+91" + digits.substring(1);
        }
        if (digits.matches("91[6-9]\\d{9}")) {
            return "+" + digits;
        }
        return digits;
    }
}
