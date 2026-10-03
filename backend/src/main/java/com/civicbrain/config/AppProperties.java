package com.civicbrain.config;

import java.math.BigDecimal;
import java.util.List;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

/**
 * Web settings (docs/02_ARCHITECTURE.md §6). Every message names the environment variable, so a missing value
 * fails the start with a clear reason.
 *
 * @param baseUrl           APP_BASE_URL - links in messages and the Origin check of refresh/logout
 * @param extraOrigins      APP_EXTRA_ORIGINS - comma list, dev only (may be empty)
 * @param storageRoot       STORAGE_ROOT - absolute photo folder outside the web root
 * @param labourRatePerHour LABOUR_RATE_PER_HOUR - empty until TDMC gives a rate (the estimate then says "rate not set")
 * @param mailFrom          SMTP_FROM - sender of every e-mail
 * @param aiServiceUrl      AI_SERVICE_URL - internal FastAPI (127.0.0.1:8001)
 */
@Validated
@ConfigurationProperties("app")
public record AppProperties(
        @NotBlank(message = "APP_BASE_URL is missing - the URL people open, e.g. http://localhost:5173")
        @Pattern(regexp = "^$|^https?://[A-Za-z0-9.-]+(:[0-9]{1,5})?$",
                message = "APP_BASE_URL must be an origin like http://localhost:5173 (no path, no trailing slash)")
        String baseUrl,
        List<String> extraOrigins,
        @NotBlank(message = "STORAGE_ROOT is missing - absolute folder for photos, e.g. C:\\dev\\civicbrain\\storage")
        String storageRoot,
        @DecimalMin(value = "0", inclusive = false, message = "LABOUR_RATE_PER_HOUR must be a positive number or empty")
        BigDecimal labourRatePerHour,
        @NotBlank(message = "SMTP_FROM is missing - e.g. \"CivicBrain TDMC <no-reply@civicbrain.local>\"")
        String mailFrom,
        @NotBlank(message = "AI_SERVICE_URL is empty - e.g. http://127.0.0.1:8001")
        String aiServiceUrl) {

    public AppProperties {
        extraOrigins = extraOrigins == null ? List.of()
                : extraOrigins.stream().map(String::strip).filter(s -> !s.isEmpty()).toList();
    }
}
