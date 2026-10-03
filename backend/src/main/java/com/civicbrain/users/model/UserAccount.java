package com.civicbrain.users.model;

import java.time.Instant;

/** One {@code users} row as the auth and profile code needs it (column names: db/SCHEMA_REFERENCE_after_V5.sql). */
public record UserAccount(
        long id,
        String fullName,
        String email,
        String phone,
        String passwordHash,
        Role role,
        boolean active,
        Instant emailVerifiedAt,
        boolean whatsappOptIn,
        boolean emailOptIn,
        String preferredLanguage,
        int failedLoginCount,
        Instant lockedUntil,
        boolean mustChangePassword,
        boolean totpEnabled,
        Instant tokenValidAfter) {

    public boolean emailVerified() {
        return emailVerifiedAt != null;
    }

    public boolean lockedAt(Instant now) {
        return lockedUntil != null && lockedUntil.isAfter(now);
    }

    @Override
    public String toString() {   // never print the hash, e-mail or phone
        return "UserAccount[id=" + id + ", role=" + role + "]";
    }
}
