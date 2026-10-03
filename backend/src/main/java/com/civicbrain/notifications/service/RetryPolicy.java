package com.civicbrain.notifications.service;

import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Optional;

/**
 * Send retries of docs/02_ARCHITECTURE.md §5 rule 10 and 12 §4: after the 1st, 2nd, 3rd failed attempt wait
 * 1, 5, 30 minutes (30 again after the 4th); the 5th failure is final. A permanent provider error (bad address)
 * is final at once (the dispatcher does not ask for a retry).
 */
public final class RetryPolicy {

    public static final int MAX_ATTEMPTS = 5;
    private static final List<Duration> DELAYS = List.of(Duration.ofMinutes(1), Duration.ofMinutes(5), Duration.ofMinutes(30));

    private RetryPolicy() {
    }

    /** When to try again after {@code attempts} failed attempts; empty = give up. */
    public static Optional<Instant> nextAttempt(int attempts, Instant now) {
        if (attempts < 1 || attempts >= MAX_ATTEMPTS) {
            return Optional.empty();
        }
        return Optional.of(now.plus(DELAYS.get(Math.min(attempts, DELAYS.size()) - 1)));
    }
}
