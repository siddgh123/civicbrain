package com.civicbrain.complaints.service;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;

import com.civicbrain.common.ApiException;
import com.civicbrain.common.AuditLog;
import com.civicbrain.common.ErrorCode;
import com.civicbrain.common.FieldErrorItem;
import com.civicbrain.common.RateLimiter;
import com.civicbrain.complaints.api.ComplaintData;
import com.civicbrain.complaints.repo.CaptureSessionRepository;
import com.civicbrain.complaints.repo.ComplaintRepository;
import com.civicbrain.complaints.repo.ReferenceRepository;
import com.civicbrain.files.service.PhotoProcessor;
import com.civicbrain.files.service.PhotoStorage;
import com.civicbrain.users.model.UserAccount;
import com.civicbrain.users.repo.UserRepository;
import com.civicbrain.workflow.Actor;
import com.civicbrain.workflow.ActorRole;
import com.civicbrain.workflow.WorkflowActor;

import jakarta.validation.ConstraintViolation;
import jakarta.validation.ConstraintViolationException;
import jakarta.validation.Validator;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.DeserializationFeature;
import tools.jackson.databind.exc.MismatchedInputException;
import tools.jackson.databind.exc.UnrecognizedPropertyException;
import tools.jackson.databind.json.JsonMapper;

/**
 * Capture sessions and complaint submission (docs/04 §5, 02 §5 "Submit complaint", FR-10/11/12). The checks run in
 * the order of 04 §5 and the first failure wins: verified citizen → rate limits (20 / h per IP counts every attempt;
 * 5 / 24 h per user counts accepted complaints - the token is given back when a later check rejects the request,
 * FR-11) → {@code data} schema incl. the depth answer rule → capture session (own and unused: 422, expired: 410) →
 * accuracy ≤ 150 m → captured within 10 min of server time → inside TDMC ({@code fn_locate_point}) → photo checks →
 * EXIF facts + re-encode → one transaction: session row lock, file write, complaint (V2/V4 triggers: history,
 * outbox SUBMITTED, ANALYZE_COMPLAINT job), image row, session used, audit row. The file is deleted again if the
 * transaction rolls back (PhotoStorage).
 */
@Service
public class ComplaintIntake {

    public static final Duration CAPTURE_SESSION_TTL = Duration.ofMinutes(10);
    public static final double MAX_ACCURACY_M = 150;
    public static final Duration MAX_LOCATION_AGE = Duration.ofMinutes(10);
    /** The {@code data} part is small JSON (07 §3 limits JSON bodies; this one needs a few hundred bytes). */
    static final int MAX_DATA_BYTES = 64 * 1024;

    private static final Logger log = LoggerFactory.getLogger(ComplaintIntake.class);

    public record Client(String ip, String userAgent, String requestId) {
    }

    public record IssuedSession(UUID id, Instant expiresAt) {
    }

    public record Submitted(long complaintId, String publicRef, String status, Integer wardNumber) {
    }

    private final UserRepository users;
    private final ReferenceRepository reference;
    private final CaptureSessionRepository sessions;
    private final ComplaintRepository complaints;
    private final PhotoProcessor photos;
    private final PhotoStorage storage;
    private final WorkflowActor workflow;
    private final AuditLog audit;
    private final RateLimiter limits;
    private final TransactionTemplate tx;
    private final Validator validator;
    private final JsonMapper json;
    private final Clock clock;

    public ComplaintIntake(UserRepository users, ReferenceRepository reference, CaptureSessionRepository sessions,
                           ComplaintRepository complaints, PhotoProcessor photos, PhotoStorage storage, WorkflowActor workflow,
                           AuditLog audit, RateLimiter limits, TransactionTemplate tx, Validator validator, JsonMapper json,
                           Clock clock) {
        this.users = users;
        this.reference = reference;
        this.sessions = sessions;
        this.complaints = complaints;
        this.photos = photos;
        this.storage = storage;
        this.workflow = workflow;
        this.audit = audit;
        this.limits = limits;
        this.tx = tx;
        this.validator = validator;
        this.json = json;
        this.clock = clock;
    }

    // ------------------------------------------------------------------ capture session

