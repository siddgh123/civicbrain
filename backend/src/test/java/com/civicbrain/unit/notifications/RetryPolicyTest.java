package com.civicbrain.unit.notifications;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Duration;
import java.time.Instant;

import org.junit.jupiter.api.Test;

import com.civicbrain.notifications.service.RetryPolicy;

/** docs/02_ARCHITECTURE.md §5 rule 10 / 12 §4: retries after 1 / 5 / 30 min, at most 5 attempts, then FAILED for good. */
class RetryPolicyTest {

    @Test
    void retriesAfterOneFiveAndThirtyMinutesUntilTheFifthAttempt() {
        Instant now = Instant.parse("2026-10-03T10:00:00Z");
        assertThat(RetryPolicy.nextAttempt(1, now)).contains(now.plus(Duration.ofMinutes(1)));
        assertThat(RetryPolicy.nextAttempt(2, now)).contains(now.plus(Duration.ofMinutes(5)));
        assertThat(RetryPolicy.nextAttempt(3, now)).contains(now.plus(Duration.ofMinutes(30)));
        assertThat(RetryPolicy.nextAttempt(4, now)).contains(now.plus(Duration.ofMinutes(30)));
        assertThat(RetryPolicy.nextAttempt(5, now)).isEmpty();
        assertThat(RetryPolicy.nextAttempt(6, now)).isEmpty();
        assertThat(RetryPolicy.MAX_ATTEMPTS).isEqualTo(5);
    }
}
