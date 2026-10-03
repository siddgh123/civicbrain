package com.civicbrain.common;

import java.sql.SQLException;
import java.sql.SQLTransientConnectionException;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.postgresql.util.PSQLException;
import org.postgresql.util.ServerErrorMessage;
import org.springframework.dao.DataAccessResourceFailureException;
import org.springframework.dao.QueryTimeoutException;
import org.springframework.transaction.CannotCreateTransactionException;

/**
 * Database errors → API errors by SQLSTATE and message prefix (docs/12_ERROR_HANDLING.md §3). This is the ONLY place
 * that reads database message text. The client never sees the database message itself.
 */
public final class DbErrorTranslator {

    private static final Pattern PLAN_NOT_FOUND = Pattern.compile("^Action plan \\S+ not found");
    private static final Pattern PLAN_NOT_DRAFT = Pattern.compile("^Only DRAFT plans");
    private static final Pattern PLAN_NOT_APPROVED = Pattern.compile("^Plan \\S+ must be APPROVED");
    private static final Pattern NOT_PLANNABLE = Pattern.compile("^Complaint (\\d+) is not free for planning");
    private static final Pattern CONTRACTOR_INACTIVE = Pattern.compile("^Contractor \\S+ is not active");
    private static final Pattern CONTRACTOR_WRONG_TYPE = Pattern.compile("^Contractor \\S+ is not registered for work type ([A-Z_]+)");
    private static final Pattern ROLE_GUARD = Pattern.compile("^Role \\S+ may not move complaint ");

    /** Unique constraint → request field (users: e-mail/phone, officers: employee code). */
    private static final Map<String, String> UNIQUE_FIELDS = Map.of(
            "uq_users_email", "email",
            "uq_users_email_lower", "email",
            "uq_users_phone", "phone",
            "uq_officers_employee_code", "employeeCode");

    private DbErrorTranslator() {
    }

    /** The API error for a database exception anywhere in the cause chain; empty if it is not a database error. */
    public static Optional<ApiException> translate(Throwable ex) {
        for (Throwable t = ex; t != null; t = t.getCause()) {
            if (t instanceof PSQLException psql && psql.getServerErrorMessage() != null) {
                ServerErrorMessage m = psql.getServerErrorMessage();
                return Optional.of(translate(m.getSQLState(), m.getMessage(), m.getConstraint()));
            }
            if (t instanceof SQLTransientConnectionException) {
                return Optional.of(unavailable());
            }
            if (t instanceof SQLException sql && sql.getSQLState() != null) {
                return Optional.of(translate(sql.getSQLState(), firstLine(sql.getMessage()), null));
            }
        }
        if (ex instanceof DataAccessResourceFailureException || ex instanceof CannotCreateTransactionException
                || ex instanceof QueryTimeoutException) {
            return Optional.of(unavailable());
        }
        return Optional.empty();
    }

    /** Maps one SQLSTATE + primary message (+ constraint name) to the API error. */
    public static ApiException translate(String sqlState, String message, String constraint) {
        String state = sqlState == null ? "" : sqlState;
        String msg = message == null ? "" : message;
        return switch (state) {
            case "23505" -> {
                String field = constraint == null ? null : UNIQUE_FIELDS.get(constraint);
                yield new ApiException(ErrorCode.ALREADY_EXISTS, "This value is already registered.",
                        field == null ? List.of() : List.of(new FieldErrorItem(field, "ALREADY_EXISTS", "is already registered")));
            }
            case "23503" -> msg.startsWith("insert or update")
                    ? new ApiException(ErrorCode.NOT_FOUND, "A referenced item does not exist.")
                    : new ApiException(ErrorCode.VALIDATION_FAILED, "The item is still in use.");
            case "23514" -> msg.startsWith("Invalid complaint status transition")
                    ? new ApiException(ErrorCode.INVALID_TRANSITION, "This complaint has already moved on. Refresh.")
                    : new ApiException(ErrorCode.VALIDATION_FAILED, "A value is not allowed.");
            // only the V2 guard is a user error; any other 42501 is a missing grant = our bug
            case "42501" -> ROLE_GUARD.matcher(msg).find()
                    ? new ApiException(ErrorCode.ROLE_NOT_ALLOWED, "You can't do this step.")
                    : internal();
            case "P0001" -> planFunctionError(msg);
            // serialization failure / deadlock: the caller retries up to 3 times, then this 503 (12 §3)
            case "40001", "40P01", "57014" -> unavailable();
            default -> state.startsWith("08") || state.startsWith("53") || state.startsWith("57P") ? unavailable() : internal();
        };
    }

    /** P0001 = plain RAISE EXCEPTION of fn_approve_action_plan / fn_assign_action_plan (V2). */
    private static ApiException planFunctionError(String msg) {
        if (PLAN_NOT_FOUND.matcher(msg).find()) {
            return new ApiException(ErrorCode.NOT_FOUND, "Not found.");
        }
        if (PLAN_NOT_DRAFT.matcher(msg).find() || PLAN_NOT_APPROVED.matcher(msg).find()) {
            return new ApiException(ErrorCode.PLAN_STATE_CONFLICT, "This plan has already moved on. Reload.");
        }
        Matcher notPlannable = NOT_PLANNABLE.matcher(msg);
        if (notPlannable.find()) {
            return new ApiException(ErrorCode.COMPLAINT_NOT_PLANNABLE,
                    "Complaint CB-%06d is not free for planning.".formatted(Long.parseLong(notPlannable.group(1))));
        }
        if (CONTRACTOR_INACTIVE.matcher(msg).find()) {
            return new ApiException(ErrorCode.CONTRACTOR_NOT_ELIGIBLE, "This contractor is not active.");
        }
        Matcher wrongType = CONTRACTOR_WRONG_TYPE.matcher(msg);
        if (wrongType.find()) {
            return new ApiException(ErrorCode.CONTRACTOR_NOT_ELIGIBLE,
                    "Choose a contractor registered for %s.".formatted(wrongType.group(1)));
        }
        return internal();
    }

    private static ApiException unavailable() {
        return new ApiException(ErrorCode.DEPENDENCY_UNAVAILABLE, "Service temporarily unavailable.");
    }

    private static ApiException internal() {
        return new ApiException(ErrorCode.INTERNAL_ERROR, "Something went wrong.");
    }

    private static String firstLine(String message) {
        if (message == null) {
            return "";
        }
        String line = message.lines().findFirst().orElse("");
        return line.startsWith("ERROR: ") ? line.substring("ERROR: ".length()) : line;
    }
}
