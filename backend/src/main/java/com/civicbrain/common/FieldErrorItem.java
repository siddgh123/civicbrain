package com.civicbrain.common;

/**
 * One entry of {@code fieldErrors}: the request field, a constraint code (NOT_BLANK, MAX, UNKNOWN_FIELD, ...) and a
 * short English message.
 */
public record FieldErrorItem(String field, String code, String message) {
}
