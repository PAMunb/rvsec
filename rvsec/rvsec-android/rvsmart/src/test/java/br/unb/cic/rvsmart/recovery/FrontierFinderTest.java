package br.unb.cic.rvsmart.recovery;

import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.graph.ContentNode;
import br.unb.cic.rvsmart.output.RvTrack;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Collections;
import java.util.HashSet;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for FrontierFinder BFS forward search (INV-RSM-46).
 */
class FrontierFinderTest {

    private FrontierFinder finder;
    private ContentGraph graph;

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;
        finder = new FrontierFinder();
        graph = new ContentGraph();
    }

    @Test
    void testFrontierFoundVia2HopPath() {
        // H1 -> H2 -> H3 (frontier: coverage 0.3)
        ContentNode h1 = graph.getOrCreate("H1", "A");
        h1.setTotalActions(10);
        saturateNode(h1, 10); // fully saturated
        h1.addTransition("H2");

        ContentNode h2 = graph.getOrCreate("H2", "A");
        h2.setTotalActions(10);
        saturateNode(h2, 10); // fully saturated
        h2.addTransition("H3");

        ContentNode h3 = graph.getOrCreate("H3", "A");
        h3.setTotalActions(10);
        saturateNode(h3, 3); // 30% coverage — frontier

        String result = finder.findFrontier("H1", graph, 0.8f, Collections.emptySet());
        assertEquals("H3", result);
    }

    @Test
    void testNoFrontierWhenAllSaturated() {
        ContentNode h1 = graph.getOrCreate("H1", "A");
        h1.setTotalActions(10);
        saturateNode(h1, 10);
        h1.addTransition("H2");

        ContentNode h2 = graph.getOrCreate("H2", "A");
        h2.setTotalActions(10);
        saturateNode(h2, 10);

        String result = finder.findFrontier("H1", graph, 0.8f, Collections.emptySet());
        assertNull(result, "No frontier when all reachable states are saturated");
    }

    @Test
    void testSterileNodesExcludedFromFrontier() {
        // H1 -> H2 (sterile, low coverage) -> H3 (low coverage, not sterile)
        ContentNode h1 = graph.getOrCreate("H1", "A");
        h1.setTotalActions(10);
        saturateNode(h1, 10);
        h1.addTransition("H2");

        ContentNode h2 = graph.getOrCreate("H2", "A");
        h2.setTotalActions(10);
        saturateNode(h2, 2); // low coverage but sterile
        h2.addTransition("H3");

        ContentNode h3 = graph.getOrCreate("H3", "A");
        h3.setTotalActions(10);
        saturateNode(h3, 1); // low coverage, not sterile

        Set<String> sterile = new HashSet<>();
        sterile.add("H2");

        String result = finder.findFrontier("H1", graph, 0.8f, sterile);
        assertEquals("H3", result, "Should skip sterile H2 and find H3");
    }

    @Test
    void testNullWhenGraphEmpty() {
        String result = finder.findFrontier("H1", graph, 0.8f, Collections.emptySet());
        assertNull(result, "Should return null when start hash not in graph");
    }

    @Test
    void testStartNodeNotReturnedAsFrontier() {
        // Start node has low coverage but should not be returned as frontier
        ContentNode h1 = graph.getOrCreate("H1", "A");
        h1.setTotalActions(10);
        saturateNode(h1, 2); // low coverage

        String result = finder.findFrontier("H1", graph, 0.8f, Collections.emptySet());
        assertNull(result, "Start node should not be returned as frontier");
    }

    @Test
    void testNearestFrontierReturned() {
        // H1 -> H2 (frontier, 1 hop) AND H1 -> H3 -> H4 (frontier, 2 hops)
        // BFS should return H2 (nearest)
        ContentNode h1 = graph.getOrCreate("H1", "A");
        h1.setTotalActions(10);
        saturateNode(h1, 10);
        h1.addTransition("H2");
        h1.addTransition("H3");

        ContentNode h2 = graph.getOrCreate("H2", "A");
        h2.setTotalActions(10);
        saturateNode(h2, 2); // frontier (20% coverage)

        ContentNode h3 = graph.getOrCreate("H3", "A");
        h3.setTotalActions(10);
        saturateNode(h3, 10); // saturated
        h3.addTransition("H4");

        ContentNode h4 = graph.getOrCreate("H4", "A");
        h4.setTotalActions(10);
        saturateNode(h4, 1); // frontier (10% coverage)

        String result = finder.findFrontier("H1", graph, 0.8f, Collections.emptySet());
        assertEquals("H2", result, "BFS should return nearest frontier (INV-RSM-46)");
    }

    @Test
    void testNullInputsHandled() {
        assertNull(finder.findFrontier(null, graph, 0.8f, null));
        assertNull(finder.findFrontier("H1", null, 0.8f, null));
    }

    /**
     * Simulate saturating N distinct actions on a node.
     * Each action gets enough executions to be considered saturated.
     */
    private void saturateNode(ContentNode node, int numActions) {
        for (int i = 0; i < numActions; i++) {
            String sig = "click@" + (i * 100) + ",500";
            for (int j = 0; j < 5; j++) {
                node.recordAction(sig, "Button");
            }
        }
    }
}
