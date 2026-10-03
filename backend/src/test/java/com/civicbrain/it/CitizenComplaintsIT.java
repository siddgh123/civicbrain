package com.civicbrain.it;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MvcResult;

import com.civicbrain.it.support.ComplaintItSupport;
import com.civicbrain.it.support.IntegrationTest;
import com.civicbrain.users.model.Role;
import com.civicbrain.workflow.ComplaintStatus;

import tools.jackson.databind.JsonNode;

/**
 * Citizen views (docs/04 §5, FR-13, FR-15) and photo download (04 §4): own list/detail with timeline, images,
 * contractor name, planned date and the master's number; feedback upsert with "not fixed" → REOPENED through
 * the DB rules; ownership inside every query - another citizen gets 404 for the complaint, its photo and its
 * feedback (07 §2; 03-testing "other user → 404"). Photos: owner, officer in scope, assigned contractor, admin.
 */
@IntegrationTest
class CitizenComplaintsIT extends ComplaintItSupport {

    @Test
    void theListShowsOnlyOwnComplaintsNewestFirst() throws Exception {
        Citizen a = citizen();
        Citizen b = citizen();
        long first = submitOk(a, "Pothole").path("complaintId").asLong();
        long second = submitOk(a, "Garbage Accumulation").path("complaintId").asLong();
        submitOk(b, "Road Damage");

        JsonNode list = getOk(a, "/api/v1/citizen/complaints");
        assertThat(list.path("totalItems").asLong()).isEqualTo(2);
        assertThat(list.path("page").asInt()).isZero();
        assertThat(list.path("size").asInt()).isEqualTo(20);
        assertThat(list.path("totalPages").asInt()).isEqualTo(1);
        JsonNode top = list.path("items").path(0);
        assertThat(top.path("complaintId").asLong()).isEqualTo(second);
        assertThat(list.path("items").path(1).path("complaintId").asLong()).isEqualTo(first);
        assertThat(top.path("publicRef").asString()).isEqualTo("CB-%06d".formatted(second));
        assertThat(top.path("title").asString()).isEqualTo("Deep pothole near the temple");
        assertThat(top.path("categoryName").asString()).isEqualTo("Garbage Accumulation");
        assertThat(top.path("status").asString()).isEqualTo("SUBMITTED");
        assertThat(top.path("wardNumber").asInt()).isEqualTo(1);
        assertThat(OffsetDateTime.parse(top.path("submittedAt").asString()).getOffset()).isEqualTo(ZoneOffset.ofHoursMinutes(5, 30));
        assertThat(top.path("thumbnailImageId").asLong()).isPositive();

        assertThat(getOk(a, "/api/v1/citizen/complaints?status=CLOSED").path("totalItems").asLong()).isZero();
        assertThat(getOk(a, "/api/v1/citizen/complaints?status=SUBMITTED&page=0&size=1").path("items").size()).isEqualTo(1);
        assertThat(fetch(a, "/api/v1/citizen/complaints?status=NOPE").getResponse().getStatus()).isEqualTo(400);
        assertThat(fetch(a, "/api/v1/citizen/complaints?size=101").getResponse().getStatus()).isEqualTo(400);
    }

