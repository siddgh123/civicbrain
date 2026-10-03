package com.civicbrain.config;

import java.util.Base64;

/**
 * A secret setting (key, token, password). {@link #toString()} never shows the value, so a failed start-up
 * validation ("rejected value [...]") or an accidental log line cannot print it (docs/07_SECURITY.md §6).
 */
public record Secret(String value) {

    public static Secret of(String value) {
        return new Secret(value);
    }

    public boolean isBlank() {
        return value == null || value.isBlank();
    }

    /** The base64-decoded key bytes (.env.example: every key is base64 from scripts/dev/new-secret.ps1). */
    public byte[] bytes() {
        return Base64.getDecoder().decode(value.strip());
    }

    @Override
    public String toString() {
        return isBlank() ? "[empty]" : "[hidden]";
    }
}
