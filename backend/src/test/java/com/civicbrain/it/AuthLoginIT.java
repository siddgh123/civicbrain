package com.civicbrain.it;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.Base64;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwsHeader;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;
import org.springframework.test.web.servlet.MvcResult;

import com.civicbrain.it.support.AuthItSupport;
import com.civicbrain.it.support.IntegrationTest;
import com.civicbrain.users.model.Role;
import com.civicbrain.users.model.UserAccount;

import tools.jackson.databind.JsonNode;

/**
 * Login, generic errors, lockout, JWT claims, PASSWORD_CHANGE_REQUIRED, logout-all and the login rate limit
 * (docs/04_API_CONTRACT.md §1, §11; docs/07_SECURITY.md §1, §2; docs/12_ERROR_HANDLING.md §2).
 * Requirements: FR-02 (password login, same 401 for unknown accounts, lockout after 10 failures; officer TOTP is P25),
 * NFR-01 (JWT claims, tampered / wrong-typ / other-audience tokens rejected, token_valid_after, login rate limit).
 */
@IntegrationTest
class AuthLoginIT extends AuthItSupport {

    @Autowired
    JwtEncoder encoder;

    @Test
    void wrongPasswordAndUnknownAccountGiveTheSame401Body() throws Exception {
        String email = uniqueEmail("generic");
        user(Role.CITIZEN, email, false);
        JsonNode wrong = body(expect401(login(email, PASSWORD + "x", uniqueIp())));
        JsonNode unknown = body(expect401(login(uniqueEmail("nobody"), PASSWORD, uniqueIp())));
        for (String field : List.of("type", "title", "status", "code", "detail")) {
            assertThat(wrong.path(field)).as(field).isEqualTo(unknown.path(field));
        }
        assertThat(wrong.path("code").asString()).isEqualTo("INVALID_CREDENTIALS");
        assertThat(wrong.propertyNames()).containsExactlyInAnyOrderElementsOf(unknown.propertyNames());
    }

    @Test
    void tenFailuresLockTheAccountAndAWrongPasswordWhileLockedStillGives401() throws Exception {
        String email = uniqueEmail("lock");
        UserAccount account = user(Role.CITIZEN, email, false);
        for (int i = 1; i <= 10; i++) {
            expect401(login(email, "Wrong-password-" + i, uniqueIp()));
        }
        mvc.perform(postJson("/api/v1/auth/login", Map.of("identifier", email, "password", PASSWORD)).with(from(uniqueIp())))
                .andExpect(status().isLocked())
                .andExpect(jsonPath("$.code").value("ACCOUNT_LOCKED"));
        JsonNode whileLocked = body(expect401(login(email, "Wrong-password-11", uniqueIp())));
        assertThat(whileLocked.path("code").asString()).isEqualTo("INVALID_CREDENTIALS");

        OffsetDateTime lockedUntil = jdbc.sql("SELECT locked_until FROM users WHERE user_id = :id").param("id", account.id())
                .query(OffsetDateTime.class).single();
        assertThat(lockedUntil.toInstant()).isBetween(Instant.now().plusSeconds(13 * 60), Instant.now().plusSeconds(16 * 60));
        assertThat(countEvents(account.id(), "ACCOUNT_LOCKED")).isEqualTo(1);
        assertThat(countEvents(account.id(), "LOGIN_FAILED")).isGreaterThanOrEqualTo(12);

        // lock over → the correct password works again and the counters are reset
        jdbc.sql("UPDATE users SET locked_until = now() - interval '1 minute' WHERE user_id = :id").param("id", account.id()).update();
        loginOk(email, PASSWORD);
        assertThat(jdbc.sql("SELECT failed_login_count FROM users WHERE user_id = :id").param("id", account.id())
                .query(Integer.class).single()).isZero();
    }

    @Test
    void loginWithThePhoneNumberInEveryCommonForm() throws Exception {
        String email = uniqueEmail("phone");
        UserAccount account = user(Role.CITIZEN, email, false);
        String local = account.phone().substring(3);
        loginOk(account.phone(), PASSWORD);
        loginOk(local, PASSWORD);
        loginOk("0" + local.substring(0, 5) + " " + local.substring(5), PASSWORD);
    }

