package com.civicbrain.notifications.channel;

/**
 * One delivery channel of the dispatcher (docs/02_ARCHITECTURE.md §5): EMAIL now, WHATSAPP through the {@code log}
 * provider until the Twilio sandbox (P16). {@link #send} returns the provider's message id; it throws
 * {@link PermanentFailure} when a retry cannot help (bad address/number) and any other exception for a retry.
 */
public interface NotificationChannel {

    /** {@code notifications.channel}. */
    String channel();

    /** {@code notifications.provider} (rule 7). */
    String provider();

    String send(Message message);

    /** What the dispatcher stored when it planned the notification. */
    record Message(long notificationId, String destination, String subject, String body) {
    }

    /** A provider refusal that a retry cannot fix (12 §4: 4xx → FAILED without retry). */
    class PermanentFailure extends RuntimeException {
        public PermanentFailure(String message, Throwable cause) {
            super(message, cause);
        }
    }
}
