package com.civicbrain.files.repo;

import java.util.Optional;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/**
 * Who may download a complaint photo (docs/04 §4, 07 §2) - decided inside the query, so "not allowed" and "not
 * found" are the same empty result (→ 404): the complaint's owner; an ADMIN; an active OFFICER with a scope row
 * matching the complaint's ward and/or work type (a NULL scope column matches everything; no row = nothing, docs/01
 * §2); a CONTRACTOR (firm account) or active CONTRACTOR_STAFF of the firm that holds an ACTIVE item for the
 * complaint in an ASSIGNED / IN_PROGRESS plan (04 §6 "Contractor access").
 */
@Repository
public class ImageAccessRepository {

    private final JdbcClient jdbc;

    public ImageAccessRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    /** The storage key of the image if {@code userId} with {@code role} may see it. */
    public Optional<String> visibleStorageKey(long imageId, long userId, String role) {
        return jdbc.sql("""
                SELECT ci.storage_key
                  FROM complaint_images ci
                  JOIN complaints c ON c.complaint_id = ci.complaint_id
                  LEFT JOIN complaint_categories cat ON cat.category_id = c.category_id
                 WHERE ci.image_id = :imageId
                   AND (c.user_id = :userId
                        OR :role = 'ADMIN'
                        OR (:role = 'OFFICER' AND EXISTS (
                              SELECT 1 FROM officers o JOIN officer_scopes s ON s.officer_id = o.officer_id
                               WHERE o.user_id = :userId AND o.is_active
                                 AND (s.ward_id IS NULL OR s.ward_id = c.ward_id)
                                 AND (s.work_type_code IS NULL OR s.work_type_code = cat.work_type_code)))
                        OR (:role IN ('CONTRACTOR', 'CONTRACTOR_STAFF') AND EXISTS (
                              SELECT 1 FROM action_plan_items i
                                JOIN action_plans p ON p.action_plan_id = i.action_plan_id
                                JOIN contractors k ON k.contractor_id = p.contractor_id
                               WHERE i.complaint_id = c.complaint_id AND i.item_status = 'ACTIVE'
                                 AND p.status IN ('ASSIGNED', 'IN_PROGRESS')
                                 AND ((:role = 'CONTRACTOR' AND k.user_id = :userId)
                                      OR (:role = 'CONTRACTOR_STAFF' AND EXISTS (
                                            SELECT 1 FROM contractor_workers w
                                             WHERE w.contractor_id = k.contractor_id AND w.user_id = :userId AND w.is_active))))))""")
                .param("imageId", imageId).param("userId", userId).param("role", role)
                .query(String.class).optional();
    }
}
