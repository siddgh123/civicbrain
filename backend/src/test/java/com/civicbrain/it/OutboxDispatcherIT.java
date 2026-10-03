package com.civicbrain.it;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import com.civicbrain.it.support.ComplaintItSupport;
import com.civicbrain.it.support.IntegrationTest;
import com.civicbrain.it.support.MailpitClient.Mail;
import com.civicbrain.notifications.service.OutboxDispatcher;
import com.civicbrain.users.model.Role;
import com.civicbrain.workflow.Actor;
import com.civicbrain.workflow.ActorRole;
import com.civicbrain.workflow.ComplaintStatus;

/**
 * The outbox dispatcher (docs/02_ARCHITECTURE.md §5 rules 1-7 and 10; FR-50 e-mail, FR-51, FR-52) against the Mailpit
 * container. The scheduler is off in profile test, so each test runs the dispatcher itself until nothing is left.
 */
@IntegrationTest
class OutboxDispatcherIT extends ComplaintItSupport {

    @Autowired
    OutboxDispatcher dispatcher;

    @Test
    void submittedSendsExactlyOneMailToTheOwnerAndASecondRunSendsNothingNew() throws Exception {
        Citizen a = citizen();
        long id = submitOk(a, "Pothole").path("complaintId").asLong();
        String ref = "CB-%06d".formatted(id);
        long outboxId = jdbc.sql("SELECT outbox_id FROM notification_outbox WHERE complaint_id = :id AND event_status = 'SUBMITTED'")
                .param("id", id).query(Long.class).single();

        drain();
        List<Mail> mails = mailpit.await(a.email(), 1);
        assertThat(mails).hasSize(1);
        Mail mail = mails.get(0);
        assertThat(mail.subject()).isEqualTo("CivicBrain: complaint " + ref + " received");
        assertThat(mail.text()).contains("Dear IT CITIZEN").contains(ref).contains("(Pothole)").contains("Near the temple")
                .doesNotContain("{{").contains("Talegaon Dabhade Municipal Council");
        Map<String, Object> n = jdbc.sql("""
                SELECT status, provider, channel, template_code, destination, dedupe_key, attempt_count, sent_at IS NOT NULL AS sent,
                       provider_message_id IS NOT NULL AS has_id, complaint_id
                  FROM notifications WHERE outbox_id = :o""").param("o", outboxId).query().singleRow();
        assertThat(n).containsEntry("status", "SENT").containsEntry("provider", "INTERNAL").containsEntry("channel", "EMAIL")
                .containsEntry("template_code", "COMPLAINT_SUBMITTED").containsEntry("destination", a.email())
                .containsEntry("dedupe_key", outboxId + ":" + a.id() + ":EMAIL").containsEntry("sent", true)
                .containsEntry("has_id", true).containsEntry("complaint_id", id);
        assertThat(((Number) n.get("attempt_count")).intValue()).isEqualTo(1);
        assertThat(jdbc.sql("SELECT processed_at IS NOT NULL FROM notification_outbox WHERE outbox_id = :o").param("o", outboxId)
                .query(Boolean.class).single()).isTrue();

        drain();
        Thread.sleep(500);
        assertThat(mailpit.to(a.email())).hasSize(1);
        assertThat(count("SELECT count(*) FROM notifications WHERE outbox_id = :o", outboxId)).isEqualTo(1);
    }

    @Test
    void aStatusWithoutTemplateIsProcessedWithoutNotifications() throws Exception {
        Citizen a = citizen();
        Citizen officer = staff(Role.OFFICER);
        long id = submitOk(a, "Road Damage").path("complaintId").asLong();
        workflow.changeStatus(id, ComplaintStatus.REJECTED, Actor.user(officer.id(), ActorRole.OFFICER), "Duplicate photo of an old issue");
        workflow.changeStatus(id, ComplaintStatus.VERIFIED, Actor.user(officer.id(), ActorRole.OFFICER), "Restored after review");
        long verifiedOutbox = jdbc.sql("SELECT outbox_id FROM notification_outbox WHERE complaint_id = :id AND event_status = 'VERIFIED'")
                .param("id", id).query(Long.class).single();

        drain();
        assertThat(jdbc.sql("SELECT processed_at IS NOT NULL FROM notification_outbox WHERE outbox_id = :o").param("o", verifiedOutbox)
                .query(Boolean.class).single()).isTrue();
        assertThat(count("SELECT count(*) FROM notifications WHERE outbox_id = :o", verifiedOutbox)).isZero();
        List<Mail> mails = mailpit.await(a.email(), 2);
        assertThat(mails).extracting(Mail::subject).containsExactlyInAnyOrder(
                "CivicBrain: complaint CB-%06d received".formatted(id),
                "CivicBrain: complaint CB-%06d could not be accepted".formatted(id));
        assertThat(mails).filteredOn(m -> m.subject().contains("could not be accepted")).singleElement()
                .satisfies(m -> assertThat(m.text()).contains("Reason: Duplicate photo of an old issue."));
    }

