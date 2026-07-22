package br.unb.cic.rvsmart.recovery;

import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.output.RvTrack;
import br.unb.cic.rvsmart.strategy.SuccessorTracker;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

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
        List<String> path = bfs.findPathToUnsaturated("hash_A", tracker, graph, 5, Collections.emptySet());
        assertNull(path);
    }

    @Test
    void testFindsDirectUnsaturatedParent() {
        // hash_B (parent) has only 2 visits, below threshold of 5
        graph.recordVisit("hash_A", "ActivityA"); // 1 visit (saturated area — start)
        graph.recordVisit("hash_B", "ActivityB"); // 1 visit — under threshold

        tracker.record("hash_B", "hash_A"); // hash_A -> parent is hash_B

        List<String> path = bfs.findPathToUnsaturated("hash_A", tracker, graph, 5, Collections.emptySet());
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

        List<String> path = bfs.findPathToUnsaturated(start, tracker, graph, 3, Collections.emptySet());
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

        List<String> path = bfs.findPathToUnsaturated(start, tracker, graph, 5, Collections.emptySet());
        assertNotNull(path);
        // Path should contain the grandparent at the end
        assertTrue(path.contains(grandparent));
    }

    @Test
    void testPathDoesNotIncludeStartHash() {
        graph.recordVisit("hash_A", "ActivityA");
        graph.recordVisit("hash_B", "ActivityB"); // 1 visit (unsaturated)

        tracker.record("hash_B", "hash_A");

        List<String> path = bfs.findPathToUnsaturated("hash_A", tracker, graph, 5, Collections.emptySet());
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

        List<String> path = bfs.findPathToUnsaturated("hash_child", tracker, graph, 5, Collections.emptySet());
        assertNotNull(path);
        assertTrue(path.contains("hash_parent"));
    }

    @Test
    void testSterileHashExcludedFromBfsResult() {
        // Chain: start <- parent (sterile, unsaturated) <- grandparent (unsaturated)
        String start = "hash_start";
        String parent = "hash_parent";
        String grandparent = "hash_grandparent";

        graph.recordVisit(parent, "ActivityP");       // 1 visit (below threshold 5)
        graph.recordVisit(grandparent, "ActivityGP"); // 1 visit (below threshold 5)

        tracker.record(grandparent, parent);
        tracker.record(parent, start);

        // Without sterile: parent is found (shortest path)
        List<String> pathNoSterile = bfs.findPathToUnsaturated(start, tracker, graph, 5, Collections.emptySet());
        assertNotNull(pathNoSterile);
        assertTrue(pathNoSterile.contains(parent));

        // With parent sterile: grandparent is found instead
        Set<String> sterile = new HashSet<>();
        sterile.add(parent);
        List<String> pathSterile = bfs.findPathToUnsaturated(start, tracker, graph, 5, sterile);
        assertNotNull(pathSterile);
        assertTrue(pathSterile.contains(grandparent),
                "BFS should skip sterile parent and find grandparent");
    }

    @Test
    void testReturnsNullWhenOnlyUnsaturatedAncestorIsSterile() {
        graph.recordVisit("hash_parent", "ActivityP"); // 1 visit (unsaturated)
        tracker.record("hash_parent", "hash_A");

        Set<String> sterile = new HashSet<>();
        sterile.add("hash_parent");
        List<String> path = bfs.findPathToUnsaturated("hash_A", tracker, graph, 5, sterile);
        assertNull(path, "Should return null when only candidate is sterile");
    }
}
