package com.civicbrain.complaints.api;

import java.time.OffsetDateTime;
import java.util.UUID;

import com.civicbrain.complaints.model.CaptureMethod;
import com.civicbrain.complaints.model.DepthAnswer;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.PositiveOrZero;
import jakarta.validation.constraints.Size;

/**
 * The {@code data} part of {@code POST /citizen/complaints} (docs/04 §5; FR-10 lengths; 07 §3 Talegaon ranges).
 * Text is trimmed before validation. The accuracy has no 150 m limit here: more than 150 m is the separate 422
 * GPS_ACCURACY_TOO_LOW later in the validation order; the depth answer rule needs the category (checked by the
 * service).
 */
public record ComplaintData(
        @NotNull @Positive Long categoryId,
        @NotNull @Size(min = 5, max = 120) @Pattern(regexp = NO_CONTROL, message = "must not contain control characters") String title,
        @NotNull @Size(min = 10, max = 1000) @Pattern(regexp = TEXT, message = "must not contain control characters") String description,
        @Size(max = 200) @Pattern(regexp = NO_CONTROL, message = "must not contain control characters") String landmark,
        @NotNull @DecimalMin(value = "18.6", message = "is outside the Talegaon area")
        @DecimalMax(value = "18.8", message = "is outside the Talegaon area") Double latitude,
        @NotNull @DecimalMin(value = "73.6", message = "is outside the Talegaon area")
        @DecimalMax(value = "73.8", message = "is outside the Talegaon area") Double longitude,
        @NotNull @PositiveOrZero @DecimalMax("100000") Double locationAccuracyM,
        @NotNull OffsetDateTime locationCapturedAt,
        @DecimalMin("-180") @DecimalMax("180") Double devicePitchDeg,
        @DecimalMin("-180") @DecimalMax("180") Double deviceRollDeg,
        @NotNull UUID captureSessionId,
        @NotNull CaptureMethod captureMethod,
        @NotNull Boolean a4InFrame,
        DepthAnswer depthAnswer) {

    /** One line of text: no control characters at all. */
    static final String NO_CONTROL = "^[^\\p{Cntrl}]*$";
    /** Free text: line breaks and tabs allowed, other control characters not. */
    static final String TEXT = "^[^\\x00-\\x08\\x0B\\x0C\\x0E-\\x1F\\x7F]*$";

    public ComplaintData {
        title = strip(title);
        description = strip(description);
        landmark = strip(landmark);
        if (landmark != null && landmark.isEmpty()) {
            landmark = null;
        }
    }

    private static String strip(String s) {
        return s == null ? null : s.strip();
    }
}
