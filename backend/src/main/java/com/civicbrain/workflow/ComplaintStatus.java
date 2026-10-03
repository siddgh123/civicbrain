package com.civicbrain.workflow;

/** The 11 values of the {@code ck_complaints_status} CHECK (docs/01_REQUIREMENTS.md §3, 03 §3.10). */
public enum ComplaintStatus {
    SUBMITTED, VERIFIED, REJECTED, MERGED, SCHEDULED, ASSIGNED, INSPECTED, IN_PROGRESS, COMPLETED, CLOSED, REOPENED
}
