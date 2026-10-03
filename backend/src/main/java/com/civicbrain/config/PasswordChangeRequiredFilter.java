package com.civicbrain.config;

import java.io.IOException;

import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.web.filter.OncePerRequestFilter;

import com.civicbrain.auth.service.AccessTokens;
import com.civicbrain.common.ErrorCode;
import com.civicbrain.common.ProblemWriter;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

/**
 * A token with {@code mcp=true} (users.must_change_password) may only call {@code GET /me}, the password change and
 * the logout endpoints; everything else → 403 PASSWORD_CHANGE_REQUIRED (docs/12_ERROR_HANDLING.md §2). Created by
 * {@link SecurityConfig} (not a bean, so it runs once, inside the security chain, after the bearer token is read).
 */
class PasswordChangeRequiredFilter extends OncePerRequestFilter {

    private final ProblemWriter problems;

    PasswordChangeRequiredFilter(ProblemWriter problems) {
        this.problems = problems;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        if (SecurityContextHolder.getContext().getAuthentication() instanceof JwtAuthenticationToken token
                && Boolean.TRUE.equals(token.getToken().getClaimAsBoolean(AccessTokens.MUST_CHANGE_PASSWORD))
                && !allowed(request)) {
            problems.write(request, response, ErrorCode.PASSWORD_CHANGE_REQUIRED, "Please set a new password first.");
            return;
        }
        chain.doFilter(request, response);
    }

    private static boolean allowed(HttpServletRequest request) {
        String path = request.getRequestURI().substring(request.getContextPath().length());
        String method = request.getMethod();
        return ("GET".equals(method) && "/api/v1/me".equals(path))
                || ("POST".equals(method) && (path.equals("/api/v1/auth/password/change") || path.equals("/api/v1/auth/logout")
                        || path.equals("/api/v1/auth/logout-all") || path.equals("/api/v1/auth/refresh")));
    }
}
