package br.unb.cic.rvsmart.graph;

import br.unb.cic.rvsmart.output.RvTrack;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for sterile screen blacklist in ContentGraph.
 * Verifies counter increment, reset, marking, and unmodifiable set.
 */
class SterileBlacklistTest {

    private ContentGraph graph;

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;
        graph = new ContentGraph();
    }

    @Test
    void testMarkSterileAfter3ConsecutiveFailures() {
        String hash = "a1b2c3d4";
        graph.incrementSterileCounter(hash);
        graph.incrementSterileCounter(hash);
        graph.incrementSterileCounter(hash);
        assertEquals(3, graph.getSterileCounter(hash));

        // Mark sterile when counter reaches threshold
        graph.markSterile(hash);
        assertTrue(graph.isSterile(hash));
    }

    @Test
    void testResetSterileCounterOnSuccess() {
        String hash = "a1b2c3d4";
        graph.incrementSterileCounter(hash);
        graph.incrementSterileCounter(hash);
        assertEquals(2, graph.getSterileCounter(hash));

        graph.resetSterileCounter(hash);
        assertEquals(0, graph.getSterileCounter(hash));
        assertFalse(graph.isSterile(hash));
    }

    @Test
    void testIsSterileReturnsFalseBeforeThreshold() {
        String hash = "a1b2c3d4";
        graph.incrementSterileCounter(hash);
        graph.incrementSterileCounter(hash);
        assertFalse(graph.isSterile(hash),
                "Hash should not be sterile before being explicitly marked");
    }

    @Test
    void testGetSterileHashesReturnsUnmodifiableSet() {
        graph.markSterile("hash1");
        graph.markSterile("hash2");

        Set<String> sterile = graph.getSterileHashes();
        assertEquals(2, sterile.size());
        assertTrue(sterile.contains("hash1"));
        assertTrue(sterile.contains("hash2"));

        assertThrows(UnsupportedOperationException.class,
                () -> sterile.add("hash3"),
                "getSterileHashes() should return unmodifiable set");
    }

    @Test
    void testNullHashIsIgnored() {
        // Should not throw
        graph.incrementSterileCounter(null);
        graph.resetSterileCounter(null);
        graph.markSterile(null);
        assertFalse(graph.isSterile(null));
        assertEquals(0, graph.getSterileCounter(null));
    }

    @Test
    void testSterileHashPersistsAfterReset() {
        String hash = "a1b2c3d4";
        graph.markSterile(hash);
        assertTrue(graph.isSterile(hash));

        // Resetting counter does NOT un-mark sterile
        graph.resetSterileCounter(hash);
        assertTrue(graph.isSterile(hash),
                "Once sterile, always sterile within a run");
    }
}
