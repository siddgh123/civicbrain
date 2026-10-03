package com.civicbrain.it;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.HexFormat;
import java.util.Map;
import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.transaction.support.TransactionTemplate;

import com.civicbrain.files.service.PhotoStorage;
import com.civicbrain.it.support.ComplaintItSupport;
import com.civicbrain.it.support.IntegrationTest;
import com.civicbrain.users.model.Role;

import tools.jackson.databind.JsonNode;

/**
 * {@code POST /citizen/capture-sessions} and {@code POST /citizen/complaints} (docs/04 §5, FR-10 server part, FR-11,
 * FR-12; 09_7DAY §4 "intake happy path" + error codes): one transaction writes the complaint (trigger → history,
 * outbox SUBMITTED, ANALYZE_COMPLAINT job), the image row and the used session; every rejection has the code of
 * docs/12 §2 in the validation order of 04 §5 (first failure wins) and leaves no row and no file behind.
 */
@IntegrationTest
class ComplaintIntakeIT extends ComplaintItSupport {

    @Autowired
    PhotoStorage storage;
    @Autowired
    TransactionTemplate tx;

    @Test
    void captureSessionIsIssuedForTenMinutesToCitizensOnly() throws Exception {
        Citizen c = citizen();
        MvcResult r = mvc.perform(post("/api/v1/citizen/capture-sessions").with(bearer(c.token())).with(from(uniqueIp()))).andReturn();
        assertThat(r.getResponse().getStatus()).isEqualTo(201);
        JsonNode b = body(r);
        UUID id = UUID.fromString(b.path("captureSessionId").asString());
        OffsetDateTime expires = OffsetDateTime.parse(b.path("expiresAt").asString());
        assertThat(expires.getOffset()).isEqualTo(ZoneOffset.ofHoursMinutes(5, 30));
        assertThat(expires).isBetween(OffsetDateTime.now().plusMinutes(9), OffsetDateTime.now().plusMinutes(11));
        assertThat(jdbc.sql("SELECT user_id FROM capture_sessions WHERE capture_session_id = :id AND used_at IS NULL")
                .param("id", id).query(Long.class).single()).isEqualTo(c.id());

        Citizen officer = staff(Role.OFFICER);
        r = mvc.perform(post("/api/v1/citizen/capture-sessions").with(bearer(officer.token()))).andReturn();
        assertThat(r.getResponse().getStatus()).isEqualTo(403);
        r = mvc.perform(post("/api/v1/citizen/capture-sessions")).andReturn();
        assertThat(r.getResponse().getStatus()).isEqualTo(401);
    }

