package br.unb.cic.rvsmart.strategy;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.output.RvTrack;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class PathBufferTest {

    private PathBuffer buffer;

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;
        buffer = new PathBuffer();
    }

    @Test
    void testHasPathReturnsFalseWhenEmpty() {
        assertFalse(buffer.hasPath());
    }

    @Test
    void testStoreAndHasPath() {
        List<String> path = Arrays.asList("hash_A", "hash_B");
        buffer.store(PathBuffer.Strategy.BACKTRACK, path);
        assertTrue(buffer.hasPath());
    }

    @Test
    void testNextActionReturnsBackActions() {
        List<String> path = Arrays.asList("hash_A", "hash_B", "hash_C");
        buffer.store(PathBuffer.Strategy.MOP, path);

        Action first = buffer.nextAction();
        assertNotNull(first);
        assertEquals(Action.Type.BACK, first.getType());

        Action second = buffer.nextAction();
        assertNotNull(second);
        assertEquals(Action.Type.BACK, second.getType());

        Action third = buffer.nextAction();
        assertNotNull(third);
        assertEquals(Action.Type.BACK, third.getType());

        // Path exhausted
        assertFalse(buffer.hasPath());
        assertNull(buffer.nextAction());
    }

    @Test
    void testInvalidateClearsPath() {
        buffer.store(PathBuffer.Strategy.COVERAGE, Arrays.asList("hash_A", "hash_B"));
        assertTrue(buffer.hasPath());

        buffer.invalidate();
        assertFalse(buffer.hasPath());
        assertNull(buffer.nextAction());
    }

    @Test
    void testInvalidateIfDivergedClearsOnMismatch() {
        // Path expects hash_A then hash_B
        buffer.store(PathBuffer.Strategy.BACKTRACK, Arrays.asList("hash_A", "hash_B"));
        // Navigate to hash_A correctly — no invalidation yet
        // (expected next is hash_A; current IS hash_A)
        buffer.invalidateIfDiverged("hash_A");
        assertTrue(buffer.hasPath());
    }

    @Test
    void testInvalidateIfDivergedClearsWhenHashDoesNotMatch() {
        buffer.store(PathBuffer.Strategy.BACKTRACK, Arrays.asList("hash_A", "hash_B"));
        // Agent landed on hash_X instead of expected hash_A
        buffer.invalidateIfDiverged("hash_X");
        assertFalse(buffer.hasPath());
    }

    @Test
    void testActiveStrategyTracked() {
        buffer.store(PathBuffer.Strategy.MOP, Arrays.asList("hash_A"));
        assertEquals(PathBuffer.Strategy.MOP, buffer.getActiveStrategy());
    }

    @Test
    void testActiveStrategyNullAfterInvalidate() {
        buffer.store(PathBuffer.Strategy.COVERAGE, Arrays.asList("hash_A"));
        buffer.invalidate();
        assertNull(buffer.getActiveStrategy());
    }

    @Test
    void testRemainingActionsCount() {
        buffer.store(PathBuffer.Strategy.BACKTRACK, Arrays.asList("h1", "h2", "h3"));
        assertEquals(3, buffer.remainingActions());

        buffer.nextAction();
        assertEquals(2, buffer.remainingActions());
    }

    @Test
    void testStoreReplacesExistingPath() {
        buffer.store(PathBuffer.Strategy.BACKTRACK, Arrays.asList("hash_A", "hash_B"));
        buffer.store(PathBuffer.Strategy.MOP, Arrays.asList("hash_X"));
        assertEquals(1, buffer.remainingActions());
        assertEquals(PathBuffer.Strategy.MOP, buffer.getActiveStrategy());
    }

    @Test
    void testEmptyPathStoreResultsInNoPath() {
        buffer.store(PathBuffer.Strategy.COVERAGE, Collections.emptyList());
        assertFalse(buffer.hasPath());
    }

    @Test
    void testNextActionReturnsNullWhenEmpty() {
        assertNull(buffer.nextAction());
    }
}
