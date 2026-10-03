package com.civicbrain.it;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.Map;

import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MvcResult;

import com.civicbrain.it.support.AuthItSupport;
import com.civicbrain.it.support.IntegrationTest;
import com.civicbrain.it.support.MailpitClient.Mail;
import com.civicbrain.users.model.Role;
import com.civicbrain.users.model.UserAccount;

import tools.jackson.databind.JsonNode;

/** FR-03: forgot (always 202, decoy for unknown e-mails) → reset with the e-mailed code → every session revoked. */
@IntegrationTest
class PasswordResetIT extends AuthItSupport {

    private static final String NEW_PASSWORD = "Another-Long-Secret-58";

    @Test
    void forgotThenResetRevokesEverySessionAndSwapsThePassword() throws Exception {
        String email = uniqueEmail("forgot");
        UserAccount account = user(Role.CITIZEN, email, false);
        Tokens before = loginOk(email, PASSWORD);

        MvcResult forgot = mvc.perform(postJson("/api/v1/auth/password/forgot", Map.of("email", email.toUpperCase()))
                .with(from(uniqueIp()))).andReturn();
        assertThat(forgot.getResponse().getStatus()).isEqualTo(202);
        JsonNode otp = body(forgot);
        assertThat(otp.path("expiresInSec").asLong()).isEqualTo(600);
        Mail mail = mailpit.await(email, 1).getFirst();
        assertThat(mail.subject()).contains("password").doesNotContainPattern("\\d");
        String code = code(mail.text());

        // a too-weak new password is refused and the code stays usable
        mvc.perform(postJson("/api/v1/auth/password/reset", Map.of("otpId", otp.path("otpId").asLong(), "code", code,
                        "newPassword", "short")).with(from(uniqueIp())))
                .andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.code").value("PASSWORD_POLICY"))
                .andExpect(jsonPath("$.fieldErrors[0].field").value("newPassword"));
        mvc.perform(postJson("/api/v1/auth/password/reset", Map.of("otpId", otp.path("otpId").asLong(), "code", code,
                        "newPassword", NEW_PASSWORD)).with(from(uniqueIp())))
                .andExpect(status().isNoContent());

        mvc.perform(get("/api/v1/me").with(bearer(before.access())))
                .andExpect(status().isUnauthorized()).andExpect(jsonPath("$.code").value("SESSION_REVOKED"));
        mvc.perform(post("/api/v1/auth/refresh").with(refreshCookie(before.cookie()))).andExpect(status().isUnauthorized());
        assertThat(login(email, PASSWORD, uniqueIp()).getResponse().getStatus()).isEqualTo(401);
        loginOk(email, NEW_PASSWORD);
        assertThat(countEvents(account.id(), "PASSWORD_RESET")).isEqualTo(1);
        mvc.perform(postJson("/api/v1/auth/password/reset", Map.of("otpId", otp.path("otpId").asLong(), "code", code,
                        "newPassword", "Yet-Another-Secret-91")).with(from(uniqueIp())))
                .andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.code").value("OTP_INVALID"));   // single use
    }

    @Test
    void unknownEmailGetsTheSameAnswerAndNoMail() throws Exception {
        String unknown = uniqueEmail("ghost");
        MvcResult forgot = mvc.perform(postJson("/api/v1/auth/password/forgot", Map.of("email", unknown))
                .with(from(uniqueIp()))).andReturn();
        assertThat(forgot.getResponse().getStatus()).isEqualTo(202);
        long otpId = body(forgot).path("otpId").asLong();
        assertThat(otpId).isPositive();
        assertThat(body(forgot).path("expiresInSec").asLong()).isEqualTo(600);
        assertThat(mailpit.to(unknown)).isEmpty();
        mvc.perform(postJson("/api/v1/auth/password/reset", Map.of("otpId", otpId, "code", "123456", "newPassword", NEW_PASSWORD))
                        .with(from(uniqueIp())))
                .andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.code").value("OTP_INVALID"));
    }

    @Test
    void aRegistrationCodeCannotResetAPassword() throws Exception {
        String email = uniqueEmail("wrongpurpose");
        long otpId = body(register(email, uniquePhone(), PASSWORD, uniqueIp())).path("otpId").asLong();
        String code = code(mailpit.await(email, 1).getFirst().text());
        mvc.perform(postJson("/api/v1/auth/password/reset", Map.of("otpId", otpId, "code", code, "newPassword", NEW_PASSWORD))
                        .with(from(uniqueIp())))
                .andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.code").value("OTP_INVALID"));
        // the registration code still verifies the e-mail
        mvc.perform(postJson("/api/v1/auth/verify-otp", Map.of("otpId", otpId, "code", code)).with(from(uniqueIp())))
                .andExpect(status().isOk());
    }

    @Test
    void forgotIsLimitedToFivePerHourPerIp() throws Exception {
        String ip = uniqueIp();
        for (int i = 0; i < 5; i++) {
            mvc.perform(postJson("/api/v1/auth/password/forgot", Map.of("email", uniqueEmail("flood"))).with(from(ip)))
                    .andExpect(status().isAccepted());
        }
        mvc.perform(postJson("/api/v1/auth/password/forgot", Map.of("email", uniqueEmail("flood"))).with(from(ip)))
                .andExpect(status().isTooManyRequests())
                .andExpect(jsonPath("$.code").value("RATE_LIMITED"));
    }
}