    @Test
    void accessTokenIsAnHs256AtJwtWithoutPersonalData() throws Exception {
        String email = uniqueEmail("claims");
        UserAccount account = user(Role.CITIZEN, email, false);
        String[] parts = loginOk(email, PASSWORD).access().split("\\.");
        JsonNode header = json.readTree(new String(Base64.getUrlDecoder().decode(parts[0]), StandardCharsets.UTF_8));
        JsonNode claims = json.readTree(new String(Base64.getUrlDecoder().decode(parts[1]), StandardCharsets.UTF_8));
        assertThat(header.path("alg").asString()).isEqualTo("HS256");
        assertThat(header.path("typ").asString()).isEqualTo("at+jwt");
        assertThat(claims.path("iss").asString()).isEqualTo("civicbrain");
        assertThat(claims.path("aud").toString()).contains("civicbrain-web");
        assertThat(claims.path("sub").asString()).isEqualTo(Long.toString(account.id()));
        assertThat(claims.path("roles").get(0).asString()).isEqualTo("CITIZEN");
        assertThat(claims.path("exp").asLong() - claims.path("iat").asLong()).isEqualTo(900);
        assertThat(claims.has("mcp")).isFalse();
        assertThat(claims.toString()).doesNotContain(email).doesNotContain(account.phone().substring(3));
    }

    @Test
    void tamperedOrWrongTypeTokensAreRejected() throws Exception {
        String email = uniqueEmail("forged");
        UserAccount account = user(Role.ADMIN, email, false);
        String token = loginOk(email, PASSWORD).access();
        String tampered = token.substring(0, token.length() - 3) + (token.endsWith("AAA") ? "BBB" : "AAA");
        mvc.perform(get("/api/v1/me").with(bearer(tampered)))
                .andExpect(status().isUnauthorized()).andExpect(jsonPath("$.code").value("UNAUTHENTICATED"));

        Instant now = Instant.now();
        JwtClaimsSet claims = JwtClaimsSet.builder().issuer("civicbrain").audience(List.of("civicbrain-web"))
                .subject(Long.toString(account.id())).issuedAt(now).expiresAt(now.plusSeconds(600))
                .claim("roles", List.of("ADMIN")).build();
        String plainJwt = encoder.encode(JwtEncoderParameters.from(JwsHeader.with(MacAlgorithm.HS256).type("JWT").build(), claims))
                .getTokenValue();
        mvc.perform(get("/api/v1/me").with(bearer(plainJwt))).andExpect(status().isUnauthorized());
        JwtClaimsSet otherAudience = JwtClaimsSet.from(claims).audience(List.of("civicbrain-ai")).build();
        String aiToken = encoder.encode(JwtEncoderParameters.from(JwsHeader.with(MacAlgorithm.HS256).type("at+jwt").build(),
                otherAudience)).getTokenValue();
        mvc.perform(get("/api/v1/me").with(bearer(aiToken))).andExpect(status().isUnauthorized());
    }

