package com.civicbrain.unit.notifications;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.junit.jupiter.api.Test;

import com.civicbrain.notifications.service.MessageFormats;
import com.civicbrain.notifications.service.TemplateRenderer;
import com.civicbrain.notifications.service.TemplateRenderer.Mode;

/**
 * The {@code {{placeholder}}} replacer of docs/02_ARCHITECTURE.md §5 rule 6: HTML-escaping in HTML mode, an unknown
 * placeholder or a missing value is an error (never a blank), and every one of the 21 templates seeded by V2
 * renders with a full value map of the 16 placeholders - nothing like {@code {{} is left.
 */
class TemplateRendererTest {

    private static final Pattern ROW = Pattern.compile(
            "\\(\\s*'([A-Z_]+)'\\s*,\\s*'(EMAIL|WHATSAPP)'\\s*,\\s*(NULL|'[A-Z_]+')\\s*,\\s*(NULL|'(?:[^']|'')*')\\s*,\\s*"
                    + "'((?:[^']|'')*)'\\s*,\\s*(true|false)\\s*\\)");

    private record Seeded(String code, String channel, String subject, String body) {
    }

    private final TemplateRenderer renderer = new TemplateRenderer();

    @Test
    void everySeededTemplateRendersWithAFullValueMap() throws IOException {
        List<Seeded> templates = seededTemplates();
        assertThat(templates).hasSize(21);
        Map<String, String> values = fullValues();
        Set<String> used = new TreeSet<>();
        for (Seeded t : templates) {
            for (Mode mode : Mode.values()) {
                String body = renderer.render(t.body(), values, mode);
                assertThat(body).as(t.code() + "/" + t.channel() + " " + mode).doesNotContain("{{").doesNotContain("}}")
                        .doesNotContain("null");
                if (t.subject() != null) {
                    assertThat(renderer.render(t.subject(), values, Mode.TEXT)).doesNotContain("{{").doesNotContain("}}");
                }
            }
            used.addAll(TemplateRenderer.placeholders(t.body()));
            if (t.subject() != null) {
                used.addAll(TemplateRenderer.placeholders(t.subject()));
            }
        }
        assertThat(used).as("exactly the 16 placeholders of 02 §5 rule 6").containsExactlyInAnyOrderElementsOf(TemplateRenderer.KNOWN);
        assertThat(TemplateRenderer.KNOWN).hasSize(16);
    }

    @Test
    void htmlModeEscapesValuesTextModeKeepsThem() {
        Map<String, String> values = Map.of("citizen_name", "Asha <b>\"O'Neil\"</b> & Co", "public_ref", "CB-000042");
        String template = "Dear {{citizen_name}}, complaint {{public_ref}}.";
        assertThat(renderer.render(template, values, Mode.HTML))
                .isEqualTo("Dear Asha &lt;b&gt;&quot;O&#39;Neil&quot;&lt;/b&gt; &amp; Co, complaint CB-000042.");
        assertThat(renderer.render(template, values, Mode.TEXT)).isEqualTo("Dear Asha <b>\"O'Neil\"</b> & Co, complaint CB-000042.");
        // a value that itself looks like a placeholder is not expanded again
        assertThat(renderer.render("{{remarks}}", Map.of("remarks", "{{public_ref}}"), Mode.TEXT)).isEqualTo("{{public_ref}}");
        assertThat(renderer.render("Reason: {{remarks}}.", Map.of("remarks", ""), Mode.TEXT)).isEqualTo("Reason: .");
    }

    @Test
    void unknownPlaceholdersMissingValuesAndBrokenBracesAreErrors() {
        assertThatThrownBy(() -> renderer.render("Hi {{nickname}}", Map.of("nickname", "x"), Mode.TEXT))
                .isInstanceOf(TemplateRenderer.TemplateException.class).hasMessageContaining("unknown placeholder {{nickname}}");
        assertThatThrownBy(() -> renderer.render("Hi {{citizen_name}}", Map.of(), Mode.TEXT))
                .isInstanceOf(TemplateRenderer.TemplateException.class).hasMessageContaining("no value for {{citizen_name}}");
        Map<String, String> withNull = new HashMap<>();
        withNull.put("citizen_name", null);
        assertThatThrownBy(() -> renderer.render("Hi {{citizen_name}}", withNull, Mode.TEXT))
                .isInstanceOf(TemplateRenderer.TemplateException.class);
        assertThatThrownBy(() -> renderer.render("Hi {{ citizen_name }}", Map.of("citizen_name", "A"), Mode.TEXT))
                .isInstanceOf(TemplateRenderer.TemplateException.class).hasMessageContaining("malformed");
        assertThatThrownBy(() -> renderer.render("Hi {{citizen_name", Map.of("citizen_name", "A"), Mode.TEXT))
                .isInstanceOf(TemplateRenderer.TemplateException.class);
    }

    @Test
    void datesUseTheUiFormatInAsiaKolkata() {
        // 02:50 UTC = 08:20 IST (05_UI_SPEC.md §2: "5 Oct 2026, 8:20 am")
        assertThat(MessageFormats.dateTime(Instant.parse("2026-10-05T02:50:00Z"))).isEqualTo("5 Oct 2026, 8:20 am");
        assertThat(MessageFormats.dateTime(Instant.parse("2026-10-05T09:35:00Z"))).isEqualTo("5 Oct 2026, 3:05 pm");
        assertThat(MessageFormats.date(LocalDate.of(2026, 10, 7))).isEqualTo("7 Oct 2026");
    }

    // ------------------------------------------------------------------ helpers

    static Map<String, String> fullValues() {
        Map<String, String> v = new HashMap<>();
        v.put("citizen_name", "Asha Patil");
        v.put("public_ref", "CB-000123");
        v.put("category", "Pothole");
        v.put("location_text", "Near the temple");
        v.put("submitted_at", "5 Oct 2026, 8:20 am");
        v.put("contractor_name", "Talegaon Road Works (prototype)");
        v.put("planned_date", "6 Oct 2026");
        v.put("inspection_notes", "Pothole 0.6 x 0.4 m confirmed");
        v.put("expected_completion", "7 Oct 2026");
        v.put("master_ref", "CB-000100");
        v.put("remarks", "Not a municipal issue");
        v.put("track_url", "http://localhost:5173/c/CB-000123");
        v.put("plan_code", "AP-20261006-ROAD-01");
        v.put("job_count", "4");
        v.put("plan_url", "http://localhost:5173/contractor/plans/7");
        v.put("review_url", "http://localhost:5173/officer/complaints/123");
        return v;
    }

    /** The template rows of the V2 migration copy Flyway applies (classpath db/migration). */
    private static List<Seeded> seededTemplates() throws IOException {
        String sql;
        try (InputStream in = TemplateRendererTest.class.getResourceAsStream("/db/migration/V2__civicbrain_app_layer.sql")) {
            assertThat(in).isNotNull();
            sql = new String(in.readAllBytes(), StandardCharsets.UTF_8);
        }
        int start = sql.indexOf("INSERT INTO notification_templates");
        int end = sql.indexOf("ON CONFLICT (template_code, channel, locale)", start);
        assertThat(start).isPositive();
        assertThat(end).isGreaterThan(start);
        Matcher m = ROW.matcher(sql.substring(start, end));
        List<Seeded> rows = new ArrayList<>();
        while (m.find()) {
            rows.add(new Seeded(m.group(1), m.group(2), literal(m.group(4)), literal("'" + m.group(5) + "'")));
        }
        return rows;
    }

    private static String literal(String sql) {
        return "NULL".equals(sql) ? null : sql.substring(1, sql.length() - 1).replace("''", "'");
    }
}
