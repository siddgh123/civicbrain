package com.civicbrain.files.api;

import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.civicbrain.auth.api.CurrentUser;
import com.civicbrain.common.ApiException;
import com.civicbrain.common.ErrorCode;
import com.civicbrain.files.repo.ImageAccessRepository;
import com.civicbrain.files.service.PhotoStorage;

/**
 * {@code GET /api/v1/files/{imageId}} (docs/04 §4): the stored JPEG for a caller who may see the complaint
 * ({@link ImageAccessRepository}), otherwise 404. Photos are never served from a static folder (07 §3).
 */
@RestController
@RequestMapping("/api/v1/files")
public class FileController {

    /** 04 §4: the browser may keep a photo for 5 minutes, shared caches never. */
    static final String CACHE_CONTROL = "private, max-age=300";

    private final ImageAccessRepository access;
    private final PhotoStorage storage;

    public FileController(ImageAccessRepository access, PhotoStorage storage) {
        this.access = access;
        this.storage = storage;
    }

    @GetMapping("/{imageId}")
    public ResponseEntity<byte[]> image(@PathVariable long imageId, Authentication authentication) {
        long userId = CurrentUser.id(authentication);
        byte[] bytes = access.visibleStorageKey(imageId, userId, role(authentication))
                .flatMap(storage::read)
                .orElseThrow(() -> new ApiException(ErrorCode.NOT_FOUND, "Not found."));
        return ResponseEntity.ok()
                .contentType(MediaType.IMAGE_JPEG)
                .header(HttpHeaders.CACHE_CONTROL, CACHE_CONTROL)
                .header(HttpHeaders.CONTENT_DISPOSITION, ContentDisposition.inline().filename(imageId + ".jpg").build().toString())
                .body(bytes);
    }

    /** The role of the bearer token ({@code ROLE_X} authority from the {@code roles} claim). */
    private static String role(Authentication authentication) {
        return authentication.getAuthorities().stream().map(GrantedAuthority::getAuthority)
                .filter(a -> a.startsWith("ROLE_")).map(a -> a.substring(5)).findFirst().orElse("");
    }
}
