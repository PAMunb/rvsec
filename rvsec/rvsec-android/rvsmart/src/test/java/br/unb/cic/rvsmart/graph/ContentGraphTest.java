package br.unb.cic.rvsmart.graph;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for ContentGraph: contentHash → ContentNode mapping.
 */
class ContentGraphTest {

    private ContentGraph graph;

    @BeforeEach
    void setUp() {
        graph = new ContentGraph();
    }

    @Test
    void testRecordVisitIncrementsCount() {
        graph.recordVisit("content1", "MainActivity");
        assertEquals(1, graph.getVisitCount("content1"));

        graph.recordVisit("content1", "MainActivity");
        assertEquals(2, graph.getVisitCount("content1"));
    }

    @Test
    void testGetReturnsNullForUnvisited() {
        assertNull(graph.get("nonexistent"));
        assertEquals(0, graph.getVisitCount("nonexistent"));
    }

    @Test
    void testRecordActionAndSuccess() {
        graph.recordVisit("content1", "Main");
        graph.recordAction("content1", "click@540,960", "Button");

        ContentNode node = graph.get("content1");
        assertNotNull(node);
        assertEquals(1, node.getExecutionCount("click@540,960"));
        assertTrue(node.isActionExecuted("click@540,960"));

        graph.recordActionSuccess("content1", "click@540,960", true);
        assertEquals(1.0f, node.getActionStrength("click@540,960"), 0.01f);
    }

    @Test
    void testSizeCountsUniqueContentHashes() {
        assertEquals(0, graph.size());
        graph.recordVisit("c1", "A");
        graph.recordVisit("c2", "B");
        assertEquals(2, graph.size());
        // Revisiting same hash doesn't increase size
        graph.recordVisit("c1", "A");
        assertEquals(2, graph.size());
    }

    @Test
    void testTotalTransitions() {
        graph.recordVisit("c1", "A");
        graph.recordVisit("c2", "B");
        graph.recordTransition("c1", "c2");

        assertEquals(1, graph.totalTransitions());

        ContentNode node = graph.get("c1");
        assertTrue(node.getTransitions().contains("c2"));
    }
}
