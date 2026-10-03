package com.civicbrain.it;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MvcResult;

import com.civicbrain.it.support.AuthItSupport;
import com.civicbrain.it.support.IntegrationTest;
import com.civicbrain.it.support.MailpitClient.Mail;

import tools.jackson.databind.JsonNode;

/**
 * Register → OTP mail (Mailpit container) → verify → login, decoys, OTP rules and limits
 * (docs/04_API_CONTRACT.md §1, §3, §11; docs/07_SECURITY.md §1, §7; 09_7DAY §4).
 */
@IntegrationTest
class AuthRegistrationIT extends AuthItSupport {

    @Test
    void registerThenOtpMailThenVerifyThenLoginAndMe() throws Exception {
        String email = uniqueEmail("reg");
        String phone = uniquePhone();
        String ip = uniqueIp();

        MvcResult registered = register(email, phone, PASSWORD, ip);
        assertThat(registered.getResponse().getStatus()).isEqualTo(202);
        JsonNode otp = body(registered);
        long otpId = otp.path("otpId").asLong();
        assertThat(otpId).isPositive();
        assertThat(otp.path("expiresInSec").asLong()).isEqualTo(600);

        List<Mail> mails = mailpit.await(email, 1);
        assertThat(mails).hasSize(1);
        assertThat(mails.getFirst().subject()).doesNotContainPattern("\\d");
        String code = code(mails.getFirst().text());

        // before verification: 403 EMAIL_NOT_VERIFIED with an otpId (the code just sent: resend limit 1 / 60 s)
        mvc.perform(postJson("/api/v1/auth/login", Map.of("identifier", email, "password", PASSWORD)).with(from(uniqueIp())))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value("EMAIL_NOT_VERIFIED"))
                .andExpect(jsonPath("$.otpId").value(otpId));

