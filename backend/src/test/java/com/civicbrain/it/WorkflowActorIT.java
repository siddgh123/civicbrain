package com.civicbrain.it;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.catchThrowable;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.transaction.support.TransactionTemplate;

import com.civicbrain.common.ApiException;
import com.civicbrain.common.DbErrorTranslator;
import com.civicbrain.common.ErrorCode;
import com.civicbrain.it.support.IntegrationTest;
import com.civicbrain.workflow.Actor;
import com.civicbrain.workflow.ActorRole;
import com.civicbrain.workflow.ComplaintStatus;
import com.civicbrain.workflow.WorkflowActor;

/**
 * Status changes go through the V2 rules with the actor context set in the same transaction (02 §3, 03 §3.1);
 * the DB errors map to the API codes of 12 §3. Every test rolls back its rows.
 */
@IntegrationTest
class WorkflowActorIT {

    @Autowired
    WorkflowActor workflow;

    @Autowired
    JdbcClient jdbc;

    @Autowired
    TransactionTemplate tx;

    @Test
    void officerVerifiesAComplaintAndTheHistoryNamesTheActor() {
        tx.executeWithoutResult(status -> {
            long officer = insertUser("wf-officer@it.local", "OFFICER");
            long complaint = insertComplaint(insertUser("wf-citizen@it.local", "CITIZEN"));

            workflow.changeStatus(complaint, ComplaintStatus.VERIFIED, Actor.user(officer, ActorRole.OFFICER), "Checked on site");

            assertThat(jdbc.sql("SELECT status FROM complaints WHERE complaint_id = :id").param("id", complaint)
                    .query(String.class).single()).isEqualTo("VERIFIED");
            var history = jdbc.sql("""
                    SELECT old_status, new_status, changed_by, actor_role, remarks FROM complaint_status_history
                     WHERE complaint_id = :id AND new_status = 'VERIFIED'""")
                    .param("id", complaint)
                    .query((rs, n) -> new Object[] {rs.getString(1), rs.getString(2), rs.getLong(3), rs.getString(4), rs.getString(5)})
                    .single();
            assertThat(history).containsExactly("SUBMITTED", "VERIFIED", officer, "OFFICER", "Checked on site");
            status.setRollbackOnly();
        });
    }

    @Test
    void invalidMoveIsRejectedByTheDatabaseAndMapsTo409InvalidTransition() {
        Throwable thrown = catchThrowable(() -> tx.executeWithoutResult(status -> {
            status.setRollbackOnly();
            long officer = insertUser("wf-officer2@it.local", "OFFICER");
            long complaint = insertComplaint(insertUser("wf-citizen2@it.local", "CITIZEN"));
            workflow.changeStatus(complaint, ComplaintStatus.CLOSED, Actor.user(officer, ActorRole.OFFICER), null);
        }));
        ApiException mapped = DbErrorTranslator.translate(thrown).orElseThrow();
        assertThat(mapped.code()).isEqualTo(ErrorCode.INVALID_TRANSITION);
        assertThat(mapped.status()).isEqualTo(409);
    }

    @Test
    void roleNotAllowedByTheGuardMapsTo403RoleNotAllowed() {
        Throwable thrown = catchThrowable(() -> tx.executeWithoutResult(status -> {
            status.setRollbackOnly();
            long citizen = insertUser("wf-citizen3@it.local", "CITIZEN");
            long complaint = insertComplaint(citizen);
            workflow.changeStatus(complaint, ComplaintStatus.VERIFIED, Actor.user(citizen, ActorRole.CITIZEN), null);
        }));
        ApiException mapped = DbErrorTranslator.translate(thrown).orElseThrow();
        assertThat(mapped.code()).isEqualTo(ErrorCode.ROLE_NOT_ALLOWED);
        assertThat(mapped.status()).isEqualTo(403);
    }

    @Test
    void unknownComplaintIsNotFound() {
        Throwable thrown = catchThrowable(() -> tx.executeWithoutResult(status -> {
            status.setRollbackOnly();
            workflow.changeStatus(Long.MAX_VALUE, ComplaintStatus.VERIFIED, Actor.system(), null);
        }));
        assertThat(thrown).isInstanceOf(ApiException.class);
        assertThat(((ApiException) thrown).code()).isEqualTo(ErrorCode.NOT_FOUND);
    }

    private long insertUser(String email, String role) {
        return jdbc.sql("""
                INSERT INTO users (full_name, email, password_hash, role)
                VALUES ('Workflow IT', :email, '$argon2id$dummy', :role) RETURNING user_id""")
                .param("email", email).param("role", role).query(Long.class).single();
    }

    private long insertComplaint(long userId) {
        return jdbc.sql("""
                INSERT INTO complaints (user_id, category_id, title, description, location)
                VALUES (:user, 1, 'Workflow IT', 'test', ST_SetSRID(ST_MakePoint(73.676, 18.744), 4326))
                RETURNING complaint_id""")
                .param("user", userId).query(Long.class).single();
    }
}
