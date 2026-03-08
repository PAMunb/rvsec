package br.unb.cic.rvsmart.strategy;

import br.unb.cic.rvsmart.core.Action;

import java.util.ArrayDeque;
import java.util.List;
import java.util.Queue;

/**
 * Stores and replays sequences of BACK actions for deterministic navigation.
 *
 * When the strategy decides to backtrack to a specific ancestor state, the BFS
 * pathfinder produces a sequence of screen hashes to pass through. PathBuffer
 * converts this sequence into a stream of BACK actions dispensed one per iteration.
 *
 * Three strategies exist, ordered by priority:
 * - MOP: backtracking to reach a known MOP-triggering screen
 * - COVERAGE: backtracking toward an under-explored screen
 * - BACKTRACK: generic stuck-recovery backtrack
 *
 * Paths are invalidated eagerly when the agent diverges from the expected sequence
 * (e.g., a BACK action lands on an unexpected screen), preventing stale navigation.
 */
public class PathBuffer {

    public enum Strategy {
        MOP,
        COVERAGE,
        BACKTRACK
    }

    private static final String ALGORITHM_SOURCE = "algorithm";

    // Active path: sequence of BACK actions remaining
    private final Queue<Action> path = new ArrayDeque<>();

    // Expected next screen hash (for divergence detection)
    private final Queue<String> expectedHashes = new ArrayDeque<>();

    // Which strategy is currently active (null if no active path)
    private Strategy activeStrategy;

    /**
     * Stores a navigation sequence for the given strategy.
     * Each entry in hashSequence is a screen hash the agent expects to pass through.
     * One BACK action is generated for each hop in the sequence.
     * Replaces any currently stored path.
     *
     * @param strategy     the navigation purpose
     * @param hashSequence ordered list of screen hashes forming the backtrack path
     */
    /**
     * Stores a navigation sequence for the given strategy.
     * hashSequence[0] is the current screen (starting position). The remaining
     * entries are intermediate positions. The LAST entry is the destination.
     * N-1 BACK actions are generated for N hashes.
     *
     * expectedHashes stores the pre-action positions (all except the last):
     * before each BACK, the agent should be at expectedHashes[i]. After the
     * last BACK, the agent arrives at hashSequence[N-1] (the destination).
     *
     * @param strategy     the navigation purpose
     * @param hashSequence ordered list: [current position, ..., target]
     */
    public void store(Strategy strategy, List<String> hashSequence) {
        path.clear();
        expectedHashes.clear();
        activeStrategy = strategy;

        if (hashSequence.size() < 2) return; // need at least start + destination

        // For each hop (N-1 hops for N positions):
        // - expectedHashes[i] = position BEFORE the i-th BACK
        // - path[i] = BACK action for the i-th hop
        for (int i = 0; i < hashSequence.size() - 1; i++) {
            expectedHashes.add(hashSequence.get(i));
            path.add(Action.back(ALGORITHM_SOURCE));
        }
    }

    /**
     * Returns true if there are remaining actions in the current path.
     */
    public boolean hasPath() {
        return !path.isEmpty();
    }

    /**
     * Returns and removes the next BACK action in the current path.
     * Returns null if no path is active.
     */
    public Action nextAction() {
        if (path.isEmpty()) return null;
        // Consume the expected hash alongside the action
        expectedHashes.poll();
        return path.poll();
    }

    /**
     * Validates the agent's current position before consuming the next hop.
     * If the agent diverged from the expected position, the path is invalidated
     * and null is returned instead of consuming a stale hop.
     *
     * @param currentHash the agent's current screen hash
     * @return the next BACK action, or null if path is empty or position mismatches
     */
    public Action consumeNext(String currentHash) {
        if (path.isEmpty()) return null;
        String expected = expectedHashes.peek();
        if (expected != null && !expected.equals(currentHash)) {
            invalidate();
            return null;
        }
        expectedHashes.poll();
        return path.poll();
    }

    /**
     * Clears all stored paths. Called when the navigation plan is no longer valid.
     */
    public void invalidate() {
        path.clear();
        expectedHashes.clear();
        activeStrategy = null;
    }

    /**
     * Checks if the current screen hash matches the next expected hash in the path.
     * If not, the agent diverged from the planned route and the path is invalidated.
     *
     * @param currentHash the screen hash observed after the last BACK action
     */
    public void invalidateIfDiverged(String currentHash) {
        String expected = expectedHashes.peek();
        if (expected != null && !expected.equals(currentHash)) {
            invalidate();
        }
    }

    /**
     * Returns the active navigation strategy, or null if no path is stored.
     */
    public Strategy getActiveStrategy() {
        return activeStrategy;
    }

    /**
     * Number of remaining actions in the current path.
     */
    public int remainingActions() {
        return path.size();
    }
}
