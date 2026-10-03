package com.civicbrain.notifications.repo;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

import com.civicbrain.common.Db;

/**
 * {@code notification_outbox}, {@code notification_templates} and {@code notifications} for the dispatcher
 * (docs/02_ARCHITECTURE.md §5 Notify, 12 §5). Outbox rows and due notifications are locked with
 * {@code FOR UPDATE SKIP LOCKED}, so two dispatchers never take the same row; {@code dedupe_key} is unique, so an
 * (event, recipient, channel) gets at most one row.
 */
@Repository
public class NotificationRepository {

    public record OutboxRow(long outboxId, String eventType, Long complaintId, Long actionPlanId, String eventStatus,
                            String remarks, Long contractorId, int attemptCount, Instant createdAt) {
    }

    public record Template(String code, String channel, String subject, String body) {
    }

    /** A user who may receive a message (owner, merged-child owner, contractor, officer). */
    public record Recipient(long userId, String fullName, String email, String phone, boolean emailOptIn, boolean whatsappOptIn,
                            boolean active) {
    }

    /** Facts of a complaint and/or plan for the placeholder values. */
    public record Facts(Long complaintId, String publicRef, String category, String landmark, String addressText, Integer wardNumber,
                        Instant submittedAt, String masterRef, String contractorName, Long actionPlanId, String planCode,
                        Integer jobCount, LocalDate plannedDate, String inspectionNotes, LocalDate expectedCompletion) {
    }

    public record NewNotification(long outboxId, long userId, Long complaintId, String channel, String templateCode,
                                  String destination, String subject, String body, String status, String lastError,
                                  Instant nextAttemptAt, String dedupeKey, Instant now) {
    }

    /** A notification claimed for sending (status SENDING, attempt counted). */
    public record Due(long notificationId, String channel, String destination, String subject, String body, int attemptCount) {
    }

    private final JdbcClient jdbc;

    public NotificationRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    // ------------------------------------------------------------------ outbox

    public List<Long> pendingOutboxIds(int limit) {
        return jdbc.sql("""
                SELECT outbox_id FROM notification_outbox WHERE processed_at IS NULL
                 ORDER BY created_at, outbox_id LIMIT :limit""")
                .param("limit", limit).query(Long.class).list();
    }

    /** The row if it is still unprocessed and no other dispatcher holds it. */
    public Optional<OutboxRow> lockOutbox(long outboxId) {
        return jdbc.sql("""
                SELECT outbox_id, event_type, complaint_id, action_plan_id, event_status, payload ->> 'remarks' AS remarks,
                       (payload ->> 'contractor_id')::bigint AS contractor_id, attempt_count, created_at
                  FROM notification_outbox WHERE outbox_id = :id AND processed_at IS NULL
                   FOR UPDATE SKIP LOCKED""")
                .param("id", outboxId)
                .query((rs, n) -> new OutboxRow(rs.getLong("outbox_id"), rs.getString("event_type"), nullableLong(rs, "complaint_id"),
                        nullableLong(rs, "action_plan_id"), rs.getString("event_status"), rs.getString("remarks"),
                        nullableLong(rs, "contractor_id"), rs.getInt("attempt_count"), Db.instant(rs, "created_at")))
                .optional();
    }

    public void markOutboxProcessed(long outboxId, Instant now) {
        jdbc.sql("UPDATE notification_outbox SET processed_at = :now, attempt_count = attempt_count + 1, last_error = NULL WHERE outbox_id = :id")
                .param("now", Db.ts(now)).param("id", outboxId).update();
    }

    /** One more failed attempt; after {@code maxAttempts} the row is closed (processed) with the error kept. */
    public void markOutboxFailed(long outboxId, String error, int maxAttempts, Instant now) {
        jdbc.sql("""
                UPDATE notification_outbox
                   SET attempt_count = attempt_count + 1, last_error = :error,
                       processed_at = CASE WHEN attempt_count + 1 >= :max THEN :now ELSE NULL END
                 WHERE outbox_id = :id AND processed_at IS NULL""")
                .param("error", error).param("max", maxAttempts).param("now", Db.ts(now)).param("id", outboxId).update();
    }

    // ------------------------------------------------------------------ templates, recipients, facts

    public List<Template> templatesForStatus(String eventStatus) {
        return jdbc.sql("""
                SELECT template_code, channel, subject, body FROM notification_templates
                 WHERE event_status = :status AND locale = 'en' AND is_active ORDER BY channel""")
                .param("status", eventStatus).query(NotificationRepository::template).list();
    }

    public List<Template> templatesByCode(String code) {
        return jdbc.sql("""
                SELECT template_code, channel, subject, body FROM notification_templates
                 WHERE template_code = :code AND locale = 'en' AND is_active ORDER BY channel""")
                .param("code", code).query(NotificationRepository::template).list();
    }

