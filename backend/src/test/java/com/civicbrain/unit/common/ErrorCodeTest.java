package com.civicbrain.unit.common;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.Map;
import java.util.TreeMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

import org.junit.jupiter.api.Test;

import com.civicbrain.common.ErrorCode;

/** The enum holds exactly the codes (and HTTP statuses) of the table in docs/12_ERROR_HANDLING.md §2. */
class ErrorCodeTest {

    private static final Path DOC = Path.of("..", "docs", "12_ERROR_HANDLING.md");

    @Test
    void enumMatchesTheErrorTableOfDoc12() throws IOException {
        Map<String, Integer> documented = new TreeMap<>();
        Pattern row = Pattern.compile("^\\| (\\d{3}) \\| ([^|]+)\\|");
        Pattern code = Pattern.compile("`([A-Z_]+)`");
        boolean inTable = false;
        for (String line : Files.readAllLines(DOC)) {
            if (line.startsWith("## 2.")) {
                inTable = true;
            } else if (line.startsWith("## 3.")) {
                break;
            }
            Matcher r = row.matcher(line);
            if (inTable && r.find()) {
                Matcher c = code.matcher(r.group(2));
                while (c.find()) {
                    documented.put(c.group(1), Integer.parseInt(r.group(1)));
                }
            }
        }
        assertThat(documented).hasSizeGreaterThan(30);

        Map<String, Integer> implemented = Arrays.stream(ErrorCode.values())
                .collect(Collectors.toMap(Enum::name, ErrorCode::status, (a, b) -> a, TreeMap::new));
        assertThat(implemented).isEqualTo(documented);
    }

    @Test
    void everyCodeHasATitle() {
        assertThat(ErrorCode.values()).allSatisfy(c -> assertThat(c.title()).isNotBlank());
    }
}
