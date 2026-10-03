package com.civicbrain.auth.api;

import java.time.Duration;
import java.util.HashSet;
import java.util.Set;

import org.springframework.http.ResponseCookie;
import org.springframework.stereotype.Component;

import com.civicbrain.common.ApiException;
import com.civicbrain.common.ErrorCode;
import com.civicbrain.config.AppProperties;

import jakarta.servlet.http.HttpServletRequest;

/**
 * The refresh cookie {@code __Host-cb_rt} (Secure, HttpOnly, SameSite=Strict, Path=/, no Domain) and the CSRF check
 * of the two cookie endpoints (docs/07_SECURITY.md §1): POST only, header {@code X-CB-CSRF: 1} and an {@code Origin}
 * equal to APP_BASE_URL or one of APP_EXTRA_ORIGINS; otherwise 403 CSRF_CHECK_FAILED.
 */
@Component
public class RefreshCookie {

    public static final String NAME = "__Host-cb_rt";
    public static final String CSRF_HEADER = "X-CB-CSRF";

    private final Set<String> allowedOrigins = new HashSet<>();

    public RefreshCookie(AppProperties app) {
        allowedOrigins.add(trim(app.baseUrl()));
        app.extraOrigins().forEach(o -> allowedOrigins.add(trim(o)));
    }

    public ResponseCookie issue(String value, Duration maxAge) {
        return base(value).maxAge(maxAge).build();
    }

    public ResponseCookie clear() {
        return base("").maxAge(Duration.ZERO).build();
    }

    public void checkCsrf(HttpServletRequest request) {
        String origin = request.getHeader("Origin");
        if (!"1".equals(request.getHeader(CSRF_HEADER)) || origin == null || !allowedOrigins.contains(trim(origin))) {
            throw new ApiException(ErrorCode.CSRF_CHECK_FAILED, "The request could not be confirmed. Please log in again.");
        }
    }

    private static ResponseCookie.ResponseCookieBuilder base(String value) {
        return ResponseCookie.from(NAME, value).httpOnly(true).secure(true).sameSite("Strict").path("/");
    }

    private static String trim(String origin) {
        String o = origin.strip();
        return o.endsWith("/") ? o.substring(0, o.length() - 1) : o;
    }
}
