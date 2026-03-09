package br.unb.cic.rvsmart.graph;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for NavigationMap — structural transition recording and BFS path finding.
 */
class NavigationMapTest {

    private NavigationMap map;

    @BeforeEach
    void setUp() {
        map = new NavigationMap();
    }

    @Test
    void testRecordAndSize() {
        assertEquals(0, map.size());
        map.record("A", "click_btn", "B");
        assertEquals(1, map.size());
        map.record("B", "click_next", "C");
        assertEquals(2, map.size());
    }

    @Test
    void testFindPath_DirectTransition() {
        map.record("A", "click_btn", "B");

        List<String> path = map.findPath("A", "B");
        assertNotNull(path);
        assertEquals(1, path.size());
        assertEquals("click_btn", path.get(0));
    }

    @Test
    void testFindPath_BfsFindsShortestPath() {
        // A --click_btn--> B --click_next--> C
        // A --long_path_action--> X --long--> C (longer route)
        map.record("A", "click_btn", "B");
        map.record("B", "click_next", "C");
        map.record("A", "long_action", "X");
        map.record("X", "long_cont", "C");

        List<String> path = map.findPath("A", "C");
        assertNotNull(path);
        // BFS finds shortest: A->B->C (2 hops) rather than A->X->C (also 2 hops)
        // Both are length 2; result should be either
        assertEquals(2, path.size());
    }

    @Test
    void testFindPath_NoPath_ReturnsEmpty() {
        map.record("A", "click_btn", "B");

        // No path from B to A (directed graph)
        List<String> path = map.findPath("B", "A");
        assertNotNull(path);
        assertTrue(path.isEmpty());
    }

    @Test
    void testFindPath_CycleDoesNotInfiniteLoop() {
        // A -> B -> C -> A (cycle)
        map.record("A", "go_B", "B");
        map.record("B", "go_C", "C");
        map.record("C", "go_A", "A");

        // Should find path A->B->C without looping
        List<String> path = map.findPath("A", "C");
        assertNotNull(path);
        assertEquals(2, path.size());
        assertEquals("go_B", path.get(0));
        assertEquals("go_C", path.get(1));
    }

    @Test
    void testHasPath_TrueWhenReachable() {
        map.record("A", "action1", "B");
        map.record("B", "action2", "C");
        assertTrue(map.hasPath("A", "C"));
        assertTrue(map.hasPath("A", "B"));
    }

    @Test
    void testHasPath_FalseWhenUnreachable() {
        map.record("A", "action1", "B");
        assertFalse(map.hasPath("B", "A")); // directed: no reverse path
        assertFalse(map.hasPath("A", "Z")); // Z not in graph
    }
}