    /**
     * Rule 1: {@code fn_complaint_notification_recipients} (owner + owners of merged children), one row per user. The
     * function is evaluated when the dispatcher runs, so a child owner is kept only for events from the child's merge
     * on (its MERGED history row at or before the event): the master's own earlier SUBMITTED mail ("your complaint ...
     * was received") must not reach a citizen whose report was linked to it a few seconds later.
     */
    public List<Recipient> complaintRecipients(long complaintId, Instant eventAt) {
        return jdbc.sql("""
                SELECT u.user_id, u.full_name, u.email, u.phone, u.email_opt_in, u.whatsapp_opt_in, u.is_active
                  FROM users u
                 WHERE u.user_id IN (
                       SELECT r.user_id FROM fn_complaint_notification_recipients(:id) r
                        WHERE r.relation = 'OWNER'
                           OR EXISTS (SELECT 1 FROM complaint_status_history h
                                       WHERE h.complaint_id = r.complaint_id AND h.new_status = 'MERGED'
                                         AND h.changed_at <= :eventAt))
                 ORDER BY u.user_id""")
                .param("id", complaintId).param("eventAt", Db.ts(eventAt)).query(NotificationRepository::recipient).list();
    }

    /** Rule 2: the login of the plan's contractor firm. */
    public List<Recipient> planContractor(long actionPlanId) {
        return jdbc.sql("""
                SELECT u.user_id, u.full_name, u.email, u.phone, u.email_opt_in, u.whatsapp_opt_in, u.is_active
                  FROM action_plans p JOIN contractors k ON k.contractor_id = p.contractor_id JOIN users u ON u.user_id = k.user_id
                 WHERE p.action_plan_id = :id""")
                .param("id", actionPlanId).query(NotificationRepository::recipient).list();
    }

    /** Rule 3: the officer who assigned the plan. */
    public List<Recipient> planAssigner(long actionPlanId) {
        return jdbc.sql("""
                SELECT u.user_id, u.full_name, u.email, u.phone, u.email_opt_in, u.whatsapp_opt_in, u.is_active
                  FROM action_plans p JOIN users u ON u.user_id = p.assigned_by_user_id
                 WHERE p.action_plan_id = :id""")
                .param("id", actionPlanId).query(NotificationRepository::recipient).list();
    }

    /**
     * The facts behind the placeholders: complaint (optional), plan = the outbox row's plan or the complaint's
     * current plan, contractor = the payload's, else the plan's, else the complaint's; the latest site inspection.
     */
    public Facts facts(Long complaintId, Long actionPlanId, Long contractorId) {
        return jdbc.sql("""
                SELECT c.complaint_id, c.public_ref, cat.category_name, c.landmark, c.address_text, w.ward_number, c.submitted_at,
                       m.public_ref AS master_ref, k.firm_name, ap.action_plan_id, ap.plan_code, ap.job_count, ap.planned_date,
                       si.findings, si.expected_completion_date
                  FROM (SELECT 1) one
                  LEFT JOIN complaints c ON c.complaint_id = :complaintId
                  LEFT JOIN complaint_categories cat ON cat.category_id = c.category_id
                  LEFT JOIN wards w ON w.ward_id = c.ward_id
                  LEFT JOIN complaints m ON m.complaint_id = c.master_complaint_id
                  LEFT JOIN action_plans ap ON ap.action_plan_id = coalesce(:planId, c.current_action_plan_id)
                  LEFT JOIN contractors k ON k.contractor_id = coalesce(:contractorId, ap.contractor_id, c.assigned_contractor_id)
                  LEFT JOIN LATERAL (
                        SELECT s.findings, s.expected_completion_date FROM site_inspections s
                         WHERE s.complaint_id = c.complaint_id ORDER BY s.inspected_at DESC, s.inspection_id DESC LIMIT 1) si ON true""")
                .param("complaintId", complaintId).param("planId", actionPlanId).param("contractorId", contractorId)
                .query((rs, n) -> new Facts(nullableLong(rs, "complaint_id"), rs.getString("public_ref"), rs.getString("category_name"),
                        rs.getString("landmark"), rs.getString("address_text"), (Integer) rs.getObject("ward_number"),
                        Db.instant(rs, "submitted_at"), rs.getString("master_ref"), rs.getString("firm_name"),
                        nullableLong(rs, "action_plan_id"), rs.getString("plan_code"), (Integer) rs.getObject("job_count"),
                        rs.getObject("planned_date", LocalDate.class), rs.getString("findings"),
                        rs.getObject("expected_completion_date", LocalDate.class)))
                .single();
    }

