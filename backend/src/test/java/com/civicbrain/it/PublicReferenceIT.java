package com.civicbrain.it;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

import java.util.ArrayList;
import java.util.List;

import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MvcResult;

import com.civicbrain.it.support.AuthItSupport;
import com.civicbrain.it.support.IntegrationTest;

import tools.jackson.databind.JsonNode;

/** {@code GET /public/categories} and {@code GET /public/wards} (docs/04 §3): no login, cached 60 s, 23 wards by number. */
@IntegrationTest
class PublicReferenceIT extends AuthItSupport {

    @Test
    void categoriesCarryWorkTypeAndTheDepthQuestionFlag() throws Exception {
        MvcResult r = mvc.perform(get("/api/v1/public/categories")).andReturn();
        assertThat(r.getResponse().getStatus()).isEqualTo(200);
        assertThat(r.getResponse().getHeader("Cache-Control")).isEqualTo("max-age=60, public");
        JsonNode list = body(r);
        assertThat(list.isArray()).isTrue();
        assertThat((long) list.size()).isEqualTo(jdbc.sql("SELECT count(*) FROM complaint_categories WHERE is_active").query(Long.class).single());
        JsonNode pothole = byName(list, "Pothole");
        assertThat(pothole.path("id").asLong()).isPositive();
        assertThat(pothole.path("workTypeCode").asString()).isEqualTo("ROAD");
        assertThat(pothole.path("citizenSelectable").asBoolean()).isTrue();
        assertThat(pothole.path("needsDepthAnswer").asBoolean()).isTrue();
        assertThat(byName(list, "Waterlogging").path("needsDepthAnswer").asBoolean()).isTrue();
        assertThat(byName(list, "Garbage Accumulation").path("needsDepthAnswer").asBoolean()).isFalse();
        assertThat(byName(list, "Garbage Accumulation").path("workTypeCode").asString()).isEqualTo("GARBAGE");
        assertThat(byName(list, "Road Damage").path("needsDepthAnswer").asBoolean()).isFalse();
    }

    @Test
    void wardsAreAGeoJsonFeatureCollectionOfThe23WardNumbers() throws Exception {
        MvcResult r = mvc.perform(get("/api/v1/public/wards")).andReturn();
        assertThat(r.getResponse().getStatus()).isEqualTo(200);
        assertThat(r.getResponse().getContentType()).startsWith("application/json");
        assertThat(r.getResponse().getHeader("Cache-Control")).isEqualTo("max-age=60, public");
        JsonNode fc = body(r);
        assertThat(fc.path("type").asString()).isEqualTo("FeatureCollection");
        assertThat(fc.path("features")).hasSize(23);
        List<Integer> numbers = new ArrayList<>();
        for (JsonNode f : fc.path("features")) {
            assertThat(f.path("type").asString()).isEqualTo("Feature");
            assertThat(f.path("geometry").path("type").asString()).isIn("Polygon", "MultiPolygon");
            assertThat(f.path("geometry").path("coordinates").size()).isPositive();
            numbers.add(f.path("properties").path("wardNumber").asInt());
        }
        assertThat(numbers).containsExactlyElementsOf(java.util.stream.IntStream.rangeClosed(1, 23).boxed().toList());
        // a second call within 60 s is served from the cache (same body)
        assertThat(mvc.perform(get("/api/v1/public/wards")).andReturn().getResponse().getContentAsString())
                .isEqualTo(r.getResponse().getContentAsString());
    }

    private static JsonNode byName(JsonNode list, String name) {
        for (JsonNode c : list) {
            if (name.equals(c.path("name").asString())) {
                return c;
            }
        }
        throw new AssertionError("category " + name + " missing");
    }
}
