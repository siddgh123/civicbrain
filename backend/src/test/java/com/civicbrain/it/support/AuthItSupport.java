package com.civicbrain.it.support;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ThreadLocalRandom;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder;
import org.springframework.test.web.servlet.request.RequestPostProcessor;

import com.civicbrain.users.model.Role;
import com.civicbrain.users.model.UserAccount;
import com.civicbrain.users.service.UserAccounts;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

/**
 * Helpers for the auth integration tests. Every test uses its own e-mail, phone and client IP, so the in-memory
 * rate limits (shared by the cached Spring context) never couple two tests.
 */
public abstract class AuthItSupport {

    public static final String PASSWORD = "Correct-Horse-Battery-42";
    public static final String ORIGIN = "http://localhost:5173";
    public static final String COOKIE = "__Host-cb_rt";
    private static final Pattern SIX_DIGITS = Pattern.compile("\\b(\\d{6})\\b");

    @Autowired
    protected MockMvc mvc;
    @Autowired
    protected JdbcClient jdbc;
    @Autowired
    protected UserAccounts accounts;
    @Autowired
    protected MailpitClient mailpit;

    protected final JsonMapper json = JsonMapper.builder().build();

    /** Login tokens: bearer + refresh cookie value. */
    public record Tokens(String access, String cookie, JsonNode body) {
    }

    protected static String uniqueEmail(String prefix) {
        return prefix + "-" + UUID.randomUUID().toString().substring(0, 8) + "@it.local";
    }

    protected static String uniquePhone() {
        return "+919" + String.format("%09d", ThreadLocalRandom.current().nextLong(1_000_000_000L));
    }

    protected static String uniqueIp() {
        ThreadLocalRandom r = ThreadLocalRandom.current();
        return "10." + r.nextInt(1, 255) + "." + r.nextInt(1, 255) + "." + r.nextInt(1, 255);
    }

    protected static RequestPostProcessor from(String ip) {
        return request -> {
            request.setRemoteAddr(ip);
            return request;
        };
    }

    protected MockHttpServletRequestBuilder postJson(String path, Object body) {
        return post(path).contentType(MediaType.APPLICATION_JSON).content(json.writeValueAsString(body));
    }

    protected String noticeVersion() {
        return jdbc.sql("SELECT version FROM privacy_notices WHERE is_current").query(String.class).single();
    }

    protected Map<String, Object> registerBody(String email, String phone, String password) {
        return Map.of("fullName", "IT Citizen", "email", email, "phone", phone, "password", password,
                "privacyNoticeVersion", noticeVersion(),
                "consents", Map.of("whatsapp", false, "publicPhoto", true, "aiTraining", false));
    }

    protected MvcResult register(String email, String phone, String password, String ip) throws Exception {
        return mvc.perform(postJson("/api/v1/auth/register", registerBody(email, phone, password)).with(from(ip))).andReturn();
    }

    protected MvcResult login(String identifier, String password, String ip) throws Exception {
        return mvc.perform(postJson("/api/v1/auth/login", Map.of("identifier", identifier, "password", password))
                .with(from(ip))).andReturn();
    }

    protected Tokens loginOk(String identifier, String password) throws Exception {
        MvcResult result = login(identifier, password, uniqueIp());
        assertThat(result.getResponse().getStatus()).as(result.getResponse().getContentAsString()).isEqualTo(200);
        JsonNode body = body(result);
        return new Tokens(body.path("accessToken").asString(), cookie(result.getResponse()), body);
    }

    /** A verified account created directly through the user service (no OTP round trip). */
    protected UserAccount user(Role role, String email, boolean mustChangePassword) {
        return accounts.create(new UserAccounts.NewAccount("IT " + role, email, role == Role.CITIZEN ? uniquePhone() : null,
                PASSWORD, role, true, mustChangePassword, null,
                role == Role.CITIZEN ? new UserAccounts.Consents(false, false, false) : null, "127.0.0.1"));
    }

    protected JsonNode body(MvcResult result) throws Exception {
        return json.readTree(result.getResponse().getContentAsString());
    }

    /** Value of the {@code __Host-cb_rt} Set-Cookie header (null when absent or cleared). */
    protected static String cookie(MockHttpServletResponse response) {
        for (String header : response.getHeaders(HttpHeaders.SET_COOKIE)) {
            if (header.startsWith(COOKIE + "=")) {
                String value = header.substring(COOKIE.length() + 1).split(";", 2)[0];
                return value.isEmpty() ? null : value;
            }
        }
        return null;
    }

    protected static String setCookieHeader(MockHttpServletResponse response) {
        return response.getHeaders(HttpHeaders.SET_COOKIE).stream().filter(h -> h.startsWith(COOKIE + "=")).findFirst().orElse(null);
    }

    /** The one 6-digit number of an OTP mail. */
    protected static String code(String text) {
        Matcher m = SIX_DIGITS.matcher(text);
        assertThat(m.find()).as("6-digit code in the mail").isTrue();
        String code = m.group(1);
        assertThat(m.find()).as("the code appears only once").isFalse();
        return code;
    }

    protected static RequestPostProcessor bearer(String token) {
        return request -> {
            request.addHeader(HttpHeaders.AUTHORIZATION, "Bearer " + token);
            return request;
        };
    }

    protected static RequestPostProcessor refreshCookie(String value) {
        return request -> {
            request.setCookies(new jakarta.servlet.http.Cookie(COOKIE, value));
            request.addHeader("X-CB-CSRF", "1");
            request.addHeader("Origin", ORIGIN);
            return request;
        };
    }

    protected long countEvents(Long userId, String type) {
        return jdbc.sql("SELECT count(*) FROM auth_events WHERE user_id = :id AND event_type = :type")
                .param("id", userId).param("type", type).query(Long.class).single();
    }

    protected long userId(String email) {
        return jdbc.sql("SELECT user_id FROM users WHERE lower(email) = lower(:e)").param("e", email).query(Long.class).single();
    }
}
