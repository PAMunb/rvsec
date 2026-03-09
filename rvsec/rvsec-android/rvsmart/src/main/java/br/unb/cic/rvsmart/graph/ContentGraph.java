package br.unb.cic.rvsmart.graph;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * Graph-based state tracking keyed by content hash.
 *
 * Maps contentHash → ContentNode. Uses LinkedHashMap to preserve insertion order
 * for deterministic BFS traversal when --seed is provided (INV-RSM-03).
 *
 * Content hash encodes the visible UI state: widget text, enabled, checkable fields.
 * Two screens with the same layout but different text content produce different
 * content hashes and thus different ContentNode entries.
 *
 * Thread-safe: all mutations go through this class (single-threaded agent loop).
 */
public class ContentGraph {

    private final LinkedHashMap<String, ContentNode> nodes = new LinkedHashMap<>();

    /**
     * Get or create a ContentNode for the given content hash.
     */
    public ContentNode getOrCreate(String contentHash, String activity) {
        ContentNode node = nodes.get(contentHash);
        if (node == null) {
            node = new ContentNode(contentHash, activity);
            nodes.put(contentHash, node);
        }
        return node;
    }

    /**
     * Get an existing ContentNode, or null if not yet visited.
     */
    public ContentNode get(String contentHash) {
        return nodes.get(contentHash);
    }

    /**
     * Record a visit to a state. Increments visit count.
     */
    public void recordVisit(String contentHash, String activity) {
        getOrCreate(contentHash, activity).incrementVisitCount();
    }

    /**
     * Record a state transition (edge) from one content state to another.
     */
    public void recordTransition(String fromHash, String toHash) {
        ContentNode from = nodes.get(fromHash);
        if (from != null) {
            from.addTransition(toHash);
        }
    }

    /**
     * Pre-mark an action before execution (crash safety).
     * If the app crashes during execution, the graph still records the attempt.
     */
    public void recordAction(String contentHash, String signature, String widgetClass) {
        ContentNode node = nodes.get(contentHash);
        if (node != null) {
            node.recordAction(signature, widgetClass);
        }
    }

    /**
     * Record whether an action caused a state transition.
     */
    public void recordActionSuccess(String contentHash, String signature, boolean hadEffect) {
        ContentNode node = nodes.get(contentHash);
        if (node != null) {
            node.recordActionSuccess(signature, hadEffect);
        }
    }

    /**
     * Get visit count for a state. Returns 0 if not yet visited.
     */
    public int getVisitCount(String contentHash) {
        ContentNode node = nodes.get(contentHash);
        return node != null ? node.getVisitCount() : 0;
    }

    /**
     * Get saturation rate for a state. Returns 1.0 if not yet visited.
     */
    public float getSaturation(String contentHash) {
        ContentNode node = nodes.get(contentHash);
        return node != null ? node.getSaturationRate() : 1.0f;
    }

    /**
     * Total number of unique content states discovered.
     */
    public int size() {
        return nodes.size();
    }

    /**
     * All discovered content hashes in insertion order.
     */
    public Set<String> getStateHashes() {
        return nodes.keySet();
    }

    /**
     * Total number of transitions (edges) across all nodes.
     */
    public int totalTransitions() {
        int total = 0;
        for (ContentNode node : nodes.values()) {
            total += node.getTransitions().size();
        }
        return total;
    }

    /**
     * All nodes in insertion order (for BFS/iteration).
     */
    public Map<String, ContentNode> getNodes() {
        return java.util.Collections.unmodifiableMap(nodes);
    }
}
