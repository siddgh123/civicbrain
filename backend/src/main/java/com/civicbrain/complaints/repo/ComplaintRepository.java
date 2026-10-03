package com.civicbrain.complaints.repo;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

import com.civicbrain.common.Db;

/**
 * {@code complaints} and {@code complaint_images} for the citizen (docs/03 §3): inserts follow rule 2 (status
 * SUBMITTED, not synthetic - the V2/V4 triggers write history, outbox and the analysis job); every read of a
 * complaint is filtered by its owner inside the query (07 §2: not yours = not found).
 */
@Repository
public class ComplaintRepository {

    /** {@code fn_locate_point} + the ward number. */
    public record Location(boolean insideBoundary, Long wardId, Integer wardNumber, Long roadId, Long poiId) {
    }

    public record NewComplaint(long userId, long categoryId, String title, String description, String landmark, double latitude,
                               double longitude, Location location, double accuracyM, Instant capturedAt, UUID captureSessionId,
                               String depthAnswer, boolean a4InFrame, Instant now) {
    }

    public record Created(long complaintId, String publicRef) {
    }

    public record NewImage(long complaintId, String fileUrl, String storageKey, String fileName, String mimeType, long userId,
                           String sha256, int width, int height, long sizeBytes, String captureMethod, Instant capturedAt,
                           double latitude, double longitude, double accuracyM, Double pitchDeg, Double rollDeg, String exifJson,
                           Instant now) {
    }

    /** One row of the citizen's list. */
    public record ListRow(long complaintId, String publicRef, String title, String categoryName, String status, Integer wardNumber,
                          Instant submittedAt, Long thumbnailImageId) {
    }

    /** The citizen's own complaint. */
    public record Detail(long complaintId, String publicRef, String title, String description, String landmark, Long categoryId,
                         String categoryName, String status, Integer wardNumber, Instant submittedAt, double latitude, double longitude,
                         String contractorName, LocalDate plannedDate, String mergedIntoPublicRef) {
    }

    public record Image(long imageId, String role) {
    }

    public record TimelineEntry(String status, Instant at, String remarks) {
    }

    private static final String LIST_COLUMNS = """
            c.complaint_id, c.public_ref, c.title, cat.category_name, c.status, w.ward_number, c.submitted_at,
            (SELECT min(ci.image_id) FROM complaint_images ci
              WHERE ci.complaint_id = c.complaint_id AND ci.image_role = 'CITIZEN_EVIDENCE') AS thumbnail_image_id""";

    private final JdbcClient jdbc;

    public ComplaintRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    public Location locate(double latitude, double longitude) {
        return jdbc.sql("""
                SELECT l.inside_boundary, l.ward_id, w.ward_number, l.road_id, l.poi_id
                  FROM fn_locate_point(:lat, :lon) l LEFT JOIN wards w ON w.ward_id = l.ward_id""")
                .param("lat", latitude).param("lon", longitude)
                .query((rs, n) -> new Location(rs.getBoolean("inside_boundary"), nullableLong(rs, "ward_id"),
                        (Integer) rs.getObject("ward_number"), nullableLong(rs, "road_id"), nullableLong(rs, "poi_id")))
                .single();
    }

    public Created insert(NewComplaint c) {
        return jdbc.sql("""
                INSERT INTO complaints (user_id, category_id, title, description, status, location, ward_id, road_id, poi_id,
                                        is_outside_boundary, submitted_at, updated_at, landmark, location_accuracy_m,
                                        location_captured_at, location_source, capture_session_id, depth_answer, a4_in_frame)
                VALUES (:userId, :categoryId, :title, :description, 'SUBMITTED', ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
                        :wardId, :roadId, :poiId, false, :now, :now, :landmark, :accuracy, :capturedAt, 'BROWSER_GPS',
                        :sessionId, :depth, :a4)
                RETURNING complaint_id, public_ref""")
                .param("userId", c.userId()).param("categoryId", c.categoryId()).param("title", c.title())
                .param("description", c.description()).param("lon", c.longitude()).param("lat", c.latitude())
                .param("wardId", c.location().wardId()).param("roadId", c.location().roadId()).param("poiId", c.location().poiId())
                .param("now", Db.ts(c.now())).param("landmark", c.landmark()).param("accuracy", c.accuracyM())
                .param("capturedAt", Db.ts(c.capturedAt())).param("sessionId", c.captureSessionId())
                .param("depth", c.depthAnswer()).param("a4", c.a4InFrame())
                .query((rs, n) -> new Created(rs.getLong("complaint_id"), rs.getString("public_ref"))).single();
    }

