package com.civicbrain.unit.auth;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Duration;
import java.util.List;

import org.junit.jupiter.api.Test;
import org.springframework.http.ResponseCookie;

import com.civicbrain.auth.api.RefreshCookie;
import com.civicbrain.config.AppProperties;

/**
 * The {@code __Host-} prefix (docs/07_SECURITY.md §1) needs Secure, Path=/ and no Domain, otherwise the browser drops
 * the cookie. Forward headers are off (P06), so behind the HTTPS tunnel {@code request.isSecure()} is false: the cookie
 * must not depend on the request at all. {@link RefreshCookie#issue} and {@link RefreshCookie#clear} take no request.
 */
class RefreshCookieTest {

    private final RefreshCookie cookie = new RefreshCookie(new AppProperties("http://localhost:5173", List.of(),
            "unused", null, "CivicBrain <no-reply@civicbrain.local>", "http://127.0.0.1:8001"));

    @Test
    void issuedCookieIsAlwaysSecureWithPathRootAndNoDomain() {
        ResponseCookie issued = cookie.issue("opaque-value", Duration.ofDays(7));

        assertThat(issued.getName()).isEqualTo("__Host-cb_rt");
        assertThat(issued.isSecure()).isTrue();
        assertThat(issued.isHttpOnly()).isTrue();
        assertThat(issued.getSameSite()).isEqualTo("Strict");
        assertThat(issued.getPath()).isEqualTo("/");
        assertThat(issued.getDomain()).isNull();
        assertThat(issued.toString())
                .startsWith("__Host-cb_rt=opaque-value;")
                .contains("; Path=/").contains("; Max-Age=604800").contains("; Secure").contains("; HttpOnly")
                .contains("; SameSite=Strict").doesNotContain("Domain=");
    }

    @Test
    void clearingCookieHasTheSameAttributesSoTheBrowserReplacesIt() {
        ResponseCookie cleared = cookie.clear();

        assertThat(cleared.getName()).isEqualTo("__Host-cb_rt");
        assertThat(cleared.getValue()).isEmpty();
        assertThat(cleared.getMaxAge()).isEqualTo(Duration.ZERO);
        assertThat(cleared.isSecure()).isTrue();
        assertThat(cleared.getPath()).isEqualTo("/");
        assertThat(cleared.getDomain()).isNull();
        assertThat(cleared.toString()).contains("; Max-Age=0").contains("; Secure").doesNotContain("Domain=");
    }
}
