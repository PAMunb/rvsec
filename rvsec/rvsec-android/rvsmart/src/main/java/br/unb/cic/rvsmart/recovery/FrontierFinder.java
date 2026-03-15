package br.unb.cic.rvsmart.recovery;

import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.graph.ContentNode;

import java.util.ArrayDeque;
import java.util.HashSet;
import java.util.Queue;
import java.util.Set;

/**
 * BFS forward through ContentGraph transitions to find the nearest frontier state.
 *
 * A frontier state is a content state with coverage below the threshold and not
 * marked as sterile. The search is diagnostic: it answers "does an unsaturated
 * state exist forward from here?" rather than providing a navigation path.
 *
 * When a frontier is found, StuckDetector returns RESTART — the agent re-enters
 * from the main activity and UCB+scorers naturally bias toward unsaturated states.
 *
 * BFS guarantees shortest-path property (INV-RSM-46): the returned frontier is
 * the nearest reachable one in terms of transition hops.
 */
public class FrontierFinder {

    /**
     * Find the nearest frontier state reachable from startHash via forward transitions.
     *
     * @param startHash         current content hash
     * @param graph             the ContentGraph with nodes and transitions
     * @param coverageThreshold coverage below this = frontier candidate (e.g. 0.8)
     * @param sterileHashes     hashes to exclude from candidates (may be null)
     * @return hash of nearest frontier node, or null if none found
     */
    public String findFrontier(String startHash, ContentGraph graph,
                                float coverageThreshold, Set<String> sterileHashes) {
        if (startHash == null || graph == null) return null;

        ContentNode startNode = graph.get(startHash);
        if (startNode == null) return null;

        Queue<String> queue = new ArrayDeque<>();
        Set<String> visited = new HashSet<>();

        queue.add(startHash);
        visited.add(startHash);

        while (!queue.isEmpty()) {
            String current = queue.poll();
            ContentNode node = graph.get(current);
            if (node == null) continue;

            // Check if this node is a frontier (not the start, not sterile, low coverage)
            if (!current.equals(startHash)) {
                boolean isSterile = sterileHashes != null && sterileHashes.contains(current);
                if (!isSterile && node.getCoverage() < coverageThreshold) {
                    return current;
                }
            }

            // Expand forward transitions
            for (String neighbor : node.getTransitions()) {
                if (!visited.contains(neighbor)) {
                    // Skip sterile nodes for traversal too — BFS continues past them
                    // to search deeper nodes (INV-RSM-44)
                    visited.add(neighbor);
                    queue.add(neighbor);
                }
            }
        }

        return null; // No frontier found
    }
}
