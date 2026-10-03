package com.civicbrain.auth.service;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.stream.Collectors;

import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

import com.civicbrain.common.ApiException;
import com.civicbrain.common.ErrorCode;
import com.civicbrain.common.FieldErrorItem;

/**
 * docs/07_SECURITY.md §1 / FR-01: 12-128 characters (code points), any characters, no composition rules; not on the
 * local blocklist, not one repeated character, not built from the user's e-mail or name. Violation → 422
 * PASSWORD_POLICY with a field error.
 */
@Component
public class PasswordPolicy {

    public static final int MIN_LENGTH = 12;
    public static final int MAX_LENGTH = 128;
    private static final String BLOCKLIST = "security/common-passwords.txt";

    private final Set<String> blocklist;

    public PasswordPolicy() {
        try (var in = new ClassPathResource(BLOCKLIST).getInputStream();
             var reader = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8))) {
            blocklist = reader.lines().map(String::strip).filter(l -> !l.isEmpty() && !l.startsWith("#"))
                    .map(l -> l.toLowerCase(Locale.ROOT)).collect(Collectors.toUnmodifiableSet());
        } catch (IOException e) {
            throw new UncheckedIOException("password blocklist " + BLOCKLIST + " missing", e);
        }
    }

    /**
     * @param field    request field for the error ({@code password} / {@code newPassword})
     * @param password the candidate
     * @param email    the account's e-mail (may be null)
     * @param fullName the account's name (may be null)
     */
    public void check(String field, String password, String email, String fullName) {
        String problem = problem(password, email, fullName);
        if (problem != null) {
            throw new ApiException(ErrorCode.PASSWORD_POLICY, problem,
                    List.of(new FieldErrorItem(field, "PASSWORD_POLICY", problem)));
        }
    }

    /** The reason the password is refused, or null. */
    String problem(String password, String email, String fullName) {
        int length = password == null ? 0 : password.codePointCount(0, password.length());
        if (length < MIN_LENGTH || length > MAX_LENGTH) {
            return "Use 12 to 128 characters.";
        }
        String lower = password.toLowerCase(Locale.ROOT);
        String base = lower.replaceAll("[\\d\\p{Punct}\\s]+$", "");
        if (blocklist.contains(lower) || blocklist.contains(base) || password.codePoints().distinct().count() == 1) {
            return "This password is too common. Choose another one.";
        }
        String letters = alphanumeric(lower);
        for (String personal : new String[] {email, email == null ? null : email.split("@", 2)[0], fullName}) {
            String p = personal == null ? "" : alphanumeric(personal.toLowerCase(Locale.ROOT));
            if (p.length() >= 4 && letters.contains(p)) {
                return "Do not use your e-mail address or name in the password.";
            }
        }
        return null;
    }

    private static String alphanumeric(String s) {
        return s.replaceAll("[^\\p{L}\\p{N}]", "");
    }
}
