package com.civicbrain.notifications.service;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import com.civicbrain.notifications.repo.NotificationRepository;
import com.civicbrain.notifications.repo.NotificationRepository.NewNotification;
import com.civicbrain.notifications.repo.NotificationRepository.OutboxRow;
import com.civicbrain.notifications.repo.NotificationRepository.Recipient;
import com.civicbrain.notifications.repo.NotificationRepository.Template;
import com.civicbrain.notifications.service.TemplateRenderer.Mode;

/**
 * Turns one outbox row into notification rows (docs/02_ARCHITECTURE.md §5 Notify): rule 1 status events → the
 * template of that status per channel and {@code fn_complaint_notification_recipients} (no template, e.g. VERIFIED
 * or SCHEDULED → no rows); rule 2 ACTION_PLAN_ASSIGNED → the plan's contractor login; rule 3 COMPLETION_SUBMITTED →
 * the officer who assigned the plan; rule 4 OTP and the other event types never produce messages here; rule 5 e-mail
 * only with {@code email_opt_in} and an address, WhatsApp only with {@code whatsapp_opt_in} and a phone. Each row
 * is rendered now (subject as text, e-mail body HTML-escaped, WhatsApp body as text) with dedupe key
 * {@code outbox_id:user_id:channel}; a template that cannot be rendered gives a FAILED row (no retry) instead.
 */
@Component
public class NotificationPlanner {

    private static final Logger log = LoggerFactory.getLogger(NotificationPlanner.class);

    private final NotificationRepository repo;
    private final TemplateRenderer renderer;
    private final PlaceholderValues values;

    public NotificationPlanner(NotificationRepository repo, TemplateRenderer renderer, PlaceholderValues values) {
        this.repo = repo;
        this.renderer = renderer;
        this.values = values;
    }

    public List<NewNotification> plan(OutboxRow row, Instant now) {
        List<Template> templates;
        List<Recipient> recipients;
        switch (row.eventType()) {
            case "COMPLAINT_STATUS_CHANGED" -> {
                if (row.complaintId() == null || row.eventStatus() == null) {
                    return List.of();
                }
                templates = repo.templatesForStatus(row.eventStatus());
                recipients = templates.isEmpty() ? List.of() : repo.complaintRecipients(row.complaintId(), row.createdAt());
            }
            case "ACTION_PLAN_ASSIGNED" -> {
                if (row.actionPlanId() == null) {
                    return List.of();
                }
                templates = repo.templatesByCode("ACTION_PLAN_ASSIGNED");
                recipients = repo.planContractor(row.actionPlanId());
            }
            case "COMPLETION_SUBMITTED" -> {
                if (row.actionPlanId() == null) {
                    return List.of();
                }
                templates = repo.templatesByCode("COMPLETION_SUBMITTED");
                recipients = repo.planAssigner(row.actionPlanId());
            }
            default -> {
                log.warn("outbox row {} has event type {} - no messages are sent for it", row.outboxId(), row.eventType());
                return List.of();
            }
        }
        if (templates.isEmpty() || recipients.isEmpty()) {
            return List.of();
        }
        NotificationRepository.Facts facts = repo.facts(row.complaintId(), row.actionPlanId(), row.contractorId());
        List<NewNotification> out = new ArrayList<>();
        for (Recipient r : recipients) {
            if (!r.active()) {
                continue;
            }
            Map<String, String> v = values.of(facts, r, row.remarks());
            for (Template t : templates) {
                String destination = destination(t.channel(), r);
                if (destination == null) {
                    continue;
                }
                String dedupe = row.outboxId() + ":" + r.userId() + ":" + t.channel();
                try {
                    String subject = t.subject() == null ? null : renderer.render(t.subject(), v, Mode.TEXT);
                    String body = renderer.render(t.body(), v, "EMAIL".equals(t.channel()) ? Mode.HTML : Mode.TEXT);
                    out.add(new NewNotification(row.outboxId(), r.userId(), row.complaintId(), t.channel(), t.code(), destination,
                            subject, body, "QUEUED", null, now, dedupe, now));
                } catch (TemplateRenderer.TemplateException e) {
                    log.warn("template {}/{} for outbox row {} not rendered: {}", t.code(), t.channel(), row.outboxId(), e.getMessage());
                    out.add(new NewNotification(row.outboxId(), r.userId(), row.complaintId(), t.channel(), t.code(), destination,
                            null, null, "FAILED", "template error: " + e.getMessage(), null, dedupe, now));
                }
            }
        }
        return out;
    }

    /** Rule 5: the address for this channel, or null when the user did not opt in / has none. */
    static String destination(String channel, Recipient r) {
        return switch (channel) {
            case "EMAIL" -> r.emailOptIn() && r.email() != null && !r.email().isBlank() ? r.email() : null;
            case "WHATSAPP" -> r.whatsappOptIn() && r.phone() != null && !r.phone().isBlank() ? r.phone() : null;
            default -> null;
        };
    }
}
