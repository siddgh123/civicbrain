package com.civicbrain.complaints.model;

/**
 * The citizen's one-tap depth answer for categories with {@code needs_depth_answer} (FR-10; V5
 * {@code complaints.depth_answer}): Pothole shallower than a finger / about a finger / deeper, Waterlogging below
 * the ankle / below the knee / above the knee.
 */
public enum DepthAnswer {
    SHALLOW, FINGER, DEEP
}
