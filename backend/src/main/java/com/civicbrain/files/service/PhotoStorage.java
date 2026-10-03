package com.civicbrain.files.service;

import java.io.IOException;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.Clock;
import java.time.ZoneOffset;
import java.time.ZonedDateTime;
import java.util.Optional;
import java.util.UUID;
import java.util.regex.Pattern;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

import com.civicbrain.common.ApiException;
import com.civicbrain.common.ErrorCode;
import com.civicbrain.config.AppProperties;

/**
 * Photos on local disk under {@code STORAGE_ROOT} (outside the web root, docs/02_ARCHITECTURE.md §1): key
 * {@code photos/<yyyy>/<mm>/<uuid>.jpg} (UTC month, random name). File + DB strategy of docs/12_ERROR_HANDLING.md §5:
 * the file is written to its final path inside the caller's transaction and deleted again if that transaction rolls
 * back. A failed write is 503 DEPENDENCY_UNAVAILABLE (no DB row is committed). Reads accept only keys of this shape,
 * so a stored key can never point outside the root.
 */
@Component
public class PhotoStorage {

    private static final Logger log = LoggerFactory.getLogger(PhotoStorage.class);
    private static final Pattern KEY = Pattern.compile("^photos/\\d{4}/\\d{2}/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\\.jpg$");

    /** {@code storageKey} for the DB row, {@code fileName} = the random name (never the client's file name). */
    public record Stored(String storageKey, String fileName, Path path) {
        public String fileUrl() {
            return "storage://" + storageKey;
        }
    }

    private final Path root;
    private final Clock clock;

    public PhotoStorage(AppProperties app, Clock clock) {
        this.root = Path.of(app.storageRoot()).toAbsolutePath().normalize();
        this.clock = clock;
    }

    public Stored store(byte[] jpeg) {
        ZonedDateTime now = ZonedDateTime.now(clock).withZoneSameInstant(ZoneOffset.UTC);
        String name = UUID.randomUUID() + ".jpg";
        String key = "photos/%04d/%02d/%s".formatted(now.getYear(), now.getMonthValue(), name);
        Path target = root.resolve(key).normalize();
        try {
            Files.createDirectories(target.getParent());
            Path temp = Files.createTempFile(target.getParent(), ".upload-", ".tmp");
            try {
                Files.write(temp, jpeg);
                moveIntoPlace(temp, target);
            } finally {
                Files.deleteIfExists(temp);
            }
        } catch (IOException | SecurityException e) {
            log.warn("photo storage write failed: {}", e.getClass().getSimpleName());
            throw new ApiException(ErrorCode.DEPENDENCY_UNAVAILABLE, "Photo storage is not available. Please try again later.");
        }
        if (TransactionSynchronizationManager.isSynchronizationActive()) {
            TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
                @Override
                public void afterCompletion(int status) {
                    if (status != STATUS_COMMITTED) {
                        delete(target);
                    }
                }
            });
        }
        return new Stored(key, name, target);
    }

    /** The bytes of a stored photo; empty when the key has a strange shape or the file is missing. */
    public Optional<byte[]> read(String storageKey) {
        return path(storageKey).flatMap(p -> {
            try {
                return Optional.of(Files.readAllBytes(p));
            } catch (IOException e) {
                log.warn("stored photo missing or unreadable: {}", storageKey);
                return Optional.empty();
            }
        });
    }

    /** Absolute path of a stored key, only for keys this class creates. */
    public Optional<Path> path(String storageKey) {
        if (storageKey == null || !KEY.matcher(storageKey).matches()) {
            return Optional.empty();
        }
        Path p = root.resolve(storageKey).normalize();
        return p.startsWith(root) ? Optional.of(p) : Optional.empty();
    }

    private static void moveIntoPlace(Path temp, Path target) throws IOException {
        try {
            Files.move(temp, target, StandardCopyOption.ATOMIC_MOVE);
        } catch (AtomicMoveNotSupportedException e) {
            Files.move(temp, target);
        }
    }

    private static void delete(Path file) {
        try {
            Files.deleteIfExists(file);
        } catch (IOException e) {
            log.warn("could not delete the photo of a rolled-back upload: {}", file.getFileName());
        }
    }
}
