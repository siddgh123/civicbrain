package com.civicbrain.common;

import java.io.IOException;
import java.util.UUID;
import java.util.regex.Pattern;

import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

/**
 * Every response carries {@code X-Request-Id} (docs/12_ERROR_HANDLING.md §1, 02 §8): a safe incoming id is kept,
 * anything else is replaced by a new UUID (no log injection). The id is in the MDC as {@code requestId} for every
 * log line of the request. Runs before the security filters, so 401/403 responses carry it too.
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class RequestIdFilter extends OncePerRequestFilter {

    public static final String HEADER = "X-Request-Id";
    public static final String MDC_KEY = "requestId";
    private static final String ATTRIBUTE = RequestIdFilter.class.getName() + ".id";
    private static final Pattern SAFE_ID = Pattern.compile("[A-Za-z0-9._-]{8,64}");

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String incoming = request.getHeader(HEADER);
        String id = incoming != null && SAFE_ID.matcher(incoming).matches() ? incoming : UUID.randomUUID().toString();
        request.setAttribute(ATTRIBUTE, id);
        response.setHeader(HEADER, id);
        MDC.put(MDC_KEY, id);
        try {
            chain.doFilter(request, response);
        } finally {
            MDC.remove(MDC_KEY);
        }
    }

    /** The id of this request (set by the filter); a fresh UUID if the filter did not run. */
    public static String currentId(HttpServletRequest request) {
        Object id = request.getAttribute(ATTRIBUTE);
        if (id instanceof String s) {
            return s;
        }
        String mdc = MDC.get(MDC_KEY);
        return mdc != null ? mdc : UUID.randomUUID().toString();
    }
}
