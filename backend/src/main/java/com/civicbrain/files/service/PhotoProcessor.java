package com.civicbrain.files.service;

import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.RenderingHints;
import java.awt.geom.AffineTransform;
import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.Map;

import javax.imageio.IIOImage;
import javax.imageio.ImageIO;
import javax.imageio.ImageReadParam;
import javax.imageio.ImageReader;
import javax.imageio.ImageWriteParam;
import javax.imageio.ImageWriter;
import javax.imageio.stream.ImageInputStream;
import javax.imageio.stream.ImageOutputStream;

import org.springframework.stereotype.Component;

import com.civicbrain.common.ApiException;
import com.civicbrain.common.ErrorCode;
import com.drew.imaging.ImageMetadataReader;
import com.drew.imaging.ImageProcessingException;
import com.drew.lang.GeoLocation;
import com.drew.metadata.Metadata;
import com.drew.metadata.exif.ExifIFD0Directory;
import com.drew.metadata.exif.ExifSubIFDDirectory;
import com.drew.metadata.exif.GpsDirectory;

/**
 * The photo upload pipeline (docs/07_SECURITY.md §3, 04 §5, 02 §1). {@link #check} runs the file checks in the
 * order of 04 §5 without decoding pixels: JPEG/PNG by magic bytes (415), ≤ 8 MB (413), shorter side ≥ 320 px
 * (422 IMAGE_TOO_SMALL), ≤ 40 MP from the header (422 IMAGE_TOO_LARGE_PIXELS, decompression-bomb guard).
 * {@link #process} keeps only the capture-time and GPS facts of the EXIF block (as data for the authenticity
 * checks), applies the EXIF orientation, scales the long side to ≤ 1920 px and re-encodes as JPEG q85 with no
 * metadata at all (re-encoding also removes any active content - 07 §3 compensating control), plus SHA-256.
 */
@Component
public class PhotoProcessor {

    public static final int MAX_BYTES = 8 * 1024 * 1024;
    public static final int MIN_SIDE_PX = 320;
    public static final long MAX_PIXELS = 40_000_000L;
    public static final int MAX_LONG_SIDE_PX = 1920;
    public static final float JPEG_QUALITY = 0.85f;
    public static final String STORED_MIME = "image/jpeg";

    private static final byte[] JPEG_MAGIC = {(byte) 0xFF, (byte) 0xD8, (byte) 0xFF};
    private static final byte[] PNG_MAGIC = {(byte) 0x89, 'P', 'N', 'G', 0x0D, 0x0A, 0x1A, 0x0A};

    public enum Format {
        JPEG("jpeg"), PNG("png");

        private final String imageIoName;

        Format(String imageIoName) {
            this.imageIoName = imageIoName;
        }
    }

    /** A file that passed the checks: its bytes, format and header dimensions. */
    public record Checked(byte[] bytes, Format format, int width, int height) {
    }

    /**
     * The stored photo: JPEG bytes (no metadata), their size and SHA-256 (hex), and the EXIF facts of the original
     * ({@code present}, optional {@code dateTimeOriginal}, {@code offsetTimeOriginal}, {@code gpsLatitude},
     * {@code gpsLongitude}, {@code gpsTimestamp}) for {@code complaint_images.exif_extracted}.
     */
    public record Processed(byte[] jpeg, int width, int height, String sha256, Map<String, Object> exif) {
    }

    public Checked check(byte[] bytes) {
        Format format = magic(bytes);
        if (format == null) {
            throw new ApiException(ErrorCode.FILE_TYPE_NOT_ALLOWED, "Only photos (JPG/PNG) are allowed.");
        }
        if (bytes.length > MAX_BYTES) {
            throw new ApiException(ErrorCode.FILE_TOO_LARGE, "Photo is too large (8 MB at most).");
        }
        int[] size = headerSize(bytes, format);
        int width = size[0];
        int height = size[1];
        if (Math.min(width, height) < MIN_SIDE_PX) {
            throw new ApiException(ErrorCode.IMAGE_TOO_SMALL,
                    "The photo is %d x %d pixels; at least %d pixels on each side are needed.".formatted(width, height, MIN_SIDE_PX));
        }
        if ((long) width * height > MAX_PIXELS) {
            throw new ApiException(ErrorCode.IMAGE_TOO_LARGE_PIXELS, "The photo has more than 40 megapixels.");
        }
        return new Checked(bytes, format, width, height);
    }

