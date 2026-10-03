package com.civicbrain.unit.auth;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Optional;

import org.junit.jupiter.api.Test;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.BadJwtException;
import org.springframework.security.oauth2.jwt.JwsHeader;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;
import org.springframework.security.oauth2.jwt.JwtValidationException;

import com.civicbrain.auth.service.AccessTokens;
import com.civicbrain.auth.service.TokenRevocationValidator;
import com.civicbrain.config.AuthProperties;
import com.civicbrain.config.JwtConfig;
import com.civicbrain.config.Secret;
import com.civicbrain.users.model.Role;
import com.civicbrain.users.model.UserAccount;
import com.civicbrain.users.repo.UserRepository;
import com.civicbrain.users.repo.UserRepository.TokenState;

/** Access tokens of docs/07_SECURITY.md §1: claims, typ, 15 min, token_valid_after revocation, 60 s skew. */
class AccessTokensTest {

    private static final Instant NOW = Instant.parse("2026-10-03T07:15:30.250Z");
    private static final AuthProperties AUTH = new AuthProperties(
            Secret.of("dGVzdC1vbmx5LWp3dC1zZWNyZXQtMDEyMzQ1Njc4OWFiY2RlZg=="), "civicbrain", "civicbrain-web",
            Secret.of("dGVzdC1vbmx5LW90cC1obWFjLWtleS0wMTIzNDU2Nzg5YWJjZA=="),
            Secret.of("dGVzdC1vbmx5LXRvdHAta2V5LTAxMjM0NTY3ODlhYmM="),
            Secret.of("dGVzdC1vbmx5LWFpLXNlcnZpY2Utand0LTAxMjM0NTY3ODlhYg=="), false);

    private final UserRepository users = mock(UserRepository.class);
    private final JwtConfig config = new JwtConfig();
    private final JwtEncoder encoder = config.jwtEncoder(AUTH);

    private JwtDecoder decoder(Instant at) {
        return config.jwtDecoder(AUTH, Clock.fixed(at, ZoneOffset.UTC), new TokenRevocationValidator(users));
    }

    private static UserAccount user(Instant tokenValidAfter, boolean mustChange) {
        return new UserAccount(7, "Asha", "asha@example.in", "+919876543210", "{argon2}x", Role.OFFICER, true, NOW,
                false, true, "en", 0, null, mustChange, false, tokenValidAfter);
    }

    @Test
    void issuedTokenDecodesWithTheDocumentedClaims() {
        Instant tva = Instant.parse("2026-10-01T00:00:00Z");
        when(users.tokenState(7)).thenReturn(Optional.of(new TokenState(true, tva)));
        AccessTokens.Issued issued = new AccessTokens(encoder, AUTH, Clock.fixed(NOW, ZoneOffset.UTC)).issue(user(tva, false));

        Jwt jwt = decoder(NOW).decode(issued.value());
        assertThat(jwt.getHeaders()).containsEntry("typ", "at+jwt").containsEntry("alg", "HS256");
        assertThat(jwt.getSubject()).isEqualTo("7");
        assertThat(jwt.getClaimAsString("iss")).isEqualTo("civicbrain");
        assertThat(jwt.getAudience()).containsExactly("civicbrain-web");
        assertThat(jwt.getClaimAsStringList("roles")).containsExactly("OFFICER");
        assertThat(jwt.getIssuedAt()).isEqualTo(Instant.parse("2026-10-03T07:15:30Z"));
        assertThat(jwt.getExpiresAt()).isEqualTo(Instant.parse("2026-10-03T07:30:30Z"));
        assertThat(jwt.getClaims()).doesNotContainKey("mcp").doesNotContainKey("email");
        assertThat(issued.expiresInSeconds()).isEqualTo(899);   // 07:15:30.250 → 07:30:30
    }

    @Test
    void mustChangePasswordIsAClaim() {
        when(users.tokenState(7)).thenReturn(Optional.of(new TokenState(true, Instant.EPOCH)));
        String token = new AccessTokens(encoder, AUTH, Clock.fixed(NOW, ZoneOffset.UTC)).issue(user(Instant.EPOCH, true)).value();
        assertThat(decoder(NOW).decode(token).getClaimAsBoolean("mcp")).isTrue();
    }

