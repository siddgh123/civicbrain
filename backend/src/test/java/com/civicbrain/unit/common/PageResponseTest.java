package com.civicbrain.unit.common;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.List;

import org.junit.jupiter.api.Test;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;

import com.civicbrain.common.ApiException;
import com.civicbrain.common.ErrorCode;
import com.civicbrain.common.PageResponse;

/** List shape of docs/04_API_CONTRACT.md conventions: items, page, size, totalItems, totalPages; size <= 100. */
class PageResponseTest {

    @Test
    void mapsASpringPage() {
        PageResponse<String> page = PageResponse.of(new PageImpl<>(List.of("a", "b"), PageRequest.of(1, 2), 5));
        assertThat(page).isEqualTo(new PageResponse<>(List.of("a", "b"), 1, 2, 5, 3));
    }

    @Test
    void pageableUsesDefaultsAndRejectsOutOfRangeValues() {
        Pageable p = PageResponse.pageable(null, null, Sort.by("submittedAt"));
        assertThat(p.getPageNumber()).isZero();
        assertThat(p.getPageSize()).isEqualTo(20);
        assertThat(PageResponse.pageable(2, 100, Sort.unsorted()).getPageSize()).isEqualTo(100);

        assertThatThrownBy(() -> PageResponse.pageable(0, 101, Sort.unsorted()))
                .isInstanceOfSatisfying(ApiException.class, e -> {
                    assertThat(e.code()).isEqualTo(ErrorCode.VALIDATION_FAILED);
                    assertThat(e.fieldErrors().getFirst().field()).isEqualTo("size");
                });
        assertThatThrownBy(() -> PageResponse.pageable(-1, 20, Sort.unsorted()))
                .isInstanceOfSatisfying(ApiException.class, e -> assertThat(e.fieldErrors().getFirst().field()).isEqualTo("page"));
    }
}
