package com.civicbrain.unit.common;

import static org.assertj.core.api.Assertions.assertThat;

import java.sql.SQLTransientConnectionException;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.postgresql.util.PSQLException;
import org.postgresql.util.ServerErrorMessage;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.jdbc.CannotGetJdbcConnectionException;
import org.springframework.transaction.CannotCreateTransactionException;

import com.civicbrain.common.ApiException;
import com.civicbrain.common.DbErrorTranslator;
import com.civicbrain.common.ErrorCode;

/** SQLSTATE + message-prefix mapping of docs/12_ERROR_HANDLING.md §3 (every prefix unit-tested). */
class DbErrorTranslatorTest {

    @ParameterizedTest(name = "{0} {1} -> {3} {2}")
    @CsvSource(delimiter = '|', value = {
            // V2 status guard
            "23514|Invalid complaint status transition SUBMITTED -> CLOSED (complaint 7)|409|INVALID_TRANSITION",
            "23514|New complaints must start in SUBMITTED (got VERIFIED)|400|VALIDATION_FAILED",
            "23514|new row for relation \"users\" violates check constraint \"ck_users_phone_format\"|400|VALIDATION_FAILED",
            "42501|Role CITIZEN may not move complaint 7 from SUBMITTED to VERIFIED|403|ROLE_NOT_ALLOWED",
            "42501|permission denied for table audit_logs|500|INTERNAL_ERROR",
            // fn_approve_action_plan / fn_assign_action_plan (P0001)
            "P0001|Action plan 12 not found|404|NOT_FOUND",
            "P0001|Only DRAFT plans can be approved (plan 12 is APPROVED)|409|PLAN_STATE_CONFLICT",
            "P0001|Plan 12 must be APPROVED before assignment (is DRAFT)|409|PLAN_STATE_CONFLICT",
            "P0001|Complaint 42 is not free for planning (wrong status or already in another plan)|409|COMPLAINT_NOT_PLANNABLE",
            "P0001|Contractor 3 is not active|422|CONTRACTOR_NOT_ELIGIBLE",
            "P0001|Contractor 3 is not registered for work type ROAD|422|CONTRACTOR_NOT_ELIGIBLE",
            "P0001|Job 5 not found|500|INTERNAL_ERROR",
            "P0001|something else entirely|500|INTERNAL_ERROR",
            // keys
            "23505|duplicate key value violates unique constraint \"uq_users_email\"|409|ALREADY_EXISTS",
            "23503|insert or update on table \"complaints\" violates foreign key constraint \"fk_x\"|404|NOT_FOUND",
            "23503|update or delete on table \"users\" violates foreign key constraint \"fk_x\" on table \"complaints\"|400|VALIDATION_FAILED",
            // concurrency, timeouts, connection
            "40001|could not serialize access due to concurrent update|503|DEPENDENCY_UNAVAILABLE",
            "40P01|deadlock detected|503|DEPENDENCY_UNAVAILABLE",
            "57014|canceling statement due to statement timeout|503|DEPENDENCY_UNAVAILABLE",
            "08006|connection failure|503|DEPENDENCY_UNAVAILABLE",
            "53300|too many connections|503|DEPENDENCY_UNAVAILABLE",
            "42P01|relation \"nope\" does not exist|500|INTERNAL_ERROR"})
    void mapsSqlStateAndMessage(String sqlState, String message, int status, ErrorCode code) {
        ApiException e = DbErrorTranslator.translate(sqlState, message, null);
        assertThat(e.code()).isEqualTo(code);
        assertThat(e.status()).isEqualTo(status);
        assertThat(e.detail()).doesNotContainIgnoringCase("violates").doesNotContain("SUBMITTED ->");
    }

    @Test
    void uniqueViolationNamesTheFieldFromTheConstraint() {
        ApiException email = DbErrorTranslator.translate("23505", "duplicate key", "uq_users_email_lower");
        assertThat(email.fieldErrors()).singleElement().satisfies(f -> {
            assertThat(f.field()).isEqualTo("email");
            assertThat(f.code()).isEqualTo("ALREADY_EXISTS");
        });
        assertThat(DbErrorTranslator.translate("23505", "duplicate key", "uq_users_phone").fieldErrors().getFirst().field())
                .isEqualTo("phone");
        assertThat(DbErrorTranslator.translate("23505", "duplicate key", "some_other_key").fieldErrors()).isEmpty();
    }

    @Test
    void notPlannableNamesTheComplaintByItsPublicRef() {
        assertThat(DbErrorTranslator.translate("P0001", "Complaint 42 is not free for planning (wrong status)", null).detail())
                .contains("CB-000042");
    }

    @Test
    void notEligibleNamesTheWorkType() {
        assertThat(DbErrorTranslator.translate("P0001", "Contractor 3 is not registered for work type ROAD", null).detail())
                .contains("ROAD");
    }

    @Test
    void findsThePostgresErrorInsideSpringExceptions() {
        PSQLException psql = new PSQLException(new ServerErrorMessage(
                "SERROR\0VERROR\0C23505\0Mduplicate key value violates unique constraint \"uq_users_phone\"\0nuq_users_phone\0"));
        ApiException e = DbErrorTranslator.translate(new DataIntegrityViolationException("could not execute", psql)).orElseThrow();
        assertThat(e.code()).isEqualTo(ErrorCode.ALREADY_EXISTS);
        assertThat(e.fieldErrors().getFirst().field()).isEqualTo("phone");
    }

    @Test
    void connectionProblemsWithoutSqlStateAreDependencyUnavailable() {
        assertThat(DbErrorTranslator.translate(new CannotGetJdbcConnectionException("pool",
                new SQLTransientConnectionException("Connection is not available, request timed out after 5000ms")))
                .orElseThrow().code()).isEqualTo(ErrorCode.DEPENDENCY_UNAVAILABLE);
        assertThat(DbErrorTranslator.translate(new CannotCreateTransactionException("no connection"))
                .orElseThrow().code()).isEqualTo(ErrorCode.DEPENDENCY_UNAVAILABLE);
    }

    @Test
    void nonDatabaseExceptionsAreNotTranslated() {
        assertThat(DbErrorTranslator.translate(new IllegalStateException("x"))).isEmpty();
    }
}
