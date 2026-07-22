package br.unb.cic.rvsmart.llm;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for CoordinateNormalizer — Qwen3-VL [0,1000) to device-pixel conversion.
 */
class CoordinateNormalizerTest {

    private static final int DEVICE_WIDTH = 1080;
    private static final int DEVICE_HEIGHT = 1920;

    // --- Standard conversions ---

    @Test
    void testCenterCoordinates() {
        // (500, 500) on a 1080x1920 device should map to (540, 960)
        int[] result = CoordinateNormalizer.normalize(500, 500, DEVICE_WIDTH, DEVICE_HEIGHT);
        assertEquals(540, result[0], "x=500 on 1080-wide device must produce pixel 540");
        assertEquals(960, result[1], "y=500 on 1920-high device must produce pixel 960");
    }

    @Test
    void testOriginCoordinates() {
        int[] result = CoordinateNormalizer.normalize(0, 0, DEVICE_WIDTH, DEVICE_HEIGHT);
        assertEquals(0, result[0]);
        assertEquals(0, result[1]);
    }

    @Test
    void testMaxCoordinates() {
        // (999, 999) should be near the bottom-right corner but within bounds
        int[] result = CoordinateNormalizer.normalize(999, 999, DEVICE_WIDTH, DEVICE_HEIGHT);
        assertTrue(result[0] < DEVICE_WIDTH, "Pixel x must be within device width");
        assertTrue(result[1] < DEVICE_HEIGHT, "Pixel y must be within device height");
        assertTrue(result[0] >= 0);
        assertTrue(result[1] >= 0);
    }

    @Test
    void testQuarterCoordinates() {
        // (250, 250) on 1080x1920 -> (270, 480)
        int[] result = CoordinateNormalizer.normalize(250, 250, DEVICE_WIDTH, DEVICE_HEIGHT);
        assertEquals(270, result[0]);
        assertEquals(480, result[1]);
    }

    @Test
    void testThreeQuarterCoordinates() {
        // (750, 750) on 1080x1920 -> (810, 1440)
        int[] result = CoordinateNormalizer.normalize(750, 750, DEVICE_WIDTH, DEVICE_HEIGHT);
        assertEquals(810, result[0]);
        assertEquals(1440, result[1]);
    }

    // --- Clamping ---

    @Test
    void testClampNegativeInput() {
        // Negative qwen coordinates clamp to 0
        int[] result = CoordinateNormalizer.normalize(-50, -100, DEVICE_WIDTH, DEVICE_HEIGHT);
        assertEquals(0, result[0], "Negative x must clamp to 0");
        assertEquals(0, result[1], "Negative y must clamp to 0");
    }

    @Test
    void testClampOverMaxInput() {
        // Values >= 1000 clamp to device_max - 1
        int[] result = CoordinateNormalizer.normalize(1500, 2000, DEVICE_WIDTH, DEVICE_HEIGHT);
        assertEquals(DEVICE_WIDTH - 1, result[0], "x > 1000 must clamp to deviceWidth-1");
        assertEquals(DEVICE_HEIGHT - 1, result[1], "y > 1000 must clamp to deviceHeight-1");
    }

    @Test
    void testClampExactly1000() {
        // 1000 is out of range [0,1000) — must clamp
        int[] result = CoordinateNormalizer.normalize(1000, 1000, DEVICE_WIDTH, DEVICE_HEIGHT);
        assertEquals(DEVICE_WIDTH - 1, result[0]);
        assertEquals(DEVICE_HEIGHT - 1, result[1]);
    }

    // --- Different device resolutions ---

    @Test
    void testSmallDeviceResolution() {
        // 720x1280 device
        int[] result = CoordinateNormalizer.normalize(500, 500, 720, 1280);
        assertEquals(360, result[0]);
        assertEquals(640, result[1]);
    }

    @Test
    void testHighDpiDevice() {
        // 1440x3040 device (e.g. Galaxy S21)
        int[] result = CoordinateNormalizer.normalize(500, 500, 1440, 3040);
        assertEquals(720, result[0]);
        assertEquals(1520, result[1]);
    }

    @Test
    void testNonSquareQwenCoordinates() {
        // x=200, y=800 on 1080x1920
        int[] result = CoordinateNormalizer.normalize(200, 800, DEVICE_WIDTH, DEVICE_HEIGHT);
        assertEquals(216, result[0]);   // (200/1000) * 1080 = 216
        assertEquals(1536, result[1]);  // (800/1000) * 1920 = 1536
    }

    // --- Return array structure ---

    @Test
    void testResultIsLengthTwo() {
        int[] result = CoordinateNormalizer.normalize(100, 200, 1080, 1920);
        assertEquals(2, result.length);
    }
}
