package br.unb.cic.rvsmart.recovery;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.output.RvTrack;
import br.unb.cic.rvsmart.strategy.SuccessorTracker;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for StuckDetector — detects when the app is stuck on the same screen.
 * Also covers Level 2 BFS recovery via the recover() method.
 */
class StuckDetectorTest {

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;
    }

    @Test
    void testNotStuckInitially() {
        StuckDetector detector = new StuckDetector(3);
        assertFalse(detector.update("hash_A"));
        assertEquals(0, detector.getConsecutiveUnchanged());
    }

    @Test
    void testIncrementingConsecutiveUnchanged() {
        StuckDetector detector = new StuckDetector(5);
        detector.update("hash_A"); // first visit, sets lastHash
        assertFalse(detector.update("hash_A")); // consecutiveUnchanged=1
        assertEquals(1, detector.getConsecutiveUnchanged());

        assertFalse(detector.update("hash_A")); // consecutiveUnchanged=2
        assertEquals(2, detector.getConsecutiveUnchanged());
    }

    @Test
    void testStuckAfterMaxBlocks() {
        StuckDetector detector = new StuckDetector(3);
        detector.update("hash_A"); // sets lastHash, consecutive=0
        detector.update("hash_A"); // consecutive=1
        detector.update("hash_A"); // consecutive=2
        assertTrue(detector.update("hash_A"), // consecutive=3 >= stuckMaxBlocks(3)
                "Should be stuck after 3 consecutive unchanged hashes");
    }

    @Test
    void testResetOnHashChange() {
        StuckDetector detector = new StuckDetector(3);
        detector.update("hash_A");
        detector.update("hash_A"); // consecutive=1
        detector.update("hash_A"); // consecutive=2

        // Screen changes — reset
        assertFalse(detector.update("hash_B"));
        assertEquals(0, detector.getConsecutiveUnchanged());
        assertEquals("hash_B", detector.getLastHash());
    }

    @Test
    void testResetOnNullHash() {
        StuckDetector detector = new StuckDetector(3);
        detector.update("hash_A");
        detector.update("hash_A"); // consecutive=1

        // Null hash = crash recovery, resets everything
        assertFalse(detector.update(null));
        assertEquals(0, detector.getConsecutiveUnchanged());
        assertNull(detector.getLastHash());
    }

    @Test
    void testResetMethod() {
        StuckDetector detector = new StuckDetector(3);
        detector.update("hash_A");
        detector.update("hash_A"); // consecutive=1

        detector.reset();
        assertEquals(0, detector.getConsecutiveUnchanged());
        assertNull(detector.getLastHash());
    }

    @Test
    void testCustomStuckMaxBlocks() {
        StuckDetector detector = new StuckDetector(1);
        detector.update("hash_A");
        // With stuckMaxBlocks=1, the very first repeat triggers stuck
        assertTrue(detector.update("hash_A"),
                "Should be stuck with stuckMaxBlocks=1 after first repeat");
    }

    @Test
    void testRecoverReturnsRestartWhenNoBfsConfigured() {
        // Without BacktrackBfs, recover() always returns RESTART
        StuckDetector detector = new StuckDetector(3);
        ContentGraph graph = new ContentGraph();
        SuccessorTracker tracker = new SuccessorTracker();

        Action action = detector.recover("hash_A", tracker, graph);
        assertNotNull(action);
        assertEquals(Action.Type.RESTART, action.getType());
    }

    @Test
    void testRecoverReturnsBackWhenUnsaturatedAncestorFound() {
        BacktrackBfs bfs = new BacktrackBfs();
        StuckDetector detector = new StuckDetector(3, bfs);

        ContentGraph graph = new ContentGraph();
        SuccessorTracker tracker = new SuccessorTracker();

        // Create an unsaturated ancestor for hash_A
        // hash_parent has 1 visit (below default saturation threshold of 5)
        graph.recordVisit("hash_parent", "ActivityP");
        tracker.record("hash_parent", "hash_A");

        Action action = detector.recover("hash_A", tracker, graph);
        assertNotNull(action);
        // Should return the first BACK from the BFS path
        assertEquals(Action.Type.BACK, action.getType());
    }

    // --- Time-based stuck detection (task 1.3a) ---

    @Test
    void testTimeStuckAfter30Seconds() {
        StuckDetector detector = new StuckDetector(100); // high threshold so iteration-based won't trigger
        long now = 100_000L;
        detector.recordNewScreen(now); // last new screen at t=100s

        // 29 seconds later — not stuck
        assertFalse(detector.isTimeStuck(now + 29_000));

        // 31 seconds later — stuck
        assertTrue(detector.isTimeStuck(now + 31_000));
    }

    @Test
    void testTimeStuckResetsOnNewScreen() {
        StuckDetector detector = new StuckDetector(100);
        long now = 100_000L;
        detector.recordNewScreen(now);

        // 31 seconds — stuck
        assertTrue(detector.isTimeStuck(now + 31_000));

        // New screen discovered at t=131s
        detector.recordNewScreen(now + 31_000);

        // 10 seconds after new screen — not stuck
        assertFalse(detector.isTimeStuck(now + 41_000));
    }

    // --- Form action exemption (task 1.3b) ---

    @Test
    void testSetTextDoesNotIncrementStuckCounter() {
        StuckDetector detector = new StuckDetector(3);
        detector.update("hash_A");
        detector.update("hash_A"); // consecutive=1

        // SET_TEXT on same screen should NOT increment counter
        detector.updateWithActionType("hash_A", Action.Type.SET_TEXT);
        assertEquals(1, detector.getConsecutiveUnchanged(),
                "SET_TEXT should not increment stuck counter");
    }

    @Test
    void testClickDoesIncrementStuckCounter() {
        StuckDetector detector = new StuckDetector(3);
        detector.update("hash_A");
        detector.update("hash_A"); // consecutive=1

        // CLICK on same screen SHOULD increment counter
        detector.updateWithActionType("hash_A", Action.Type.CLICK);
        assertEquals(2, detector.getConsecutiveUnchanged(),
                "CLICK should increment stuck counter");
    }

    // --- Dynamic threshold (task 1.3c) ---

    @Test
    void testDynamicThresholdWithFewElements() {
        // max(8, 3 * 1.5) = max(8, 4.5) = 8
        StuckDetector detector = new StuckDetector(10); // base threshold
        detector.update("hash_A");
        for (int i = 0; i < 7; i++) {
            detector.update("hash_A"); // consecutive 1-7
        }
        assertFalse(detector.isStuckWithDynamicThreshold(3),
                "7 consecutive < max(8, 3*1.5)=8, not stuck");
        detector.update("hash_A"); // consecutive=8
        assertTrue(detector.isStuckWithDynamicThreshold(3),
                "8 consecutive >= max(8, 3*1.5)=8, stuck");
    }

    @Test
    void testDynamicThresholdWithManyElements() {
        // max(8, 30 * 1.5) = max(8, 45) = 45
        StuckDetector detector = new StuckDetector(100);
        detector.update("hash_A");
        for (int i = 0; i < 44; i++) {
            detector.update("hash_A"); // consecutive 1-44
        }
        assertFalse(detector.isStuckWithDynamicThreshold(30),
                "44 consecutive < max(8, 30*1.5)=45, not stuck");
        detector.update("hash_A"); // consecutive=45
        assertTrue(detector.isStuckWithDynamicThreshold(30),
                "45 consecutive >= max(8, 30*1.5)=45, stuck");
    }

    @Test
    void testRecoverReturnsRestartWhenAllAncestorsSaturated() {
        BacktrackBfs bfs = new BacktrackBfs();
        StuckDetector detector = new StuckDetector(3, bfs);

        ContentGraph graph = new ContentGraph();
        SuccessorTracker tracker = new SuccessorTracker();

        // hash_A has no parents — BFS finds no path
        Action action = detector.recover("hash_A", tracker, graph);
        assertNotNull(action);
        assertEquals(Action.Type.RESTART, action.getType());
    }
}