    @Test
    void detailHasImagesTimelineAndAnotherCitizenGets404ForComplaintPhotoAndFeedback() throws Exception {
        Citizen a = citizen();
        Citizen b = citizen();
        long id = submitOk(a, "Pothole").path("complaintId").asLong();

        JsonNode d = getOk(a, "/api/v1/citizen/complaints/" + id);
        assertThat(d.path("publicRef").asString()).isEqualTo("CB-%06d".formatted(id));
        assertThat(d.path("description").asString()).startsWith("Large pothole");
        assertThat(d.path("landmark").asString()).isEqualTo("Near the temple");
        assertThat(d.path("latitude").asDouble()).isEqualTo(IN_LAT);
        assertThat(d.path("longitude").asDouble()).isEqualTo(IN_LON);
        assertThat(d.path("canGiveFeedback").asBoolean()).isFalse();
        assertThat(d.path("contractorName").isMissingNode() || d.path("contractorName").isNull()).isTrue();
        assertThat(d.path("timeline")).hasSize(1);
        assertThat(d.path("timeline").path(0).path("status").asString()).isEqualTo("SUBMITTED");
        assertThat(d.path("images")).hasSize(1);
        assertThat(d.path("images").path(0).path("role").asString()).isEqualTo("CITIZEN_EVIDENCE");
        long imageId = d.path("images").path(0).path("imageId").asLong();

        assertNotFound(fetch(b, "/api/v1/citizen/complaints/" + id));
        assertNotFound(fetch(a, "/api/v1/citizen/complaints/99999999"));
        assertNotFound(fetch(b, "/api/v1/files/" + imageId));
        assertNotFound(mvc.perform(postJson("/api/v1/citizen/complaints/" + id + "/feedback", Map.of("isResolved", true))
                .with(bearer(b.token()))).andReturn());

        MvcResult photo = fetch(a, "/api/v1/files/" + imageId);
        assertThat(photo.getResponse().getStatus()).isEqualTo(200);
        assertThat(photo.getResponse().getContentType()).isEqualTo("image/jpeg");
        assertThat(photo.getResponse().getHeader("Cache-Control")).isEqualTo("private, max-age=300");
        byte[] bytes = photo.getResponse().getContentAsByteArray();
        assertThat(bytes[0]).isEqualTo((byte) 0xFF);
        assertThat(bytes[1]).isEqualTo((byte) 0xD8);
        assertNotFound(fetch(a, "/api/v1/files/99999999"));
        assertThat(mvc.perform(get("/api/v1/files/" + imageId)).andReturn().getResponse().getStatus()).isEqualTo(401);
    }

    @Test
    void photosAreVisibleToTheAdminTheOfficerInScopeAndTheAssignedContractorOnly() throws Exception {
        Citizen owner = citizen();
        long id = submitOk(owner, "Pothole").path("complaintId").asLong();
        long imageId = jdbc.sql("SELECT image_id FROM complaint_images WHERE complaint_id = :id").param("id", id).query(Long.class).single();
        String path = "/api/v1/files/" + imageId;

        assertThat(fetch(staff(Role.ADMIN), path).getResponse().getStatus()).isEqualTo(200);

        Citizen wardOfficer = officerWithScope(1, null);
        Citizen roadOfficer = officerWithScope(null, "ROAD");
        Citizen otherWard = officerWithScope(2, null);
        Citizen garbageOfficer = officerWithScope(null, "GARBAGE");
        Citizen noScope = officerWithScope(null, null);
        jdbc.sql("DELETE FROM officer_scopes WHERE officer_id = (SELECT officer_id FROM officers WHERE user_id = :u)")
                .param("u", noScope.id()).update();
        assertThat(fetch(wardOfficer, path).getResponse().getStatus()).isEqualTo(200);
        assertThat(fetch(roadOfficer, path).getResponse().getStatus()).isEqualTo(200);
        assertNotFound(fetch(otherWard, path));
        assertNotFound(fetch(garbageOfficer, path));
        assertNotFound(fetch(noScope, path));

        Citizen contractor = staff(Role.CONTRACTOR);
        long firm = contractorFirm(contractor.id(), "IT Roads (prototype)");
        assertNotFound(fetch(contractor, path));
        long plan = assignedPlan(firm, id, "ASSIGNED", LocalDate.of(2026, 10, 5));
        assertThat(fetch(contractor, path).getResponse().getStatus()).isEqualTo(200);
        Citizen otherFirm = staff(Role.CONTRACTOR);
        contractorFirm(otherFirm.id(), "IT Other Firm (prototype)");
        assertNotFound(fetch(otherFirm, path));
        jdbc.sql("UPDATE action_plan_items SET item_status = 'REMOVED' WHERE action_plan_id = :p").param("p", plan).update();
        assertNotFound(fetch(contractor, path));
    }

