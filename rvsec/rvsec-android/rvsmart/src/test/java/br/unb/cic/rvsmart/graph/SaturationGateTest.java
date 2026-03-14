package br.unb.cic.rvsmart.graph;

import br.unb.cic.rvsmart.core.Config;
import br.unb.cic.rvsmart.output.RvTrack;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for the saturation gate: ContentGraph.getSaturation() returns correct
 * values and Config.getRetrySaturationThreshold() default (INV-RSM-45).
 */
class SaturationGateTest {

    private ContentGraph graph;

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;
        graph = new ContentGraph();
    }

    @Test
    void testGetSaturationReturns1ForUnknownHash() {
        assertEquals(1.0f, graph.getSaturation("unknown"), 0.001f,
                "Unknown hash should return 1.0 (fully saturated)");
    }

    @Test
    void testGetSaturationReturns0ForNewNodeWithActions() {
        ContentNode node = graph.getOrCreate("hash_A", "ActivityA");
        node.setTotalActions(10);
        assertEquals(0.0f, graph.getSaturation("hash_A"), 0.001f,
                "New node with no executed actions should return 0.0");
    }

    @Test
    void testRetrySaturationThresholdDefault() {
        Config config = Config.defaults();
        assertEquals(0.95f, config.getRetrySaturationThreshold(), 0.001f);
    }

    @Test
    void testSaturationGateLogic() {
        // Simulate: threshold 0.95, screen saturation ~0.96 → should skip retries
        Config config = Config.defaults();
        ContentNode node = graph.getOrCreate("hash_A", "ActivityA");
        node.setTotalActions(25);
        // Saturate 24 out of 25 actions (96%)
        for (int i = 0; i < 24; i++) {
            String sig = "click@" + (i * 100) + ",500";
            for (int j = 0; j < 5; j++) {  // exceed per-action saturation threshold
                node.recordAction(sig, "Button");
            }
        }
        float saturation = graph.getSaturation("hash_A");
        assertTrue(saturation >= config.getRetrySaturationThreshold(),
                "Saturation " + saturation + " should be >= threshold 0.95");
    }
}
