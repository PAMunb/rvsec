package br.unb.cic.rvsmart.strategy;

import br.unb.cic.rvsmart.graph.NavigationMap;
import br.unb.cic.rvsmart.graph.StructuralGraph;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Plans backtrack sequences for the agent loop.
 *
 * Two-stage backtracking:
 *   Stage 1 — BACK: the plan begins with a single "BACK" marker. AgentLoop
 *   injects the actual BACK key press and checks if the resulting structHash
 *   matches the expected target. If it does, backtracking is complete.
 *
 *   Stage 2 — Replay: if BACK did not land on the expected state, the agent
 *   calls planReplay() which uses NavigationMap to produce an action sequence
 *   that re-navigates from the current state to the target by replaying the
 *   original forward transitions.
 *
 * BacktrackStrategy only plans sequences; execution is performed by AgentLoop.
 * This is orthogonal to BacktrackBfs, which does ancestor BFS for stuck recovery.
 */
public class BacktrackStrategy {

    /** Marker returned as the first element of planBacktrack(). */
    public static final String BACK_MARKER = "BACK";

    private final NavigationMap navigationMap;
    private final StructuralGraph structuralGraph;

    private int replayCount;

    public BacktrackStrategy(NavigationMap navigationMap, StructuralGraph structuralGraph) {
        this.navigationMap = navigationMap;
        this.structuralGraph = structuralGraph;
        this.replayCount = 0;
    }

    /**
     * Plan a backtrack from currentStructHash toward targetStructHash.
     * Returns a list whose first element is BACK_MARKER ("BACK").
     * AgentLoop executes the BACK press and verifies the result.
     * If BACK fails, AgentLoop calls planReplay() for a replay-based plan.
     *
     * @param currentStructHash  structural hash of the current state
     * @param targetStructHash   structural hash of the desired target state
     * @return list starting with BACK_MARKER
     */
    public List<String> planBacktrack(String currentStructHash, String targetStructHash) {
        List<String> plan = new ArrayList<>();
        plan.add(BACK_MARKER);
        return plan;
    }

    /**
     * Plan a replay sequence from currentStructHash to targetStructHash using
     * NavigationMap BFS. Returns the ordered list of action signatures to execute.
     * Returns an empty list if no path is found.
     *
     * Increments replayCount each time a non-empty plan is produced.
     *
     * @param currentStructHash  structural hash of the current state
     * @param targetStructHash   structural hash of the desired target state
     * @return action signature list; empty if unreachable
     */
    public List<String> planReplay(String currentStructHash, String targetStructHash) {
        List<String> path = navigationMap.findPath(currentStructHash, targetStructHash);
        if (!path.isEmpty()) {
            replayCount++;
        }
        return path;
    }

    /**
     * Returns true if there is a known forward path from fromStructHash to toStructHash
     * in the NavigationMap.
     */
    public boolean canReach(String fromStructHash, String toStructHash) {
        return navigationMap.hasPath(fromStructHash, toStructHash);
    }

    /**
     * Number of times planReplay() produced a non-empty path.
     * Used by MetricsCollector to track replay-based backtrack frequency.
     */
    public int getReplayCount() {
        return replayCount;
    }
}
