package com.civicbrain.unit.common;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Duration;

import org.junit.jupiter.api.Test;

import com.civicbrain.common.ErrorCode;
import com.civicbrain.common.RateLimitedException;
import com.civicbrain.common.RateLimiter;
import com.civicbrain.common.RateLimiter.Kind;
import com.civicbrain.config.RateLimitProperties;
import com.civicbrain.config.RateLimitProperties.Limit;

/** Bucket4j limits of docs/04_API_CONTRACT.md §11: per key, 429 with Retry-After, per-IP multiplier (e2e). */
class RateLimiterTest {

    private static RateLimitProperties properties(int ipMultiplier) {
        Limit hour5 = new Limit(5, Duration.ofHours(1));
        return new RateLimitProperties(ipMultiplier, new Limit(30, Duration.ofMinutes(15)), new Limit(2, Duration.ofMinutes(15)),
                hour5, new Limit(1, Duration.ofSeconds(60)), hour5, new Limit(20, Duration.ofHours(1)),
                new Limit(5, Duration.ofHours(24)), new Limit(20, Duration.ofHours(1)), new Limit(300, Duration.ofMinutes(1)));
    }

    @Test
    void limitIsPerKeyAndAnswers429WithRetryAfter() {
        RateLimiter limiter = new RateLimiter(properties(1));
        limiter.consume(Kind.LOGIN_IP, "10.0.0.1");
        limiter.consume(Kind.LOGIN_IP, "10.0.0.1");
        limiter.consume(Kind.LOGIN_IP, "10.0.0.2");
        assertThatThrownBy(() -> limiter.consume(Kind.LOGIN_IP, "10.0.0.1"))
                .isInstanceOfSatisfying(RateLimitedException.class, e -> {
                    assertThat(e.code()).isEqualTo(ErrorCode.RATE_LIMITED);
                    assertThat(e.status()).isEqualTo(429);
                    assertThat(e.retryAfterSeconds()).isBetween(1L, 15 * 60L);
                });
    }

    @Test
    void otpSendAllowsOnePerMinutePerDestinationIgnoringCase() {
        RateLimiter limiter = new RateLimiter(properties(1));
        assertThat(limiter.tryConsume(Kind.OTP_SEND, "A@x.in")).isTrue();
        assertThat(limiter.tryConsume(Kind.OTP_SEND, "a@X.in")).isFalse();
        assertThat(limiter.tryConsume(Kind.OTP_SEND, "b@x.in")).isTrue();
        assertThatThrownBy(() -> limiter.consume(Kind.OTP_SEND, "a@x.in"))
                .isInstanceOfSatisfying(RateLimitedException.class, e -> assertThat(e.retryAfterSeconds()).isBetween(1L, 60L));
    }

    @Test
    void ipMultiplierRaisesOnlyPerIpLimits() {
        RateLimiter limiter = new RateLimiter(properties(100));
        for (int i = 0; i < 200; i++) {
            limiter.consume(Kind.LOGIN_IP, "127.0.0.1");
        }
        assertThat(limiter.tryConsume(Kind.LOGIN_IP, "127.0.0.1")).isFalse();
        assertThat(limiter.tryConsume(Kind.OTP_SEND, "c@x.in")).isTrue();
        assertThat(limiter.tryConsume(Kind.OTP_SEND, "c@x.in")).isFalse();
    }
}
