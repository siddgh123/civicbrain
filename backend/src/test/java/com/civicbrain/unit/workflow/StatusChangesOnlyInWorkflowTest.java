package com.civicbrain.unit.workflow;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.regex.Pattern;
import java.util.stream.Stream;

import org.junit.jupiter.api.Test;

/**
 * Complaint status changes only through {@code WorkflowActor.changeStatus} (docs/02_ARCHITECTURE.md §3): no
 * {@code setStatus(} and no SQL that sets {@code complaints.status} outside the {@code workflow} package. Other
 * entities use intention-revealing methods (markSent, approve, ...) instead of a setStatus setter.
 */
class StatusChangesOnlyInWorkflowTest {

    private static final Path SOURCES = Path.of("src", "main", "java");
    private static final Path WORKFLOW = SOURCES.resolve(Path.of("com", "civicbrain", "workflow"));

    /** Any setStatus( - entity setter or its call - except the HTTP status of a servlet response. */
    private static final Pattern SET_STATUS = Pattern.compile("(?<!response\\.)\\bsetStatus\\s*\\(");
    private static final Pattern SQL_STATUS_UPDATE =
            Pattern.compile("(?i)\\bupdate\\s+(public\\.)?complaints\\b[^;\"]*?\\bset\\b[^;\"]*?(?<![\\w.])status\\s*=");

    @Test
    void noComplaintStatusChangeOutsideTheWorkflowPackage() throws IOException {
        List<String> violations;
        try (Stream<Path> files = Files.walk(SOURCES)) {
            violations = files.filter(f -> f.toString().endsWith(".java"))
                    .filter(f -> !f.startsWith(WORKFLOW))
                    .filter(f -> violates(read(f)))
                    .map(Path::toString)
                    .toList();
        }
        assertThat(violations).as("use WorkflowActor.changeStatus(...) instead").isEmpty();
        assertThat(read(WORKFLOW.resolve("WorkflowActor.java"))).as("the scanner must see the real update").matches(s -> violates(s));
    }

    @Test
    void scannerRecognisesViolationsAndIgnoresOtherColumns() {
        assertThat(violates("complaint.setStatus(ComplaintStatus.CLOSED);")).isTrue();
        assertThat(violates("public void setStatus(String status) {")).isTrue();
        assertThat(violates("response.setStatus(401);")).isFalse();
        assertThat(violates("jdbc.sql(\"UPDATE complaints SET status = :s WHERE complaint_id = :id\")")).isTrue();
        assertThat(violates("\"\"\"\n update complaints\n    set ai_status = 'FAILED', status = 'VERIFIED'\n\"\"\"")).isTrue();
        assertThat(violates("jdbc.sql(\"UPDATE complaints SET ai_status = 'FAILED' WHERE complaint_id = :id\")")).isFalse();
        assertThat(violates("jdbc.sql(\"UPDATE notifications SET status = 'SENT'\")")).isFalse();
        assertThat(violates("job.markSucceeded();")).isFalse();
    }

    private static boolean violates(String source) {
        return SET_STATUS.matcher(source).find() || SQL_STATUS_UPDATE.matcher(source).find();
    }

    private static String read(Path file) {
        try {
            return Files.readString(file);
        } catch (IOException e) {
            throw new IllegalStateException(e);
        }
    }
}
