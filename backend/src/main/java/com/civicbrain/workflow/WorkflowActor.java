package com.civicbrain.workflow;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import com.civicbrain.common.ApiException;
import com.civicbrain.common.ErrorCode;

/**
 * The ONLY way the backend changes {@code complaints.status} (docs/02_ARCHITECTURE.md §3, 03 §3.1). Inside one
 * transaction it sets the actor context with {@code set_config(..., true)} and updates the row; the V2 triggers
 * check the move and the role, write the history and the outbox. Invalid move → SQLSTATE 23514 → 409
 * INVALID_TRANSITION, wrong role → 42501 → 403 ROLE_NOT_ALLOWED (mapped by the error advice).
 */
@Component
public class WorkflowActor {

    private final JdbcClient jdbc;

    public WorkflowActor(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    /**
     * Moves one complaint to {@code target} as {@code actor}; {@code remarks} (may be null) ends up in the status
     * history and the {@code remarks} placeholder of the citizen message.
     */
    @Transactional
    public void changeStatus(long complaintId, ComplaintStatus target, Actor actor, String remarks) {
        jdbc.sql("""
                SELECT set_config('civicbrain.actor_user_id', :userId, true),
                       set_config('civicbrain.actor_role', :role, true),
                       set_config('civicbrain.status_remarks', :remarks, true)""")
                .param("userId", actor.userId() == null ? "" : actor.userId().toString())
                .param("role", actor.role().name())
                .param("remarks", remarks == null ? "" : remarks)
                .query().singleRow();
        int updated = jdbc.sql("UPDATE complaints SET status = :status, updated_at = now() WHERE complaint_id = :id")
                .param("status", target.name())
                .param("id", complaintId)
                .update();
        if (updated == 0) {
            throw new ApiException(ErrorCode.NOT_FOUND, "Not found.");
        }
    }
}
