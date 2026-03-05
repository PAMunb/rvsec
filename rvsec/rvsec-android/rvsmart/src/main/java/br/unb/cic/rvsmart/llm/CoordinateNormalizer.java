package br.unb.cic.rvsmart.llm;

/**
 * Converts Qwen3-VL normalized coordinates to device pixel coordinates.
 *
 * Qwen3-VL returns coordinates in the [0, 1000) range for both x and y axes,
 * independent of the actual device resolution. This class converts that space
 * to pixel coordinates and clamps the result to the device boundaries.
 *
 * Reference: https://github.com/QwenLM/Qwen3-VL/issues/1486
 */
public final class CoordinateNormalizer {

    // Static utility class — no instances needed
    private CoordinateNormalizer() {}

    /**
     * Convert Qwen3-VL normalized coordinates to device pixels.
     *
     * Formula:
     *   pixelX = (int)((qwenX / 1000.0) * deviceWidth)
     *   pixelY = (int)((qwenY / 1000.0) * deviceHeight)
     *
     * Both axes are clamped to [0, dimension - 1] so the result is always a valid
     * tap target on the screen.
     *
     * @param qwenX       x coordinate in [0, 1000) from the model
     * @param qwenY       y coordinate in [0, 1000) from the model
     * @param deviceWidth device width in pixels
     * @param deviceHeight device height in pixels
     * @return int[]{pixelX, pixelY} clamped to device bounds
     */
    public static int[] normalize(int qwenX, int qwenY, int deviceWidth, int deviceHeight) {
        int pixelX = (int) ((qwenX / 1000.0) * deviceWidth);
        int pixelY = (int) ((qwenY / 1000.0) * deviceHeight);

        // Clamp to device bounds so we never produce an off-screen coordinate
        pixelX = Math.max(0, Math.min(pixelX, deviceWidth - 1));
        pixelY = Math.max(0, Math.min(pixelY, deviceHeight - 1));

        return new int[]{pixelX, pixelY};
    }
}
