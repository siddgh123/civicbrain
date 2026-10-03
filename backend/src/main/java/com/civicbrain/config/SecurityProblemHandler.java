package com.civicbrain.config;

import java.io.IOException;

import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.web.AuthenticationEntryPoint;
import org.springframework.security.web.access.AccessDeniedHandler;
import org.springframework.stereotype.Component;

import com.civicbrain.common.ErrorCode;
import com.civicbrain.common.ProblemWriter;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

/** Security-filter errors as the same RFC 9457 body as the error advice: 401 UNAUTHENTICATED, 403 FORBIDDEN. */
@Component
public class SecurityProblemHandler implements AuthenticationEntryPoint, AccessDeniedHandler {

    private final ProblemWriter problems;

    public SecurityProblemHandler(ProblemWriter problems) {
        this.problems = problems;
    }

    @Override
    public void commence(HttpServletRequest request, HttpServletResponse response, AuthenticationException e) throws IOException {
        response.setHeader("WWW-Authenticate", "Bearer");
        problems.write(request, response, ErrorCode.UNAUTHENTICATED, "Please log in.");
    }

    @Override
    public void handle(HttpServletRequest request, HttpServletResponse response, AccessDeniedException e) throws IOException {
        problems.write(request, response, ErrorCode.FORBIDDEN, "You are not allowed to do this.");
    }
}
