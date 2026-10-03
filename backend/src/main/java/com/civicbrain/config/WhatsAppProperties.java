package com.civicbrain.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.Pattern;

/**
 * WhatsApp channel (docs/02_ARCHITECTURE.md §6, 09_BUILD_PLAN_7DAY §2.3): {@code log} during the build, the Twilio
 * sandbox for the demo, Meta in Phase 2. Only the chosen provider's keys are required.
 */
@Validated
@ConfigurationProperties("app.whatsapp")
public record WhatsAppProperties(
        @Pattern(regexp = "log|meta|twilio", message = "WHATSAPP_PROVIDER is missing or not one of log, meta, twilio")
        String provider,
        Secret metaToken,
        String metaPhoneId,
        Secret metaAppSecret,
        Secret metaVerifyToken,
        String metaApiVersion,
        String twilioSid,
        Secret twilioToken,
        String twilioFrom) {

    public WhatsAppProperties {
        provider = provider == null ? "" : provider.strip();
    }

    @AssertTrue(message = "WHATSAPP_PROVIDER=twilio needs TWILIO_SID, TWILIO_TOKEN and TWILIO_FROM")
    public boolean isTwilioConfigured() {
        return !"twilio".equals(provider) || (present(twilioSid) && present(twilioToken) && present(twilioFrom));
    }

    @AssertTrue(message = "WHATSAPP_PROVIDER=meta needs META_WA_TOKEN, META_WA_PHONE_ID, META_WA_APP_SECRET and META_WA_VERIFY_TOKEN")
    public boolean isMetaConfigured() {
        return !"meta".equals(provider)
                || (present(metaToken) && present(metaPhoneId) && present(metaAppSecret) && present(metaVerifyToken));
    }

    private static boolean present(String s) {
        return s != null && !s.isBlank();
    }

    private static boolean present(Secret s) {
        return s != null && !s.isBlank();
    }
}
