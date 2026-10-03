package com.civicbrain.workflow;

import java.util.Objects;

/**
 * Who changes a status. The role is always set: with no role the V2 guard would skip its role check. Only
 * {@link ActorRole#SYSTEM} may act without a user id.
 */
public record Actor(Long userId, ActorRole role) {

    public Actor {
        Objects.requireNonNull(role, "role");
        if (userId == null && role != ActorRole.SYSTEM) {
            throw new IllegalArgumentException("Only the SYSTEM actor may have no user id");
        }
    }

    public static Actor user(long userId, ActorRole role) {
        return new Actor(userId, role);
    }

    public static Actor system() {
        return new Actor(null, ActorRole.SYSTEM);
    }
}
