package br.unb.cic.rvsmart.recovery;

import br.unb.cic.rvsmart.graph.DynamicStateGraph;
import br.unb.cic.rvsmart.graph.ScreenNode;
import br.unb.cic.rvsmart.strategy.SuccessorTracker;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Queue;
import java.util.Set;

/**
 * BFS pathfinder on the parent graph for Level 2 stuck recovery.
 *
 * When the stuck detector fires Level 1 and simple BACK actions fail to help,
 * BacktrackBfs searches ancestor states for one with fewer visits than the
 * saturation threshold. The path to that state is returned as an ordered list
 * of screen hashes — each hop corresponds to one BACK action in PathBuffer.
 *
 * BFS is used (not DFS) to find the shortest path to an unsaturated ancestor,
 * minimising the number of BACK actions needed and reducing the risk of
 * navigating to a dead-end state.
 */
public class BacktrackBfs {

    /**
     * BFS from startHash through parent edges recorded in SuccessorTracker.
     * Returns the shortest path (list of hashes) to an ancestor with
     * visitCount < saturationThreshold. Returns null if no such ancestor exists.
     *
     * @param startHash            the current screen hash
     * @param tracker              parent-child edge store
     * @param graph                graph with visit counts
     * @param saturationThreshold  max visitCount to be considered unsaturated
     * @return ordered list of hashes from startHash to the target (inclusive of start,
     *         exclusive of start itself — i.e. the sequence of screens to navigate through),
     *         or null if not found
     */
    public List<String> findPathToUnsaturated(String startHash, SuccessorTracker tracker,
                                              DynamicStateGraph graph, int saturationThreshold) {
        Queue<String> queue = new ArrayDeque<>();
        Set<String> visited = new HashSet<>();
        Map<String, String> parentMap = new HashMap<>(); // child -> parent for path reconstruction

        queue.add(startHash);
        visited.add(startHash);

        while (!queue.isEmpty()) {
            String current = queue.poll();

            // Check if this node is unsaturated (and not the start node itself)
            if (!current.equals(startHash)) {
                ScreenNode node = graph.get(current);
                int visitCount = node != null ? node.getVisitCount() : 0;
                if (visitCount < saturationThreshold) {
                    return reconstructPath(startHash, current, parentMap);
                }
            }

            // Expand parents (going backwards through the state graph)
            for (String parent : tracker.getParents(current)) {
                if (!visited.contains(parent)) {
                    visited.add(parent);
                    parentMap.put(parent, current);
                    queue.add(parent);
                }
            }
        }

        return null; // No unsaturated ancestor found
    }

    /**
     * Reconstructs the path from startHash to targetHash using the BFS parent map.
     * Returns the hashes in order from startHash to targetHash (both inclusive).
     * PathBuffer generates N-1 BACK actions for N hashes.
     */
    private List<String> reconstructPath(String startHash, String targetHash,
                                         Map<String, String> parentMap) {
        List<String> path = new ArrayList<>();
        String current = targetHash;

        while (current != null && !current.equals(startHash)) {
            path.add(current);
            current = parentMap.get(current);
        }
        path.add(startHash); // include starting position

        Collections.reverse(path);
        return path;
    }
}
