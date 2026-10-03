package com.civicbrain.it;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MvcResult;

import com.civicbrain.it.support.AuthItSupport;
import com.civicbrain.it.support.IntegrationTest;
import com.civicbrain.users.model.Role;

import jakarta.servlet.http.Cookie;

/**
 * Refresh cookie: rotation, reuse detection, CSRF header + Origin, logout (docs/04 §1, docs/07 §1, 09_7DAY §4).
 * Requirement: NFR-01 (session management).
 */
@IntegrationTest
class AuthSessionIT extends AuthItSupport {

    @Test
    void refreshRotatesTheCookieAndReuseRevokesTheWholeFamily() throws Exception {
        String email = uniqueEmail("rotate");
        user(Role.CITIZEN, email, false);
        Tokens tokens = loginOk(email, PASSWORD);

        MvcResult first = mvc.perform(post("/api/v1/auth/refresh").with(refreshCookie(tokens.cookie()))).andReturn();
        assertThat(first.getResponse().getStatus()).isEqualTo(200);
        assertThat(body(first).path("accessToken").asString()).isNotBlank();
        assertThat(body(first).path("expiresIn").asLong()).isPositive();
        String rotated = cookie(first.getResponse());
        assertThat(rotated).isNotBlank().isNotEqualTo(tokens.cookie());
        assertThat(setCookieHeader(first.getResponse()))
                .contains("Path=/").contains("Secure").contains("HttpOnly").contains("SameSite=Strict").contains("Max-Age=")
                .doesNotContain("Domain=");

        // the old cookie again = reuse → 401 SESSION_REVOKED, and the rotated one is dead too
        mvc.perform(post("/api/v1/auth/refresh").with(refreshCookie(tokens.cookie())))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("SESSION_REVOKED"));
        mvc.perform(post("/api/v1/auth/refresh").with(refreshCookie(rotated)))
                .andExpect(status().isUnauthorized());

        long userId = userId(email);
        assertThat(countEvents(userId, "REFRESH_REUSE_DETECTED")).isPositive();
        assertThat(jdbc.sql("SELECT count(*) FROM auth_refresh_tokens WHERE user_id = :id AND revoked_at IS NULL")
                .param("id", userId).query(Long.class).single()).isZero();
        assertThat(jdbc.sql("SELECT token_hash FROM auth_refresh_tokens WHERE user_id = :id").param("id", userId)
                .query(String.class).list()).allSatisfy(h -> assertThat(h).matches("[0-9a-f]{64}").isNotEqualTo(rotated));
    }

    @Test
    void refreshNeedsTheCsrfHeaderAndAnAllowedOrigin() throws Exception {
        String email = uniqueEmail("csrf");
        user(Role.CITIZEN, email, false);
        Tokens tokens = loginOk(email, PASSWORD);
        Cookie cookie = new Cookie(COOKIE, tokens.cookie());

        mvc.perform(post("/api/v1/auth/refresh").cookie(cookie).header("Origin", ORIGIN))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value("CSRF_CHECK_FAILED"));
        mvc.perform(post("/api/v1/auth/refresh").cookie(cookie).header("X-CB-CSRF", "1").header("Origin", "http://evil.example"))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value("CSRF_CHECK_FAILED"));
        mvc.perform(post("/api/v1/auth/refresh").cookie(cookie).header("X-CB-CSRF", "1"))
                .andExpect(status().isForbidden());
        mvc.perform(post("/api/v1/auth/logout").cookie(cookie).header("Origin", ORIGIN))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value("CSRF_CHECK_FAILED"));

        // the cookie was not used by the refused calls; APP_EXTRA_ORIGINS (test: http://127.0.0.1:5173) is allowed
        mvc.perform(post("/api/v1/auth/refresh").cookie(cookie).header("X-CB-CSRF", "1").header("Origin", "http://127.0.0.1:5173"))
                .andExpect(status().isOk());
    }

    @Test
    void logoutRevokesTheFamilyAndClearsTheCookie() throws Exception {
        String email = uniqueEmail("logout");
        user(Role.CITIZEN, email, false);
        Tokens tokens = loginOk(email, PASSWORD);

        MvcResult logout = mvc.perform(post("/api/v1/auth/logout").with(refreshCookie(tokens.cookie()))).andReturn();
        assertThat(logout.getResponse().getStatus()).isEqualTo(204);
        assertThat(setCookieHeader(logout.getResponse())).startsWith(COOKIE + "=;").contains("Max-Age=0").contains("Path=/");
        assertThat(cookie(logout.getResponse())).isNull();

        mvc.perform(post("/api/v1/auth/refresh").with(refreshCookie(tokens.cookie()))).andExpect(status().isUnauthorized());
        assertThat(countEvents(userId(email), "LOGOUT")).isEqualTo(1);
    }

    @Test
    void missingUnknownOrExpiredRefreshTokenGives401() throws Exception {
        mvc.perform(post("/api/v1/auth/refresh").header("X-CB-CSRF", "1").header("Origin", ORIGIN))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("UNAUTHENTICATED"));
        mvc.perform(post("/api/v1/auth/refresh").with(refreshCookie("not-a-real-token")))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("UNAUTHENTICATED"));

        String email = uniqueEmail("expired");
        user(Role.CITIZEN, email, false);
        Tokens tokens = loginOk(email, PASSWORD);
        jdbc.sql("UPDATE auth_refresh_tokens SET issued_at = now() - interval '9 days', expires_at = now() - interval '1 day' WHERE user_id = :id")
                .param("id", userId(email)).update();
        mvc.perform(post("/api/v1/auth/refresh").with(refreshCookie(tokens.cookie())))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("UNAUTHENTICATED"));
    }

    @Test
    void officerSessionsAreShorterThanCitizenSessions() throws Exception {
        String officer = uniqueEmail("officer");
        user(Role.OFFICER, officer, false);
        MvcResult login = login(officer, PASSWORD, uniqueIp());
        assertThat(setCookieHeader(login.getResponse())).contains("Max-Age=3600");
        String citizen = uniqueEmail("citizen");
        user(Role.CITIZEN, citizen, false);
        assertThat(setCookieHeader(login(citizen, PASSWORD, uniqueIp()).getResponse())).contains("Max-Age=604800");
    }
}
