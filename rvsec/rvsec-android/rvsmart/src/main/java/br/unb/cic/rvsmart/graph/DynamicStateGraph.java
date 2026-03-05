package br.unb.cic.rvsmart.graph;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * Graph-based state tracking using structural hashes and action signatures.
 *
 * Uses LinkedHashMap to preserve insertion order for deterministic BFS
 * traversal when --seed is provided. Each state is a ScreenNode identified
 * by its structural hash (INV-RSM-03).
 *
 * Thread-safe: all mutations go through this class (single-threaded agent loop).
 */
public class DynamicStateGraph {

    private final LinkedHashMap<String, ScreenNode> nodes = new LinkedHashMap<>();

    /**
     * Get or create a ScreenNode for the given hash.
     */
    public ScreenNode getOrCreate(String hash, String activity) {
        ScreenNode node = nodes.get(hash);
        if (node == null) {
            node = new ScreenNode(hash, activity);
            nodes.put(hash, node);
        }
        return node;
    }

    /**
     * Get an existing ScreenNode, or null if not yet visited.
     */
    public ScreenNode get(String hash) {
        return nodes.get(hash);
    }

    /**
     * Record a visit to a state. Increments visit count.
     */
    public void recordVisit(String hash, String activity) {
        getOrCreate(hash, activity).incrementVisitCount();
    }

    /**
     * Record a state transition (edge) from one state to another.
     */
    public void recordTransition(String fromHash, String toHash) {
        ScreenNode from = nodes.get(fromHash);
        if (from != null) {
            from.addTransition(toHash);
        }
    }

    /**
     * Pre-mark an action before execution (crash safety).
     * If the app crashes during execution, the graph still records the attempt.
     */
    public void recordAction(String hash, String signature, String widgetClass) {
        ScreenNode node = nodes.get(hash);
        if (node != null) {
            node.recordAction(signature, widgetClass);
        }
    }

    /**
     * Record whether an action caused a state transition.
     */
    public void recordActionSuccess(String hash, String signature, boolean success) {
        ScreenNode node = nodes.get(hash);
        if (node != null) {
            node.recordActionSuccess(signature, success);
        }
    }

    /**
     * Get visit count for a state. Returns 0 if not yet visited.
     */
    public int getVisitCount(String hash) {
        ScreenNode node = nodes.get(hash);
        return node != null ? node.getVisitCount() : 0;
    }

    /**
     * Get saturation rate for a state. Returns 1.0 if not yet visited.
     */
    public float getSaturation(String hash) {
        ScreenNode node = nodes.get(hash);
        return node != null ? node.getSaturationRate() : 1.0f;
    }

    /**
     * Total number of unique states discovered.
     */
    public int size() {
        return nodes.size();
    }

    /**
     * All discovered state hashes in insertion order.
     */
    public Set<String> getStateHashes() {
        return nodes.keySet();
    }

    /**
     * Total number of transitions (edges) across all nodes.
     * Each node tracks unique target hashes; this sums those counts.
     */
    public int totalTransitions() {
        int total = 0;
        for (ScreenNode node : nodes.values()) {
            total += node.getTransitions().size();
        }
        return total;
    }

    /**
     * All nodes in insertion order (for BFS/iteration).
     */
    public Map<String, ScreenNode> getNodes() {
        return java.util.Collections.unmodifiableMap(nodes);
    }
}
