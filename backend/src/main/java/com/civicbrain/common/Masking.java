package com.civicbrain.common;

/** Personal data in logs and audit rows (docs/07_SECURITY.md §6): masked phones, no CR/LF (log injection). */
public final class Masking {

    private Masking() {
    }

    /** {@code +919876544321} → {@code +91******4321}; null stays null. */
    public static String phone(String phone) {
        if (phone == null) {
            return null;
        }
        String p = phone.strip();
        if (p.length() <= 4) {
            return "****";
        }
        int keepStart = p.startsWith("+") ? Math.min(3, p.length() - 4) : 0;
        return p.substring(0, keepStart) + "*".repeat(p.length() - 4 - keepStart) + p.substring(p.length() - 4);
    }

    /** An e-mail stays (lower case, safe characters); anything else is treated as a phone and masked. */
    public static String identifier(String identifier) {
        if (identifier == null) {
            return null;
        }
        return identifier.contains("@") ? logSafe(identifier, 255) : phone(logSafe(identifier, 30));
    }

    /** Control characters (CR, LF, ...) replaced by spaces, cut to {@code max} characters; null stays null. */
    public static String logSafe(String value, int max) {
        if (value == null) {
            return null;
        }
        String clean = value.replaceAll("\\p{Cntrl}", " ");
        return clean.length() > max ? clean.substring(0, max) : clean;
    }
}
