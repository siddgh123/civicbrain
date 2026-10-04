package com.civicbrain.common;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.stream.Collectors;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.MessageSourceResolvable;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.authentication.AuthenticationTrustResolver;
import org.springframework.security.authentication.AuthenticationTrustResolverImpl;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.validation.FieldError;
import org.springframework.web.ErrorResponse;
import org.springframework.web.HttpMediaTypeException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.context.request.async.AsyncRequestNotUsableException;
import org.springframework.web.method.annotation.HandlerMethodValidationException;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.servlet.resource.NoResourceFoundException;
import org.springframework.http.converter.HttpMessageNotReadableException;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.ConstraintViolationException;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.exc.MismatchedInputException;
import tools.jackson.databind.exc.UnrecognizedPropertyException;

/**
 * The one error advice (rule 10): every exception → RFC 9457 body with {@code code}, {@code requestId} and
 * {@code fieldErrors} (docs/12_ERROR_HANDLING.md §1-§3). Unexpected errors are logged with their stack trace and
 * answered 500 INTERNAL_ERROR without any internals.
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);
    private static final AuthenticationTrustResolver TRUST = new AuthenticationTrustResolverImpl();
    private static final String CHECK_FIELDS = "Please check the highlighted fields.";

    @ExceptionHandler(ApiException.class)
    ResponseEntity<ApiProblem> api(ApiException e, HttpServletRequest request) {
        return respond(e, request, null);
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    ResponseEntity<ApiProblem> invalidBody(MethodArgumentNotValidException e, HttpServletRequest request) {
        List<FieldErrorItem> fields = new ArrayList<>();
        for (FieldError f : e.getBindingResult().getFieldErrors()) {
            fields.add(new FieldErrorItem(f.getField(), constraintCode(f.getCode()), f.getDefaultMessage()));
        }
        e.getBindingResult().getGlobalErrors().forEach(g ->
                fields.add(new FieldErrorItem(g.getObjectName(), constraintCode(g.getCode()), g.getDefaultMessage())));
        return respond(new ApiException(ErrorCode.VALIDATION_FAILED, CHECK_FIELDS, fields), request, null);
    }

    @ExceptionHandler(HandlerMethodValidationException.class)
    ResponseEntity<ApiProblem> invalidParameters(HandlerMethodValidationException e, HttpServletRequest request) {
        List<FieldErrorItem> fields = new ArrayList<>();
        e.getParameterValidationResults().forEach(result -> {
            String parameter = result.getMethodParameter().getParameterName();
            for (MessageSourceResolvable error : result.getResolvableErrors()) {
                String field = error instanceof FieldError f ? f.getField() : parameter;
                fields.add(new FieldErrorItem(field, constraintCode(lastCode(error)), error.getDefaultMessage()));
            }
        });
        return respond(new ApiException(ErrorCode.VALIDATION_FAILED, CHECK_FIELDS, fields), request, null);
    }

    @ExceptionHandler(ConstraintViolationException.class)
    ResponseEntity<ApiProblem> constraintViolation(ConstraintViolationException e, HttpServletRequest request) {
        List<FieldErrorItem> fields = e.getConstraintViolations().stream().map(v -> {
            String path = v.getPropertyPath().toString();
            String field = path.contains(".") ? path.substring(path.lastIndexOf('.') + 1) : path;
            String annotation = v.getConstraintDescriptor().getAnnotation().annotationType().getSimpleName();
            return new FieldErrorItem(field, constraintCode(annotation), v.getMessage());
        }).collect(Collectors.toList());
        return respond(new ApiException(ErrorCode.VALIDATION_FAILED, CHECK_FIELDS, fields), request, null);
    }

    /** Unknown JSON field or a value of the wrong type/enum → 400 VALIDATION_FAILED; unreadable JSON → MALFORMED_REQUEST. */
    @ExceptionHandler(HttpMessageNotReadableException.class)
    ResponseEntity<ApiProblem> unreadable(HttpMessageNotReadableException e, HttpServletRequest request) {
        Throwable cause = e.getMostSpecificCause();
        if (cause instanceof UnrecognizedPropertyException unknown) {
            return respond(ApiException.validation(jsonPath(unknown), "UNKNOWN_FIELD", "is not allowed"), request, null);
        }
        if (cause instanceof MismatchedInputException mismatch && !mismatch.getPath().isEmpty()) {
            return respond(ApiException.validation(jsonPath(mismatch), "INVALID_VALUE", "has an invalid value"), request, null);
        }
        return respond(new ApiException(ErrorCode.MALFORMED_REQUEST, "The request body could not be read."), request, null);
    }

    @ExceptionHandler(MissingServletRequestParameterException.class)
    ResponseEntity<ApiProblem> missingParameter(MissingServletRequestParameterException e, HttpServletRequest request) {
        return respond(ApiException.validation(e.getParameterName(), "REQUIRED", "is required"), request, null);
    }

    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    ResponseEntity<ApiProblem> typeMismatch(MethodArgumentTypeMismatchException e, HttpServletRequest request) {
        return respond(ApiException.validation(e.getName(), "INVALID_VALUE", "has an invalid value"), request, null);
    }

    @ExceptionHandler(HttpMediaTypeException.class)
    ResponseEntity<ApiProblem> mediaType(HttpMediaTypeException e, HttpServletRequest request) {
        return respond(new ApiException(ErrorCode.MALFORMED_REQUEST, "Wrong content type."), request, null);
    }

    @ExceptionHandler(MaxUploadSizeExceededException.class)
    ResponseEntity<ApiProblem> tooLarge(MaxUploadSizeExceededException e, HttpServletRequest request) {
        return respond(new ApiException(ErrorCode.FILE_TOO_LARGE, "Photo is too large."), request, null);
    }

    @ExceptionHandler(NoResourceFoundException.class)
    ResponseEntity<ApiProblem> noResource(NoResourceFoundException e, HttpServletRequest request) {
        return respond(new ApiException(ErrorCode.NOT_FOUND, "Not found."), request, null);
    }

    /** Method security: anonymous → 401, signed in → 403 (the filter chain handles the URL rules). */
    @ExceptionHandler(AccessDeniedException.class)
    ResponseEntity<ApiProblem> accessDenied(AccessDeniedException e, HttpServletRequest request) {
        var authentication = SecurityContextHolder.getContext().getAuthentication();
        boolean anonymous = authentication == null || TRUST.isAnonymous(authentication);
        return respond(anonymous ? new ApiException(ErrorCode.UNAUTHENTICATED, "Please log in.")
                : new ApiException(ErrorCode.FORBIDDEN, "You are not allowed to do this."), request, null);
    }

    @ExceptionHandler(AuthenticationException.class)
    ResponseEntity<ApiProblem> authentication(AuthenticationException e, HttpServletRequest request) {
        return respond(new ApiException(ErrorCode.UNAUTHENTICATED, "Please log in."), request, null);
    }

    /**
     * The client closed the connection while the response was written (e.g. the SPA aborts a photo request when the
     * page changes): nothing can be sent any more and it is not a server error (12 §2), so DEBUG only. A void handler
     * with the response parameter counts as fully handled (no problem body is written to the closed connection).
     */
    @ExceptionHandler(AsyncRequestNotUsableException.class)
    void clientGone(AsyncRequestNotUsableException e, HttpServletRequest request, HttpServletResponse response) {
        log.debug("{} {} -> client closed the connection", request.getMethod(), request.getRequestURI());
    }

    /** Database errors (12 §3), Spring MVC's own errors by status, and everything unexpected → 500. */
    @ExceptionHandler(Exception.class)
    ResponseEntity<ApiProblem> unexpected(Exception e, HttpServletRequest request) {
        var database = DbErrorTranslator.translate(e);
        if (database.isPresent()) {
            return respond(database.get(), request, e);
        }
        if (e instanceof ErrorResponse spring && spring.getStatusCode().is4xxClientError()) {
            int status = spring.getStatusCode().value();
            ErrorCode code = status == 404 ? ErrorCode.NOT_FOUND : ErrorCode.MALFORMED_REQUEST;
            return respond(new ApiException(code, status, status == 405 ? "Method not allowed." : "The request was not accepted."),
                    request, null);
        }
        return respond(new ApiException(ErrorCode.INTERNAL_ERROR, "Something went wrong."), request, e);
    }

    private static ResponseEntity<ApiProblem> respond(ApiException e, HttpServletRequest request, Throwable cause) {
        if (cause != null && e.status() >= 500) {
            if (e.code() == ErrorCode.DEPENDENCY_UNAVAILABLE) {
                log.warn("{} {} -> 503 dependency unavailable: {}", request.getMethod(), request.getRequestURI(), cause.toString());
            } else {
                log.error("{} {} -> 500 unexpected error", request.getMethod(), request.getRequestURI(), cause);
            }
        }
        var response = ResponseEntity.status(e.status()).contentType(MediaType.parseMediaType(ApiProblem.MEDIA_TYPE));
        if (e instanceof RateLimitedException limited) {
            response.header(HttpHeaders.RETRY_AFTER, Long.toString(limited.retryAfterSeconds()));
        }
        return response.body(ApiProblem.of(e, RequestIdFilter.currentId(request)));
    }

    /** NotBlank → NOT_BLANK, Max → MAX, DecimalMin → DECIMAL_MIN, typeMismatch → TYPE_MISMATCH. */
    static String constraintCode(String code) {
        if (code == null || code.isBlank()) {
            return "INVALID";
        }
        return code.replaceAll("([a-z0-9])([A-Z])", "$1_$2").toUpperCase(Locale.ROOT);
    }

    private static String lastCode(MessageSourceResolvable error) {
        String[] codes = error.getCodes();
        return codes == null || codes.length == 0 ? null : codes[codes.length - 1];
    }

    private static String jsonPath(JacksonException e) {
        return e.getPath().stream()
                .map(ref -> ref.getPropertyName() != null ? ref.getPropertyName() : "[" + ref.getIndex() + "]")
                .collect(Collectors.joining(".")).replace(".[", "[");
    }
}
