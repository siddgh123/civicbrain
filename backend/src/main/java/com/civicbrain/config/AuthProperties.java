package com.civicbrain.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

import jakarta.validation.constraints.NotBlank;

/**
 * Auth and crypto keys (docs/07_SECURITY.md §1, §5). Keys are {@link Secret}s: validation messages and logs never
 * show the value.
 *
 * @param jwtSecret          JWT_SECRET - HS256 key of the access tokens, base64 of >= 32 random bytes
 * @param jwtIssuer          JWT_ISSUER - "civicbrain"
 * @param jwtAudience        JWT_AUDIENCE - "civicbrain-web"
 * @param otpHmacKey         OTP_HMAC_KEY - HMAC-SHA256 key of e-mail OTP codes
 * @param totpEncKey         TOTP_ENC_KEY - AES-256-GCM key of TOTP secrets, exactly 32 bytes
 * @param aiServiceJwtSecret AI_SERVICE_JWT_SECRET - HS256 key of the 60-second service JWT (aud civicbrain-ai)
 * @param mfaRequired        TOTP for officers/admins (optional P25; false in the MVP)
 */
@Validated
@ConfigurationProperties("app.auth")
public record AuthProperties(
        @Base64Key(message = "JWT_SECRET is missing or not base64 of at least 32 random bytes (scripts/dev/new-secret.ps1)")
        Secret jwtSecret,
        @NotBlank(message = "JWT_ISSUER is missing - set it to civicbrain")
        String jwtIssuer,
        @NotBlank(message = "JWT_AUDIENCE is missing - set it to civicbrain-web")
        String jwtAudience,
        @Base64Key(message = "OTP_HMAC_KEY is missing or not base64 of at least 32 random bytes (scripts/dev/new-secret.ps1)")
        Secret otpHmacKey,
        @Base64Key(minBytes = 32, maxBytes = 32,
                message = "TOTP_ENC_KEY is missing or not base64 of exactly 32 random bytes (scripts/dev/new-secret.ps1)")
        Secret totpEncKey,
        @Base64Key(message = "AI_SERVICE_JWT_SECRET is missing or not base64 of at least 32 random bytes (scripts/dev/new-secret.ps1)")
        Secret aiServiceJwtSecret,
        boolean mfaRequired) {
}
