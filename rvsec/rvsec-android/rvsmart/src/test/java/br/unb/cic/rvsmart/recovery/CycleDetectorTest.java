package br.unb.cic.rvsmart.recovery;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class CycleDetectorTest {

    @Test
    void testPeriod2Detection() {
        CycleDetector detector = new CycleDetector();
        detector.recordHash("A");
        detector.recordHash("B");
        detector.recordHash("A");
        detector.recordHash("B");
        assertTrue(detector.isCycleDetected(), "A-B-A-B should be detected as period-2 cycle");
    }

    @Test
    void testPeriod3Detection() {
        CycleDetector detector = new CycleDetector();
        detector.recordHash("A");
        detector.recordHash("B");
        detector.recordHash("C");
        detector.recordHash("A");
        detector.recordHash("B");
        detector.recordHash("C");
        assertTrue(detector.isCycleDetected(), "A-B-C-A-B-C should be detected as period-3 cycle");
    }

    @Test
    void testPeriod4Detection() {
        CycleDetector detector = new CycleDetector();
        detector.recordHash("A");
        detector.recordHash("B");
        detector.recordHash("C");
        detector.recordHash("D");
        detector.recordHash("A");
        detector.recordHash("B");
        detector.recordHash("C");
        detector.recordHash("D");
        assertTrue(detector.isCycleDetected(), "A-B-C-D-A-B-C-D should be detected as period-4 cycle");
    }

    @Test
    void testNoFalsePositiveOnNonRepeatingSequence() {
        CycleDetector detector = new CycleDetector();
        detector.recordHash("A");
        detector.recordHash("B");
        detector.recordHash("C");
        detector.recordHash("D");
        detector.recordHash("E");
        assertFalse(detector.isCycleDetected(), "Non-repeating sequence should not trigger cycle detection");
    }

    @Test
    void testRingBufferOverflow() {
        CycleDetector detector = new CycleDetector();
        // Fill beyond buffer size (10)
        for (int i = 0; i < 12; i++) {
            detector.recordHash("hash_" + i);
        }
        assertEquals(10, detector.getBufferSize(), "Buffer should not exceed 10 entries");
        assertFalse(detector.isCycleDetected(), "Unique hashes should not trigger cycle");
    }

    @Test
    void testResetClearsCycleState() {
        CycleDetector detector = new CycleDetector();
        detector.recordHash("A");
        detector.recordHash("B");
        detector.recordHash("A");
        detector.recordHash("B");
        assertTrue(detector.isCycleDetected());
        detector.reset();
        assertFalse(detector.isCycleDetected(), "After reset, no cycle should be detected");
        assertEquals(0, detector.getBufferSize(), "Buffer should be empty after reset");
    }

    @Test
    void testInsufficientDataNoCycle() {
        CycleDetector detector = new CycleDetector();
        detector.recordHash("A");
        detector.recordHash("B");
        detector.recordHash("A");
        // Only 3 entries — period-2 needs 4
        assertFalse(detector.isCycleDetected(), "Insufficient data should not trigger cycle");
    }
}
