package com.civicbrain.auth.api;

import org.springframework.security.core.Authentication;
import org.springframework.security.oauth2.jwt.Jwt;

import com.civicbrain.auth.service.AuthEvents;
import com.civicbrain.common.ApiException;
import com.civicbrain.common.ErrorCode;

import jakarta.servlet.http.HttpServletRequest;

/** The signed-in user (JWT {@code sub}) and the client of a request (IP, user agent) for audit rows. */
public final class CurrentUser {

    private CurrentUser() {
    }

    public static long id(Authentication authentication) {
        if (authentication != null && authentication.getPrincipal() instanceof Jwt jwt) {
            try {
                return Long.parseLong(jwt.getSubject());
            } catch (NumberFormatException e) {
                // fall through
            }
        }
        throw new ApiException(ErrorCode.UNAUTHENTICATED, "Please log in.");
    }

    public static AuthEvents.Client client(HttpServletRequest request) {
        return new AuthEvents.Client(request.getRemoteAddr(), request.getHeader("User-Agent"));
    }
}