    @Test
    void aTokenIssuedBeforeTokenValidAfterIsRevoked() {
        when(users.tokenState(7)).thenReturn(Optional.of(new TokenState(true, Instant.EPOCH)));
        String token = new AccessTokens(encoder, AUTH, Clock.fixed(NOW, ZoneOffset.UTC)).issue(user(Instant.EPOCH, false)).value();
        // logout-all in the same second: token_valid_after = next whole second (UserRepository.revokeAccessTokens)
        when(users.tokenState(7)).thenReturn(Optional.of(new TokenState(true, Instant.parse("2026-10-03T07:15:31Z"))));
        assertThatThrownBy(() -> decoder(NOW).decode(token))
                .isInstanceOfSatisfying(JwtValidationException.class, e -> assertThat(e.getErrors())
                        .anyMatch(err -> TokenRevocationValidator.SESSION_REVOKED.equals(err.getErrorCode())));

        // a token issued right after the revocation (same second) gets iat = token_valid_after and is valid
        String fresh = new AccessTokens(encoder, AUTH, Clock.fixed(NOW, ZoneOffset.UTC))
                .issue(user(Instant.parse("2026-10-03T07:15:31Z"), false)).value();
        assertThat(decoder(NOW).decode(fresh).getIssuedAt()).isEqualTo(Instant.parse("2026-10-03T07:15:31Z"));
    }

    @Test
    void inactiveOrUnknownUsersAreRevoked() {
        when(users.tokenState(7)).thenReturn(Optional.of(new TokenState(true, Instant.EPOCH)));
        String token = new AccessTokens(encoder, AUTH, Clock.fixed(NOW, ZoneOffset.UTC)).issue(user(Instant.EPOCH, false)).value();
        when(users.tokenState(7)).thenReturn(Optional.of(new TokenState(false, Instant.EPOCH)));
        assertThatThrownBy(() -> decoder(NOW).decode(token)).isInstanceOf(JwtValidationException.class);
        when(users.tokenState(7)).thenReturn(Optional.empty());
        assertThatThrownBy(() -> decoder(NOW).decode(token)).isInstanceOf(JwtValidationException.class);
    }

    @Test
    void expiryHasSixtySecondsOfSkew() {
        when(users.tokenState(7)).thenReturn(Optional.of(new TokenState(true, Instant.EPOCH)));
        String token = new AccessTokens(encoder, AUTH, Clock.fixed(NOW, ZoneOffset.UTC)).issue(user(Instant.EPOCH, false)).value();
        decoder(Instant.parse("2026-10-03T07:31:20Z")).decode(token);   // exp 07:30:30 + 50 s
        assertThatThrownBy(() -> decoder(Instant.parse("2026-10-03T07:31:40Z")).decode(token))
                .isInstanceOf(JwtValidationException.class);
    }

    @Test
    void wrongTypeOrAudienceIsRejected() {
        when(users.tokenState(7)).thenReturn(Optional.of(new TokenState(true, Instant.EPOCH)));
        JwtClaimsSet claims = JwtClaimsSet.builder().issuer("civicbrain").audience(List.of("civicbrain-web")).subject("7")
                .issuedAt(NOW).expiresAt(NOW.plusSeconds(600)).claim("roles", List.of("ADMIN")).build();
        String typJwt = encoder.encode(JwtEncoderParameters.from(JwsHeader.with(MacAlgorithm.HS256).type("JWT").build(), claims)).getTokenValue();
        assertThatThrownBy(() -> decoder(NOW).decode(typJwt)).isInstanceOf(BadJwtException.class);

        JwtClaimsSet ai = JwtClaimsSet.from(claims).audience(List.of("civicbrain-ai")).build();
        String aiToken = encoder.encode(JwtEncoderParameters.from(JwsHeader.with(MacAlgorithm.HS256).type("at+jwt").build(), ai)).getTokenValue();
        assertThatThrownBy(() -> decoder(NOW).decode(aiToken)).isInstanceOf(JwtValidationException.class);

        JwtClaimsSet otherIssuer = JwtClaimsSet.from(claims).issuer("someone-else").build();
        String foreign = encoder.encode(JwtEncoderParameters.from(JwsHeader.with(MacAlgorithm.HS256).type("at+jwt").build(), otherIssuer)).getTokenValue();
        assertThatThrownBy(() -> decoder(NOW).decode(foreign)).isInstanceOf(JwtValidationException.class);
    }

    @Test
    void notBeforeRoundsUpToAWholeSecond() {
        assertThat(AccessTokens.notBefore(Instant.parse("2026-10-03T07:15:30Z"))).isEqualTo(Instant.parse("2026-10-03T07:15:30Z"));
        assertThat(AccessTokens.notBefore(Instant.parse("2026-10-03T07:15:30.000001Z"))).isEqualTo(Instant.parse("2026-10-03T07:15:31Z"));
        assertThat(AccessTokens.notBefore(null)).isEqualTo(Instant.EPOCH);
    }
}
