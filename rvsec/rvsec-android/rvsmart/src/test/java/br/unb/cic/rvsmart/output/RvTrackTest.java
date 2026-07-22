package br.unb.cic.rvsmart.output;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class RvTrackTest {

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;  // Disable Log.i() for unit tests
        RvTrack.resetCounters();
    }

    @Test
    void testResetCountersZerosAll() {
        RvTrack.crash(0, "java", "CLICK", 100);
        RvTrack.resetCounters();
        assertEquals(0, RvTrack.getCrashRecoveries());
        assertEquals(0, RvTrack.getBacktrackCount());
        assertEquals(0, RvTrack.getStuckLevel1Count());
    }

    @Test
    void testCrashIncrementsCrashRecoveries() {
        RvTrack.crash(1, "java", "CLICK", 50);
        RvTrack.crash(2, "native", "BACK", 75);
        assertEquals(2, RvTrack.getCrashRecoveries());
    }

    @Test
    void testStuckLevel1Increments() {
        RvTrack.stuck(1, 1, "abc123", 10, "BACK");
        assertEquals(1, RvTrack.getStuckLevel1Count());
        assertEquals(0, RvTrack.getStuckLevel2Count());
    }

    @Test
    void testStuckLevel2Increments() {
        RvTrack.stuck(1, 2, "abc123", 20, "BFS");
        assertEquals(0, RvTrack.getStuckLevel1Count());
        assertEquals(1, RvTrack.getStuckLevel2Count());
    }

    @Test
    void testBacktrackIncrementsCount() {
        RvTrack.backtrack(5, 1, "aaa", "bbb", 3, "stuck");
        RvTrack.backtrack(6, 2, "bbb", "ccc", 5, "saturation");
        assertEquals(2, RvTrack.getBacktrackCount());
    }

    @Test
    void testOomIncrementsThrottleEvents() {
        RvTrack.oom(10, 8.5, 75, 1500);
        assertEquals(1, RvTrack.getOomThrottleEvents());
    }

    @Test
    void testLearnIncrementsRetriesWhenPositive() {
        RvTrack.learn(1, 1.0, 0, true, 2);
        RvTrack.learn(2, 0.5, 0, false, 0);
        RvTrack.learn(3, -0.1, 0, false, 3);
        assertEquals(5, RvTrack.getMultiAttemptRetries());
    }

    @Test
    void testLearnZeroRetriesDoesNotIncrement() {
        RvTrack.learn(1, 1.0, 0, true, 0);
        assertEquals(0, RvTrack.getMultiAttemptRetries());
    }

    @Test
    void testIncrementSystemDialogs() {
        RvTrack.incrementSystemDialogs();
        RvTrack.incrementSystemDialogs();
        assertEquals(2, RvTrack.getSystemDialogsDismissed());
    }

    @Test
    void testIncrementRestarts() {
        RvTrack.incrementRestarts();
        assertEquals(1, RvTrack.getRestartCount());
    }

    @Test
    void testIncrementCircuitBreakerTrips() {
        RvTrack.incrementCircuitBreakerTrips();
        RvTrack.incrementCircuitBreakerTrips();
        RvTrack.incrementCircuitBreakerTrips();
        assertEquals(3, RvTrack.getCircuitBreakerTrips());
    }

    @Test
    void testAllCountersIndependent() {
        RvTrack.crash(0, "java", "CLICK", 50);
        RvTrack.stuck(1, 1, "hash", 10, "BACK");
        RvTrack.backtrack(2, 1, "a", "b", 1, "test");
        RvTrack.oom(3, 5.0, 100, 1000);
        RvTrack.learn(4, 1.0, 0, true, 2);
        RvTrack.incrementSystemDialogs();
        RvTrack.incrementRestarts();
        RvTrack.incrementCircuitBreakerTrips();

        assertEquals(1, RvTrack.getCrashRecoveries());
        assertEquals(1, RvTrack.getStuckLevel1Count());
        assertEquals(1, RvTrack.getBacktrackCount());
        assertEquals(1, RvTrack.getOomThrottleEvents());
        assertEquals(2, RvTrack.getMultiAttemptRetries());
        assertEquals(1, RvTrack.getSystemDialogsDismissed());
        assertEquals(1, RvTrack.getRestartCount());
        assertEquals(1, RvTrack.getCircuitBreakerTrips());
    }
}
