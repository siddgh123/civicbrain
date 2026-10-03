package com.civicbrain.common;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * The one typed exception of the API (rule 10): an {@link ErrorCode}, the HTTP status (normally the code's own),
 * a safe {@code detail} for the client, optional field errors and optional RFC 9457 extension members. The error
 * advice turns it into RFC 9457.
 */
public class ApiException extends RuntimeException {

    private final ErrorCode code;
    private final int status;
    private final String detail;
    private final List<FieldErrorItem> fieldErrors;
    private final Map<String, Object> extensions;

    public ApiException(ErrorCode code, String detail) {
        this(code, code.status(), detail, List.of());
    }

    public ApiException(ErrorCode code, int status, String detail) {
        this(code, status, detail, List.of());
    }

    public ApiException(ErrorCode code, String detail, List<FieldErrorItem> fieldErrors) {
        this(code, code.status(), detail, fieldErrors);
    }

    public ApiException(ErrorCode code, int status, String detail, List<FieldErrorItem> fieldErrors) {
        this(code, status, detail, fieldErrors, Map.of());
    }

    private ApiException(ErrorCode code, int status, String detail, List<FieldErrorItem> fieldErrors, Map<String, Object> extensions) {
        super(code.name() + ": " + detail);
        this.code = code;
        this.status = status;
        this.detail = detail;
        this.fieldErrors = List.copyOf(fieldErrors);
        this.extensions = Map.copyOf(extensions);
    }

    public static ApiException validation(String field, String fieldCode, String message) {
        return new ApiException(ErrorCode.VALIDATION_FAILED, "Please check the highlighted fields.",
                List.of(new FieldErrorItem(field, fieldCode, message)));
    }

    /** A copy with one more top-level member in the problem body (never secrets or other users' data). */
    public ApiException with(String member, Object value) {
        Map<String, Object> more = new LinkedHashMap<>(extensions);
        more.put(member, value);
        return new ApiException(code, status, detail, fieldErrors, more);
    }

    public ErrorCode code() {
        return code;
    }

    public int status() {
        return status;
    }

    public String detail() {
        return detail;
    }

    public List<FieldErrorItem> fieldErrors() {
        return fieldErrors;
    }

    public Map<String, Object> extensions() {
        return extensions;
    }
}
