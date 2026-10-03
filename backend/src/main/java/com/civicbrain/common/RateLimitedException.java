package com.civicbrain.common;

/** 429 RATE_LIMITED; the error advice and the filters add {@code Retry-After: <seconds>} (docs/04_API_CONTRACT.md §11). */
public class RateLimitedException extends ApiException {

    private final long retryAfterSeconds;

    public RateLimitedException(long retryAfterSeconds) {
        super(ErrorCode.RATE_LIMITED, "Too many requests. Please wait " + retryAfterSeconds + " seconds.");
        this.retryAfterSeconds = retryAfterSeconds;
    }

    public long retryAfterSeconds() {
        return retryAfterSeconds;
    }
}
