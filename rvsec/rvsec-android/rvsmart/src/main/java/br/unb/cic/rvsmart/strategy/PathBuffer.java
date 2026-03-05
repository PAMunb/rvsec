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
    public void store(Strategy strategy, List<String> hashSequence) {
        path.clear();
        expectedHashes.clear();
        activeStrategy = strategy;

        for (String hash : hashSequence) {
            path.add(Action.back(ALGORITHM_SOURCE));
            expectedHashes.add(hash);
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