    // ------------------------------------------------------------------ notifications

    /** Inserts unless a row with the same dedupe key exists; true when inserted. */
    public boolean insert(NewNotification n) {
        return jdbc.sql("""
                INSERT INTO notifications (outbox_id, user_id, complaint_id, channel, template_code, destination, rendered_subject,
                                           rendered_body, status, last_error, next_attempt_at, dedupe_key, created_at)
                VALUES (:outboxId, :userId, :complaintId, :channel, :code, :destination, :subject, :body, :status, :error, :next,
                        :dedupe, :now)
                ON CONFLICT (dedupe_key) DO NOTHING""")
                .param("outboxId", n.outboxId()).param("userId", n.userId()).param("complaintId", n.complaintId())
                .param("channel", n.channel()).param("code", n.templateCode()).param("destination", n.destination())
                .param("subject", n.subject()).param("body", n.body()).param("status", n.status()).param("error", n.lastError())
                .param("next", Db.ts(n.nextAttemptAt())).param("dedupe", n.dedupeKey()).param("now", Db.ts(n.now()))
                .update() == 1;
    }

    /**
     * Claims up to {@code limit} due rows (QUEUED, or FAILED with a retry time that has come) for sending: status
     * SENDING, attempt counted, {@code next_attempt_at} = claim time (used to find interrupted sends).
     */
    public List<Due> claimDue(int limit, int maxAttempts, Instant now) {
        return jdbc.sql("""
                WITH due AS (
                    SELECT notification_id FROM notifications
                     WHERE status IN ('QUEUED', 'FAILED') AND next_attempt_at <= :now AND attempt_count < :max
                     ORDER BY next_attempt_at, notification_id
                     LIMIT :limit
                       FOR UPDATE SKIP LOCKED)
                UPDATE notifications n
                   SET status = 'SENDING', attempt_count = n.attempt_count + 1, next_attempt_at = :now
                  FROM due WHERE n.notification_id = due.notification_id
                RETURNING n.notification_id, n.channel, n.destination, n.rendered_subject, n.rendered_body, n.attempt_count""")
                .param("now", Db.ts(now)).param("max", maxAttempts).param("limit", limit)
                .query((rs, row) -> new Due(rs.getLong("notification_id"), rs.getString("channel"), rs.getString("destination"),
                        rs.getString("rendered_subject"), rs.getString("rendered_body"), rs.getInt("attempt_count")))
                .list();
    }

    public void markSent(long notificationId, String provider, String providerMessageId, Instant now) {
        jdbc.sql("""
                UPDATE notifications SET status = 'SENT', provider = :provider, provider_message_id = :messageId, sent_at = :now,
                                         next_attempt_at = NULL, last_error = NULL
                 WHERE notification_id = :id""")
                .param("provider", provider).param("messageId", providerMessageId).param("now", Db.ts(now)).param("id", notificationId)
                .update();
    }

    /** FAILED; with {@code nextAttemptAt} it is retried then, without it the failure is final. */
    public void markFailed(long notificationId, String provider, String error, Instant nextAttemptAt) {
        jdbc.sql("""
                UPDATE notifications SET status = 'FAILED', provider = coalesce(:provider, provider), last_error = :error,
                                         next_attempt_at = :next
                 WHERE notification_id = :id""")
                .param("provider", provider).param("error", error).param("next", Db.ts(nextAttemptAt)).param("id", notificationId)
                .update();
    }

    /**
     * Rows left in SENDING (the process stopped during a send) are closed as FAILED without a retry: the message may
     * already have gone out, and each (event, recipient, channel) is sent at most once (FR-51).
     */
    public int closeInterruptedSends(Instant claimedBefore) {
        return jdbc.sql("""
                UPDATE notifications SET status = 'FAILED', next_attempt_at = NULL,
                                         last_error = 'interrupted while sending; not retried (at most once)'
                 WHERE status = 'SENDING' AND next_attempt_at < :before""")
                .param("before", Db.ts(claimedBefore)).update();
    }

    // ------------------------------------------------------------------ mapping

    private static Template template(ResultSet rs, int row) throws SQLException {
        return new Template(rs.getString("template_code"), rs.getString("channel"), rs.getString("subject"), rs.getString("body"));
    }

    private static Recipient recipient(ResultSet rs, int row) throws SQLException {
        return new Recipient(rs.getLong("user_id"), rs.getString("full_name"), rs.getString("email"), rs.getString("phone"),
                rs.getBoolean("email_opt_in"), rs.getBoolean("whatsapp_opt_in"), rs.getBoolean("is_active"));
    }

    private static Long nullableLong(ResultSet rs, String column) throws SQLException {
        long value = rs.getLong(column);
        return rs.wasNull() ? null : value;
    }
}