        String wrong = code.equals("000000") ? "111111" : "000000";
        mvc.perform(postJson("/api/v1/auth/verify-otp", Map.of("otpId", otpId, "code", wrong)).with(from(ip)))
                .andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.code").value("OTP_INVALID"));
        mvc.perform(postJson("/api/v1/auth/verify-otp", Map.of("otpId", otpId, "code", code)).with(from(ip)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.verified").value(true));
        mvc.perform(postJson("/api/v1/auth/verify-otp", Map.of("otpId", otpId, "code", code)).with(from(ip)))
                .andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.code").value("OTP_INVALID"));   // single use

        Tokens tokens = loginOk(email, PASSWORD);
        assertThat(tokens.cookie()).isNotBlank();
        assertThat(tokens.body().path("expiresIn").asLong()).isBetween(895L, 905L);
        assertThat(tokens.body().path("user").path("role").asString()).isEqualTo("CITIZEN");
        assertThat(tokens.body().path("user").path("mustChangePassword").asBoolean()).isFalse();

        mvc.perform(get("/api/v1/me").with(bearer(tokens.access())))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.email").value(email))
                .andExpect(jsonPath("$.role").value("CITIZEN"))
                .andExpect(jsonPath("$.phoneMasked").value("+91******" + phone.substring(phone.length() - 4)))
                .andExpect(jsonPath("$.whatsappOptIn").value(false))
                .andExpect(jsonPath("$.consents.length()").value(4))
                .andExpect(jsonPath("$.consents[?(@.type == 'PRIVACY_NOTICE')].granted").value(true))
                .andExpect(jsonPath("$.consents[?(@.type == 'PUBLIC_PHOTO')].granted").value(true))
                .andExpect(jsonPath("$.consents[0].noticeVersion").value(noticeVersion()));

        long userId = userId(email);
        for (String type : List.of("ACCOUNT_CREATED", "OTP_SENT", "OTP_FAILED", "OTP_VERIFIED", "LOGIN_SUCCESS")) {
            assertThat(countEvents(userId, type)).as(type).isPositive();
        }
    }

    @Test
    void existingEmailOrPhoneGetsADecoyAndTheOwnerAMail() throws Exception {
        String email = uniqueEmail("owner");
        String phone = uniquePhone();
        assertThat(register(email, phone, PASSWORD, uniqueIp()).getResponse().getStatus()).isEqualTo(202);
        assertThat(mailpit.await(email, 1)).hasSize(1);

        MvcResult again = register(email.toUpperCase(), uniquePhone(), PASSWORD, uniqueIp());
        assertThat(again.getResponse().getStatus()).isEqualTo(202);
        long decoyOtp = body(again).path("otpId").asLong();
        assertThat(decoyOtp).isPositive();
        assertThat(body(again).path("expiresInSec").asLong()).isEqualTo(600);
        assertThat(jdbc.sql("SELECT count(*) FROM users WHERE lower(email) = lower(:e)").param("e", email)
                .query(Long.class).single()).isEqualTo(1);
        assertThat(jdbc.sql("SELECT user_id IS NULL FROM auth_otp_codes WHERE otp_id = :id").param("id", decoyOtp)
                .query(Boolean.class).single()).isTrue();

        List<Mail> mails = mailpit.await(email, 2);
        assertThat(mails).hasSize(2);
        Mail ownerMail = mails.stream().filter(m -> m.subject().contains("tried to register")).findFirst().orElseThrow();
        assertThat(ownerMail.text()).doesNotContainPattern("\\b\\d{6}\\b");
        mvc.perform(postJson("/api/v1/auth/verify-otp", Map.of("otpId", decoyOtp, "code", "123456")).with(from(uniqueIp())))
                .andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.code").value("OTP_INVALID"));

        String otherEmail = uniqueEmail("samephone");
        MvcResult samePhone = register(otherEmail, phone, PASSWORD, uniqueIp());
        assertThat(samePhone.getResponse().getStatus()).isEqualTo(202);
        assertThat(body(samePhone).path("otpId").asLong()).isPositive();
        assertThat(jdbc.sql("SELECT count(*) FROM users WHERE lower(email) = lower(:e)").param("e", otherEmail)
                .query(Long.class).single()).isZero();
        assertThat(mailpit.to(otherEmail)).isEmpty();
    }

    @Test
    void theOtpCodeIsNeverStoredInTheOutboxOrNotifications() throws Exception {
        String email = uniqueEmail("nostore");
        register(email, uniquePhone(), PASSWORD, uniqueIp());
        String code = code(mailpit.await(email, 1).getFirst().text());

        assertThat(jdbc.sql("SELECT count(*) FROM notification_outbox WHERE payload::text LIKE :p")
                .param("p", "%" + code + "%").query(Long.class).single()).isZero();
        assertThat(jdbc.sql("""
                SELECT count(*) FROM notifications
                 WHERE coalesce(rendered_body, '') LIKE :p OR coalesce(rendered_subject, '') LIKE :p""")
                .param("p", "%" + code + "%").query(Long.class).single()).isZero();
        assertThat(jdbc.sql("SELECT count(*) FROM auth_events WHERE details::text LIKE :p OR identifier LIKE :p")
                .param("p", "%" + code + "%").query(Long.class).single()).isZero();
        assertThat(jdbc.sql("SELECT code_hmac FROM auth_otp_codes WHERE destination = :e").param("e", email)
                .query(String.class).single()).matches("[0-9a-f]{64}").doesNotContain(code);
    }

    @Test
    void expiredCodeAndTooManyAttempts() throws Exception {
        String email = uniqueEmail("expire");
        long otpId = body(register(email, uniquePhone(), PASSWORD, uniqueIp())).path("otpId").asLong();
        String code = code(mailpit.await(email, 1).getFirst().text());
        jdbc.sql("UPDATE auth_otp_codes SET created_at = now() - interval '20 minutes', expires_at = now() - interval '10 minutes' WHERE otp_id = :id")
                .param("id", otpId).update();
        mvc.perform(postJson("/api/v1/auth/verify-otp", Map.of("otpId", otpId, "code", code)).with(from(uniqueIp())))
                .andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.code").value("OTP_EXPIRED"));

        String email2 = uniqueEmail("attempts");
        long otp2 = body(register(email2, uniquePhone(), PASSWORD, uniqueIp())).path("otpId").asLong();
        String code2 = code(mailpit.await(email2, 1).getFirst().text());
        String wrong = code2.equals("000000") ? "111111" : "000000";
        for (int i = 0; i < 5; i++) {
            mvc.perform(postJson("/api/v1/auth/verify-otp", Map.of("otpId", otp2, "code", wrong)).with(from(uniqueIp())))
                    .andExpect(jsonPath("$.code").value("OTP_INVALID"));
        }
        mvc.perform(postJson("/api/v1/auth/verify-otp", Map.of("otpId", otp2, "code", code2)).with(from(uniqueIp())))
                .andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.code").value("OTP_ATTEMPTS_EXCEEDED"));
    }

    @Test
    void resendIsLimitedToOnePerMinuteAndUnknownIdsLookTheSame() throws Exception {
        String email = uniqueEmail("resend");
        long otpId = body(register(email, uniquePhone(), PASSWORD, uniqueIp())).path("otpId").asLong();
        mvc.perform(postJson("/api/v1/auth/resend-otp", Map.of("otpId", otpId)).with(from(uniqueIp())))
                .andExpect(status().isTooManyRequests())
                .andExpect(jsonPath("$.code").value("RATE_LIMITED"))
                .andExpect(header().exists("Retry-After"));
        mvc.perform(postJson("/api/v1/auth/resend-otp", Map.of("otpId", 999_999_999L)).with(from(uniqueIp())))
                .andExpect(status().isAccepted());
    }

    @Test
    void passwordPolicyAndValidation() throws Exception {
        mvc.perform(postJson("/api/v1/auth/register", registerBody(uniqueEmail("short"), uniquePhone(), "short-pw"))
                        .with(from(uniqueIp())))
                .andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.code").value("PASSWORD_POLICY"))
                .andExpect(jsonPath("$.fieldErrors[0].field").value("password"));
        mvc.perform(postJson("/api/v1/auth/register", registerBody(uniqueEmail("common"), uniquePhone(), "Password2026!!"))
                        .with(from(uniqueIp())))
                .andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.code").value("PASSWORD_POLICY"));

        mvc.perform(postJson("/api/v1/auth/register", registerBody(uniqueEmail("phone"), "9876543210", PASSWORD))
                        .with(from(uniqueIp())))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.fieldErrors[0].field").value("phone"));

        Map<String, Object> oldNotice = new HashMap<>(registerBody(uniqueEmail("notice"), uniquePhone(), PASSWORD));
        oldNotice.put("privacyNoticeVersion", "1999-01-v0");
        mvc.perform(postJson("/api/v1/auth/register", oldNotice).with(from(uniqueIp())))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.fieldErrors[0].field").value("privacyNoticeVersion"));

        Map<String, Object> extra = new HashMap<>(registerBody(uniqueEmail("extra"), uniquePhone(), PASSWORD));
        extra.put("role", "ADMIN");
        mvc.perform(postJson("/api/v1/auth/register", extra).with(from(uniqueIp())))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.fieldErrors[0].code").value("UNKNOWN_FIELD"));
    }

    @Test
    void registerIsLimitedToFivePerHourPerIp() throws Exception {
        String ip = uniqueIp();
        for (int i = 0; i < 5; i++) {
            mvc.perform(postJson("/api/v1/auth/register", registerBody(uniqueEmail("limit"), uniquePhone(), "short"))
                    .with(from(ip))).andExpect(status().isUnprocessableContent());
        }
        MvcResult limited = register(uniqueEmail("limit"), uniquePhone(), PASSWORD, ip);
        assertThat(limited.getResponse().getStatus()).isEqualTo(429);
        assertThat(body(limited).path("code").asString()).isEqualTo("RATE_LIMITED");
        assertThat(Long.parseLong(limited.getResponse().getHeader("Retry-After"))).isPositive();
    }

    @Test
    void behindTheLocalProxyTheLimitIsKeyedOnTheRightMostForwardedAddress() throws Exception {
        // MockMvc's peer is 127.0.0.1 (= the Vite proxy / tunnel); the first X-Forwarded-For entry is forged each time
        String email = uniqueEmail("xff");
        mvc.perform(postJson("/api/v1/auth/register", registerBody(email, uniquePhone(), PASSWORD))
                        .header("X-Forwarded-For", "1.2.3.4, 203.0.113.9"))
                .andExpect(status().isAccepted());
        assertThat(jdbc.sql("SELECT host(request_ip) FROM auth_otp_codes WHERE destination = :e").param("e", email)
                .query(String.class).single()).isEqualTo("203.0.113.9");
        for (int i = 2; i <= 5; i++) {
            mvc.perform(postJson("/api/v1/auth/register", registerBody(uniqueEmail("xff"), uniquePhone(), "short"))
                            .header("X-Forwarded-For", "1.2.3." + i + ", 203.0.113.9"))
                    .andExpect(status().isUnprocessableContent());
        }
        mvc.perform(postJson("/api/v1/auth/register", registerBody(uniqueEmail("xff"), uniquePhone(), PASSWORD))
                        .header("X-Forwarded-For", "198.51.100.77, 203.0.113.9"))
                .andExpect(status().isTooManyRequests())
                .andExpect(jsonPath("$.code").value("RATE_LIMITED"));
        // another client behind the same proxy has its own bucket
        mvc.perform(postJson("/api/v1/auth/register", registerBody(uniqueEmail("xff"), uniquePhone(), "short"))
                        .header("X-Forwarded-For", "1.2.3.4, 203.0.113.10"))
                .andExpect(status().isUnprocessableContent());
    }

    @Test
    void privacyNoticeIsPublicAndCached() throws Exception {
        mvc.perform(get("/api/v1/public/privacy-notice"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.version").value("2026-10-v1"))
                .andExpect(jsonPath("$.summary").isNotEmpty())
                .andExpect(jsonPath("$.publishedAt").value(org.hamcrest.Matchers.endsWith("+05:30")))
                .andExpect(header().string("Cache-Control", org.hamcrest.Matchers.containsString("max-age=60")));
    }
}
