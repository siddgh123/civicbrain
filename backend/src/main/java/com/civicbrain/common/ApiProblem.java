package com.civicbrain.common;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonInclude;

/**
 * RFC 9457 Problem Details body of every API error (docs/12_ERROR_HANDLING.md §1). {@code detail} never holds
 * stack traces, SQL, file paths, other users' data or secrets; empty {@code detail}/{@code fieldErrors} are left out.
 */
@JsonInclude(JsonInclude.Include.NON_EMPTY)
public record ApiProblem(String type, String title, int status, String code, String detail, String requestId,
                         List<FieldErrorItem> fieldErrors) {

    public static final String MEDIA_TYPE = "application/problem+json";

    public static ApiProblem of(ErrorCode code, int status, String detail, String requestId, List<FieldErrorItem> fieldErrors) {
        return new ApiProblem(code.type(), code.title(), status, code.name(), detail, requestId, List.copyOf(fieldErrors));
    }

    public static ApiProblem of(ApiException e, String requestId) {
        return of(e.code(), e.status(), e.detail(), requestId, e.fieldErrors());
    }
}
