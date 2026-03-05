package br.unb.cic.rvsmart.device;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for HeapMonitor constants, initial state, and iteration-skipping logic.
 *
 * Note: The check() method calls Runtime.getRuntime() at CHECK_INTERVAL boundaries,
 * which depends on actual JVM heap state. We only test paths that do NOT reach
 * the Runtime call (iteration 0 and non-interval iterations).
 */
class HeapMonitorTest {

    private static final int THROTTLE_MS = 200;
    private static final int MAX_ITEMS = 2000;

    private HeapMonitor monitor;

    @BeforeEach
    void setUp() {
        UiCapture uiCapture = new UiCapture(MAX_ITEMS);
        monitor = new HeapMonitor(THROTTLE_MS, MAX_ITEMS, uiCapture);
    }

    // --- Constants ---

    @Test
    void testCheckInterval() {
        assertEquals(100, HeapMonitor.CHECK_INTERVAL);
    }

    @Test
    void testCriticalThreshold() {
        assertEquals(0.10, HeapMonitor.CRITICAL_THRESHOLD, 0.001);
    }

    @Test
    void testWarningThreshold() {
        assertEquals(0.20, HeapMonitor.WARNING_THRESHOLD, 0.001);
    }

    @Test
    void testThrottleIncreaseFactor() {
        assertEquals(1.5, HeapMonitor.THROTTLE_INCREASE_FACTOR, 0.001);
    }

    @Test
    void testSustainedPressureChecks() {
        assertEquals(3, HeapMonitor.SUSTAINED_PRESSURE_CHECKS);
    }

    @Test
    void testReducedMaxItems() {
        assertEquals(1000, HeapMonitor.REDUCED_MAX_ITEMS);
    }

    // --- Initial state ---

    @Test
    void testInitialThrottleMs() {
        assertEquals(THROTTLE_MS, monitor.getCurrentThrottleMs());
    }

    @Test
    void testInitialThrottleNotIncreased() {
        assertFalse(monitor.isThrottleIncreased());
    }

    @Test
    void testInitialMaxItemsNotReduced() {
        assertFalse(monitor.isMaxItemsReduced());
    }

    // --- check() skips non-interval iterations ---

    @Test
    void testCheckSkipsIterationZero() {
        int result = monitor.check(0);
        assertEquals(THROTTLE_MS, result);
    }

    @Test
    void testCheckSkipsNonIntervalIteration() {
        assertEquals(THROTTLE_MS, monitor.check(1));
        assertEquals(THROTTLE_MS, monitor.check(50));
        assertEquals(THROTTLE_MS, monitor.check(99));
    }

    @Test
    void testCheckSkipsMultipleNonIntervalIterations() {
        // Iterations 101-199 should all be skipped (not multiples of 100)
        for (int i = 101; i < 200; i++) {
            assertEquals(THROTTLE_MS, monitor.check(i),
                    "Iteration " + i + " should return original throttle");
        }
    }

    @Test
    void testStateUnchangedAfterSkippedChecks() {
        monitor.check(0);
        monitor.check(1);
        monitor.check(50);
        monitor.check(99);

        assertEquals(THROTTLE_MS, monitor.getCurrentThrottleMs());
        assertFalse(monitor.isThrottleIncreased());
        assertFalse(monitor.isMaxItemsReduced());
    }

    // --- Constructor with different values ---

    @Test
    void testConstructorWithDifferentThrottle() {
        UiCapture uiCapture = new UiCapture(500);
        HeapMonitor custom = new HeapMonitor(500, 1500, uiCapture);

        assertEquals(500, custom.getCurrentThrottleMs());
        assertFalse(custom.isThrottleIncreased());
        assertFalse(custom.isMaxItemsReduced());
    }
}
