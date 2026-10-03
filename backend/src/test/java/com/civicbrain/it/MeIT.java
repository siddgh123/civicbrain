package com.civicbrain.it;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.Map;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import com.civicbrain.it.support.AuthItSupport;
import com.civicbrain.it.support.IntegrationTest;
import com.civicbrain.users.model.Role;
import com.civicbrain.users.model.UserAccount;

/** {@code /me}: own profile, consents, WhatsApp opt-in kept in sync with the consent (docs/04 §2, FR-60, 02 §5). */
@IntegrationTest
class MeIT extends AuthItSupport {

    @Test
    void meNeedsAToken() throws Exception {
        mvc.perform(get("/api/v1/me")).andExpect(status().isUnauthorized()).andExpect(jsonPath("$.code").value("UNAUTHENTICATED"));
        mvc.perform(get("/api/v1/me").header("Authorization", "Bearer not.a.jwt")).andExpect(status().isUnauthorized());
    }

    @Test
    void profileUpdateKeepsWhatsappOptInAndConsentTogether() throws Exception {
        String email = uniqueEmail("me");
        UserAccount account = user(Role.CITIZEN, email, false);
        String token = loginOk(email, PASSWORD).access();

        Map<String, Object> change = Map.of("fullName", "  New Name  ", "preferredLanguage", "mr", "emailOptIn", false, "whatsappOptIn", true);
        mvc.perform(put("/api/v1/me").contentType(MediaType.APPLICATION_JSON).content(json.writeValueAsString(change)).with(bearer(token)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.fullName").value("New Name"))
                .andExpect(jsonPath("$.preferredLanguage").value("mr"))
                .andExpect(jsonPath("$.emailOptIn").value(false))
                .andExpect(jsonPath("$.whatsappOptIn").value(true))
                .andExpect(jsonPath("$.consents[?(@.type == 'WHATSAPP_MESSAGES')].granted").value(true));
        assertThat(jdbc.sql("SELECT count(*) FROM audit_logs WHERE user_id = :id AND action = 'PROFILE_UPDATED'")
                .param("id", account.id()).query(Long.class).single()).isEqualTo(1);

        mvc.perform(postJson("/api/v1/me/consents", Map.of("consentType", "WHATSAPP_MESSAGES", "granted", false)).with(bearer(token)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.whatsappOptIn").value(false))
                .andExpect(jsonPath("$.consents[?(@.type == 'WHATSAPP_MESSAGES')].granted").value(false));
        mvc.perform(postJson("/api/v1/me/consents", Map.of("consentType", "AI_TRAINING", "granted", true)).with(bearer(token)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.consents[?(@.type == 'AI_TRAINING')].granted").value(true));
        assertThat(jdbc.sql("SELECT whatsapp_opt_in FROM users WHERE user_id = :id").param("id", account.id())
                .query(Boolean.class).single()).isFalse();
        assertThat(jdbc.sql("SELECT count(*) FROM audit_logs WHERE user_id = :id AND action = 'CONSENT_CHANGED'")
                .param("id", account.id()).query(Long.class).single()).isEqualTo(2);
    }

    @Test
    void invalidChangesAreRejected() throws Exception {
        String email = uniqueEmail("me-bad");
        user(Role.CITIZEN, email, false);
        String token = loginOk(email, PASSWORD).access();
        Map<String, Object> badLanguage = Map.of("fullName", "Name", "preferredLanguage", "fr", "emailOptIn", true, "whatsappOptIn", false);
        mvc.perform(put("/api/v1/me").contentType(MediaType.APPLICATION_JSON).content(json.writeValueAsString(badLanguage)).with(bearer(token)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.fieldErrors[0].field").value("preferredLanguage"));
        mvc.perform(postJson("/api/v1/me/consents", Map.of("consentType", "PRIVACY_NOTICE", "granted", false)).with(bearer(token)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.fieldErrors[0].field").value("consentType"));
        mvc.perform(postJson("/api/v1/me/consents", Map.of("consentType", "MARKETING", "granted", true)).with(bearer(token)))
                .andExpect(status().isBadRequest());
    }
}