    public IssuedSession issueCaptureSession(long userId, Client client) {
        requireVerified(userId);
        Instant now = clock.instant();
        Instant expires = now.plus(CAPTURE_SESSION_TTL);
        return tx.execute(status -> {
            UUID id = sessions.insert(userId, now, expires, client.ip(), client.userAgent());
            audit.userActionByKey(userId, "capture_session", id.toString(), "CAPTURE_SESSION_ISSUED",
                    Map.of("expiresAt", expires.toString()), client.ip(), client.requestId());
            return new IssuedSession(id, expires);
        });
    }

    // ------------------------------------------------------------------ submit

    public Submitted submit(long userId, byte[] dataPart, byte[] photo, Client client) {
        requireVerified(userId);
        limits.consume(RateLimiter.Kind.COMPLAINT_IP, client.ip());
        String userKey = "user:" + userId;
        limits.consume(RateLimiter.Kind.COMPLAINT_USER, userKey);
        boolean accepted = false;
        try {
            Submitted submitted = validateAndStore(userId, dataPart, photo, client);
            accepted = true;
            return submitted;
        } finally {
            if (!accepted) {
                limits.refund(RateLimiter.Kind.COMPLAINT_USER, userKey);
            }
        }
    }

    private Submitted validateAndStore(long userId, byte[] dataPart, byte[] photo, Client client) {
        // JSON schema (incl. the multipart shape and the depth answer rule)
        ComplaintData data = parse(dataPart);
        ReferenceRepository.Category category = reference.category(data.categoryId())
                .filter(c -> c.active() && c.citizenSelectable())
                .orElseThrow(() -> ApiException.validation("categoryId", "INVALID_VALUE", "is not a category you can choose"));
        if (category.needsDepthAnswer() && data.depthAnswer() == null) {
            throw ApiException.validation("depthAnswer", "REQUIRED", "is required for " + category.name());
        }
        if (!category.needsDepthAnswer() && data.depthAnswer() != null) {
            throw ApiException.validation("depthAnswer", "NOT_ALLOWED", "must be empty for " + category.name());
        }
        if (photo == null) {
            throw ApiException.validation("photo", "REQUIRED", "is required");
        }

        // capture session: own + unused (422), not expired (410)
        Instant now = clock.instant();
        CaptureSessionRepository.Session session = sessions.find(data.captureSessionId(), userId).orElseThrow(ComplaintIntake::invalidSession);
        checkSession(session, now);

        // location
        if (data.locationAccuracyM() > MAX_ACCURACY_M) {
            throw new ApiException(ErrorCode.GPS_ACCURACY_TOO_LOW,
                    "Accuracy was %d m; 150 m or better is needed.".formatted(Math.round(data.locationAccuracyM())),
                    List.of(new FieldErrorItem("locationAccuracyM", "MAX", "must be ≤ 150")));
        }
        Instant capturedAt = data.locationCapturedAt().toInstant();
        if (Duration.between(capturedAt, now).abs().compareTo(MAX_LOCATION_AGE) > 0) {
            throw new ApiException(ErrorCode.LOCATION_STALE, "The location was captured more than 10 minutes ago. Please capture again.",
                    List.of(new FieldErrorItem("locationCapturedAt", "STALE", "must be within 10 minutes of now")));
        }
        ComplaintRepository.Location location = complaints.locate(data.latitude(), data.longitude());
        if (!location.insideBoundary()) {
            throw new ApiException(ErrorCode.OUTSIDE_BOUNDARY, "This location is outside Talegaon Dabhade Municipal Council.");
        }

        // photo: type, size, pixels, then EXIF facts + re-encode
        PhotoProcessor.Processed processed = photos.process(photos.check(photo));
        String exifJson = json.writeValueAsString(processed.exif());

        ComplaintRepository.Created created = tx.execute(status -> {
            Instant txNow = clock.instant();
            checkSession(sessions.lock(data.captureSessionId(), userId).orElseThrow(ComplaintIntake::invalidSession), txNow);
            PhotoStorage.Stored stored = storage.store(processed.jpeg());
            workflow.actAs(Actor.user(userId, ActorRole.CITIZEN), null);
            ComplaintRepository.Created c = complaints.insert(new ComplaintRepository.NewComplaint(userId, category.id(), data.title(),
                    data.description(), data.landmark(), data.latitude(), data.longitude(), location, data.locationAccuracyM(),
                    capturedAt, data.captureSessionId(), data.depthAnswer() == null ? null : data.depthAnswer().name(),
                    data.a4InFrame(), txNow));
            long imageId = complaints.insertImage(new ComplaintRepository.NewImage(c.complaintId(), stored.fileUrl(), stored.storageKey(),
                    stored.fileName(), PhotoProcessor.STORED_MIME, userId, processed.sha256(), processed.width(), processed.height(),
                    processed.jpeg().length, data.captureMethod().name(), capturedAt, data.latitude(), data.longitude(),
                    data.locationAccuracyM(), data.devicePitchDeg(), data.deviceRollDeg(), exifJson, txNow));
            sessions.markUsed(data.captureSessionId(), c.complaintId(), txNow);
            Map<String, Object> newValue = new LinkedHashMap<>();
            newValue.put("publicRef", c.publicRef());
            newValue.put("categoryId", category.id());
            newValue.put("wardNumber", location.wardNumber());
            newValue.put("imageId", imageId);
            newValue.put("captureMethod", data.captureMethod().name());
            audit.userAction(userId, "complaint", c.complaintId(), "COMPLAINT_CREATED", null, newValue, client.ip(), client.requestId());
            return c;
        });
        log.info("complaint {} submitted (ward {}, category {})", created.publicRef(), location.wardNumber(), category.id());
        return new Submitted(created.complaintId(), created.publicRef(), "SUBMITTED", location.wardNumber());
    }

