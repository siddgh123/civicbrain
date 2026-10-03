package com.civicbrain.privacy.api;

import java.time.Duration;
import java.time.OffsetDateTime;

import org.springframework.http.CacheControl;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.civicbrain.common.ApiException;
import com.civicbrain.common.ErrorCode;
import com.civicbrain.common.Times;
import com.civicbrain.privacy.repo.PrivacyRepository;

/** {@code GET /public/privacy-notice}: the current versioned notice shown at registration (FR-60, 04 §3, 07 §7). */
@RestController
@RequestMapping("/api/v1/public")
public class PrivacyNoticeController {

    public record PrivacyNoticeResponse(String version, OffsetDateTime publishedAt, String summary) {
    }

    private final PrivacyRepository privacy;

    public PrivacyNoticeController(PrivacyRepository privacy) {
        this.privacy = privacy;
    }

    @GetMapping("/privacy-notice")
    public ResponseEntity<PrivacyNoticeResponse> current() {
        var notice = privacy.currentNotice().orElseThrow(() -> new ApiException(ErrorCode.NOT_FOUND, "Not found."));
        return ResponseEntity.ok()
                .cacheControl(CacheControl.maxAge(Duration.ofSeconds(60)).cachePublic())
                .body(new PrivacyNoticeResponse(notice.version(), Times.api(notice.publishedAt()), notice.summary()));
    }
}
