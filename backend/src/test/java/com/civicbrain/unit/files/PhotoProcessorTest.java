package com.civicbrain.unit.files;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.zip.CRC32;

import javax.imageio.ImageIO;

import org.junit.jupiter.api.Test;

import com.civicbrain.common.ApiException;
import com.civicbrain.common.ErrorCode;
import com.civicbrain.files.service.PhotoProcessor;

/**
 * The upload pipeline of docs/07_SECURITY.md §3 and 04 §5 (FR-11): magic bytes (415), size (413), header
 * dimensions before any decoding (422 IMAGE_TOO_SMALL / IMAGE_TOO_LARGE_PIXELS), EXIF facts kept as data,
 * re-encoded JPEG without any metadata, orientation applied, long side ≤ 1920 px, SHA-256 of the stored bytes.
 */
class PhotoProcessorTest {

    private final PhotoProcessor photos = new PhotoProcessor();

    @Test
    void cameraJpegIsReencodedWithoutExifRotatedAndItsCaptureFactsAreKept() throws Exception {
        byte[] original = resource("/photos/exif_gps_orientation6.jpg");
        assertThat(new String(original, StandardCharsets.ISO_8859_1)).contains("Exif").contains("FixtureCam");

        PhotoProcessor.Checked checked = photos.check(original);
        assertThat(checked.format()).isEqualTo(PhotoProcessor.Format.JPEG);
        assertThat(checked.width()).isEqualTo(800);
        assertThat(checked.height()).isEqualTo(600);

        PhotoProcessor.Processed result = photos.process(checked);
        byte[] jpeg = result.jpeg();
        assertThat(jpeg[0]).isEqualTo((byte) 0xFF);
        assertThat(jpeg[1]).isEqualTo((byte) 0xD8);
        String raw = new String(jpeg, StandardCharsets.ISO_8859_1);
        assertThat(raw).doesNotContain("Exif").doesNotContain("FixtureCam").doesNotContain("CivicBrain test");
        assertThat(hasSegment(jpeg, 0xE1)).as("no APP1 (EXIF/XMP) segment").isFalse();

        // orientation 6 = rotate 90° clockwise: the 800x600 pixels are stored upright as 600x800
        assertThat(result.width()).isEqualTo(600);
        assertThat(result.height()).isEqualTo(800);
        BufferedImage stored = ImageIO.read(new ByteArrayInputStream(jpeg));
        assertThat(stored.getWidth()).isEqualTo(600);
        assertThat(stored.getHeight()).isEqualTo(800);
        // the red block of the stored top-left corner is now at the top-right corner
        assertThat(isRed(stored.getRGB(575, 20))).isTrue();
        assertThat(isRed(stored.getRGB(20, 20))).isFalse();

        assertThat(result.sha256()).isEqualTo(HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(jpeg)));
        assertThat(result.exif()).containsEntry("present", true)
                .containsEntry("dateTimeOriginal", "2026:10:03 10:15:30")
                .containsEntry("offsetTimeOriginal", "+05:30")
                .doesNotContainKey("make").doesNotContainKey("model");
        assertThat((Double) result.exif().get("gpsLatitude")).isCloseTo(18.7440, org.assertj.core.data.Offset.offset(1e-6));
        assertThat((Double) result.exif().get("gpsLongitude")).isCloseTo(73.6760, org.assertj.core.data.Offset.offset(1e-6));
    }

    @Test
    void pngWithTransparencyBecomesAnRgbJpegAndAPhotoWithoutExifSaysSo() throws Exception {
        BufferedImage argb = new BufferedImage(1000, 500, BufferedImage.TYPE_INT_ARGB);
        Graphics2D g = argb.createGraphics();
        g.setColor(new Color(0, 128, 0, 255));
        g.fillRect(0, 0, 500, 500);
        g.dispose();   // right half stays fully transparent
        byte[] png = encode(argb, "png");

        PhotoProcessor.Checked checked = photos.check(png);
        assertThat(checked.format()).isEqualTo(PhotoProcessor.Format.PNG);
        PhotoProcessor.Processed result = photos.process(checked);
        BufferedImage stored = ImageIO.read(new ByteArrayInputStream(result.jpeg()));
        assertThat(stored.getWidth()).isEqualTo(1000);
        assertThat(stored.getHeight()).isEqualTo(500);
        assertThat(stored.getColorModel().hasAlpha()).isFalse();
        assertThat(new Color(stored.getRGB(900, 250)).getRed()).as("transparent → white").isGreaterThan(240);
        assertThat(result.exif()).containsEntry("present", false).hasSize(1);
    }

    @Test
    void theLongSideIsLimitedTo1920Pixels() throws Exception {
        PhotoProcessor.Processed result = photos.process(photos.check(encode(picture(4000, 3000), "jpg")));
        assertThat(result.width()).isEqualTo(1920);
        assertThat(result.height()).isEqualTo(1440);
        BufferedImage stored = ImageIO.read(new ByteArrayInputStream(result.jpeg()));
        assertThat(stored.getWidth()).isEqualTo(1920);
        assertThat(stored.getHeight()).isEqualTo(1440);
    }

    @Test
    void onlyJpegAndPngByTheirMagicBytes() throws Exception {
        assertCode(() -> photos.check("this is not an image, just text ".repeat(40).getBytes(StandardCharsets.US_ASCII)),
                ErrorCode.FILE_TYPE_NOT_ALLOWED);
        assertCode(() -> photos.check(new byte[0]), ErrorCode.FILE_TYPE_NOT_ALLOWED);
        assertCode(() -> photos.check(null), ErrorCode.FILE_TYPE_NOT_ALLOWED);
        assertCode(() -> photos.check(encode(picture(640, 480), "gif")), ErrorCode.FILE_TYPE_NOT_ALLOWED);
        assertCode(() -> photos.check(encode(picture(640, 480), "bmp")), ErrorCode.FILE_TYPE_NOT_ALLOWED);
        // JPEG magic bytes, but no readable image behind them
        byte[] fake = new byte[2048];
        fake[0] = (byte) 0xFF;
        fake[1] = (byte) 0xD8;
        fake[2] = (byte) 0xFF;
        assertCode(() -> photos.check(fake), ErrorCode.FILE_TYPE_NOT_ALLOWED);
    }

    @Test
    void sizeAndPixelLimitsComeAfterTheMagicBytesAndBeforeDecoding() throws Exception {
        byte[] big = new byte[PhotoProcessor.MAX_BYTES + 1];
        big[0] = (byte) 0xFF;
        big[1] = (byte) 0xD8;
        big[2] = (byte) 0xFF;
        assertCode(() -> photos.check(big), ErrorCode.FILE_TOO_LARGE);

        assertCode(() -> photos.check(encode(picture(319, 1000), "jpg")), ErrorCode.IMAGE_TOO_SMALL);
        assertCode(() -> photos.check(encode(picture(1000, 300), "png")), ErrorCode.IMAGE_TOO_SMALL);
        assertThat(photos.check(encode(picture(320, 320), "jpg")).width()).isEqualTo(320);

        // a PNG header announcing 7000 x 6000 = 42 MP (no pixel data at all): refused from the header alone
        assertCode(() -> photos.check(pngHeaderOnly(7000, 6000)), ErrorCode.IMAGE_TOO_LARGE_PIXELS);
    }

    // ------------------------------------------------------------------ helpers

    private static void assertCode(org.assertj.core.api.ThrowableAssert.ThrowingCallable call, ErrorCode code) {
        assertThatThrownBy(call).isInstanceOf(ApiException.class)
                .satisfies(e -> assertThat(((ApiException) e).code()).isEqualTo(code));
    }

    private static byte[] resource(String name) throws IOException {
        try (InputStream in = PhotoProcessorTest.class.getResourceAsStream(name)) {
            assertThat(in).as(name).isNotNull();
            return in.readAllBytes();
        }
    }

    static BufferedImage picture(int width, int height) {
        BufferedImage img = new BufferedImage(width, height, BufferedImage.TYPE_INT_RGB);
        Graphics2D g = img.createGraphics();
        g.setColor(new Color(120, 110, 100));
        g.fillRect(0, 0, width, height);
        g.setColor(Color.DARK_GRAY);
        g.fillOval(width / 4, height / 4, width / 2, height / 2);
        g.dispose();
        return img;
    }

    static byte[] encode(BufferedImage image, String format) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        assertThat(ImageIO.write(image, format, out)).as("writer for " + format).isTrue();
        return out.toByteArray();
    }

    private static boolean isRed(int rgb) {
        Color c = new Color(rgb);
        return c.getRed() > 200 && c.getGreen() < 60 && c.getBlue() < 60;
    }

    /** Is there a JPEG marker segment {@code 0xFF <marker>} before the image data starts? */
    private static boolean hasSegment(byte[] jpeg, int marker) {
        int i = 2;
        while (i + 4 <= jpeg.length && (jpeg[i] & 0xFF) == 0xFF) {
            int m = jpeg[i + 1] & 0xFF;
            if (m == marker) {
                return true;
            }
            if (m == 0xDA) {   // start of scan: no more metadata segments
                return false;
            }
            int length = ((jpeg[i + 2] & 0xFF) << 8) | (jpeg[i + 3] & 0xFF);
            i += 2 + length;
        }
        return false;
    }

    /** PNG signature + a valid IHDR chunk (8-bit grey) and nothing else. */
    private static byte[] pngHeaderOnly(int width, int height) {
        ByteBuffer ihdr = ByteBuffer.allocate(17);
        ihdr.put("IHDR".getBytes(StandardCharsets.US_ASCII)).putInt(width).putInt(height)
                .put((byte) 8).put((byte) 0).put((byte) 0).put((byte) 0).put((byte) 0);
        CRC32 crc = new CRC32();
        crc.update(ihdr.array());
        ByteBuffer png = ByteBuffer.allocate(8 + 4 + 17 + 4);
        png.put(new byte[] {(byte) 0x89, 'P', 'N', 'G', 0x0D, 0x0A, 0x1A, 0x0A}).putInt(13).put(ihdr.array())
                .putInt((int) crc.getValue());
        return png.array();
    }
}