    // ------------------------------------------------------------------ helpers

    /** 403 EMAIL_NOT_VERIFIED for an unverified account (login refuses them too; this is the endpoint's own check). */
    private void requireVerified(long userId) {
        UserAccount user = users.findById(userId).filter(UserAccount::active)
                .orElseThrow(() -> new ApiException(ErrorCode.SESSION_REVOKED, "You were signed out. Please log in again."));
        if (!user.emailVerified()) {
            throw new ApiException(ErrorCode.EMAIL_NOT_VERIFIED, "Please verify your e-mail first.");
        }
    }

    private ComplaintData parse(byte[] dataPart) {
        if (dataPart == null || dataPart.length == 0) {
            throw ApiException.validation("data", "REQUIRED", "is required");
        }
        if (dataPart.length > MAX_DATA_BYTES) {
            throw ApiException.validation("data", "SIZE", "is too large");
        }
        ComplaintData data;
        try {
            data = json.readerFor(ComplaintData.class).with(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES).readValue(dataPart);
        } catch (UnrecognizedPropertyException e) {
            throw ApiException.validation(path(e), "UNKNOWN_FIELD", "is not allowed");
        } catch (MismatchedInputException e) {
            if (e.getPath().isEmpty()) {
                throw new ApiException(ErrorCode.MALFORMED_REQUEST, "The complaint data could not be read.");
            }
            throw ApiException.validation(path(e), "INVALID_VALUE", "has an invalid value");
        } catch (JacksonException e) {
            throw new ApiException(ErrorCode.MALFORMED_REQUEST, "The complaint data could not be read.");
        }
        if (data == null) {
            throw ApiException.validation("data", "REQUIRED", "is required");
        }
        Set<ConstraintViolation<ComplaintData>> violations = validator.validate(data);
        if (!violations.isEmpty()) {
            throw new ConstraintViolationException(violations);
        }
        return data;
    }

    private static void checkSession(CaptureSessionRepository.Session session, Instant now) {
        if (session.used()) {
            throw invalidSession();
        }
        if (session.expiredAt(now)) {
            throw new ApiException(ErrorCode.CAPTURE_SESSION_EXPIRED, "Please take the photo again.");
        }
    }

    private static ApiException invalidSession() {
        return new ApiException(ErrorCode.CAPTURE_SESSION_INVALID, "Please take the photo again.");
    }

    private static String path(JacksonException e) {
        return e.getPath().stream()
                .map(ref -> ref.getPropertyName() != null ? ref.getPropertyName() : "[" + ref.getIndex() + "]")
                .collect(Collectors.joining(".")).replace(".[", "[");
    }
}
