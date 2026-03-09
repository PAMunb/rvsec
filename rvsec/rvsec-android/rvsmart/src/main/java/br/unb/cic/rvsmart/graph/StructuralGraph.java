package br.unb.cic.rvsmart.graph;

import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

/**
 * Clusters content states by structural hash.
 *
 * Maps structHash → Set<contentHash>. Structural hash encodes layout identity
 * (className, resourceID, interactMask) without dynamic content. Multiple content
 * states with the same layout belong to the same structural cluster.
 *
 * This allows the agent to detect when it is revisiting a structurally familiar
 * screen with different content (e.g., a list screen populated with different items).
 *
 * Also maintains the reverse mapping contentHash → structHash for efficient lookup.
 */
public class StructuralGraph {

    // structHash -> set of contentHashes that share this structure
    private final Map<String, Set<String>> clusters = new HashMap<>();

    // contentHash -> structHash (reverse index for fast lookup)
    private final Map<String, String> contentToStruct = new HashMap<>();

    /**
     * Register a content state under its structural cluster.
     *
     * @param structHash   the structural hash (layout identity)
     * @param contentHash  the content hash (state identity within the layout)
     */
    public void register(String structHash, String contentHash) {
        clusters.computeIfAbsent(structHash, k -> new HashSet<>()).add(contentHash);
        contentToStruct.put(contentHash, structHash);
    }

    /**
     * Get all content hashes in the same structural cluster.
     * Returns an empty set if the structHash has never been registered.
     */
    public Set<String> getCluster(String structHash) {
        Set<String> cluster = clusters.get(structHash);
        return cluster != null ? Collections.unmodifiableSet(cluster) : Collections.emptySet();
    }

    /**
     * Get the structural hash for a given content hash.
     * Returns null if the content hash has never been registered.
     */
    public String getStructHash(String contentHash) {
        return contentToStruct.get(contentHash);
    }

    /**
     * Total number of unique structural clusters.
     */
    public int size() {
        return clusters.size();
    }
}