    @Test
    void detailShowsTheContractorFirmPlannedDateAndTheMastersNumber() throws Exception {
        Citizen a = citizen();
        Citizen b = citizen();
        long id = submitOk(a, "Pothole").path("complaintId").asLong();
        Citizen contractor = staff(Role.CONTRACTOR);
        long firm = contractorFirm(contractor.id(), "Talegaon Road Works (prototype)");
        long plan = assignedPlan(firm, id, "ASSIGNED", LocalDate.of(2026, 10, 6));
        jdbc.sql("UPDATE complaints SET assigned_contractor_id = :k, current_action_plan_id = :p WHERE complaint_id = :id")
                .param("k", firm).param("p", plan).param("id", id).update();
        JsonNode d = getOk(a, "/api/v1/citizen/complaints/" + id);
        assertThat(d.path("contractorName").asString()).isEqualTo("Talegaon Road Works (prototype)");
        assertThat(d.path("plannedDate").asString()).isEqualTo("2026-10-06");

        long child = submitOk(a, "Pothole").path("complaintId").asLong();
        long master = submitOk(b, "Pothole").path("complaintId").asLong();
        jdbc.sql("UPDATE complaints SET master_complaint_id = :m WHERE complaint_id = :c").param("m", master).param("c", child).update();
        move(child, a.id(), ComplaintStatus.MERGED);
        JsonNode merged = getOk(a, "/api/v1/citizen/complaints/" + child);
        assertThat(merged.path("status").asString()).isEqualTo("MERGED");
        assertThat(merged.path("mergedIntoPublicRef").asString()).isEqualTo("CB-%06d".formatted(master));
        assertThat(merged.path("timeline").path(0).path("status").asString()).as("newest first").isEqualTo("MERGED");
        assertThat(merged.path("timeline").path(1).path("status").asString()).isEqualTo("SUBMITTED");
    }

    @Test
    void feedbackOnlyWhenCompletedOrClosedAndNotFixedReopensThroughTheDbRules() throws Exception {
        Citizen a = citizen();
        Citizen officer = staff(Role.OFFICER);
        long id = submitOk(a, "Pothole").path("complaintId").asLong();
        String path = "/api/v1/citizen/complaints/" + id + "/feedback";

        MvcResult r = mvc.perform(postJson(path, Map.of("isResolved", true, "rating", 5)).with(bearer(a.token()))).andReturn();
        assertThat(r.getResponse().getStatus()).isEqualTo(422);
        assertThat(body(r).path("code").asString()).isEqualTo("FEEDBACK_NOT_ALLOWED");

        move(id, officer.id(), ComplaintStatus.VERIFIED, ComplaintStatus.SCHEDULED, ComplaintStatus.ASSIGNED, ComplaintStatus.INSPECTED,
                ComplaintStatus.IN_PROGRESS, ComplaintStatus.COMPLETED);
        assertThat(getOk(a, "/api/v1/citizen/complaints/" + id).path("canGiveFeedback").asBoolean()).isTrue();

        r = mvc.perform(postJson(path, Map.of("isResolved", true, "rating", 6)).with(bearer(a.token()))).andReturn();
        assertThat(r.getResponse().getStatus()).isEqualTo(400);

        r = mvc.perform(postJson(path, Map.of("isResolved", true, "rating", 5, "comment", "Good work")).with(bearer(a.token()))).andReturn();
        assertThat(r.getResponse().getStatus()).as(r.getResponse().getContentAsString()).isEqualTo(201);
        assertThat(body(r).path("status").asString()).isEqualTo("COMPLETED");
        assertThat(status(id)).isEqualTo("COMPLETED");

        r = mvc.perform(postJson(path, Map.of("isResolved", false, "rating", 2, "comment", "It came back after the rain"))
                .with(bearer(a.token()))).andReturn();
        assertThat(r.getResponse().getStatus()).as(r.getResponse().getContentAsString()).isEqualTo(201);
        assertThat(body(r).path("status").asString()).isEqualTo("REOPENED");
        assertThat(status(id)).isEqualTo("REOPENED");

        // one row per (complaint, user), updated; the previous answer is in audit_logs
        List<Map<String, Object>> rows = jdbc.sql("SELECT is_resolved, rating, comment FROM complaint_feedback WHERE complaint_id = :id")
                .param("id", id).query().listOfRows();
        assertThat(rows).singleElement().satisfies(f -> assertThat(f).containsEntry("is_resolved", false)
                .containsEntry("rating", 2).containsEntry("comment", "It came back after the rain"));
        assertThat(jdbc.sql("""
                SELECT old_value ->> 'rating' FROM audit_logs
                 WHERE entity_type = 'complaint' AND entity_id = :id AND action = 'FEEDBACK_UPDATED'""")
                .param("id", id).query(String.class).single()).isEqualTo("5");
        // the status move went through the V2 rules as the citizen, without the citizen's comment
        Map<String, Object> h = jdbc.sql("""
                SELECT changed_by, actor_role, remarks FROM complaint_status_history
                 WHERE complaint_id = :id AND new_status = 'REOPENED'""").param("id", id).query().singleRow();
        assertThat(h).containsEntry("changed_by", a.id()).containsEntry("actor_role", "CITIZEN");
        assertThat((String) h.get("remarks")).doesNotContain("rain");
        assertThat(jdbc.sql("SELECT count(*) FROM notification_outbox WHERE complaint_id = :id AND event_status = 'REOPENED'")
                .param("id", id).query(Long.class).single()).isEqualTo(1);

        r = mvc.perform(postJson(path, Map.of("isResolved", false)).with(bearer(a.token()))).andReturn();
        assertThat(body(r).path("code").asString()).isEqualTo("FEEDBACK_NOT_ALLOWED");

        // CLOSED → "not fixed" also reopens
        long closed = submitOk(a, "Road Damage").path("complaintId").asLong();
        move(closed, officer.id(), ComplaintStatus.VERIFIED, ComplaintStatus.SCHEDULED, ComplaintStatus.ASSIGNED, ComplaintStatus.INSPECTED,
                ComplaintStatus.IN_PROGRESS, ComplaintStatus.COMPLETED, ComplaintStatus.CLOSED);
        r = mvc.perform(postJson("/api/v1/citizen/complaints/" + closed + "/feedback", Map.of("isResolved", false))
                .with(bearer(a.token()))).andReturn();
        assertThat(r.getResponse().getStatus()).isEqualTo(201);
        assertThat(status(closed)).isEqualTo("REOPENED");
    }

