package br.unb.cic.rvsmart.device;

import android.util.Log;

/**
 * Monitors runtime heap memory and adapts throttle/MAX_ITEMS to prevent OOM (INV-RSM-13).
 *
 * Check interval: every 100 iterations.
 * Critical threshold (< 10% free): increase throttle_ms by 50%.
 * Warning threshold (< 20% free): log warning.
 * Sustained pressure (3 consecutive critical checks): reduce MAX_ITEMS to 1000.
 * Recovery (>= 20% free): restore original values.
 */
public class HeapMonitor {

    private static final String TAG = "RVSMART";

    static final int CHECK_INTERVAL = 100;
    static final double CRITICAL_THRESHOLD = 0.10;
    static final double WARNING_THRESHOLD = 0.20;
    static final double THROTTLE_INCREASE_FACTOR = 1.5;
    static final int SUSTAINED_PRESSURE_CHECKS = 3;
    static final int REDUCED_MAX_ITEMS = 1000;

    private final int originalThrottleMs;
    private final int originalMaxItems;
    private final UiCapture uiCapture;

    private int currentThrottleMs;
    private int consecutiveCriticalChecks;
    private boolean throttleIncreased;
    private boolean maxItemsReduced;

    public HeapMonitor(int throttleMs, int maxItems, UiCapture uiCapture) {
        this.originalThrottleMs = throttleMs;
        this.originalMaxItems = maxItems;
        this.uiCapture = uiCapture;
        this.currentThrottleMs = throttleMs;
    }

    /**
     * Check memory status if the iteration count aligns with CHECK_INTERVAL.
     * Called from the learning phase of each iteration.
     *
     * @param iteration Current iteration number (0-based)
     * @return Current throttle_ms value (may be increased under pressure)
     */
    public int check(int iteration) {
        if (iteration % CHECK_INTERVAL != 0 || iteration == 0) {
            return currentThrottleMs;
        }

        Runtime rt = Runtime.getRuntime();
        long free = rt.freeMemory();
        long max = rt.maxMemory();
        double freeRatio = (double) free / max;

        if (freeRatio < CRITICAL_THRESHOLD) {
            handleCriticalPressure(free, max, freeRatio);
        } else if (freeRatio < WARNING_THRESHOLD) {
            Log.w(TAG, String.format("Memory warning: free=%dMB (%.0f%%)",
                    free / (1024 * 1024), freeRatio * 100));
            consecutiveCriticalChecks = 0;
        } else {
            handleRecovery(free, max, freeRatio);
        }

        return currentThrottleMs;
    }

    private void handleCriticalPressure(long free, long max, double freeRatio) {
        consecutiveCriticalChecks++;

        if (!throttleIncreased) {
            currentThrottleMs = (int) (originalThrottleMs * THROTTLE_INCREASE_FACTOR);
            throttleIncreased = true;
            Log.w(TAG, String.format("Memory pressure: free=%dMB (%.0f%%), throttle increased to %dms",
                    free / (1024 * 1024), freeRatio * 100, currentThrottleMs));
        }

        if (consecutiveCriticalChecks >= SUSTAINED_PRESSURE_CHECKS && !maxItemsReduced) {
            uiCapture.setMaxItems(REDUCED_MAX_ITEMS);
            maxItemsReduced = true;
            Log.w(TAG, "Sustained memory pressure: reducing MAX_ITEMS to " + REDUCED_MAX_ITEMS);
        }
    }

    private void handleRecovery(long free, long max, double freeRatio) {
        if (throttleIncreased || maxItemsReduced) {
            currentThrottleMs = originalThrottleMs;
            throttleIncreased = false;
            if (maxItemsReduced) {
                uiCapture.setMaxItems(originalMaxItems);
                maxItemsReduced = false;
            }
            consecutiveCriticalChecks = 0;
            Log.i(TAG, "Memory pressure resolved, restoring defaults");
        }
    }

    public int getCurrentThrottleMs() {
        return currentThrottleMs;
    }

    public boolean isThrottleIncreased() {
        return throttleIncreased;
    }

    public boolean isMaxItemsReduced() {
        return maxItemsReduced;
    }
}