    public Processed process(Checked checked) {
        Map<String, Object> exif = new LinkedHashMap<>();
        int orientation = readExif(checked.bytes(), exif);
        BufferedImage decoded = decode(checked);
        BufferedImage upright = orient(decoded, orientation);
        BufferedImage scaled = scaleToRgb(upright);
        byte[] jpeg = encodeJpeg(scaled);
        return new Processed(jpeg, scaled.getWidth(), scaled.getHeight(), sha256(jpeg), exif);
    }

    // ------------------------------------------------------------------ checks

    private static Format magic(byte[] bytes) {
        if (bytes == null) {
            return null;
        }
        if (startsWith(bytes, JPEG_MAGIC)) {
            return Format.JPEG;
        }
        if (startsWith(bytes, PNG_MAGIC)) {
            return Format.PNG;
        }
        return null;
    }

    private static boolean startsWith(byte[] bytes, byte[] prefix) {
        if (bytes.length < prefix.length) {
            return false;
        }
        for (int i = 0; i < prefix.length; i++) {
            if (bytes[i] != prefix[i]) {
                return false;
            }
        }
        return true;
    }

    /** Width and height from the file header only (no pixel decoding); unreadable → 415. */
    private static int[] headerSize(byte[] bytes, Format format) {
        ImageReader reader = reader(format);
        try (ImageInputStream in = ImageIO.createImageInputStream(new ByteArrayInputStream(bytes))) {
            reader.setInput(in, true, true);
            return new int[] {reader.getWidth(0), reader.getHeight(0)};
        } catch (IOException | RuntimeException e) {
            throw unreadable();
        } finally {
            reader.dispose();
        }
    }

    // ------------------------------------------------------------------ EXIF

    /** Copies the capture-time and GPS facts into {@code facts}; returns the EXIF orientation (1 = none). */
    private static int readExif(byte[] bytes, Map<String, Object> facts) {
        Metadata metadata;
        try {
            metadata = ImageMetadataReader.readMetadata(new ByteArrayInputStream(bytes), bytes.length);
        } catch (ImageProcessingException | IOException | RuntimeException e) {
            facts.put("present", false);
            return 1;
        }
        ExifIFD0Directory ifd0 = metadata.getFirstDirectoryOfType(ExifIFD0Directory.class);
        ExifSubIFDDirectory sub = metadata.getFirstDirectoryOfType(ExifSubIFDDirectory.class);
        GpsDirectory gps = metadata.getFirstDirectoryOfType(GpsDirectory.class);
        facts.put("present", ifd0 != null || sub != null || gps != null);
        if (sub != null) {
            putText(facts, "dateTimeOriginal", sub.getString(ExifSubIFDDirectory.TAG_DATETIME_ORIGINAL));
            putText(facts, "offsetTimeOriginal", sub.getString(ExifSubIFDDirectory.TAG_TIME_ZONE_ORIGINAL));
        }
        if (gps != null) {
            GeoLocation location = gps.getGeoLocation();
            if (location != null && !location.isZero()) {
                facts.put("gpsLatitude", location.getLatitude());
                facts.put("gpsLongitude", location.getLongitude());
            }
            var gpsDate = gps.getGpsDate();
            if (gpsDate != null) {
                facts.put("gpsTimestamp", gpsDate.toInstant().toString());
            }
        }
        Integer orientation = ifd0 == null ? null : ifd0.getInteger(ExifIFD0Directory.TAG_ORIENTATION);
        return orientation == null || orientation < 1 || orientation > 8 ? 1 : orientation;
    }

    private static void putText(Map<String, Object> facts, String key, String value) {
        if (value != null) {
            String clean = value.replaceAll("\\p{Cntrl}", "").strip();
            if (!clean.isEmpty()) {
                facts.put(key, clean.length() > 40 ? clean.substring(0, 40) : clean);
            }
        }
    }

    // ------------------------------------------------------------------ pixels

    /** Decodes; very large photos are subsampled while decoding (to ≥ 2× the target size) to save memory. */
    private static BufferedImage decode(Checked checked) {
        ImageReader reader = reader(checked.format());
        try (ImageInputStream in = ImageIO.createImageInputStream(new ByteArrayInputStream(checked.bytes()))) {
            reader.setInput(in, true, true);
            ImageReadParam param = reader.getDefaultReadParam();
            int step = Math.max(1, Math.max(checked.width(), checked.height()) / (2 * MAX_LONG_SIDE_PX));
            if (step > 1) {
                param.setSourceSubsampling(step, step, 0, 0);
            }
            BufferedImage image = reader.read(0, param);
            if (image == null) {
                throw unreadable();
            }
            return image;
        } catch (IOException | RuntimeException e) {
            if (e instanceof ApiException api) {
                throw api;
            }
            throw unreadable();
        } finally {
            reader.dispose();
        }
    }

