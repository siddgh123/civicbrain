package com.civicbrain.unit.common;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;

import com.civicbrain.unit.support.WebSliceTest;

/**
 * RFC 9457 extension members (otpId of 403 EMAIL_NOT_VERIFIED), Retry-After on 429 RATE_LIMITED, and the role areas
 * and bearer handling of the security chain (docs/07_SECURITY.md §2, docs/12_ERROR_HANDLING.md §1-§2).
 */
@WebSliceTest
class ProblemExtensionsTest {

    @Autowired
    MockMvc mvc;

    @Test
    void extensionMembersAreTopLevelFields() throws Exception {
        mvc.perform(get("/api/v1/public/test/extension"))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value("EMAIL_NOT_VERIFIED"))
                .andExpect(jsonPath("$.otpId").value(42))
                .andExpect(jsonPath("$.extensions").doesNotExist());
    }

    @Test
    void rateLimitedCarriesRetryAfter() throws Exception {
        mvc.perform(get("/api/v1/public/test/limited"))
                .andExpect(status().isTooManyRequests())
                .andExpect(jsonPath("$.code").value("RATE_LIMITED"))
                .andExpect(header().string("Retry-After", "17"));
    }

    @Test
    void anInvalidBearerTokenGives401EvenOnPublicPaths() throws Exception {
        mvc.perform(get("/api/v1/public/test/ping").header("Authorization", "Bearer x.y.z"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("UNAUTHENTICATED"));
    }

    @Test
    @WithMockUser(roles = "OFFICER")
    void officerReachesTheOfficerArea() throws Exception {
        mvc.perform(get("/api/v1/officer/test/ping")).andExpect(status().isOk());
    }

    @Test
    void logoutAllAndPasswordChangeNeedABearerToken() throws Exception {
        mvc.perform(post("/api/v1/auth/logout-all")).andExpect(status().isUnauthorized());
        mvc.perform(post("/api/v1/auth/password/change")).andExpect(status().isUnauthorized());
    }
}
