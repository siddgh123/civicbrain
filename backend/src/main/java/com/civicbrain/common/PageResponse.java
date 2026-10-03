package com.civicbrain.common;

import java.util.List;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;

/**
 * List shape of every list endpoint (docs/04_API_CONTRACT.md conventions):
 * {@code {"items": [...], "page": 0, "size": 20, "totalItems": 57, "totalPages": 3}}, {@code size <= 100}.
 */
public record PageResponse<T>(List<T> items, int page, int size, long totalItems, int totalPages) {

    public static final int DEFAULT_SIZE = 20;
    public static final int MAX_SIZE = 100;

    public static <T> PageResponse<T> of(Page<T> page) {
        return new PageResponse<>(page.getContent(), page.getNumber(), page.getSize(), page.getTotalElements(), page.getTotalPages());
    }

    /** {@code ?page=&size=} → Pageable (defaults 0 / 20); out of range → 400 VALIDATION_FAILED on that field. */
    public static Pageable pageable(Integer page, Integer size, Sort sort) {
        int p = page == null ? 0 : page;
        int s = size == null ? DEFAULT_SIZE : size;
        if (p < 0) {
            throw ApiException.validation("page", "MIN", "must be 0 or more");
        }
        if (s < 1 || s > MAX_SIZE) {
            throw ApiException.validation("size", "RANGE", "must be between 1 and " + MAX_SIZE);
        }
        return PageRequest.of(p, s, sort == null ? Sort.unsorted() : sort);
    }
}
