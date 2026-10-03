package com.civicbrain.common;

/**
 * Every API error code with its HTTP status - exactly the table of docs/12_ERROR_HANDLING.md §2 (ErrorCodeTest
 * compares them). The UI shows its own message per code (i18n key {@code errors.<code>}); {@link #title()} is the
 * short RFC 9457 title.
 */
public enum ErrorCode {
    VALIDATION_FAILED(400, "Validation failed"),
    MALFORMED_REQUEST(400, "Malformed request"),
    UNAUTHENTICATED(401, "Authentication required"),
    INVALID_CREDENTIALS(401, "Invalid credentials"),
    SESSION_REVOKED(401, "Session revoked"),
    FORBIDDEN(403, "Forbidden"),
    ROLE_NOT_ALLOWED(403, "Role not allowed for this step"),
    EMAIL_NOT_VERIFIED(403, "E-mail not verified"),
    MFA_REQUIRED(403, "Two-factor authentication required"),
    CSRF_CHECK_FAILED(403, "CSRF check failed"),
    NOT_FOUND(404, "Not found"),
    INVALID_TRANSITION(409, "Invalid status transition"),
    STALE_VERSION(409, "Changed by someone else"),
    ALREADY_EXISTS(409, "Already exists"),
    COMPLAINT_NOT_PLANNABLE(409, "Complaint cannot be planned"),
    PLAN_STATE_CONFLICT(409, "Plan state conflict"),
    BLUR_NOT_READY(409, "Blurred copy not ready"),
    CAPTURE_SESSION_EXPIRED(410, "Capture session expired"),
    FILE_TOO_LARGE(413, "File too large"),
    FILE_TYPE_NOT_ALLOWED(415, "File type not allowed"),
    CAPTURE_SESSION_INVALID(422, "Capture session invalid"),
    GPS_ACCURACY_TOO_LOW(422, "Location is not accurate enough"),
    LOCATION_STALE(422, "Location is too old"),
    OUTSIDE_BOUNDARY(422, "Outside the municipal boundary"),
    IMAGE_TOO_SMALL(422, "Image too small"),
    IMAGE_TOO_LARGE_PIXELS(422, "Image has too many pixels"),
    OTP_INVALID(422, "Code is incorrect"),
    OTP_EXPIRED(422, "Code expired"),
    OTP_ATTEMPTS_EXCEEDED(422, "Too many attempts for this code"),
    TOTP_INVALID(422, "Authenticator code is incorrect"),
    PASSWORD_POLICY(422, "Password does not meet the policy"),
    CONTRACTOR_NOT_ELIGIBLE(422, "Contractor not eligible"),
    FEEDBACK_NOT_ALLOWED(422, "Feedback not allowed"),
    CONSENT_MISSING(422, "Consent missing"),
    ACCOUNT_LOCKED(423, "Account locked"),
    RATE_LIMITED(429, "Too many requests"),
    INTERNAL_ERROR(500, "Internal error"),
    DEPENDENCY_UNAVAILABLE(503, "Service temporarily unavailable");

    private static final String TYPE_PREFIX = "https://civicbrain.app/errors/";

    private final int status;
    private final String title;

    ErrorCode(int status, String title) {
        this.status = status;
        this.title = title;
    }

    public int status() {
        return status;
    }

    public String title() {
        return title;
    }

    /** RFC 9457 {@code type} URI. */
    public String type() {
        return TYPE_PREFIX + name();
    }
}