    // ------------------------------------------------------------------ helpers

    private MvcResult fetch(Citizen c, String path) throws Exception {
        return mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get(path).with(bearer(c.token()))).andReturn();
    }

    private JsonNode getOk(Citizen c, String path) throws Exception {
        MvcResult r = fetch(c, path);
        assertThat(r.getResponse().getStatus()).as(r.getResponse().getContentAsString()).isEqualTo(200);
        return body(r);
    }

    private void assertNotFound(MvcResult r) throws Exception {
        assertThat(r.getResponse().getStatus()).as(r.getResponse().getContentAsString()).isEqualTo(404);
        assertThat(body(r).path("code").asString()).isEqualTo("NOT_FOUND");
    }

    /** An OFFICER with one scope row (ward number and/or work type; both null = a row matching everything). */
    private Citizen officerWithScope(Integer wardNumber, String workType) throws Exception {
        Citizen officer = staff(Role.OFFICER);
        long officerId = jdbc.sql("""
                INSERT INTO officers (user_id, employee_code, department, designation)
                VALUES (:u, :code, 'IT department (prototype)', 'IT officer') RETURNING officer_id""")
                .param("u", officer.id()).param("code", "IT-" + UUID.randomUUID()).query(Long.class).single();
        jdbc.sql("""
                INSERT INTO officer_scopes (officer_id, ward_id, work_type_code)
                VALUES (:o, (SELECT ward_id FROM wards WHERE ward_number = :w), :t)""")
                .param("o", officerId).param("w", wardNumber).param("t", workType).update();
        return officer;
    }

    private long contractorFirm(long userId, String firmName) {
        return jdbc.sql("""
                INSERT INTO contractors (user_id, firm_name, contact_person, phone)
                VALUES (:u, :f, 'IT contact', :p) RETURNING contractor_id""")
                .param("u", userId).param("f", firmName).param("p", uniquePhone()).query(Long.class).single();
    }

    private long assignedPlan(long contractorId, long complaintId, String planStatus, LocalDate date) {
        long plan = jdbc.sql("""
                INSERT INTO action_plans (plan_code, work_type_code, planned_date, status, contractor_id)
                VALUES (:code, 'ROAD', :d, :s, :k) RETURNING action_plan_id""")
                .param("code", "IT-" + UUID.randomUUID()).param("d", date).param("s", planStatus).param("k", contractorId)
                .query(Long.class).single();
        jdbc.sql("INSERT INTO action_plan_items (action_plan_id, complaint_id, sequence_no) VALUES (:p, :c, 1)")
                .param("p", plan).param("c", complaintId).update();
        return plan;
    }
}
