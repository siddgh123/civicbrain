package com.civicbrain.notifications.channel;

import java.util.UUID;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import com.civicbrain.common.Masking;
import com.civicbrain.config.WhatsAppProperties;

/**
 * WhatsApp provider {@code log} (docs/02_ARCHITECTURE.md §6-§7, 09_7DAY §2.3): the message is not sent anywhere;
 * one log line with the notification id, the masked number and the length (never the text or the full number).
 * Provider INTERNAL (rule 7). The Twilio sandbox channel comes with P16; until then every provider logs only.
 */
@Component
public class LogWhatsAppChannel implements NotificationChannel {

    private static final Logger log = LoggerFactory.getLogger(LogWhatsAppChannel.class);

    public LogWhatsAppChannel(WhatsAppProperties whatsapp) {
        if (!"log".equals(whatsapp.provider())) {
            log.warn("WHATSAPP_PROVIDER={} is not built yet (P16): WhatsApp messages are only logged", whatsapp.provider());
        }
    }

    @Override
    public String channel() {
        return "WHATSAPP";
    }

    @Override
    public String provider() {
        return "INTERNAL";
    }

    @Override
    public String send(Message message) {
        log.info("whatsapp (log provider): notification {} to {} ({} characters)", message.notificationId(),
                Masking.phone(message.destination()), message.body() == null ? 0 : message.body().length());
        return "log-" + UUID.randomUUID();
    }
}
