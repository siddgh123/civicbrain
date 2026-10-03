package com.civicbrain.unit.common;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Duration;
import java.util.List;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.springframework.mock.web.MockHttpServletRequest;

import com.civicbrain.common.ClientIp;
import com.civicbrain.common.RateLimitedException;
import com.civicbrain.common.RateLimiter;
import com.civicbrain.common.RateLimiter.Kind;
import com.civicbrain.config.RateLimitProperties;
import com.civicbrain.config.RateLimitProperties.Limit;

/**
 * The rate-limit IP (docs/04_API_CONTRACT.md §11): X-Forwarded-For is read from the right, loopback hops are skipped,
 * the first other address is the client; the client-written left part never becomes the key.
 * Requirement: NFR-01 (rate limits that a forged header cannot bypass).
 */
class ClientIpTest {

    private static MockHttpServletRequest from(String peer, String... forwardedFor) {
        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/api/v1/auth/login");
        request.setRemoteAddr(peer);
        for (String value : forwardedFor) {
            request.addHeader("X-Forwarded-For", value);
        }
        return request;
    }

    @Test
    void loopbackRequestIsKeyedOnTheRightMostAddressAndTheForgedFirstEntryDoesNotMatter() {
        assertThat(ClientIp.of(from("127.0.0.1", "1.2.3.4, 203.0.113.9"))).isEqualTo("203.0.113.9");
        assertThat(ClientIp.of(from("127.0.0.1", "9.9.9.9, 203.0.113.9"))).isEqualTo("203.0.113.9");
        assertThat(ClientIp.of(from("127.0.0.1", "203.0.113.9"))).isEqualTo("203.0.113.9");

        // the same rate-limit bucket whatever the first entry says
        Limit hour5 = new Limit(5, Duration.ofHours(1));
        RateLimiter limiter = new RateLimiter(new RateLimitProperties(1, new Limit(30, Duration.ofMinutes(15)),
                new Limit(2, Duration.ofMinutes(15)), hour5, new Limit(1, Duration.ofSeconds(60)), hour5,
                new Limit(20, Duration.ofHours(1)), hour5, new Limit(20, Duration.ofHours(1)), new Limit(300, Duration.ofMinutes(1))));
        limiter.consume(Kind.LOGIN_IP, ClientIp.of(from("127.0.0.1", "1.2.3.4, 203.0.113.9")));
        limiter.consume(Kind.LOGIN_IP, ClientIp.of(from("127.0.0.1", "5.6.7.8, 203.0.113.9")));
        assertThatThrownBy(() -> limiter.consume(Kind.LOGIN_IP, ClientIp.of(from("127.0.0.1", "8.8.4.4, 203.0.113.9"))))
                .isInstanceOf(RateLimitedException.class);
        assertThat(limiter.tryConsume(Kind.LOGIN_IP, ClientIp.of(from("127.0.0.1", "1.2.3.4, 203.0.113.10")))).isTrue();
    }

    @ParameterizedTest
    @CsvSource(delimiter = '|', value = {
            "127.0.0.1        | 203.0.113.9, 127.0.0.1           | 203.0.113.9",   // loopback hops on the right are skipped
            "0:0:0:0:0:0:0:1  | 1.2.3.4, 203.0.113.9             | 203.0.113.9",   // IPv6 loopback peer (Tomcat's form)
            "::1              | 1.2.3.4, 203.0.113.9, ::1        | 203.0.113.9",
            "127.0.0.1        | 1.2.3.4, 10.0.0.5                | 10.0.0.5",      // a private address is not a trusted hop
            "127.0.0.1        | 1.2.3.4, [2001:DB8::7]           | 2001:db8::7",
            "127.0.0.1        | 1.2.3.4, unknown                 | 127.0.0.1",     // broken chain: nothing left of it is trusted
            "127.0.0.1        | 1.2.3.4, 999.1.1.1               | 127.0.0.1",
            "127.0.0.1        | 1.2.3.4, :::::                   | 127.0.0.1",
            "127.0.0.1        | 1.2.3.4, ::ffff:127.0.0.1         | 1.2.3.4",       // IPv4-mapped loopback hop is skipped
            "127.0.0.1        | 127.0.0.1, ::1                   | 127.0.0.1",
            "192.168.1.20     | 1.2.3.4, 203.0.113.9             | 192.168.1.20",  // not a loopback peer: header ignored
            "203.0.113.50     | 127.0.0.1                        | 203.0.113.50"})
    void rightToLeftWalk(String peer, String header, String expected) {
        assertThat(ClientIp.of(from(peer, header))).isEqualTo(expected);
    }

    @Test
    void severalHeaderLinesAreOneListInOrder() {
        assertThat(ClientIp.of(from("127.0.0.1", "1.2.3.4", "203.0.113.9, 127.0.0.1"))).isEqualTo("203.0.113.9");
        assertThat(ClientIp.resolve("127.0.0.1", List.of("203.0.113.9", "1.2.3.4"))).isEqualTo("1.2.3.4");
    }

    @Test
    void withoutTheHeaderThePeerIsTheClient() {
        assertThat(ClientIp.of(from("127.0.0.1"))).isEqualTo("127.0.0.1");
        assertThat(ClientIp.of(from("127.0.0.1", "  ,  "))).isEqualTo("127.0.0.1");
        assertThat(ClientIp.resolve(null, List.of("203.0.113.9"))).isNull();
    }
}
