package com.civicbrain.notifications.service;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;

import com.civicbrain.common.Masking;
import com.civicbrain.notifications.channel.NotificationChannel;
import com.civicbrain.notifications.repo.NotificationRepository;
import com.civicbrain.notifications.repo.NotificationRepository.Due;
import com.civicbrain.notifications.repo.NotificationRepository.NewNotification;

/**
 * The notification dispatcher of docs/02_ARCHITECTURE.md §5 (FR-50/51/52, 12 §4-§5). Every 10 s (scheduling is off
 * in the profiles test, e2e-seed and bootstrap-admin; tests call {@link #dispatchOnce()} themselves):
 * <ol>
 * <li>up to 50 unprocessed outbox rows, each in its own transaction and locked {@code FOR UPDATE SKIP LOCKED}:
 * {@link NotificationPlanner} rows inserted with {@code ON CONFLICT (dedupe_key) DO NOTHING}, row marked processed
 * (a failing row is retried next run and closed after 5 attempts);</li>
 * <li>up to 50 due notifications claimed (SENDING, attempt counted) and sent outside any transaction: SENT with the
 * provider message id, or FAILED with the next attempt after 1 / 5 / 30 min (max 5), or FAILED for good on a
 * permanent provider error.</li>
 * </ol>
 */
@Service
public class OutboxDispatcher {

    public static final int BATCH = 50;
    /** A row still SENDING after this long belongs to a process that stopped mid-send. */
    static final Duration INTERRUPTED_AFTER = Duration.ofMinutes(10);

    private static final Logger log = LoggerFactory.getLogger(OutboxDispatcher.class);

    /** Counts of one run. */
    public record RunResult(int outboxProcessed, int sent, int failed) {
    }

    private final NotificationRepository repo;
    private final NotificationPlanner planner;
    private final Map<String, NotificationChannel> channels;
    private final TransactionTemplate tx;
    private final Clock clock;

    public OutboxDispatcher(NotificationRepository repo, NotificationPlanner planner, List<NotificationChannel> channels,
                            TransactionTemplate tx, Clock clock) {
        this.repo = repo;
        this.planner = planner;
        this.channels = channels.stream().collect(Collectors.toMap(NotificationChannel::channel, Function.identity()));
        this.tx = tx;
        this.clock = clock;
    }

    @Scheduled(initialDelay = 10_000, fixedDelay = 10_000)
    public void scheduled() {
        try {
            RunResult r = dispatchOnce();
            if (r.outboxProcessed() + r.sent() + r.failed() > 0) {
                log.info("notification dispatcher: {} outbox row(s) processed, {} sent, {} failed", r.outboxProcessed(), r.sent(), r.failed());
            }
        } catch (RuntimeException e) {
            log.error("notification dispatcher run failed", e);
        }
    }

    public RunResult dispatchOnce() {
        int processed = processOutbox();
        int[] sent = sendDue();
        return new RunResult(processed, sent[0], sent[1]);
    }

    // ------------------------------------------------------------------ outbox → notifications

    int processOutbox() {
        int processed = 0;
        for (long id : repo.pendingOutboxIds(BATCH)) {
            try {
                Boolean done = tx.execute(status -> repo.lockOutbox(id).map(row -> {
                    Instant now = clock.instant();
                    List<NewNotification> planned = planner.plan(row, now);
                    planned.forEach(repo::insert);
                    repo.markOutboxProcessed(id, now);
                    return true;
                }).orElse(false));
                if (Boolean.TRUE.equals(done)) {
                    processed++;
                }
            } catch (RuntimeException e) {
                log.warn("outbox row {} not processed: {}", id, e.getClass().getSimpleName());
                tx.executeWithoutResult(status -> repo.markOutboxFailed(id, Masking.logSafe(e.getClass().getSimpleName() + ": "
                        + e.getMessage(), 500), RetryPolicy.MAX_ATTEMPTS, clock.instant()));
            }
        }
        return processed;
    }

    // ------------------------------------------------------------------ send

    /** {sent, failed} of this run. */
    int[] sendDue() {
        Instant now = clock.instant();
        int interrupted = tx.execute(status -> repo.closeInterruptedSends(now.minus(INTERRUPTED_AFTER)));
        if (interrupted > 0) {
            log.warn("{} notification(s) were interrupted while sending and are not retried", interrupted);
        }
        List<Due> due = tx.execute(status -> repo.claimDue(BATCH, RetryPolicy.MAX_ATTEMPTS, now));
        int sent = 0;
        int failed = 0;
        for (Due d : due) {
            NotificationChannel channel = channels.get(d.channel());
            if (channel == null) {
                repo.markFailed(d.notificationId(), null, "no channel " + d.channel() + " configured", null);
                failed++;
                continue;
            }
            try {
                String messageId = channel.send(new NotificationChannel.Message(d.notificationId(), d.destination(), d.subject(), d.body()));
                repo.markSent(d.notificationId(), channel.provider(), Masking.logSafe(messageId, 128), clock.instant());
                sent++;
            } catch (NotificationChannel.PermanentFailure e) {
                log.warn("notification {} ({}) failed for good: {}", d.notificationId(), d.channel(), e.getMessage());
                repo.markFailed(d.notificationId(), channel.provider(), Masking.logSafe(e.getMessage(), 500), null);
                failed++;
            } catch (RuntimeException e) {
                Instant next = RetryPolicy.nextAttempt(d.attemptCount(), clock.instant()).orElse(null);
                log.warn("notification {} ({}) attempt {} failed: {}{}", d.notificationId(), d.channel(), d.attemptCount(),
                        e.getClass().getSimpleName(), next == null ? " - no more retries" : "");
                repo.markFailed(d.notificationId(), channel.provider(),
                        Masking.logSafe(e.getClass().getSimpleName() + ": " + e.getMessage(), 500), next);
                failed++;
            }
        }
        return new int[] {sent, failed};
    }
}
