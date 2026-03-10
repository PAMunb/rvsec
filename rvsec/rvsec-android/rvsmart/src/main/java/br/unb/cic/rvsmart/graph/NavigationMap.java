package br.unb.cic.rvsmart.graph;

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
 * Records structural-level transitions for replay-based backtracking.
 *
 * Maps (fromStructHash, actionSignature) → toStructHash. This allows the
 * agent to reconstruct a replay sequence when BACK-based backtracking fails
 * and the agent needs to navigate from one structural state to another by
 * replaying the original action sequence.
 *
 * Uses BFS to find the shortest replay path between two structural states.
 */
public class NavigationMap {

    // adjacency: fromStructHash -> (actionSignature -> toStructHash)
    private final Map<String, Map<String, String>> transitions = new HashMap<>();

    /**
     * Record a structural transition.
     *
     * @param fromStructHash   structural hash of the source state
     * @param actionSignature  signature of the action that caused the transition
     * @param toStructHash     structural hash of the destination state
     */
    public void record(String fromStructHash, String actionSignature, String toStructHash) {
        transitions
                .computeIfAbsent(fromStructHash, k -> new HashMap<>())
                .put(actionSignature, toStructHash);
    }

    /**
     * BFS shortest path from fromStructHash to toStructHash.
     * Returns the ordered list of action signatures to execute.
     * Returns an empty list if no path exists or from == to.
     *
     * @param fromStructHash  starting structural hash
     * @param toStructHash    target structural hash
     * @return list of action signatures; empty if unreachable
     */
    public List<String> findPath(String fromStructHash, String toStructHash) {
        if (fromStructHash == null || toStructHash == null) return Collections.emptyList();
        if (fromStructHash.equals(toStructHash)) return Collections.emptyList();

        // BFS over structural graph
        Queue<String> queue = new ArrayDeque<>();
        Set<String> visited = new HashSet<>();
        // child -> (parent, action that reached child)
        Map<String, String[]> prev = new HashMap<>();

        queue.add(fromStructHash);
        visited.add(fromStructHash);

        while (!queue.isEmpty()) {
            String current = queue.poll();
            Map<String, String> outgoing = transitions.get(current);
            if (outgoing == null) continue;

            for (Map.Entry<String, String> entry : outgoing.entrySet()) {
                String action = entry.getKey();
                String next = entry.getValue();
                if (visited.contains(next)) continue;
                visited.add(next);
                prev.put(next, new String[]{current, action});
                if (toStructHash.equals(next)) {
                    return reconstructPath(fromStructHash, toStructHash, prev);
                }
                queue.add(next);
            }
        }

        return Collections.emptyList(); // no path found
    }

    /**
     * Returns true if a path exists from fromStructHash to toStructHash.
     */
    public boolean hasPath(String fromStructHash, String toStructHash) {
        return !findPath(fromStructHash, toStructHash).isEmpty();
    }

    /**
     * Returns the list of action signatures for all outgoing edges from a structural hash.
     * Returns null if no edges exist for the given hash.
     */
    public List<String> getOutgoingActions(String structHash) {
        Map<String, String> outgoing = transitions.get(structHash);
        if (outgoing == null || outgoing.isEmpty()) return null;
        return new ArrayList<>(outgoing.keySet());
    }

    /**
     * Total number of recorded transitions (edges in the structural graph).
     */
    public int size() {
        int count = 0;
        for (Map<String, String> outgoing : transitions.values()) {
            count += outgoing.size();
        }
        return count;
    }

    private List<String> reconstructPath(String from, String to, Map<String, String[]> prev) {
        List<String> actions = new ArrayList<>();
        String current = to;
        while (!current.equals(from)) {
            String[] entry = prev.get(current);
            if (entry == null) return Collections.emptyList(); // should not happen
            actions.add(entry[1]); // action that led to current
            current = entry[0];   // parent node
        }
        Collections.reverse(actions);
        return actions;
    }
}
