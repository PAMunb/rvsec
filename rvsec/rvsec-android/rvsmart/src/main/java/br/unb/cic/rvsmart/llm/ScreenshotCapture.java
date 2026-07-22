package br.unb.cic.rvsmart.llm;

import android.graphics.Bitmap;
import android.graphics.Rect;

import java.io.ByteArrayOutputStream;
import java.lang.reflect.Method;

/**
 * Captures screenshots from the Android device for LLM analysis.
 *
 * Uses SurfaceControl.screenshot() via reflection as the primary method because
 * it does not require an active UiAutomation session and works from app_process.
 * Falls back to UiAutomation.takeScreenshot() if the reflection path fails.
 *
 * Returns null rather than throwing when capture is not possible, so the
 * caller can skip the LLM step gracefully and continue with the algorithm.
 */
public class ScreenshotCapture {

    /**
     * Capture a screenshot and return PNG bytes.
     *
     * @param width  target width (device display width)
     * @param height target height (device display height)
     * @return PNG byte array, or null if capture failed
     */
    public byte[] capture(int width, int height) {
        byte[] result = captureViaSurfaceControl(width, height);
        if (result != null) return result;
        return captureViaUiAutomation();
    }

    /**
     * Primary: SurfaceControl.screenshot() via reflection.
     *
     * SurfaceControl is a hidden Android API available on API 29+ from app_process.
     * Reflection is required because it is not part of the public SDK.
     */
    private byte[] captureViaSurfaceControl(int width, int height) {
        try {
            Class<?> surfaceControlClass = Class.forName("android.view.SurfaceControl");
            Method screenshotMethod = surfaceControlClass.getMethod(
                    "screenshot", Rect.class, int.class, int.class, int.class);

            Rect displayRect = new Rect(0, 0, width, height);
            Object bitmapObj = screenshotMethod.invoke(null, displayRect, width, height, 0);
            if (bitmapObj == null) return null;

            Bitmap bitmap = (Bitmap) bitmapObj;
            return bitmapToPng(bitmap);

        } catch (Exception e) {
            // Reflection not available or no permission — fall through to backup
            return null;
        }
    }

    /**
     * Fallback: UiAutomation.takeScreenshot().
     *
     * UiAutomation is available when running under the instrumentation framework.
     * From raw app_process this path usually fails, but it serves as a safety net.
     */
    private byte[] captureViaUiAutomation() {
        try {
            // Obtain the current UiAutomation via InstrumentationRegistry — may not be available
            Class<?> registryClass = Class.forName("androidx.test.platform.app.InstrumentationRegistry");
            Method getInstrumentation = registryClass.getMethod("getInstrumentation");
            Object instrumentation = getInstrumentation.invoke(null);

            Method getUiAutomation = instrumentation.getClass().getMethod("getUiAutomation");
            Object uiAutomation = getUiAutomation.invoke(instrumentation);

            Method takeScreenshot = uiAutomation.getClass().getMethod("takeScreenshot");
            Object bitmapObj = takeScreenshot.invoke(uiAutomation);
            if (bitmapObj == null) return null;

            Bitmap bitmap = (Bitmap) bitmapObj;
            return bitmapToPng(bitmap);

        } catch (Exception e) {
            return null;
        }
    }

    /** Compress a Bitmap to PNG bytes. */
    private byte[] bitmapToPng(Bitmap bitmap) {
        try {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            bitmap.compress(Bitmap.CompressFormat.PNG, 100, out);
            return out.toByteArray();
        } catch (Exception e) {
            return null;
        }
    }
}
