package com.civicbrain.auth.service;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;

import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwsHeader;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;
import org.springframework.stereotype.Component;

import com.civicbrain.config.AuthProperties;
import com.civicbrain.users.model.UserAccount;

/**
 * Access tokens of docs/07_SECURITY.md §1: JWT HS256, header {@code typ=at+jwt}, claims {@code iss}, {@code aud},
 * {@code sub} (user id), {@code roles}, {@code iat}, {@code exp} (15 min) and {@code mcp=true} while the user must
 * change the password (PASSWORD_CHANGE_REQUIRED). No personal data.
 * <p>{@code iat} is a whole second (JWT NumericDate) and never before {@code users.token_valid_after}, so a token
 * issued right after a revocation is valid and every older one is not ({@link #notBefore}).
 */
@Component
public class AccessTokens {

    public static final String TYPE = "at+jwt";
    public static final String ROLES = "roles";
    public static final String MUST_CHANGE_PASSWORD = "mcp";
    public static final Duration LIFETIME = Duration.ofMinutes(15);

    public record Issued(String value, long expiresInSeconds) {
        @Override
        public String toString() {
            return "Issued[expiresIn=" + expiresInSeconds + "]";
        }
    }

    private final JwtEncoder encoder;
    private final AuthProperties auth;
    private final Clock clock;

    public AccessTokens(JwtEncoder encoder, AuthProperties auth, Clock clock) {
        this.encoder = encoder;
        this.auth = auth;
        this.clock = clock;
    }

    public Issued issue(UserAccount user) {
        Instant now = clock.instant();
        Instant issuedAt = later(now.truncatedTo(ChronoUnit.SECONDS), notBefore(user.tokenValidAfter()));
        Instant expiresAt = issuedAt.plus(LIFETIME);
        JwtClaimsSet.Builder claims = JwtClaimsSet.builder()
                .issuer(auth.jwtIssuer())
                .audience(List.of(auth.jwtAudience()))
                .subject(Long.toString(user.id()))
                .issuedAt(issuedAt)
                .expiresAt(expiresAt)
                .claim(ROLES, List.of(user.role().name()));
        if (user.mustChangePassword()) {
            claims.claim(MUST_CHANGE_PASSWORD, true);
        }
        JwsHeader header = JwsHeader.with(MacAlgorithm.HS256).type(TYPE).build();
        String value = encoder.encode(JwtEncoderParameters.from(header, claims.build())).getTokenValue();
        return new Issued(value, Duration.between(now, expiresAt).toSeconds());
    }

    /** The earliest valid {@code iat} for a user: {@code token_valid_after} rounded up to a whole second. */
    public static Instant notBefore(Instant tokenValidAfter) {
        if (tokenValidAfter == null) {
            return Instant.EPOCH;
        }
        Instant whole = tokenValidAfter.truncatedTo(ChronoUnit.SECONDS);
        return whole.equals(tokenValidAfter) ? whole : whole.plusSeconds(1);
    }

    private static Instant later(Instant a, Instant b) {
        return a.isAfter(b) ? a : b;
    }
}
