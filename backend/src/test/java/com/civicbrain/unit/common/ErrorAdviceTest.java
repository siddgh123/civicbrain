package com.civicbrain.unit.common;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.containsInAnyOrder;
import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.matchesPattern;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import com.civicbrain.unit.support.WebSliceTest;

/** RFC 9457 bodies with code, requestId and fieldErrors for every error path (docs/12_ERROR_HANDLING.md §1-§3). */
@WebSliceTest
class ErrorAdviceTest {

    private static final String PROBLEM_JSON = "application/problem+json";
    private static final String UUID_PATTERN = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";

    @Autowired
    MockMvc mvc;

    @Test
    void validationErrorGives400ValidationFailedWithFieldErrors() throws Exception {
        MvcResult result = mvc.perform(post("/api/v1/public/test/body").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\" \",\"accuracyM\":240}"))
                .andExpect(status().isBadRequest())
                .andExpect(content().contentType(PROBLEM_JSON))
                .andExpect(jsonPath("$.type").value("https://civicbrain.app/errors/VALIDATION_FAILED"))
                .andExpect(jsonPath("$.status").value(400))
                .andExpect(jsonPath("$.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.fieldErrors", hasSize(2)))
                .andExpect(jsonPath("$.fieldErrors[*].field", containsInAnyOrder("name", "accuracyM")))
                .andExpect(jsonPath("$.fieldErrors[*].code", containsInAnyOrder("NOT_BLANK", "MAX")))
                .andReturn();
        assertThat(result.getResponse().getHeader("X-Request-Id")).matches(UUID_PATTERN);
        assertThat(result.getResponse().getContentAsString()).contains(result.getResponse().getHeader("X-Request-Id"));
    }

    @Test
    void unknownJsonFieldGives400() throws Exception {
        mvc.perform(post("/api/v1/public/test/body").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"a\",\"accuracyM\":10,\"isAdmin\":true}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.fieldErrors[0].field").value("isAdmin"))
                .andExpect(jsonPath("$.fieldErrors[0].code").value("UNKNOWN_FIELD"));
    }

    @Test
    void badEnumValueGives400WithTheField() throws Exception {
        mvc.perform(post("/api/v1/public/test/body").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"a\",\"accuracyM\":10,\"kind\":\"VOLCANO\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.fieldErrors[0].field").value("kind"))
                .andExpect(jsonPath("$.fieldErrors[0].code").value("INVALID_VALUE"));
    }

    @Test
    void unreadableJsonGives400MalformedRequest() throws Exception {
        mvc.perform(post("/api/v1/public/test/body").contentType(MediaType.APPLICATION_JSON).content("{\"name\":"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("MALFORMED_REQUEST"));
    }

    @Test
    void wrongContentTypeGives400MalformedRequest() throws Exception {
        mvc.perform(post("/api/v1/public/test/body").contentType(MediaType.TEXT_PLAIN).content("name=a"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("MALFORMED_REQUEST"));
    }

    @Test
    void invalidRequestParameterGives400ValidationFailed() throws Exception {
        mvc.perform(get("/api/v1/public/test/param").param("size", "500"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.fieldErrors[0].field").value("size"))
                .andExpect(jsonPath("$.fieldErrors[0].code").value("MAX"));
        mvc.perform(get("/api/v1/public/test/param").param("size", "ten"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.fieldErrors[0].field").value("size"));
    }

    @Test
    void anyExceptionGives500InternalErrorWithoutInternals() throws Exception {
        MvcResult result = mvc.perform(get("/api/v1/public/test/boom"))
                .andExpect(status().isInternalServerError())
                .andExpect(content().contentType(PROBLEM_JSON))
                .andExpect(jsonPath("$.code").value("INTERNAL_ERROR"))
                .andExpect(jsonPath("$.requestId").value(matchesPattern(UUID_PATTERN)))
                .andReturn();
        assertThat(result.getResponse().getContentAsString())
                .doesNotContain("test-only-leak-marker", "secret", "IllegalStateException", "at com.", "trace", "\\\\");
    }

    @Test
    void apiExceptionKeepsItsCodeStatusAndDetail() throws Exception {
        mvc.perform(get("/api/v1/public/test/api-exception"))
                .andExpect(status().is(422))
                .andExpect(jsonPath("$.type").value("https://civicbrain.app/errors/GPS_ACCURACY_TOO_LOW"))
                .andExpect(jsonPath("$.code").value("GPS_ACCURACY_TOO_LOW"))
                .andExpect(jsonPath("$.status").value(422))
                .andExpect(jsonPath("$.detail").value("Accuracy was 240 m; 150 m or better is needed."))
                .andExpect(jsonPath("$.fieldErrors").doesNotExist());
    }

    @Test
    void databaseTransitionErrorGives409InvalidTransition() throws Exception {
        mvc.perform(get("/api/v1/public/test/db-transition"))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("INVALID_TRANSITION"))
                .andExpect(content().string(org.hamcrest.Matchers.not(org.hamcrest.Matchers.containsString("SUBMITTED"))));
    }

    @Test
    void unknownPathUnderAPermittedPrefixGives404NotFound() throws Exception {
        mvc.perform(get("/api/v1/public/test/nothing-here"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("NOT_FOUND"));
    }

    @Test
    void safeIncomingRequestIdIsKeptAndUnsafeOneReplaced() throws Exception {
        mvc.perform(get("/api/v1/public/test/boom").header("X-Request-Id", "client-abc-12345"))
                .andExpect(header().string("X-Request-Id", "client-abc-12345"))
                .andExpect(jsonPath("$.requestId").value("client-abc-12345"));
        mvc.perform(get("/api/v1/public/test/boom").header("X-Request-Id", "bad\r\nInjected: yes"))
                .andExpect(header().string("X-Request-Id", matchesPattern(UUID_PATTERN)));
    }
}
