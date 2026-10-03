package com.civicbrain.notifications.service;

import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.springframework.stereotype.Component;

/**
 * The small {@code {{name}}} replacer of docs/02_ARCHITECTURE.md §5 rule 6. Only the 16 placeholders of the seeded
 * templates exist; an unknown name, a missing value or a broken {@code {{} is a {@link TemplateException} - never a
 * blank. {@link Mode#HTML} escapes every value (the template text itself is plain text); {@link Mode#TEXT} keeps
 * values as they are (e-mail subject, plain-text part, WhatsApp). Values are inserted once - a value that looks
 * like a placeholder is not expanded again.
 */
@Component
public class TemplateRenderer {

    /** The 16 placeholders of 02 §5 rule 6, in that order. */
    public static final List<String> KNOWN = List.of("citizen_name", "public_ref", "category", "location_text", "submitted_at",
            "contractor_name", "planned_date", "inspection_notes", "expected_completion", "master_ref", "remarks", "track_url",
            "plan_code", "job_count", "plan_url", "review_url");

    private static final Pattern PLACEHOLDER = Pattern.compile("\\{\\{([a-z_]+)}}");

    public enum Mode { HTML, TEXT }

    /** A template that cannot be rendered: unknown placeholder, missing value, broken braces. */
    public static class TemplateException extends RuntimeException {
        public TemplateException(String message) {
            super(message);
        }
    }

    public String render(String template, Map<String, String> values, Mode mode) {
        if (template == null) {
            return null;
        }
        Matcher m = PLACEHOLDER.matcher(template);
        StringBuilder out = new StringBuilder(template.length() + 64);
        int last = 0;
        while (m.find()) {
            literal(template.substring(last, m.start()), out);
            String name = m.group(1);
            if (!KNOWN.contains(name)) {
                throw new TemplateException("unknown placeholder {{" + name + "}}");
            }
            String value = values.get(name);
            if (value == null) {
                throw new TemplateException("no value for {{" + name + "}}");
            }
            out.append(mode == Mode.HTML ? escape(value) : value);
            last = m.end();
        }
        literal(template.substring(last), out);
        return out.toString();
    }

    /** Placeholder names used in a template, in order of first use. */
    public static Set<String> placeholders(String template) {
        Set<String> names = new LinkedHashSet<>();
        if (template != null) {
            Matcher m = PLACEHOLDER.matcher(template);
            while (m.find()) {
                names.add(m.group(1));
            }
        }
        return names;
    }

    /** HTML text escaping for values: {@code & < > " '}. */
    public static String escape(String value) {
        StringBuilder sb = new StringBuilder(value.length() + 16);
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            switch (c) {
                case '&' -> sb.append("&amp;");
                case '<' -> sb.append("&lt;");
                case '>' -> sb.append("&gt;");
                case '"' -> sb.append("&quot;");
                case '\'' -> sb.append("&#39;");
                default -> sb.append(c);
            }
        }
        return sb.toString();
    }

    private static void literal(String text, StringBuilder out) {
        if (text.contains("{{") || text.contains("}}")) {
            throw new TemplateException("malformed placeholder near \"" + text.strip() + "\"");
        }
        out.append(text);
    }
}
