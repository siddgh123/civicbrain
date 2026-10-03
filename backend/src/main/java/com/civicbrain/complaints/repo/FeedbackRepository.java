package com.civicbrain.complaints.repo;

import java.time.Instant;
import java.util.Optional;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

import com.civicbrain.common.Db;

/** {@code complaint_feedback}: one row per (complaint, user) - a second answer updates it (docs/04 §5, FR-15). */
@Repository
public class FeedbackRepository {

    public record Feedback(boolean isResolved, Integer rating, String comment) {
    }

    private final JdbcClient jdbc;

    public FeedbackRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    public Optional<Feedback> find(long complaintId, long userId) {
        return jdbc.sql("SELECT is_resolved, rating, comment FROM complaint_feedback WHERE complaint_id = :c AND user_id = :u")
                .param("c", complaintId).param("u", userId)
                .query((rs, n) -> new Feedback(rs.getBoolean("is_resolved"), (Integer) rs.getObject("rating"), rs.getString("comment")))
                .optional();
    }

    public void upsert(long complaintId, long userId, Feedback f, Instant now) {
        jdbc.sql("""
                INSERT INTO complaint_feedback (complaint_id, user_id, is_resolved, rating, comment, created_at)
                VALUES (:c, :u, :resolved, :rating, :comment, :now)
                ON CONFLICT (complaint_id, user_id) DO UPDATE
                   SET is_resolved = EXCLUDED.is_resolved, rating = EXCLUDED.rating, comment = EXCLUDED.comment,
                       created_at = EXCLUDED.created_at""")
                .param("c", complaintId).param("u", userId).param("resolved", f.isResolved()).param("rating", f.rating())
                .param("comment", f.comment()).param("now", Db.ts(now)).update();
    }
}