    @Test
    void happyPathStoresComplaintImageHistoryOutboxJobAndUsedSession() throws Exception {
        Citizen c = citizen();
        String session = captureSession(c);
        Map<String, Object> data = data("Pothole", session);
        data.put("depthAnswer", "DEEP");
        data.put("a4InFrame", true);
        String capturedAt = OffsetDateTime.now(ZoneOffset.ofHoursMinutes(5, 30)).minusSeconds(45).withNano(0).toString();
        data.put("locationCapturedAt", capturedAt);
        byte[] photo = resource("/photos/exif_gps_orientation6.jpg");

        MvcResult r = submit(c, data, photo);
        assertThat(r.getResponse().getStatus()).as(r.getResponse().getContentAsString()).isEqualTo(201);
        JsonNode b = body(r);
        long id = b.path("complaintId").asLong();
        assertThat(b.path("publicRef").asString()).matches("CB-\\d{6}").isEqualTo("CB-%06d".formatted(id));
        assertThat(b.path("status").asString()).isEqualTo("SUBMITTED");
        assertThat(b.path("wardNumber").asInt()).isEqualTo(1);
        assertThat(r.getResponse().getHeader("Location")).isEqualTo("/api/v1/citizen/complaints/" + id);

        Map<String, Object> row = jdbc.sql("""
                SELECT c.user_id, c.status, c.is_synthetic, c.depth_answer, c.a4_in_frame, w.ward_number, c.road_id, c.poi_id,
                       c.location_source, c.location_accuracy_m::float8 AS acc, c.location_captured_at, c.capture_session_id,
                       c.title, c.landmark, ST_Y(c.location) AS lat, ST_X(c.location) AS lon, c.category_id
                  FROM complaints c JOIN wards w ON w.ward_id = c.ward_id WHERE c.complaint_id = :id""")
                .param("id", id).query().singleRow();
        assertThat(row).containsEntry("user_id", c.id()).containsEntry("status", "SUBMITTED").containsEntry("is_synthetic", false)
                .containsEntry("depth_answer", "DEEP").containsEntry("a4_in_frame", true).containsEntry("ward_number", 1)
                .containsEntry("location_source", "BROWSER_GPS").containsEntry("acc", 12.5)
                .containsEntry("title", "Deep pothole near the temple").containsEntry("landmark", "Near the temple")
                .containsEntry("lat", IN_LAT).containsEntry("lon", IN_LON).containsEntry("category_id", categoryId("Pothole"));
        assertThat(row.get("road_id")).isNotNull();
        assertThat(row.get("poi_id")).isNotNull();
        assertThat(row.get("capture_session_id").toString()).isEqualTo(session);
        assertThat(((java.sql.Timestamp) row.get("location_captured_at")).toInstant()).isEqualTo(OffsetDateTime.parse(capturedAt).toInstant());

        // trigger rows of the same transaction
        assertThat(jdbc.sql("SELECT old_status, new_status, changed_by, actor_role FROM complaint_status_history WHERE complaint_id = :id")
                .param("id", id).query().listOfRows())
                .singleElement().satisfies(h -> assertThat(h).containsEntry("old_status", null).containsEntry("new_status", "SUBMITTED")
                        .containsEntry("changed_by", c.id()).containsEntry("actor_role", "CITIZEN"));
        assertThat(jdbc.sql("SELECT event_type || ':' || event_status FROM notification_outbox WHERE complaint_id = :id")
                .param("id", id).query(String.class).list()).containsExactly("COMPLAINT_STATUS_CHANGED:SUBMITTED");
        assertThat(jdbc.sql("SELECT job_type || ':' || status FROM jobs WHERE ref_id = :id AND job_type = 'ANALYZE_COMPLAINT'")
                .param("id", id).query(String.class).list()).containsExactly("ANALYZE_COMPLAINT:QUEUED");
        assertThat(jdbc.sql("SELECT used_by_complaint_id FROM capture_sessions WHERE capture_session_id = :s AND used_at IS NOT NULL")
                .param("s", UUID.fromString(session)).query(Long.class).single()).isEqualTo(id);
        assertThat(jdbc.sql("SELECT count(*) FROM audit_logs WHERE entity_type = 'complaint' AND entity_id = :id AND action = 'COMPLAINT_CREATED'")
                .param("id", id).query(Long.class).single()).isEqualTo(1);

        // the image row and the stored file: re-encoded, upright, no EXIF, SHA-256 of the stored bytes
        Map<String, Object> img = jdbc.sql("""
                SELECT file_url, storage_key, file_name, mime_type, sha256, width_px, height_px, file_size_bytes, image_role,
                       uploaded_by, capture_method, capture_accuracy_m::float8 AS acc, device_pitch_deg::float8 AS pitch,
                       device_roll_deg::float8 AS roll, client_captured_at, ST_Y(capture_location) AS lat,
                       exif_extracted ->> 'dateTimeOriginal' AS dto, (exif_extracted ->> 'gpsLatitude')::float8 AS exif_lat,
                       (exif_extracted -> 'make') IS NOT NULL AS has_make, processing_status
                  FROM complaint_images WHERE complaint_id = :id""").param("id", id).query().singleRow();
        String key = (String) img.get("storage_key");
        assertThat(key).matches("photos/\\d{4}/\\d{2}/[0-9a-f-]{36}\\.jpg");
        assertThat(img).containsEntry("file_url", "storage://" + key).containsEntry("mime_type", "image/jpeg")
                .containsEntry("image_role", "CITIZEN_EVIDENCE").containsEntry("uploaded_by", c.id())
                .containsEntry("capture_method", "IN_APP_CAMERA").containsEntry("acc", 12.5).containsEntry("pitch", 55.5)
                .containsEntry("roll", -1.25).containsEntry("width_px", 600).containsEntry("height_px", 800)
                .containsEntry("lat", IN_LAT).containsEntry("dto", "2026:10:03 10:15:30").containsEntry("has_make", false)
                .containsEntry("processing_status", "PENDING");
        assertThat((String) img.get("file_name")).isEqualTo(key.substring(key.lastIndexOf('/') + 1));
        assertThat((Double) img.get("exif_lat")).isBetween(18.7439, 18.7441);
        assertThat(((java.sql.Timestamp) img.get("client_captured_at")).toInstant()).isEqualTo(OffsetDateTime.parse(capturedAt).toInstant());
        Path file = storage.path(key).orElseThrow();
        byte[] stored = Files.readAllBytes(file);
        assertThat(stored[0]).isEqualTo((byte) 0xFF);
        assertThat(new String(stored, StandardCharsets.ISO_8859_1)).doesNotContain("Exif").doesNotContain("FixtureCam");
        assertThat(img.get("sha256")).isEqualTo(HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(stored)));
        assertThat(img.get("file_size_bytes")).isEqualTo((long) stored.length);
    }

    @Test
    void captureSessionMustBeOwnUnusedAndNotExpired() throws Exception {
        Citizen c = citizen();
        Citizen other = citizen();
        String used = submitOk(c, "Road Damage").path("complaintId").asString();
        String usedSession = jdbc.sql("SELECT capture_session_id::text FROM complaints WHERE complaint_id = :id")
                .param("id", Long.parseLong(used)).query(String.class).single();

        expect(submit(c, data("Road Damage", usedSession), jpeg(800, 600, 1)), 422, "CAPTURE_SESSION_INVALID");
        expect(submit(c, data("Road Damage", UUID.randomUUID().toString()), jpeg(800, 600, 2)), 422, "CAPTURE_SESSION_INVALID");
        expect(submit(c, data("Road Damage", captureSession(other)), jpeg(800, 600, 3)), 422, "CAPTURE_SESSION_INVALID");

        String expired = captureSession(c);
        jdbc.sql("UPDATE capture_sessions SET issued_at = now() - interval '20 minutes', expires_at = now() - interval '10 minutes' "
                + "WHERE capture_session_id = :s").param("s", UUID.fromString(expired)).update();
        expect(submit(c, data("Road Damage", expired), jpeg(800, 600, 4)), 410, "CAPTURE_SESSION_EXPIRED");
        assertThat(countComplaints(c)).isEqualTo(1);
    }

    @Test
    void locationMustBeAccurateFreshAndInsideTdmc() throws Exception {
        Citizen c = citizen();
        Map<String, Object> far = data("Pothole", captureSession(c));
        far.put("locationAccuracyM", 400);
        MvcResult r = submit(c, far, jpeg(800, 600, 5));
        expect(r, 422, "GPS_ACCURACY_TOO_LOW");
        JsonNode b = body(r);
        assertThat(b.path("fieldErrors").path(0).path("field").asString()).isEqualTo("locationAccuracyM");
        assertThat(b.path("detail").asString()).contains("400").contains("150");

        Map<String, Object> stale = data("Pothole", captureSession(c));
        stale.put("locationCapturedAt", OffsetDateTime.now(ZoneOffset.UTC).minusMinutes(11).toString());
        expect(submit(c, stale, jpeg(800, 600, 6)), 422, "LOCATION_STALE");

        Map<String, Object> outside = data("Pothole", captureSession(c));
        outside.put("latitude", OUT_LAT);
        outside.put("longitude", OUT_LON);
        expect(submit(c, outside, jpeg(800, 600, 7)), 422, "OUTSIDE_BOUNDARY");
        assertThat(countComplaints(c)).isZero();
    }

    @Test
    void theFileIsCheckedByMagicBytesAndPixels() throws Exception {
        Citizen c = citizen();
        byte[] text = "this is not an image, just text ".repeat(40).getBytes(StandardCharsets.US_ASCII);
        expect(submit(c, data("Pothole", captureSession(c)), text), 415, "FILE_TYPE_NOT_ALLOWED");
        expect(submit(c, data("Pothole", captureSession(c)), jpeg(300, 200, 8)), 422, "IMAGE_TOO_SMALL");
        expect(submit(c, data("Pothole", captureSession(c)), new byte[0]), 415, "FILE_TYPE_NOT_ALLOWED");
        MvcResult r = submit(c, data("Pothole", captureSession(c)), null);
        expect(r, 400, "VALIDATION_FAILED");
        assertThat(body(r).path("fieldErrors").path(0).path("field").asString()).isEqualTo("photo");
        assertThat(countComplaints(c)).isZero();
    }

    @Test
    void theDataPartIsValidatedIncludingTheDepthAnswerRule() throws Exception {
        Citizen c = citizen();
        Map<String, Object> noDepth = data("Pothole", captureSession(c));
        noDepth.remove("depthAnswer");
        assertField(submit(c, noDepth, jpeg(800, 600, 9)), "depthAnswer");

        Map<String, Object> garbageDepth = data("Garbage Accumulation", captureSession(c));
        garbageDepth.put("depthAnswer", "DEEP");
        assertField(submit(c, garbageDepth, jpeg(800, 600, 10)), "depthAnswer");

        Map<String, Object> unknownField = data("Pothole", captureSession(c));
        unknownField.put("priority", "HIGH");
        assertField(submit(c, unknownField, jpeg(800, 600, 11)), "priority");

        Map<String, Object> shortTitle = data("Pothole", captureSession(c));
        shortTitle.put("title", "Hole");
        assertField(submit(c, shortTitle, jpeg(800, 600, 12)), "title");

        Map<String, Object> badCategory = data("Pothole", captureSession(c));
        badCategory.put("categoryId", 9_999_999);
        assertField(submit(c, badCategory, jpeg(800, 600, 13)), "categoryId");

        Map<String, Object> badDepth = data("Pothole", captureSession(c));
        badDepth.put("depthAnswer", "VERY_DEEP");
        assertField(submit(c, badDepth, jpeg(800, 600, 14)), "depthAnswer");

        expect(submitRaw(c, "{not json".getBytes(StandardCharsets.UTF_8), jpeg(800, 600, 15), uniqueIp()), 400, "MALFORMED_REQUEST");
        assertField(submitRaw(c, null, jpeg(800, 600, 16), uniqueIp()), "data");
        assertThat(countComplaints(c)).isZero();
    }

    @Test
    void theFirstFailingCheckWins() throws Exception {
        Citizen c = citizen();
        // bad session + bad accuracy → the session (checked first)
        Map<String, Object> d = data("Pothole", UUID.randomUUID().toString());
        d.put("locationAccuracyM", 400);
        expect(submit(c, d, jpeg(800, 600, 17)), 422, "CAPTURE_SESSION_INVALID");
        // bad accuracy + outside → accuracy
        d = data("Pothole", captureSession(c));
        d.put("locationAccuracyM", 400);
        d.put("latitude", OUT_LAT);
        d.put("longitude", OUT_LON);
        expect(submit(c, d, jpeg(800, 600, 18)), 422, "GPS_ACCURACY_TOO_LOW");
        // outside + text file → boundary (before the file)
        d = data("Pothole", captureSession(c));
        d.put("latitude", OUT_LAT);
        d.put("longitude", OUT_LON);
        expect(submit(c, d, "plain text".repeat(50).getBytes(StandardCharsets.US_ASCII)), 422, "OUTSIDE_BOUNDARY");
        // schema error + used/unknown session → schema (before the session)
        d = data("Pothole", UUID.randomUUID().toString());
        d.remove("depthAnswer");
        assertField(submit(c, d, jpeg(800, 600, 19)), "depthAnswer");
        // nothing was stored, every session issued here is still unused
        assertThat(countComplaints(c)).isZero();
        assertThat(jdbc.sql("SELECT count(*) FROM capture_sessions WHERE user_id = :u AND used_at IS NOT NULL")
                .param("u", c.id()).query(Long.class).single()).isZero();
    }

    @Test
    void fiveAcceptedComplaintsPer24HoursAndRejectedOnesDoNotCount() throws Exception {
        Citizen c = citizen();
        expect(submit(c, data("Pothole", UUID.randomUUID().toString()), jpeg(800, 600, 20)), 422, "CAPTURE_SESSION_INVALID");
        for (int i = 0; i < 5; i++) {
            submitOk(c, "Road Damage");
        }
        MvcResult r = submit(c, data("Road Damage", captureSession(c)), jpeg(800, 600, 21));
        expect(r, 429, "RATE_LIMITED");
        assertThat(r.getResponse().getHeader("Retry-After")).isNotBlank();
        assertThat(countComplaints(c)).isEqualTo(5);
    }

    @Test
    void onlyCitizensSubmit() throws Exception {
        Citizen officer = staff(Role.OFFICER);
        MvcResult r = submit(officer, data("Pothole", UUID.randomUUID().toString()), jpeg(800, 600, 22));
        expect(r, 403, "FORBIDDEN");
    }

    @Test
    void aRolledBackTransactionDeletesTheStoredPhoto() throws Exception {
        Path[] written = new Path[1];
        tx.executeWithoutResult(status -> {
            written[0] = storage.store(new byte[] {(byte) 0xFF, (byte) 0xD8, (byte) 0xFF, 0x00}).path();
            assertThat(Files.exists(written[0])).isTrue();
            status.setRollbackOnly();
        });
        assertThat(Files.exists(written[0])).isFalse();

        Path[] kept = new Path[1];
        tx.executeWithoutResult(status -> kept[0] = storage.store(new byte[] {(byte) 0xFF, (byte) 0xD8, (byte) 0xFF, 0x01}).path());
        assertThat(Files.exists(kept[0])).isTrue();
    }

    // ------------------------------------------------------------------ helpers

    private void expect(MvcResult r, int status, String code) throws Exception {
        assertThat(r.getResponse().getStatus()).as(r.getResponse().getContentAsString()).isEqualTo(status);
        assertThat(body(r).path("code").asString()).isEqualTo(code);
    }

    private void assertField(MvcResult r, String field) throws Exception {
        expect(r, 400, "VALIDATION_FAILED");
        assertThat(body(r).path("fieldErrors").findValuesAsString("field")).as(r.getResponse().getContentAsString()).contains(field);
    }

    private long countComplaints(Citizen c) {
        return jdbc.sql("SELECT count(*) FROM complaints WHERE user_id = :u").param("u", c.id()).query(Long.class).single();
    }
}