    @Test
    void ownersOfMergedChildrenGetTheMastersMailsOncePerChannelAndOptInIsRespected() throws Exception {
        Citizen a = citizen();
        Citizen b = citizen();
        Citizen c = citizen();
        Citizen officer = staff(Role.OFFICER);
        long master = submitOk(a, "Pothole").path("complaintId").asLong();
        long childB = submitOk(b, "Pothole").path("complaintId").asLong();
        long childC = submitOk(c, "Pothole").path("complaintId").asLong();
        for (long child : new long[] {childB, childC}) {
            jdbc.sql("UPDATE complaints SET master_complaint_id = :m WHERE complaint_id = :c").param("m", master).param("c", child).update();
            move(child, officer.id(), ComplaintStatus.MERGED);
        }
        // c: no e-mail, WhatsApp on (log provider in profile test)
        jdbc.sql("UPDATE users SET email_opt_in = false, whatsapp_opt_in = true WHERE user_id = :u").param("u", c.id()).update();
        drain();

        workflow.changeStatus(master, ComplaintStatus.REJECTED, Actor.user(officer.id(), ActorRole.OFFICER), "Outside council work");
        long rejected = jdbc.sql("SELECT outbox_id FROM notification_outbox WHERE complaint_id = :id AND event_status = 'REJECTED'")
                .param("id", master).query(Long.class).single();
        drain();
        drain();

        String masterRef = "CB-%06d".formatted(master);
        List<Mail> forB = mailpit.await(b.email(), 3);
        assertThat(forB).extracting(Mail::subject).containsExactlyInAnyOrder(
                "CivicBrain: complaint CB-%06d received".formatted(childB),
                "CivicBrain: complaint CB-%06d linked to an existing complaint".formatted(childB),
                "CivicBrain: complaint " + masterRef + " could not be accepted");
        assertThat(forB).filteredOn(m -> m.subject().contains("linked")).singleElement()
                .satisfies(m -> assertThat(m.text()).contains("already registered as " + masterRef));
        assertThat(mailpit.await(a.email(), 2)).extracting(Mail::subject).containsExactlyInAnyOrder(
                "CivicBrain: complaint " + masterRef + " received", "CivicBrain: complaint " + masterRef + " could not be accepted");
        assertThat(mailpit.to(c.email())).as("e-mail opt-out").isEmpty();

        List<Map<String, Object>> rows = jdbc.sql("""
                SELECT user_id, channel, status, provider FROM notifications WHERE outbox_id = :o ORDER BY user_id, channel""")
                .param("o", rejected).query().listOfRows();
        assertThat(rows).hasSize(3);
        assertThat(rows).filteredOn(r -> r.get("user_id").equals(c.id())).singleElement()
                .satisfies(r -> assertThat(r).containsEntry("channel", "WHATSAPP").containsEntry("status", "SENT")
                        .containsEntry("provider", "INTERNAL"));
        assertThat(rows).filteredOn(r -> !r.get("user_id").equals(c.id())).allSatisfy(r -> assertThat(r)
                .containsEntry("channel", "EMAIL").containsEntry("status", "SENT"));
        assertThat(jdbc.sql("SELECT rendered_body FROM notifications WHERE outbox_id = :o AND channel = 'WHATSAPP'")
                .param("o", rejected).query(String.class).single()).isEqualTo("Complaint " + masterRef + " was not accepted. Reason: Outside council work");
    }

    @Test
    void planAssignedGoesToTheContractorAndCompletionToTheAssigningOfficer() throws Exception {
        Citizen contractor = staff(Role.CONTRACTOR);
        Citizen officer = staff(Role.OFFICER);
        Citizen a = citizen();
        long complaint = submitOk(a, "Pothole").path("complaintId").asLong();
        long firm = jdbc.sql("""
                INSERT INTO contractors (user_id, firm_name, contact_person, phone)
                VALUES (:u, 'Indrayani Roads (prototype)', 'IT contact', :p) RETURNING contractor_id""")
                .param("u", contractor.id()).param("p", uniquePhone()).query(Long.class).single();
        String planCode = "AP-IT-" + UUID.randomUUID().toString().substring(0, 8);
        long plan = jdbc.sql("""
                INSERT INTO action_plans (plan_code, work_type_code, planned_date, status, contractor_id, job_count,
                                          assigned_by_user_id, assigned_at)
                VALUES (:code, 'ROAD', :d, 'ASSIGNED', :k, 3, :officer, now()) RETURNING action_plan_id""")
                .param("code", planCode).param("d", LocalDate.of(2026, 10, 6)).param("k", firm).param("officer", officer.id())
                .query(Long.class).single();
        jdbc.sql("INSERT INTO notification_outbox (event_type, action_plan_id) VALUES ('ACTION_PLAN_ASSIGNED', :p)").param("p", plan).update();
        jdbc.sql("""
                INSERT INTO notification_outbox (event_type, complaint_id, action_plan_id)
                VALUES ('COMPLETION_SUBMITTED', :c, :p)""").param("c", complaint).param("p", plan).update();
        drain();

        Mail planMail = mailpit.await(contractor.email(), 1).get(0);
        assertThat(planMail.subject()).isEqualTo("CivicBrain: new action plan " + planCode);
        assertThat(planMail.text()).contains("Dear Indrayani Roads (prototype)").contains("3 jobs").contains("6 Oct 2026")
                .contains("http://localhost:5173/contractor/plans/" + plan);
        Mail review = mailpit.await(officer.email(), 1).get(0);
        assertThat(review.subject()).isEqualTo("CivicBrain: completion proof submitted for CB-%06d".formatted(complaint));
        assertThat(review.text()).contains("Contractor Indrayani Roads (prototype)")
                .contains("http://localhost:5173/officer/complaints/" + complaint);
    }

    // ------------------------------------------------------------------ helpers

    /** Runs the dispatcher until a run finds nothing to do (other tests' rows are processed as well). */
    private void drain() {
        for (int i = 0; i < 50; i++) {
            OutboxDispatcher.RunResult r = dispatcher.dispatchOnce();
            if (r.outboxProcessed() == 0 && r.sent() == 0 && r.failed() == 0) {
                return;
            }
        }
        throw new AssertionError("the dispatcher did not finish");
    }

    private long count(String sql, long id) {
        return jdbc.sql(sql).param("o", id).query(Long.class).single();
    }
}
