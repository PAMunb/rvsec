package br.unb.cic.rvsmart.graph;

import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
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
    private final Set<String> sterileHashes = new HashSet<>();
    private final Map<String, Integer> sterileCounters = new HashMap<>();
    private final Set<String> tarpitHashes = new HashSet<>();

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
     * Increment the sterile counter for a hash. Called when UIAutomator returns null root
     * and the hash was the last known content hash from the previous successful iteration.
     */
    public void incrementSterileCounter(String hash) {
        if (hash == null) return;
        sterileCounters.put(hash, sterileCounters.getOrDefault(hash, 0) + 1);
    }

    /**
     * Reset the sterile counter for a hash. Called when a successful parse occurs
     * at this hash, preventing transient failures from blacklisting valid screens.
     */
    public void resetSterileCounter(String hash) {
        if (hash == null) return;
        sterileCounters.remove(hash);
    }

    /**
     * Mark a hash as permanently sterile for this run.
     * Once sterile, a hash remains sterile for the duration of the run.
     */
    public void markSterile(String hash) {
        if (hash == null) return;
        sterileHashes.add(hash);
    }

    /**
     * Check if a hash is marked sterile.
     */
    public boolean isSterile(String hash) {
        return hash != null && sterileHashes.contains(hash);
    }

    /**
     * Get unmodifiable view of all sterile hashes (INV-RSM-44).
     */
    public Set<String> getSterileHashes() {
        return Collections.unmodifiableSet(sterileHashes);
    }

    /**
     * Get the current sterile counter for a hash.
     */
    public int getSterileCounter(String hash) {
        return hash != null ? sterileCounters.getOrDefault(hash, 0) : 0;
    }

    /**
     * Mark a hash as a tarpit screen. Unlike sterile screens (UIAutomator failure),
     * tarpit screens parse fine but the agent makes no algorithmic progress.
     */
    public void markTarpit(String hash) {
        if (hash != null) tarpitHashes.add(hash);
    }

    /**
     * Check if a hash is marked as tarpit.
     */
    public boolean isTarpit(String hash) {
        return hash != null && tarpitHashes.contains(hash);
    }

    /**
     * Get unmodifiable view of all tarpit hashes.
     */
    public Set<String> getTarpitHashes() {
        return Collections.unmodifiableSet(tarpitHashes);
    }

    /**
     * All nodes in insertion order (for BFS/iteration).
     */
    public Map<String, ContentNode> getNodes() {
        return Collections.unmodifiableMap(nodes);
    }
}
