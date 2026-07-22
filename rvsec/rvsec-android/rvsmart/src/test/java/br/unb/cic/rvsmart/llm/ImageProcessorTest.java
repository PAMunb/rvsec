package br.unb.cic.rvsmart.llm;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for ImageProcessor.calculateResizedDimensions().
 *
 * The processScreenshot() method uses android.graphics.Bitmap which is not available
 * in JUnit (only a stub at compile time). Only the pure-Java helper method
 * calculateResizedDimensions() is tested here.
 */
class ImageProcessorTest {

    private static final int MAX_EDGE = 1000;

    // --- No resize needed ---

    @Test
    void testImageAlreadyWithinBoundsNotResized() {
        int[] dims = ImageProcessor.calculateResizedDimensions(800, 600, MAX_EDGE);
        assertEquals(800, dims[0]);
        assertEquals(600, dims[1]);
    }

    @Test
    void testImageExactly1000x1000NotResized() {
        int[] dims = ImageProcessor.calculateResizedDimensions(1000, 1000, MAX_EDGE);
        assertEquals(1000, dims[0]);
        assertEquals(1000, dims[1]);
    }

    @Test
    void testSquareImageSmallerThanMaxNotResized() {
        int[] dims = ImageProcessor.calculateResizedDimensions(500, 500, MAX_EDGE);
        assertEquals(500, dims[0]);
        assertEquals(500, dims[1]);
    }

    // --- Resize with aspect ratio preservation ---

    @Test
    void testLandscapeImageResized() {
        // 1920x1080 — width is the longest edge, should scale to 1000x562(ish)
        int[] dims = ImageProcessor.calculateResizedDimensions(1920, 1080, MAX_EDGE);
        assertEquals(MAX_EDGE, dims[0], "Width must be 1000 (longest edge)");
        assertTrue(dims[1] < MAX_EDGE, "Height must be less than 1000");
        // Check aspect ratio is roughly preserved: 1080/1920 ≈ 0.5625
        double aspect = (double) dims[1] / dims[0];
        assertEquals(1080.0 / 1920.0, aspect, 0.01, "Aspect ratio must be preserved");
    }

    @Test
    void testPortraitImageResized() {
        // 1080x1920 — height is the longest edge, should scale to 562x1000
        int[] dims = ImageProcessor.calculateResizedDimensions(1080, 1920, MAX_EDGE);
        assertTrue(dims[0] < MAX_EDGE, "Width must be less than 1000");
        assertEquals(MAX_EDGE, dims[1], "Height must be 1000 (longest edge)");
        double aspect = (double) dims[0] / dims[1];
        assertEquals(1080.0 / 1920.0, aspect, 0.01, "Aspect ratio must be preserved");
    }

    @Test
    void testSquareImageResized() {
        // 2000x2000 — both edges equal, should scale to 1000x1000
        int[] dims = ImageProcessor.calculateResizedDimensions(2000, 2000, MAX_EDGE);
        assertEquals(MAX_EDGE, dims[0]);
        assertEquals(MAX_EDGE, dims[1]);
    }

    @Test
    void testExactlyOverMaxEdge() {
        // 1001x999 — width exceeds max by 1
        int[] dims = ImageProcessor.calculateResizedDimensions(1001, 999, MAX_EDGE);
        assertEquals(MAX_EDGE, dims[0]);
        assertTrue(dims[1] < MAX_EDGE);
        assertTrue(dims[1] > 0);
    }

    @Test
    void testWideAspectRatio() {
        // 4000x500 — very wide, width is longest
        int[] dims = ImageProcessor.calculateResizedDimensions(4000, 500, MAX_EDGE);
        assertEquals(MAX_EDGE, dims[0]);
        assertEquals(125, dims[1]);  // 500 * (1000/4000) = 125
    }

    @Test
    void testTallAspectRatio() {
        // 500x4000 — very tall, height is longest
        int[] dims = ImageProcessor.calculateResizedDimensions(500, 4000, MAX_EDGE);
        assertEquals(125, dims[0]);  // 500 * (1000/4000) = 125
        assertEquals(MAX_EDGE, dims[1]);
    }

    // --- Edge cases ---

    @Test
    void testResultIsLengthTwo() {
        int[] dims = ImageProcessor.calculateResizedDimensions(1080, 1920, MAX_EDGE);
        assertEquals(2, dims.length);
    }

    @Test
    void testOutputAlwaysPositive() {
        int[] dims = ImageProcessor.calculateResizedDimensions(10000, 10000, MAX_EDGE);
        assertTrue(dims[0] >= 1, "Width must be at least 1");
        assertTrue(dims[1] >= 1, "Height must be at least 1");
    }

    @Test
    void testVerySmallImageNotResized() {
        int[] dims = ImageProcessor.calculateResizedDimensions(10, 10, MAX_EDGE);
        assertEquals(10, dims[0]);
        assertEquals(10, dims[1]);
    }

    @Test
    void testCustomMaxEdge() {
        // Custom max of 500
        int[] dims = ImageProcessor.calculateResizedDimensions(1000, 500, 500);
        assertEquals(500, dims[0]);
        assertEquals(250, dims[1]);
    }

    @Test
    void testZeroWidthReturnsOriginal() {
        int[] dims = ImageProcessor.calculateResizedDimensions(0, 500, MAX_EDGE);
        assertEquals(0, dims[0]);
        assertEquals(500, dims[1]);
    }

    @Test
    void testZeroHeightReturnsOriginal() {
        int[] dims = ImageProcessor.calculateResizedDimensions(500, 0, MAX_EDGE);
        assertEquals(500, dims[0]);
        assertEquals(0, dims[1]);
    }
}
