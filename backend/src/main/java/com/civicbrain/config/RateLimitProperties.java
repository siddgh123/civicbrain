package com.civicbrain.config;

import java.time.Duration;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;

/**
 * The rate limits of docs/04_API_CONTRACT.md §11 ({@code app.rate-limits.*}). The {@code e2e} profile multiplies the
 * per-IP limits by {@code ipMultiplier} (Playwright and the smoke run from one IP) and raises {@code complaintUser}.
 *
 * @param ipMultiplier      factor for every per-IP limit (1; e2e 100)
 * @param loginIdentifier   /auth/login per identifier (30 / 15 min)
 * @param loginIp           /auth/login per IP (100 / 15 min)
 * @param registerIp        /auth/register and /auth/password/forgot per IP (5 / hour)
 * @param otpSendShort      OTP send/resend per destination (1 / 60 s)
 * @param otpSend           OTP send/resend per destination (5 / hour)
 * @param otpVerifyAccount  OTP verify per account (20 / hour; 5 attempts per code come from the code row)
 * @param complaintUser     POST /citizen/complaints per user (5 / 24 h; e2e 100)
 * @param complaintIp       POST /citizen/complaints per IP (20 / hour)
 * @param authenticatedUser everything else authenticated, per user (300 / min)
 */
@Validated
@ConfigurationProperties("app.rate-limits")
public record RateLimitProperties(
        @Min(1) int ipMultiplier,
        @NotNull @Valid Limit loginIdentifier,
        @NotNull @Valid Limit loginIp,
        @NotNull @Valid Limit registerIp,
        @NotNull @Valid Limit otpSendShort,
        @NotNull @Valid Limit otpSend,
        @NotNull @Valid Limit otpVerifyAccount,
        @NotNull @Valid Limit complaintUser,
        @NotNull @Valid Limit complaintIp,
        @NotNull @Valid Limit authenticatedUser) {

    /** {@code capacity} requests per {@code period}, refilled smoothly. */
    public record Limit(@Min(1) long capacity, @NotNull Duration period) {
    }
}
