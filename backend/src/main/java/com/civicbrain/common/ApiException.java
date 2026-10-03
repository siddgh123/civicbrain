package com.civicbrain.common;

import java.util.List;

/**
 * The one typed exception of the API (rule 10): an {@link ErrorCode}, the HTTP status (normally the code's own),
 * a safe {@code detail} for the client and optional field errors. The error advice turns it into RFC 9457.
 */
public class ApiException extends RuntimeException {

    private final ErrorCode code;
    private final int status;
    private final String detail;
    private final List<FieldErrorItem> fieldErrors;

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
        super(code.name() + ": " + detail);
        this.code = code;
        this.status = status;
        this.detail = detail;
        this.fieldErrors = List.copyOf(fieldErrors);
    }

    public static ApiException validation(String field, String fieldCode, String message) {
        return new ApiException(ErrorCode.VALIDATION_FAILED, "Please check the highlighted fields.",
                List.of(new FieldErrorItem(field, fieldCode, message)));
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
}
