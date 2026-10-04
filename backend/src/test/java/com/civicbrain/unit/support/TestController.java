package com.civicbrain.unit.support;

import java.util.Map;

import org.postgresql.util.PSQLException;
import org.postgresql.util.ServerErrorMessage;
import org.springframework.boot.test.context.TestComponent;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.web.context.request.async.AsyncRequestNotUsableException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.civicbrain.common.ApiException;
import com.civicbrain.common.ErrorCode;
import com.civicbrain.common.RateLimitedException;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

/**
 * Test-only endpoints (src/test, never in the jar) that trigger each error path of the advice. {@code @TestComponent}
 * keeps it out of component scanning, so only {@link WebSliceTest} (which imports it) sees it - never the full
 * application context of the integration tests.
 */
@TestComponent
@RestController
public class TestController {

    public enum Kind { POTHOLE, GARBAGE }

    public record Body(@NotBlank String name, @NotNull @Max(150) Integer accuracyM, Kind kind) {
    }

    @PostMapping("/api/v1/public/test/body")
    public Body body(@Valid @RequestBody Body body) {
        return body;
    }

    @GetMapping("/api/v1/public/test/param")
    public Map<String, Integer> param(@RequestParam @Min(1) @Max(100) int size) {
        return Map.of("size", size);
    }

    @GetMapping("/api/v1/public/test/boom")
    public String boom() {
        throw new IllegalStateException("internal detail test-only-leak-marker in C:\\secret\\path");
    }

    @GetMapping("/api/v1/public/test/api-exception")
    public String apiException() {
        throw new ApiException(ErrorCode.GPS_ACCURACY_TOO_LOW, "Accuracy was 240 m; 150 m or better is needed.");
    }

    @GetMapping("/api/v1/public/test/db-transition")
    public String dbTransition() {
        throw new DataIntegrityViolationException("could not execute statement", new PSQLException(new ServerErrorMessage(
                "SERROR\0VERROR\0C23514\0MInvalid complaint status transition SUBMITTED -> CLOSED (complaint 7)\0")));
    }

    @GetMapping("/api/v1/public/test/extension")
    public String extension() {
        throw new ApiException(ErrorCode.EMAIL_NOT_VERIFIED, "Please verify your e-mail.").with("otpId", 42L);
    }

    @GetMapping("/api/v1/public/test/limited")
    public String limited() {
        throw new RateLimitedException(17);
    }

    /** What Spring throws when the client closed the connection while the response was written. */
    @GetMapping("/api/v1/public/test/client-gone")
    public String clientGone() throws AsyncRequestNotUsableException {
        throw new AsyncRequestNotUsableException(
                "ServletOutputStream failed to write: java.io.IOException: An established connection was aborted");
    }

    @GetMapping({"/api/v1/public/test/ping", "/api/v1/auth/test/ping", "/actuator/health"})
    public Map<String, String> ping() {
        return Map.of("status", "UP");
    }

    @GetMapping("/api/v1/officer/test/ping")
    public Map<String, String> officerPing() {
        return Map.of("status", "UP");
    }
}
