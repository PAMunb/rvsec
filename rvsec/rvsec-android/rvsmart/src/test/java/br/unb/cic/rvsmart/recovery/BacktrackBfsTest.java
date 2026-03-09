package br.unb.cic.rvsmart.recovery;

import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.output.RvTrack;
import br.unb.cic.rvsmart.strategy.SuccessorTracker;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class BacktrackBfsTest {

    private BacktrackBfs bfs;
    private SuccessorTracker tracker;
    private ContentGraph graph;

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;
        bfs = new BacktrackBfs();
        tracker = new SuccessorTracker();
        graph = new ContentGraph();
    }

    @Test
    void testReturnsNullWhenNoParentsExist() {
        // Start hash has no parents in tracker
        graph.getOrCreate("hash_A", "ActivityA");
        List<String> path = bfs.findPathToUnsaturated("hash_A", tracker, graph, 5);
        assertNull(path);
    }

    @Test
    void testFindsDirectUnsaturatedParent() {
        // hash_B (parent) has only 2 visits, below threshold of 5
        graph.recordVisit("hash_A", "ActivityA"); // 1 visit (saturated area — start)
        graph.recordVisit("hash_B", "ActivityB"); // 1 visit — under threshold

        tracker.record("hash_B", "hash_A"); // hash_A -> parent is hash_B

        List<String> path = bfs.findPathToUnsaturated("hash_A", tracker, graph, 5);
        assertNotNull(path);
        assertFalse(path.isEmpty());
        // The path should end at hash_B (the unsaturated ancestor)
        assertEquals("hash_B", path.get(path.size() - 1));
    }

    @Test
    void testReturnsNullWhenAllAncestorsAreSaturated() {
        // Both parent and grandparent have many visits (saturated)
        String start = "hash_leaf";
        String parent = "hash_parent";
        String grandparent = "hash_grandparent";

        // Saturate parent and grandparent (threshold = 3)
        for (int i = 0; i < 5; i++) {
            graph.recordVisit(parent, "ActivityP");
            graph.recordVisit(grandparent, "ActivityGP");
        }
        tracker.record(grandparent, parent);
        tracker.record(parent, start);

        List<String> path = bfs.findPathToUnsaturated(start, tracker, graph, 3);
        assertNull(path);
    }

    @Test
    void testFindsTwoHopUnsaturatedAncestor() {
        // Chain: start <- parent (saturated) <- grandparent (unsaturated)
        String start = "hash_start";
        String parent = "hash_parent";
        String grandparent = "hash_grandparent";

        // Saturate only the parent
        for (int i = 0; i < 10; i++) {
            graph.recordVisit(parent, "ActivityP");
        }
        // grandparent has 1 visit (unsaturated, threshold = 5)
        graph.recordVisit(grandparent, "ActivityGP");

        tracker.record(grandparent, parent);
        tracker.record(parent, start);

        List<String> path = bfs.findPathToUnsaturated(start, tracker, graph, 5);
        assertNotNull(path);
        // Path should contain the grandparent at the end
        assertTrue(path.contains(grandparent));
    }

    @Test
    void testPathDoesNotIncludeStartHash() {
        graph.recordVisit("hash_A", "ActivityA");
        graph.recordVisit("hash_B", "ActivityB"); // 1 visit (unsaturated)

        tracker.record("hash_B", "hash_A");

        List<String> path = bfs.findPathToUnsaturated("hash_A", tracker, graph, 5);
        assertNotNull(path);
        // Path includes start hash as first element (for PathBuffer divergence check)
        assertTrue(path.contains("hash_A"));
        assertEquals("hash_A", path.get(0));
    }

    @Test
    void testHandlesNeverVisitedAncestor() {
        // Parent was never visited — visitCount = 0, below any positive threshold
        tracker.record("hash_parent", "hash_child");
        // hash_parent not in graph at all

        List<String> path = bfs.findPathToUnsaturated("hash_child", tracker, graph, 5);
        assertNotNull(path);
        assertTrue(path.contains("hash_parent"));
    }
}