    /** EXIF orientation 2-8 applied to the pixels (the stored file has no orientation tag any more). */
    static BufferedImage orient(BufferedImage image, int orientation) {
        if (orientation <= 1) {
            return image;
        }
        int w = image.getWidth();
        int h = image.getHeight();
        boolean swap = orientation >= 5;
        AffineTransform t = new AffineTransform();
        switch (orientation) {
            case 2 -> { t.translate(w, 0); t.scale(-1, 1); }
            case 3 -> { t.translate(w, h); t.rotate(Math.PI); }
            case 4 -> { t.translate(0, h); t.scale(1, -1); }
            case 5 -> { t.rotate(-Math.PI / 2); t.scale(-1, 1); }
            case 6 -> { t.translate(h, 0); t.rotate(Math.PI / 2); }
            case 7 -> { t.scale(-1, 1); t.translate(-h, 0); t.translate(0, w); t.rotate(3 * Math.PI / 2); }
            case 8 -> { t.translate(0, w); t.rotate(3 * Math.PI / 2); }
            default -> { return image; }
        }
        BufferedImage out = new BufferedImage(swap ? h : w, swap ? w : h, BufferedImage.TYPE_INT_RGB);
        Graphics2D g = out.createGraphics();
        g.setColor(Color.WHITE);
        g.fillRect(0, 0, out.getWidth(), out.getHeight());
        g.drawImage(image, t, null);
        g.dispose();
        return out;
    }

    /** RGB (transparency → white), long side ≤ 1920 px, bicubic. */
    private static BufferedImage scaleToRgb(BufferedImage image) {
        int w = image.getWidth();
        int h = image.getHeight();
        double factor = Math.min(1.0, (double) MAX_LONG_SIDE_PX / Math.max(w, h));
        int tw = Math.max(1, (int) Math.round(w * factor));
        int th = Math.max(1, (int) Math.round(h * factor));
        if (factor == 1.0 && image.getType() == BufferedImage.TYPE_INT_RGB) {
            return image;
        }
        BufferedImage out = new BufferedImage(tw, th, BufferedImage.TYPE_INT_RGB);
        Graphics2D g = out.createGraphics();
        g.setRenderingHint(RenderingHints.KEY_INTERPOLATION, RenderingHints.VALUE_INTERPOLATION_BICUBIC);
        g.setRenderingHint(RenderingHints.KEY_RENDERING, RenderingHints.VALUE_RENDER_QUALITY);
        g.setColor(Color.WHITE);
        g.fillRect(0, 0, tw, th);
        g.drawImage(image, 0, 0, tw, th, null);
        g.dispose();
        return out;
    }

    /** Baseline JPEG, quality 0.85, no metadata (ImageIO writes only its default JFIF header). */
    private static byte[] encodeJpeg(BufferedImage image) {
        Iterator<ImageWriter> writers = ImageIO.getImageWritersByFormatName("jpeg");
        if (!writers.hasNext()) {
            throw new IllegalStateException("No JPEG writer in this JVM");
        }
        ImageWriter writer = writers.next();
        ByteArrayOutputStream out = new ByteArrayOutputStream(256 * 1024);
        try (ImageOutputStream stream = ImageIO.createImageOutputStream(out)) {
            writer.setOutput(stream);
            ImageWriteParam param = writer.getDefaultWriteParam();
            param.setCompressionMode(ImageWriteParam.MODE_EXPLICIT);
            param.setCompressionQuality(JPEG_QUALITY);
            writer.write(null, new IIOImage(image, null, null), param);
        } catch (IOException e) {
            throw new IllegalStateException("JPEG encoding failed", e);
        } finally {
            writer.dispose();
        }
        return out.toByteArray();
    }

    private static ImageReader reader(Format format) {
        Iterator<ImageReader> readers = ImageIO.getImageReadersByFormatName(format.imageIoName);
        if (!readers.hasNext()) {
            throw new IllegalStateException("No ImageIO reader for " + format);
        }
        return readers.next();
    }

    private static String sha256(byte[] bytes) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    private static ApiException unreadable() {
        return new ApiException(ErrorCode.FILE_TYPE_NOT_ALLOWED, "The photo could not be read. Only photos (JPG/PNG) are allowed.");
    }
}
