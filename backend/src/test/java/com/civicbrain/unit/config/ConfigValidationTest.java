package com.civicbrain.unit.config;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;

import com.civicbrain.config.AppProperties;
import com.civicbrain.config.AuthProperties;
import com.civicbrain.config.WhatsAppProperties;

/** Required settings fail the start with the environment variable's name and never echo a secret (rule 10). */
class ConfigValidationTest {

    @EnableConfigurationProperties({AppProperties.class, AuthProperties.class, WhatsAppProperties.class})
    static class PropertiesOnly {
    }

    private final ApplicationContextRunner runner = new ApplicationContextRunner().withUserConfiguration(PropertiesOnly.class);

    private static Map<String, String> valid() {
        Map<String, String> p = new LinkedHashMap<>();
        p.put("app.base-url", "http://localhost:5173");
        p.put("app.extra-origins", "http://127.0.0.1:5173");
        p.put("app.storage-root", "/tmp/cb-test");
        p.put("app.mail-from", "CivicBrain Test <no-reply@test.local>");
        p.put("app.ai-service-url", "http://127.0.0.1:8001");
        p.put("app.auth.jwt-secret", b64("test-only-jwt-secret-0123456789abcdef"));
        p.put("app.auth.jwt-issuer", "civicbrain");
        p.put("app.auth.jwt-audience", "civicbrain-web");
        p.put("app.auth.otp-hmac-key", b64("test-only-otp-hmac-key-0123456789abcd"));
        p.put("app.auth.totp-enc-key", b64("test-only-totp-key-0123456789abc"));
        p.put("app.auth.ai-service-jwt-secret", b64("test-only-ai-service-jwt-0123456789ab"));
        p.put("app.whatsapp.provider", "log");
        return p;
    }

    @Test
    void validSettingsStart() {
        run(valid()).run(ctx -> {
            assertThat(ctx).hasNotFailed();
            AuthProperties auth = ctx.getBean(AuthProperties.class);
            assertThat(auth.totpEncKey().bytes()).hasSize(32);
            assertThat(auth.jwtSecret().toString()).doesNotContain(valid().get("app.auth.jwt-secret"));
            assertThat(ctx.getBean(AppProperties.class).extraOrigins()).containsExactly("http://127.0.0.1:5173");
        });
    }

    @Test
    void emptyOptionalValuesAreAccepted() {
        Map<String, String> p = valid();
        p.put("app.extra-origins", "");
        p.put("app.labour-rate-per-hour", "");
        run(p).run(ctx -> {
            assertThat(ctx).hasNotFailed();
            AppProperties app = ctx.getBean(AppProperties.class);
            assertThat(app.extraOrigins()).isEmpty();
            assertThat(app.labourRatePerHour()).isNull();
        });
    }

    @ParameterizedTest
    @CsvSource({
            "app.base-url, APP_BASE_URL",
            "app.storage-root, STORAGE_ROOT",
            "app.mail-from, SMTP_FROM",
            "app.auth.jwt-secret, JWT_SECRET",
            "app.auth.jwt-issuer, JWT_ISSUER",
            "app.auth.jwt-audience, JWT_AUDIENCE",
            "app.auth.otp-hmac-key, OTP_HMAC_KEY",
            "app.auth.totp-enc-key, TOTP_ENC_KEY",
            "app.auth.ai-service-jwt-secret, AI_SERVICE_JWT_SECRET",
            "app.whatsapp.provider, WHATSAPP_PROVIDER"})
    void missingRequiredPropertyFailsTheStartNamingTheVariable(String key, String envVar) {
        Map<String, String> p = valid();
        p.put(key, "");   // what ${VAR:} gives when the variable is not set
        run(p).run(ctx -> {
            assertThat(ctx).hasFailed();
            assertThat(messages(ctx.getStartupFailure())).contains(envVar);
        });
    }

    @Test
    void weakSecretIsRejectedWithoutPrintingIt() {
        String weak = b64("short-test-only-key");   // 19 bytes < 32
        Map<String, String> p = valid();
        p.put("app.auth.jwt-secret", weak);
        run(p).run(ctx -> {
            assertThat(ctx).hasFailed();
            assertThat(messages(ctx.getStartupFailure())).contains("JWT_SECRET").doesNotContain(weak);
        });
    }

    @Test
    void placeholderFromEnvExampleIsRejected() {
        Map<String, String> p = valid();
        p.put("app.auth.otp-hmac-key", "REPLACE_WITH_BASE64_32_BYTES");
        run(p).run(ctx -> assertThat(messages(ctx.getStartupFailure())).contains("OTP_HMAC_KEY"));
    }

    @Test
    void totpKeyMustBeExactly32Bytes() {
        Map<String, String> p = valid();
        p.put("app.auth.totp-enc-key", b64("test-only-totp-key-0123456789abcdef"));   // 35 bytes
        run(p).run(ctx -> assertThat(messages(ctx.getStartupFailure())).contains("TOTP_ENC_KEY"));
    }

    @Test
    void baseUrlMustBeAnHttpOrigin() {
        Map<String, String> p = valid();
        p.put("app.base-url", "localhost:5173/app");
        run(p).run(ctx -> assertThat(messages(ctx.getStartupFailure())).contains("APP_BASE_URL"));
    }

    @Test
    void unknownWhatsAppProviderFails() {
        Map<String, String> p = valid();
        p.put("app.whatsapp.provider", "sms");
        run(p).run(ctx -> assertThat(messages(ctx.getStartupFailure())).contains("WHATSAPP_PROVIDER"));
    }

    @Test
    void twilioProviderNeedsItsCredentials() {
        Map<String, String> p = valid();
        p.put("app.whatsapp.provider", "twilio");
        run(p).run(ctx -> assertThat(messages(ctx.getStartupFailure())).contains("TWILIO_SID", "TWILIO_TOKEN"));
    }

    private ApplicationContextRunner run(Map<String, String> properties) {
        List<String> pairs = new ArrayList<>();
        properties.forEach((k, v) -> pairs.add(k + "=" + v));
        return runner.withPropertyValues(pairs.toArray(String[]::new));
    }

    private static String messages(Throwable failure) {
        StringBuilder text = new StringBuilder();
        for (Throwable t = failure; t != null; t = t.getCause()) {
            text.append(t.getMessage()).append('\n');
        }
        return text.toString();
    }

    private static String b64(String s) {
        return Base64.getEncoder().encodeToString(s.getBytes(StandardCharsets.US_ASCII));
    }
}