    @Test
    void roleAreasFollowTheRolesClaim() throws Exception {
        String citizen = loginOk(user(Role.CITIZEN, uniqueEmail("area-c"), false).email(), PASSWORD).access();
        String admin = loginOk(user(Role.ADMIN, uniqueEmail("area-a"), false).email(), PASSWORD).access();
        mvc.perform(get("/api/v1/officer/complaints").with(bearer(citizen)))
                .andExpect(status().isForbidden()).andExpect(jsonPath("$.code").value("FORBIDDEN"));
        mvc.perform(get("/api/v1/admin/jobs").with(bearer(citizen))).andExpect(status().isForbidden());
        mvc.perform(get("/api/v1/citizen/complaints").with(bearer(admin))).andExpect(status().isForbidden());
        mvc.perform(get("/api/v1/admin/not-built-yet").with(bearer(admin))).andExpect(status().isNotFound());
        mvc.perform(post("/api/v1/auth/logout-all")).andExpect(status().isUnauthorized());
        mvc.perform(post("/api/v1/auth/password/change").contentType(MediaType.APPLICATION_JSON).content("{}"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void mustChangePasswordAllowsOnlyMeAndThePasswordChange() throws Exception {
        String email = uniqueEmail("mcp");
        user(Role.CONTRACTOR, email, true);
        Tokens tokens = loginOk(email, PASSWORD);
        assertThat(tokens.body().path("user").path("mustChangePassword").asBoolean()).isTrue();

        Map<String, Object> profile = Map.of("fullName", "Changed", "preferredLanguage", "en", "emailOptIn", true, "whatsappOptIn", false);
        mvc.perform(put("/api/v1/me").contentType(MediaType.APPLICATION_JSON).content(json.writeValueAsString(profile))
                        .with(bearer(tokens.access())))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value("PASSWORD_CHANGE_REQUIRED"));
        mvc.perform(get("/api/v1/contractor/worklist").with(bearer(tokens.access())))
                .andExpect(jsonPath("$.code").value("PASSWORD_CHANGE_REQUIRED"));
        mvc.perform(get("/api/v1/me").with(bearer(tokens.access()))).andExpect(status().isOk());

        mvc.perform(postJson("/api/v1/auth/password/change", Map.of("currentPassword", "not-the-password", "newPassword", "A-brand-new-secret-77"))
                        .with(bearer(tokens.access())))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.fieldErrors[0].field").value("currentPassword"));
        mvc.perform(postJson("/api/v1/auth/password/change", Map.of("currentPassword", PASSWORD, "newPassword", PASSWORD))
                        .with(bearer(tokens.access())))
                .andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.code").value("PASSWORD_POLICY"));
        mvc.perform(postJson("/api/v1/auth/password/change", Map.of("currentPassword", PASSWORD, "newPassword", "A-brand-new-secret-77"))
                        .with(bearer(tokens.access()))
                        .cookie(new jakarta.servlet.http.Cookie(COOKIE, tokens.cookie())))
                .andExpect(status().isNoContent());

        // every older access token is revoked; the caller's own refresh family continues with mcp cleared
        mvc.perform(get("/api/v1/me").with(bearer(tokens.access())))
                .andExpect(status().isUnauthorized()).andExpect(jsonPath("$.code").value("SESSION_REVOKED"));
        MvcResult refreshed = mvc.perform(post("/api/v1/auth/refresh").with(refreshCookie(tokens.cookie()))).andReturn();
        assertThat(refreshed.getResponse().getStatus()).isEqualTo(200);
        String fresh = body(refreshed).path("accessToken").asString();
        mvc.perform(put("/api/v1/me").contentType(MediaType.APPLICATION_JSON).content(json.writeValueAsString(profile))
                .with(bearer(fresh))).andExpect(status().isOk());
        expect401(login(email, PASSWORD, uniqueIp()));
        loginOk(email, "A-brand-new-secret-77");
    }

    @Test
    void logoutAllInvalidatesAnExistingAccessTokenAndEveryRefreshFamily() throws Exception {
        String email = uniqueEmail("logoutall");
        user(Role.CITIZEN, email, false);
        Tokens first = loginOk(email, PASSWORD);
        Tokens second = loginOk(email, PASSWORD);
        mvc.perform(get("/api/v1/me").with(bearer(first.access()))).andExpect(status().isOk());

        mvc.perform(post("/api/v1/auth/logout-all").with(bearer(first.access()))).andExpect(status().isNoContent());

        mvc.perform(get("/api/v1/me").with(bearer(first.access())))
                .andExpect(status().isUnauthorized()).andExpect(jsonPath("$.code").value("SESSION_REVOKED"));
        mvc.perform(get("/api/v1/me").with(bearer(second.access()))).andExpect(status().isUnauthorized());
        mvc.perform(post("/api/v1/auth/refresh").with(refreshCookie(second.cookie()))).andExpect(status().isUnauthorized());
        assertThat(countEvents(userId(email), "LOGOUT_ALL")).isEqualTo(1);

        Tokens again = loginOk(email, PASSWORD);   // a new login right after works
        mvc.perform(get("/api/v1/me").with(bearer(again.access()))).andExpect(status().isOk());
    }

    @Test
    void loginIsLimitedTo30PerIdentifier() throws Exception {
        String identifier = uniqueEmail("flood");
        for (int i = 0; i < 30; i++) {
            expect401(login(identifier, PASSWORD, uniqueIp()));
        }
        MvcResult limited = login(identifier, PASSWORD, uniqueIp());
        assertThat(limited.getResponse().getStatus()).isEqualTo(429);
        assertThat(body(limited).path("code").asString()).isEqualTo("RATE_LIMITED");
        assertThat(limited.getResponse().getHeader("Retry-After")).isNotBlank();
    }

    private static MvcResult expect401(MvcResult result) throws Exception {
        assertThat(result.getResponse().getStatus()).as(result.getResponse().getContentAsString()).isEqualTo(401);
        return result;
    }
}
