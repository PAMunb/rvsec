package br.unb.cic.rvsmart.recovery;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for TarpitDetector — detects screens where the agent accumulates
 * iterations without making progress (no new state, no new MOP, same hash,
 * no action effect).
 */
class TarpitDetectorTest {

    private TarpitDetector detector;

    @BeforeEach
    void setUp() {
        detector = new TarpitDetector(15);
    }

    @Test
    void noTarpitBeforeThreshold() {
        for (int i = 0; i < 14; i++) {
            boolean declared = detector.recordIteration("hash-A", false, false, false);
            assertFalse(declared, "Should not declare tarpit at iteration " + i);
        }
        assertFalse(detector.isTarpit("hash-A"));
    }

    @Test
    void tarpitDeclaredAtThreshold() {
        // First call sets lastHash, counter stays 0 (hash changed from null)
        detector.recordIteration("hash-A", false, false, false);

        for (int i = 0; i < 14; i++) {
            assertFalse(detector.recordIteration("hash-A", false, false, false));
        }
        // 15th no-progress iteration should declare tarpit
        assertTrue(detector.recordIteration("hash-A", false, false, false));
        assertTrue(detector.isTarpit("hash-A"));
    }

    @Test
    void counterResetsOnNewStateDiscovery() {
        detector.recordIteration("hash-A", false, false, false); // sets lastHash
        for (int i = 0; i < 10; i++) {
            detector.recordIteration("hash-A", false, false, false);
        }

        // New state resets counter to 0
        detector.recordIteration("hash-A", true, false, false);

        // After reset, need 15 more no-progress iterations to trigger
        for (int i = 0; i < 14; i++) {
            assertFalse(detector.recordIteration("hash-A", false, false, false));
        }
        assertTrue(detector.recordIteration("hash-A", false, false, false));
    }

    @Test
    void counterResetsOnMopCoverage() {
        detector.recordIteration("hash-A", false, false, false); // sets lastHash
        for (int i = 0; i < 10; i++) {
            detector.recordIteration("hash-A", false, false, false);
        }

        // MOP coverage resets counter
        detector.recordIteration("hash-A", false, true, false);

        // Should not be tarpit yet — counter was reset
        for (int i = 0; i < 14; i++) {
            assertFalse(detector.recordIteration("hash-A", false, false, false));
        }
        assertFalse(detector.isTarpit("hash-A"));
    }

    @Test
    void counterResetsOnHashChange() {
        detector.recordIteration("hash-A", false, false, false); // sets lastHash
        for (int i = 0; i < 10; i++) {
            detector.recordIteration("hash-A", false, false, false);
        }

        assertFalse(detector.recordIteration("hash-B", false, false, false));

        for (int i = 0; i < 14; i++) {
            assertFalse(detector.recordIteration("hash-B", false, false, false));
        }
        assertTrue(detector.recordIteration("hash-B", false, false, false));
    }

    @Test
    void nullHashIgnored() {
        assertFalse(detector.recordIteration(null, false, false, false));
        assertFalse(detector.isTarpit(null));
    }

    @Test
    void differentHashesHaveIndependentCounters() {
        detector.recordIteration("hash-A", false, false, false); // sets lastHash
        for (int i = 0; i < 10; i++) {
            detector.recordIteration("hash-A", false, false, false);
        }

        detector.recordIteration("hash-B", false, false, false);
        for (int i = 0; i < 14; i++) {
            detector.recordIteration("hash-B", false, false, false);
        }
        assertTrue(detector.recordIteration("hash-B", false, false, false));
        assertTrue(detector.isTarpit("hash-B"));

        assertFalse(detector.isTarpit("hash-A"));
    }

    @Test
    void getTarpitHashesReturnsUnmodifiableSet() {
        detector.recordIteration("hash-A", false, false, false);
        for (int i = 0; i < 15; i++) {
            detector.recordIteration("hash-A", false, false, false);
        }

        assertThrows(UnsupportedOperationException.class,
                () -> detector.getTarpitHashes().add("should-fail"));
    }

    // -------------------------------------------------------------------------
    // gh41 — hadEffect resets counter
    // -------------------------------------------------------------------------

    @Test
    void counterResetsOnHadEffect() {
        detector.recordIteration("hash-A", false, false, false); // sets lastHash
        for (int i = 0; i < 13; i++) {
            detector.recordIteration("hash-A", false, false, false);
        }
        // 13 no-progress iterations accumulated — approaching threshold

        // hadEffect=true resets counter
        detector.recordIteration("hash-A", false, false, true);

        // After reset, need 15 more no-progress iterations to trigger
        for (int i = 0; i < 14; i++) {
            assertFalse(detector.recordIteration("hash-A", false, false, false));
        }
        assertFalse(detector.isTarpit("hash-A"),
                "Should not be tarpit — counter was reset by hadEffect");
    }

    // -------------------------------------------------------------------------
    // gh41 — threshold 50 test (uses a separate detector instance)
    // -------------------------------------------------------------------------

    @Test
    void tarpitThreshold50() {
        TarpitDetector d50 = new TarpitDetector(50);

        d50.recordIteration("hash-A", false, false, false); // sets lastHash
        // 49 iterations with no progress — should NOT trigger
        for (int i = 0; i < 49; i++) {
            assertFalse(d50.recordIteration("hash-A", false, false, false));
        }
        assertFalse(d50.isTarpit("hash-A"), "Should not be tarpit at 49 iterations");

        // 50th iteration triggers tarpit
        assertTrue(d50.recordIteration("hash-A", false, false, false));
        assertTrue(d50.isTarpit("hash-A"), "Should be tarpit at 50 iterations");
    }
}
