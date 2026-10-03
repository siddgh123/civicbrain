package com.civicbrain.config;

import java.io.IOException;

import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.oauth2.jwt.JwtValidationException;
import org.springframework.security.web.AuthenticationEntryPoint;
import org.springframework.security.web.access.AccessDeniedHandler;
import org.springframework.stereotype.Component;

import com.civicbrain.auth.service.TokenRevocationValidator;
import com.civicbrain.common.ErrorCode;
import com.civicbrain.common.ProblemWriter;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

/**
 * Security-filter errors as the same RFC 9457 body as the error advice: 401 UNAUTHENTICATED (401 SESSION_REVOKED
 * for a token issued before {@code users.token_valid_after} or of a disabled user), 403 FORBIDDEN.
 */
@Component
public class SecurityProblemHandler implements AuthenticationEntryPoint, AccessDeniedHandler {

    private final ProblemWriter problems;

    public SecurityProblemHandler(ProblemWriter problems) {
        this.problems = problems;
    }

    @Override
    public void commence(HttpServletRequest request, HttpServletResponse response, AuthenticationException e) throws IOException {
        response.setHeader("WWW-Authenticate", "Bearer");
        if (revoked(e)) {
            problems.write(request, response, ErrorCode.SESSION_REVOKED, "You were signed out. Please log in again.");
        } else {
            problems.write(request, response, ErrorCode.UNAUTHENTICATED, "Please log in.");
        }
    }

    @Override
    public void handle(HttpServletRequest request, HttpServletResponse response, AccessDeniedException e) throws IOException {
        problems.write(request, response, ErrorCode.FORBIDDEN, "You are not allowed to do this.");
    }

    private static boolean revoked(Throwable e) {
        for (Throwable t = e; t != null; t = t.getCause()) {
            if (t instanceof JwtValidationException invalid && invalid.getErrors().stream()
                    .anyMatch(err -> TokenRevocationValidator.SESSION_REVOKED.equals(err.getErrorCode()))) {
                return true;
            }
        }
        return false;
    }
}
