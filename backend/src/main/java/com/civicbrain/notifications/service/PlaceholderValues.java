package com.civicbrain.notifications.service;

import java.util.HashMap;
import java.util.Map;

import org.springframework.stereotype.Component;

import com.civicbrain.config.AppProperties;
import com.civicbrain.notifications.repo.NotificationRepository.Facts;
import com.civicbrain.notifications.repo.NotificationRepository.Recipient;

/**
 * The values of the 16 placeholders (docs/02_ARCHITECTURE.md §5 rule 6) for one recipient of one event. A value is
 * present only when its fact exists (a template that needs a missing one fails to render - never a blank);
 * {@code remarks} is always present ("" when the status change had none). Links: {@code track_url} =
 * {@code APP_BASE_URL/c/<publicRef>}, {@code plan_url} = {@code /contractor/plans/<id>}, {@code review_url} =
 * {@code /officer/complaints/<id>}. Dates in Asia/Kolkata ({@link MessageFormats}).
 */
@Component
public class PlaceholderValues {

    private final String baseUrl;

    public PlaceholderValues(AppProperties app) {
        this.baseUrl = app.baseUrl();
    }

    public Map<String, String> of(Facts f, Recipient recipient, String remarks) {
        Map<String, String> v = new HashMap<>();
        put(v, "citizen_name", recipient.fullName());
        put(v, "public_ref", f.publicRef());
        put(v, "category", f.category());
        put(v, "location_text", locationText(f));
        if (f.submittedAt() != null) {
            v.put("submitted_at", MessageFormats.dateTime(f.submittedAt()));
        }
        put(v, "contractor_name", f.contractorName());
        if (f.plannedDate() != null) {
            v.put("planned_date", MessageFormats.date(f.plannedDate()));
        }
        put(v, "inspection_notes", f.inspectionNotes());
        if (f.expectedCompletion() != null) {
            v.put("expected_completion", MessageFormats.date(f.expectedCompletion()));
        }
        put(v, "master_ref", f.masterRef());
        v.put("remarks", remarks == null ? "" : remarks.strip());
        if (f.publicRef() != null) {
            v.put("track_url", baseUrl + "/c/" + f.publicRef());
        }
        put(v, "plan_code", f.planCode());
        if (f.jobCount() != null) {
            v.put("job_count", Integer.toString(f.jobCount()));
        }
        if (f.actionPlanId() != null) {
            v.put("plan_url", baseUrl + "/contractor/plans/" + f.actionPlanId());
        }
        if (f.complaintId() != null) {
            v.put("review_url", baseUrl + "/officer/complaints/" + f.complaintId());
        }
        return v;
    }

    /** Landmark, else the address text, else "Ward N". */
    static String locationText(Facts f) {
        if (f.landmark() != null && !f.landmark().isBlank()) {
            return f.landmark().strip();
        }
        if (f.addressText() != null && !f.addressText().isBlank()) {
            return f.addressText().strip();
        }
        return f.wardNumber() == null ? null : "Ward " + f.wardNumber();
    }

    private static void put(Map<String, String> v, String key, String value) {
        if (value != null && !value.isBlank()) {
            v.put(key, value.strip());
        }
    }
}
