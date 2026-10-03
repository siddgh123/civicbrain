package com.civicbrain.unit.config;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.ResultActions;

import com.civicbrain.unit.support.WebSliceTest;

/** Deny-all chain, public paths and the security headers of docs/07_SECURITY.md §2, §4. */
@WebSliceTest
class SecurityConfigTest {

    private static final String CSP = "default-src 'self'; img-src 'self' blob: data: https://tile.openstreetmap.org; "
            + "connect-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; object-src 'none'; "
            + "base-uri 'none'; frame-ancestors 'none'; form-action 'self'";

    @Autowired
    MockMvc mvc;

    @Test
    void unknownApiPathGives401WithProblemDetails() throws Exception {
        assertSecurityHeaders(mvc.perform(get("/api/v1/x"))
                .andExpect(status().isUnauthorized())
                .andExpect(content().contentType("application/problem+json"))
                .andExpect(jsonPath("$.code").value("UNAUTHENTICATED"))
                .andExpect(jsonPath("$.requestId").isNotEmpty())
                .andExpect(header().exists("X-Request-Id"))
                .andExpect(header().string("WWW-Authenticate", "Bearer")));
    }

    @Test
    void anonymousCannotReachRoleAreasOrMutateAnything() throws Exception {
        mvc.perform(get("/api/v1/officer/test/ping")).andExpect(status().isUnauthorized());
        mvc.perform(post("/api/v1/x")).andExpect(status().isUnauthorized());
        mvc.perform(get("/")).andExpect(status().isUnauthorized());
    }

    @Test
    @WithMockUser(roles = "CITIZEN")
    void authenticatedUserStillHitsDenyAllWith403Forbidden() throws Exception {
        mvc.perform(get("/api/v1/officer/test/ping"))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value("FORBIDDEN"));
    }

    @Test
    void healthIsPublic() throws Exception {
        assertSecurityHeaders(mvc.perform(get("/actuator/health")).andExpect(status().isOk()));
    }

    @Test
    void authAndPublicPathsArePermitted() throws Exception {
        mvc.perform(get("/api/v1/auth/test/ping")).andExpect(status().isOk());
        mvc.perform(get("/api/v1/public/test/ping")).andExpect(status().isOk());
    }

    @Test
    void stateless() throws Exception {
        MvcResult result = mvc.perform(get("/api/v1/public/test/ping")).andReturn();
        assertThat(result.getResponse().getHeader("Set-Cookie")).isNull();
        assertThat(result.getRequest().getSession(false)).isNull();
    }

    @Test
    void hstsOnlyOverHttps() throws Exception {
        mvc.perform(get("/api/v1/public/test/ping").secure(true))
                .andExpect(header().string("Strict-Transport-Security", "max-age=31536000"));
        mvc.perform(get("/api/v1/public/test/ping")).andExpect(header().doesNotExist("Strict-Transport-Security"));
    }

    private static void assertSecurityHeaders(ResultActions actions) throws Exception {
        actions.andExpect(header().string("Content-Security-Policy", CSP))
                .andExpect(header().string("X-Content-Type-Options", "nosniff"))
                .andExpect(header().string("X-Frame-Options", "DENY"))
                .andExpect(header().string("Referrer-Policy", "strict-origin-when-cross-origin"))
                .andExpect(header().string("Permissions-Policy", "camera=(self), geolocation=(self), microphone=(), payment=()"))
                .andExpect(header().string("Cross-Origin-Opener-Policy", "same-origin"));
    }
}
