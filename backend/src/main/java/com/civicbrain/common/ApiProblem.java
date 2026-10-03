package com.civicbrain.common;

import java.util.List;
import java.util.Map;

import com.fasterxml.jackson.annotation.JsonAnyGetter;
import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.annotation.JsonInclude;

/**
 * RFC 9457 Problem Details body of every API error (docs/12_ERROR_HANDLING.md §1). {@code detail} never holds
 * stack traces, SQL, file paths, other users' data or secrets; empty {@code detail}/{@code fieldErrors} are left out.
 * {@code extensions} are RFC 9457 extension members written at the top level (e.g. {@code otpId} of 403
 * EMAIL_NOT_VERIFIED).
 */
@JsonInclude(JsonInclude.Include.NON_EMPTY)
public record ApiProblem(String type, String title, int status, String code, String detail, String requestId,
                         List<FieldErrorItem> fieldErrors, @JsonIgnore Map<String, Object> extensions) {

    public static final String MEDIA_TYPE = "application/problem+json";

    public static ApiProblem of(ErrorCode code, int status, String detail, String requestId, List<FieldErrorItem> fieldErrors) {
        return new ApiProblem(code.type(), code.title(), status, code.name(), detail, requestId, List.copyOf(fieldErrors), Map.of());
    }

    public static ApiProblem of(ApiException e, String requestId) {
        return new ApiProblem(e.code().type(), e.code().title(), e.status(), e.code().name(), e.detail(), requestId,
                e.fieldErrors(), e.extensions());
    }

    @JsonAnyGetter
    public Map<String, Object> extensionMembers() {
        return extensions;
    }
}
