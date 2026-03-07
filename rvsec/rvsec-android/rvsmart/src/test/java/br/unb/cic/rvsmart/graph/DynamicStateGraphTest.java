package br.unb.cic.rvsmart.graph;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for DynamicStateGraph and ScreenNode operations.
 */
class DynamicStateGraphTest {

    private DynamicStateGraph graph;

    @BeforeEach
    void setUp() {
        graph = new DynamicStateGraph();
    }

    @Test
    void testRecordVisit() {
        graph.recordVisit("hash1", "MainActivity");
        assertEquals(1, graph.getVisitCount("hash1"));

        graph.recordVisit("hash1", "MainActivity");
        assertEquals(2, graph.getVisitCount("hash1"));
    }

    @Test
    void testUnvisitedReturnsZero() {
        assertEquals(0, graph.getVisitCount("nonexistent"));
    }

    @Test
    void testRecordTransition() {
        graph.recordVisit("hash1", "Activity1");
        graph.recordVisit("hash2", "Activity2");
        graph.recordTransition("hash1", "hash2");

        ScreenNode node = graph.get("hash1");
        assertTrue(node.getTransitions().contains("hash2"));
    }

    @Test
    void testRecordAction() {
        graph.recordVisit("hash1", "Main");
        graph.recordAction("hash1", "click@540,960", "Button");

        ScreenNode node = graph.get("hash1");
        assertEquals(1, node.getExecutionCount("click@540,960"));
        assertTrue(node.isActionExecuted("click@540,960"));
    }

    @Test
    void testActionStrength() {
        graph.recordVisit("hash1", "Main");

        ScreenNode node = graph.get("hash1");
        // Untested action returns 0.5 (neutral)
        assertEquals(0.5f, node.getActionStrength("click@100,200"), 0.01f);

        // Execute 3 times, succeed 2 times
        node.recordAction("click@100,200", "Button");
        node.recordActionSuccess("click@100,200", true);
        node.recordAction("click@100,200", "Button");
        node.recordActionSuccess("click@100,200", true);
        node.recordAction("click@100,200", "Button");
        node.recordActionSuccess("click@100,200", false);

        assertEquals(2.0f / 3.0f, node.getActionStrength("click@100,200"), 0.01f);
    }

    @Test
    void testSaturation() {
        graph.recordVisit("hash1", "Main");
        // No actions — saturation is 1.0 (fully saturated)
        assertEquals(1.0f, graph.getSaturation("hash1"), 0.01f);

        // Unvisited — saturation is 1.0
        assertEquals(1.0f, graph.getSaturation("nonexistent"), 0.01f);
    }

    @Test
    void testSaturationRate() {
        ScreenNode node = new ScreenNode("hash1", "Main");
        node.setTotalActions(3);

        // No actions executed
        assertEquals(0.0f, node.getSaturationRate(), 0.01f);

        // Execute one action 4 times (threshold=4 for Button)
        node.recordAction("click@100,200", "Button");
        node.recordAction("click@100,200", "Button");
        node.recordAction("click@100,200", "Button");
        node.recordAction("click@100,200", "Button");
        // 1 saturated / 3 total = 0.33
        assertEquals(1.0f / 3.0f, node.getSaturationRate(), 0.01f);
    }

    @Test
    void testMultiValueWidgetThreshold() {
        ScreenNode node = new ScreenNode("hash1", "Form");
        node.setTotalActions(1);
        node.setMultiValueThreshold(4);

        // EditText needs 4 executions to saturate
        node.recordAction("click@100,200", "EditText");
        node.recordAction("click@100,200", "EditText");
        assertFalse(node.isActionSaturated("click@100,200"));

        node.recordAction("click@100,200", "EditText");
        node.recordAction("click@100,200", "EditText");
        assertTrue(node.isActionSaturated("click@100,200"));
    }

    @Test
    void testSystemActionsExcludedFromSaturation() {
        ScreenNode node = new ScreenNode("hash1", "Main");
        node.setTotalActions(2);

        // Execute a BACK action 10 times — should NOT count in saturation
        for (int i = 0; i < 10; i++) {
            node.recordAction("back@0,0", "");
        }
        // Only BACK is executed, but it's a system action → 0 saturated / 2 total
        assertEquals(0.0f, node.getSaturationRate(), 0.01f);
    }

    @Test
    void testCoverage() {
        ScreenNode node = new ScreenNode("hash1", "Main");
        node.setTotalActions(4);

        assertEquals(0.0f, node.getCoverage(), 0.01f);

        node.recordAction("click@100,200", "Button");
        node.recordAction("click@300,400", "Button");
        assertEquals(0.5f, node.getCoverage(), 0.01f);
    }

    @Test
    void testCumulativeReward() {
        ScreenNode node = new ScreenNode("hash1", "Main");
        assertEquals(0.0, node.getCumulativeReward("click@100,200"), 0.01);

        node.setCumulativeReward("click@100,200", 5.0);
        assertEquals(5.0, node.getCumulativeReward("click@100,200"), 0.01);
    }

    @Test
    void testInsertionOrder() {
        graph.recordVisit("c", "C");
        graph.recordVisit("a", "A");
        graph.recordVisit("b", "B");

        // LinkedHashMap preserves insertion order
        String[] hashes = graph.getStateHashes().toArray(new String[0]);
        assertEquals("c", hashes[0]);
        assertEquals("a", hashes[1]);
        assertEquals("b", hashes[2]);
    }

    @Test
    void testGraphSize() {
        assertEquals(0, graph.size());
        graph.recordVisit("h1", "A");
        graph.recordVisit("h2", "B");
        assertEquals(2, graph.size());
        // Revisiting same hash doesn't increase size
        graph.recordVisit("h1", "A");
        assertEquals(2, graph.size());
    }
}
