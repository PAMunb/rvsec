package br.unb.cic.rvsmart.strategy;

import br.unb.cic.rvsmart.output.RvTrack;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class PlateauDetectorTest {

    private PlateauDetector detector;

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;
        detector = new PlateauDetector();
    }

    @Test
    void testPlateauDetectedAfterTenNoProgressIterations() {
        for (int i = 0; i < 10; i++) {
            detector.recordIteration(false, false);
        }
        assertTrue(detector.isPlateauDetected());
    }

    @Test
    void testPlateauNotDetectedBeforeWindowFull() {
        for (int i = 0; i < 9; i++) {
            detector.recordIteration(false, false);
        }
        assertFalse(detector.isPlateauDetected());
    }

    @Test
    void testPlateauClearsOnNewStateDiscovery() {
        for (int i = 0; i < 10; i++) {
            detector.recordIteration(false, false);
        }
        assertTrue(detector.isPlateauDetected());

        // New state breaks plateau
        detector.recordIteration(true, false);
        assertFalse(detector.isPlateauDetected());
    }

    @Test
    void testPlateauClearsOnNewMopCoverage() {
        for (int i = 0; i < 10; i++) {
            detector.recordIteration(false, false);
        }
        assertTrue(detector.isPlateauDetected());

        // New MOP coverage breaks plateau
        detector.recordIteration(false, true);
        assertFalse(detector.isPlateauDetected());
    }

    @Test
    void testNoPlateauWhenProgressOngoing() {
        // Mixed progress: every 3rd iteration has progress
        for (int i = 0; i < 20; i++) {
            boolean hasProgress = (i % 3 == 0);
            detector.recordIteration(hasProgress, false);
        }
        assertFalse(detector.isPlateauDetected());
    }

    @Test
    void testWindowBoundaryExactlyAtTen() {
        // 9 no-progress + 1 progress + 9 no-progress = not plateau
        for (int i = 0; i < 9; i++) {
            detector.recordIteration(false, false);
        }
        detector.recordIteration(true, false);
        for (int i = 0; i < 9; i++) {
            detector.recordIteration(false, false);
        }
        assertFalse(detector.isPlateauDetected());

        // One more no-progress fills window with 10 no-progress
        detector.recordIteration(false, false);
        assertTrue(detector.isPlateauDetected());
    }

    @Test
    void testGetConsecutiveNoProgressReturnsCorrectCount() {
        assertEquals(0, detector.getConsecutiveNoProgress());

        detector.recordIteration(false, false);
        assertEquals(1, detector.getConsecutiveNoProgress());

        detector.recordIteration(false, false);
        detector.recordIteration(false, false);
        assertEquals(3, detector.getConsecutiveNoProgress());

        // Progress resets count
        detector.recordIteration(true, false);
        assertEquals(0, detector.getConsecutiveNoProgress());

        // Resumes counting
        detector.recordIteration(false, false);
        detector.recordIteration(false, false);
        assertEquals(2, detector.getConsecutiveNoProgress());
    }

    @Test
    void testGetConsecutiveNoProgressResetsByMopCoverage() {
        for (int i = 0; i < 5; i++) {
            detector.recordIteration(false, false);
        }
        assertEquals(5, detector.getConsecutiveNoProgress());

        detector.recordIteration(false, true);
        assertEquals(0, detector.getConsecutiveNoProgress());
    }

    @Test
    void testInitialStateIsNotPlateau() {
        assertFalse(detector.isPlateauDetected());
        assertEquals(0, detector.getConsecutiveNoProgress());
    }
}
