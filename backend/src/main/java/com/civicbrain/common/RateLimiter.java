package com.civicbrain.common;

import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import com.civicbrain.config.RateLimitProperties;
import com.civicbrain.config.RateLimitProperties.Limit;

import io.github.bucket4j.Bandwidth;
import io.github.bucket4j.Bucket;
import io.github.bucket4j.ConsumptionProbe;
import io.github.bucket4j.local.LocalBucketBuilder;

/**
 * In-memory Bucket4j limits of docs/04_API_CONTRACT.md §11 (reset on restart). One bucket per (limit, key); a key
 * is an IP, an identifier, a destination or a user id. Hits are logged with the limit name only (no e-mail/phone).
 */
@Component
public class RateLimiter {

    /** The named limits; per-IP limits are multiplied by {@code app.rate-limits.ip-multiplier}. */
    public enum Kind {
        LOGIN_IDENTIFIER, LOGIN_IP, REGISTER_IP, OTP_SEND, OTP_VERIFY_ACCOUNT, COMPLAINT_USER, COMPLAINT_IP, AUTHENTICATED_USER
    }

    private static final Logger log = LoggerFactory.getLogger(RateLimiter.class);
    /** Guard against unbounded growth (many IPs/identifiers): start again with empty buckets. */
    private static final int MAX_BUCKETS = 100_000;

    private final Map<Kind, List<Bandwidth>> limits;
    private final Map<String, Bucket> buckets = new ConcurrentHashMap<>();

    public RateLimiter(RateLimitProperties properties) {
        int ip = properties.ipMultiplier();
        limits = Map.of(
                Kind.LOGIN_IDENTIFIER, bandwidths(1, properties.loginIdentifier()),
                Kind.LOGIN_IP, bandwidths(ip, properties.loginIp()),
                Kind.REGISTER_IP, bandwidths(ip, properties.registerIp()),
                Kind.OTP_SEND, bandwidths(1, properties.otpSendShort(), properties.otpSend()),
                Kind.OTP_VERIFY_ACCOUNT, bandwidths(1, properties.otpVerifyAccount()),
                Kind.COMPLAINT_USER, bandwidths(1, properties.complaintUser()),
                Kind.COMPLAINT_IP, bandwidths(ip, properties.complaintIp()),
                Kind.AUTHENTICATED_USER, bandwidths(1, properties.authenticatedUser()));
    }

    /** Takes one token or throws 429 RATE_LIMITED with the seconds until the next token. */
    public void consume(Kind kind, String key) {
        ConsumptionProbe probe = probe(kind, key);
        if (!probe.isConsumed()) {
            long seconds = Math.max(1, TimeUnit.NANOSECONDS.toSeconds(probe.getNanosToWaitForRefill() + 999_999_999L));
            log.info("rate limit hit: {}", kind);
            throw new RateLimitedException(seconds);
        }
    }

    /** Takes one token if available; false (nothing thrown) when the limit is reached. */
    public boolean tryConsume(Kind kind, String key) {
        boolean consumed = probe(kind, key).isConsumed();
        if (!consumed) {
            log.info("rate limit hit: {} (silent)", kind);
        }
        return consumed;
    }

    /**
     * Gives back one token taken by {@link #consume} (never above the capacity), for limits that count only accepted
     * requests - e.g. 5 complaints / 24 h (FR-11) is checked early but a rejected submission is not a complaint.
     */
    public void refund(Kind kind, String key) {
        Bucket bucket = buckets.get(bucketKey(kind, key));
        if (bucket != null) {
            bucket.addTokens(1);
        }
    }

    private ConsumptionProbe probe(Kind kind, String key) {
        if (buckets.size() > MAX_BUCKETS) {
            log.warn("rate limiter: more than {} buckets - all limits start again", MAX_BUCKETS);
            buckets.clear();
        }
        return buckets.computeIfAbsent(bucketKey(kind, key), k -> newBucket(limits.get(kind))).tryConsumeAndReturnRemaining(1);
    }

    private static String bucketKey(Kind kind, String key) {
        return kind.name() + '|' + (key == null ? "" : key.strip().toLowerCase(Locale.ROOT));
    }

    private static Bucket newBucket(List<Bandwidth> bandwidths) {
        LocalBucketBuilder builder = Bucket.builder();
        bandwidths.forEach(builder::addLimit);
        return builder.build();
    }

    private static List<Bandwidth> bandwidths(int multiplier, Limit... limits) {
        return Arrays.stream(limits).map(l -> {
            long capacity = l.capacity() * multiplier;
            return Bandwidth.builder().capacity(capacity).refillGreedy(capacity, l.period()).build();
        }).toList();
    }
}
