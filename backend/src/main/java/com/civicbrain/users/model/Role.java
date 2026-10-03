package com.civicbrain.users.model;

/** {@code users.role} (CHECK list of the schema). FIELD_TEAM is legacy: such rows exist only in old data and get no area. */
public enum Role {
    CITIZEN, OFFICER, ADMIN, CONTRACTOR, CONTRACTOR_STAFF, FIELD_TEAM;

    /** Refresh-token lifetimes of docs/07_SECURITY.md §1: absolute and idle, in hours. */
    public long refreshAbsoluteHours() {
        return switch (this) {
            case CITIZEN -> 30 * 24;
            case OFFICER, ADMIN -> 24;
            default -> 7 * 24;
        };
    }

    public long refreshIdleHours() {
        return switch (this) {
            case CITIZEN -> 7 * 24;
            case OFFICER, ADMIN -> 1;
            default -> 3 * 24;
        };
    }
}
