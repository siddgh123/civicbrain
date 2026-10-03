package com.civicbrain.unit.common;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Duration;

import org.junit.jupiter.api.Test;

import com.civicbrain.common.RateLimitedException;
import com.civicbrain.common.RateLimiter;
import com.civicbrain.common.RateLimiter.Kind;
import com.civicbrain.config.RateLimitProperties;
import com.civicbrain.config.RateLimitProperties.Limit;

/** {@link RateLimiter#refund}: 5 complaints / 24 h counts accepted complaints only (FR-11), never above the capacity. */
class RateLimiterRefundTest {

    private static RateLimiter limiter() {
        Limit any = new Limit(100, Duration.ofHours(1));
        return new RateLimiter(new RateLimitProperties(1, any, any, any, any, any, any,
                new Limit(5, Duration.ofHours(24)), any, any));
    }

    @Test
    void aRefundedTokenCanBeUsedAgainButNeverRaisesTheCapacity() {
        RateLimiter limits = limiter();
        limits.refund(Kind.COMPLAINT_USER, "user:1");   // no bucket yet: nothing happens
        for (int i = 0; i < 5; i++) {
            limits.consume(Kind.COMPLAINT_USER, "user:1");
            limits.refund(Kind.COMPLAINT_USER, "user:1");   // e.g. the submission failed a later check
        }
        limits.refund(Kind.COMPLAINT_USER, "user:1");       // already full: stays at 5
        for (int i = 0; i < 5; i++) {
            limits.consume(Kind.COMPLAINT_USER, "user:1");
        }
        assertThatThrownBy(() -> limits.consume(Kind.COMPLAINT_USER, "user:1")).isInstanceOf(RateLimitedException.class);
        assertThat(limits.tryConsume(Kind.COMPLAINT_USER, "user:2")).isTrue();
    }
}
