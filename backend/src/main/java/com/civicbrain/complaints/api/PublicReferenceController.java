package com.civicbrain.complaints.api;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.function.Supplier;

import org.springframework.http.CacheControl;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.civicbrain.complaints.repo.ReferenceRepository;

/**
 * {@code GET /public/categories} and {@code GET /public/wards} (docs/04 §3): no login, cached 60 s on the server and
 * in the browser. The wards are GeoJSON served as {@code application/json} (the SPA asks for JSON).
 */
@RestController
@RequestMapping("/api/v1/public")
public class PublicReferenceController {

    static final Duration CACHE = Duration.ofSeconds(60);

    public record CategoryResponse(long id, String name, String workTypeCode, boolean citizenSelectable, boolean needsDepthAnswer) {
    }

    private final Cached<List<CategoryResponse>> categories;
    private final Cached<String> wards;

    public PublicReferenceController(ReferenceRepository reference, Clock clock) {
        this.categories = new Cached<>(clock, () -> reference.activeCategories().stream()
                .map(c -> new CategoryResponse(c.id(), c.name(), c.workTypeCode(), c.citizenSelectable(), c.needsDepthAnswer()))
                .toList());
        this.wards = new Cached<>(clock, reference::wardsGeoJson);
    }

    @GetMapping("/categories")
    public ResponseEntity<List<CategoryResponse>> categories() {
        return ResponseEntity.ok().cacheControl(CacheControl.maxAge(CACHE).cachePublic()).body(categories.get());
    }

    @GetMapping(value = "/wards", produces = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<String> wards() {
        return ResponseEntity.ok().cacheControl(CacheControl.maxAge(CACHE).cachePublic())
                .contentType(MediaType.APPLICATION_JSON).body(wards.get());
    }

    /** A value computed at most once per 60 s (reference data changes only through migrations). */
    static final class Cached<T> {
        private final Clock clock;
        private final Supplier<T> loader;
        private volatile T value;
        private volatile Instant loadedAt = Instant.MIN;

        Cached(Clock clock, Supplier<T> loader) {
            this.clock = clock;
            this.loader = loader;
        }

        T get() {
            Instant now = clock.instant();
            T current = value;
            if (current == null || loadedAt.plus(CACHE).isBefore(now)) {
                synchronized (this) {
                    if (value == null || loadedAt.plus(CACHE).isBefore(now)) {
                        value = loader.get();
                        loadedAt = now;
                    }
                    current = value;
                }
            }
            return current;
        }
    }
}