    public long insertImage(NewImage i) {
        return jdbc.sql("""
                INSERT INTO complaint_images (complaint_id, file_url, storage_key, file_name, mime_type, uploaded_at, image_role,
                                              uploaded_by, sha256, width_px, height_px, file_size_bytes, capture_method,
                                              client_captured_at, capture_location, capture_accuracy_m, device_pitch_deg,
                                              device_roll_deg, exif_extracted)
                VALUES (:complaintId, :fileUrl, :key, :fileName, :mime, :now, 'CITIZEN_EVIDENCE', :userId, :sha, :w, :h, :size,
                        :method, :capturedAt, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), :accuracy, :pitch, :roll,
                        CAST(:exif AS jsonb))
                RETURNING image_id""")
                .param("complaintId", i.complaintId()).param("fileUrl", i.fileUrl()).param("key", i.storageKey())
                .param("fileName", i.fileName()).param("mime", i.mimeType()).param("now", Db.ts(i.now())).param("userId", i.userId())
                .param("sha", i.sha256()).param("w", i.width()).param("h", i.height()).param("size", i.sizeBytes())
                .param("method", i.captureMethod()).param("capturedAt", Db.ts(i.capturedAt()))
                .param("lon", i.longitude()).param("lat", i.latitude()).param("accuracy", i.accuracyM())
                .param("pitch", i.pitchDeg()).param("roll", i.rollDeg()).param("exif", i.exifJson())
                .query(Long.class).single();
    }

    // ------------------------------------------------------------------ citizen reads (owner inside every query)

    public List<ListRow> listOwn(long userId, String status, int limit, long offset) {
        return jdbc.sql("SELECT " + LIST_COLUMNS + """
                  FROM complaints c
                  LEFT JOIN complaint_categories cat ON cat.category_id = c.category_id
                  LEFT JOIN wards w ON w.ward_id = c.ward_id
                 WHERE c.user_id = :userId AND (CAST(:status AS varchar) IS NULL OR c.status = CAST(:status AS varchar))
                 ORDER BY c.submitted_at DESC, c.complaint_id DESC
                 LIMIT :limit OFFSET :offset""")
                .param("userId", userId).param("status", status).param("limit", limit).param("offset", offset)
                .query((rs, n) -> new ListRow(rs.getLong("complaint_id"), rs.getString("public_ref"), rs.getString("title"),
                        rs.getString("category_name"), rs.getString("status"), (Integer) rs.getObject("ward_number"),
                        Db.instant(rs, "submitted_at"), nullableLong(rs, "thumbnail_image_id")))
                .list();
    }

    public long countOwn(long userId, String status) {
        return jdbc.sql("""
                SELECT count(*) FROM complaints c
                 WHERE c.user_id = :userId AND (CAST(:status AS varchar) IS NULL OR c.status = CAST(:status AS varchar))""")
                .param("userId", userId).param("status", status).query(Long.class).single();
    }

    public Optional<Detail> findOwn(long complaintId, long userId) {
        return jdbc.sql("""
                SELECT c.complaint_id, c.public_ref, c.title, c.description, c.landmark, c.category_id, cat.category_name,
                       c.status, w.ward_number, c.submitted_at, ST_Y(c.location) AS lat, ST_X(c.location) AS lon,
                       k.firm_name, ap.planned_date, m.public_ref AS master_ref
                  FROM complaints c
                  LEFT JOIN complaint_categories cat ON cat.category_id = c.category_id
                  LEFT JOIN wards w ON w.ward_id = c.ward_id
                  LEFT JOIN contractors k ON k.contractor_id = c.assigned_contractor_id
                  LEFT JOIN action_plans ap ON ap.action_plan_id = c.current_action_plan_id
                  LEFT JOIN complaints m ON m.complaint_id = c.master_complaint_id AND c.status = 'MERGED'
                 WHERE c.complaint_id = :id AND c.user_id = :userId""")
                .param("id", complaintId).param("userId", userId)
                .query((rs, n) -> new Detail(rs.getLong("complaint_id"), rs.getString("public_ref"), rs.getString("title"),
                        rs.getString("description"), rs.getString("landmark"), nullableLong(rs, "category_id"),
                        rs.getString("category_name"), rs.getString("status"), (Integer) rs.getObject("ward_number"),
                        Db.instant(rs, "submitted_at"), rs.getDouble("lat"), rs.getDouble("lon"), rs.getString("firm_name"),
                        rs.getObject("planned_date", LocalDate.class), rs.getString("master_ref")))
                .optional();
    }

    /** Images of a complaint (call only after the ownership check). */
    public List<Image> images(long complaintId) {
        return jdbc.sql("SELECT image_id, image_role FROM complaint_images WHERE complaint_id = :id ORDER BY image_id")
                .param("id", complaintId).query((rs, n) -> new Image(rs.getLong("image_id"), rs.getString("image_role"))).list();
    }

    /** Status history, newest first (call only after the ownership check). */
    public List<TimelineEntry> timeline(long complaintId) {
        return jdbc.sql("""
                SELECT new_status, changed_at, remarks FROM complaint_status_history
                 WHERE complaint_id = :id ORDER BY changed_at DESC, status_history_id DESC""")
                .param("id", complaintId)
                .query((rs, n) -> new TimelineEntry(rs.getString("new_status"), Db.instant(rs, "changed_at"), rs.getString("remarks")))
                .list();
    }

    /** Status of the caller's own complaint, row-locked for the feedback transaction. */
    public Optional<String> lockOwnStatus(long complaintId, long userId) {
        return jdbc.sql("SELECT status FROM complaints WHERE complaint_id = :id AND user_id = :userId FOR UPDATE")
                .param("id", complaintId).param("userId", userId).query(String.class).optional();
    }

    private static Long nullableLong(ResultSet rs, String column) throws SQLException {
        long value = rs.getLong(column);
        return rs.wasNull() ? null : value;
    }
}
