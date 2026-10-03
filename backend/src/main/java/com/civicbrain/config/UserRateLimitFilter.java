package com.civicbrain.config;

import java.io.IOException;

import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.web.filter.OncePerRequestFilter;

import com.civicbrain.common.ProblemWriter;
import com.civicbrain.common.RateLimitedException;
import com.civicbrain.common.RateLimiter;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

/** "Everything else authenticated: 300 / min per user" (docs/04_API_CONTRACT.md §11) → 429 RATE_LIMITED + Retry-After. */
class UserRateLimitFilter extends OncePerRequestFilter {

    private final RateLimiter limits;
    private final ProblemWriter problems;

    UserRateLimitFilter(RateLimiter limits, ProblemWriter problems) {
        this.limits = limits;
        this.problems = problems;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        if (SecurityContextHolder.getContext().getAuthentication() instanceof JwtAuthenticationToken token) {
            try {
                limits.consume(RateLimiter.Kind.AUTHENTICATED_USER, token.getToken().getSubject());
            } catch (RateLimitedException e) {
                problems.write(request, response, e);
                return;
            }
        }
        chain.doFilter(request, response);
    }
}
