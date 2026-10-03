package com.civicbrain.common;

import java.io.IOException;
import java.util.List;

import org.springframework.stereotype.Component;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import tools.jackson.databind.json.JsonMapper;

/** Writes an {@link ApiProblem} straight to the servlet response, for errors raised in filters (security). */
@Component
public class ProblemWriter {

    private final JsonMapper json;

    public ProblemWriter(JsonMapper json) {
        this.json = json;
    }

    public void write(HttpServletRequest request, HttpServletResponse response, ErrorCode code, String detail) throws IOException {
        ApiProblem body = ApiProblem.of(code, code.status(), detail, RequestIdFilter.currentId(request), List.of());
        response.setStatus(code.status());
        response.setContentType(ApiProblem.MEDIA_TYPE);   // JSON is UTF-8 by definition (RFC 8259): no charset parameter
        response.getOutputStream().write(json.writeValueAsBytes(body));
    }
}
