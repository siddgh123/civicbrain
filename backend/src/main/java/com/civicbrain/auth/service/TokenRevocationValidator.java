package com.civicbrain.auth.service;

import java.time.Instant;

import org.springframework.security.oauth2.core.OAuth2Error;
import org.springframework.security.oauth2.core.OAuth2TokenValidator;
import org.springframework.security.oauth2.core.OAuth2TokenValidatorResult;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.stereotype.Component;

import com.civicbrain.users.repo.UserRepository;

/**
 * {@code iat >= users.token_valid_after} and the user is active (docs/07_SECURITY.md §1: logout-all, password
 * change/reset, role change, disable). A failure carries the error code {@value #SESSION_REVOKED}, which the entry
 * point answers with 401 SESSION_REVOKED.
 */
@Component
public class TokenRevocationValidator implements OAuth2TokenValidator<Jwt> {

    public static final String SESSION_REVOKED = "session_revoked";
    private static final OAuth2Error REVOKED = new OAuth2Error(SESSION_REVOKED, "The session was revoked.", null);

    private final UserRepository users;

    public TokenRevocationValidator(UserRepository users) {
        this.users = users;
    }

    @Override
    public OAuth2TokenValidatorResult validate(Jwt jwt) {
        long userId;
        try {
            userId = Long.parseLong(jwt.getSubject());
        } catch (NumberFormatException | NullPointerException e) {
            return OAuth2TokenValidatorResult.failure(new OAuth2Error("invalid_token", "Bad subject.", null));
        }
        Instant issuedAt = jwt.getIssuedAt();
        var state = users.tokenState(userId);
        if (issuedAt == null || state.isEmpty() || !state.get().active()
                || issuedAt.isBefore(AccessTokens.notBefore(state.get().tokenValidAfter()))) {
            return OAuth2TokenValidatorResult.failure(REVOKED);
        }
        return OAuth2TokenValidatorResult.success();
    }
}
