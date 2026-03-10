package br.unb.cic.rvsmart.strategy;

import br.unb.cic.rvsmart.core.UICoverageTracker;
import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.graph.ContentNode;

import java.util.HashMap;
import java.util.Map;

/**
 * Controls the three-phase exploration strategy for the rvsmart agent.
 *
 * Phases:
 *   PHASE_1 — Broad exploration: prioritise untested content states and actions.
 *   PHASE_2 — Deep exploration: all reachable content states have had at least
 *             one action executed; agent focuses on under-explored areas.
 *   PHASE_3 — Saturation: UI coverage has plateaued; agent shifts to
 *             targeted/random recovery strategies.
 *
 * Transitions:
 *   PHASE_1 → PHASE_2  when no reachable content state has an untested action.
 *   PHASE_2 → PHASE_3  when PlateauDetector signals plateau (WINDOW_SIZE
 *                       consecutive iterations with no coverage gain).
 *   any     → PHASE_1  when a new content state is first discovered.
 *
 * Cluster forcing (4.2): tracks how many times Phase 1 was re-entered for each
 * structural cluster (structHash). After 20 re-entries for the same cluster,
 * isClusterForced() returns true — ActionSelector should treat that cluster as
 * Phase 2 regardless of global phase, preventing infinite content-hash loops.
 */
public class PhaseController {

    /** The three exploration phases. */
    public enum Phase {
        PHASE_1,
        PHASE_2,
        PHASE_3
    }

    /** Threshold for forcing a structural cluster to be treated as Phase 2. */
    static final int CLUSTER_FORCE_THRESHOLD = 20;

    /** Threshold for preference activities (lower than normal cluster forcing). */
    static final int PREFERENCE_FORCE_THRESHOLD = 5;

    private Phase currentPhase = Phase.PHASE_1;

    private final ContentGraph contentGraph;
    private final UICoverageTracker uiCoverageTracker;
    private final PlateauDetector plateauDetector;

    /**
     * Per-structHash count of Phase 1 re-entries. Used to detect clusters that
     * keep discovering new content hashes without making real progress (4.2).
     */
    private final Map<String, Integer> phase1ReentriesByCluster = new HashMap<>();

    public PhaseController(ContentGraph contentGraph,
                           UICoverageTracker uiCoverageTracker,
                           PlateauDetector plateauDetector) {
        this.contentGraph = contentGraph;
        this.uiCoverageTracker = uiCoverageTracker;
        this.plateauDetector = plateauDetector;
    }

    // -------------------------------------------------------------------------
    // Phase query
    // -------------------------------------------------------------------------

    /** Returns the current exploration phase. */
    public Phase currentPhase() {
        return currentPhase;
    }

    // -------------------------------------------------------------------------
    // Phase transition triggers
    // -------------------------------------------------------------------------

    /**
     * Call when a content state is first discovered (i.e. a genuinely new
     * contentHash appears). Resets to PHASE_1 from any phase, unless:
     * - BUG-02: cycle detected on same cluster (skip reset to avoid looping)
     * - BUG-05: preference/settings activity has exceeded re-entry threshold
     *
     * @param contentHash    the newly discovered content hash
     * @param activityName   current activity name (for preference detection)
     * @param structHash     structural hash of the current cluster
     * @param isCycleDetected true if the transition is a cycle back to a known state
     */
    public void onNewContentState(String contentHash, String activityName,
                                   String structHash, boolean isCycleDetected) {
        // BUG-02: Don't reset to Phase 1 if cycle detected on same cluster
        if (isCycleDetected) {
            return;
        }
        // BUG-05: Detect preference/settings activities and limit re-entries
        if (isPreferenceActivity(activityName)) {
            int reentries = phase1ReentriesByCluster.getOrDefault(structHash, 0);
            if (reentries >= PREFERENCE_FORCE_THRESHOLD) {
                return;
            }
        }
        currentPhase = Phase.PHASE_1;
    }

    /**
     * Backward-compatible overload for callers that don't have activity/cycle context.
     */
    public void onNewContentState(String contentHash) {
        onNewContentState(contentHash, null, null, false);
    }

    /**
     * Call once per agent iteration with the coverage delta gained (0 if no
     * new coverage was observed). Drives plateau detection and the
     * PHASE_2 → PHASE_3 transition.
     *
     * <p>The {@code coverageDelta} is translated to the PlateauDetector's
     * boolean API: progress = (coverageDelta > 0). isNewState is always false
     * here because new-state discovery is handled via onNewContentState().</p>
     *
     * <p>When phase is PHASE_1 and all content states are now explored, this
     * method also triggers the PHASE_1 → PHASE_2 transition.</p>
     *
     * @param coverageDelta coverage gained in this iteration (≥ 0)
     */
    public void onIteration(int coverageDelta) {
        // Feed plateau detector regardless of current phase so it builds up
        // accurate history before PHASE_2 begins.
        plateauDetector.recordIteration(false, coverageDelta > 0);

        switch (currentPhase) {
            case PHASE_1:
                if (!hasUntestedActionsInAnyReachableState()) {
                    currentPhase = Phase.PHASE_2;
                }
                break;

            case PHASE_2:
                if (plateauDetector.isPlateauDetected()) {
                    currentPhase = Phase.PHASE_3;
                }
                break;

            case PHASE_3:
                // Terminal phase — no automatic forward transition.
                break;
        }
    }

    /**
     * Returns true if any known content state has at least one action that has
     * never been executed (i.e. is absent from executionCounts).
     *
     * A state with totalActions == 0 is considered unexplored (we do not yet
     * know its action set), so it is treated as having untested actions.
     */
    public boolean hasUntestedActionsInAnyReachableState() {
        for (ContentNode node : contentGraph.getNodes().values()) {
            if (node.getTotalActions() == 0) {
                // Actions not yet registered — state is unexplored.
                return true;
            }
            if (node.getExecutedActions().size() < node.getTotalActions()) {
                return true;
            }
        }
        return false;
    }

    // -------------------------------------------------------------------------
    // Cluster forcing (4.2)
    // -------------------------------------------------------------------------

    /**
     * Increment the Phase 1 re-entry count for the given structural cluster.
     * Call this every time the agent enters Phase 1 while the current screen
     * belongs to structHash.
     *
     * @param structHash structural hash of the current cluster
     */
    public void onPhase1Entry(String structHash) {
        int current = phase1ReentriesByCluster.getOrDefault(structHash, 0);
        phase1ReentriesByCluster.put(structHash, current + 1);
    }

    /**
     * Returns true if Phase 1 has been re-entered {@value #CLUSTER_FORCE_THRESHOLD}
     * or more times for this structural cluster. ActionSelector should treat the
     * cluster as if it is in PHASE_2 when this returns true.
     *
     * @param structHash structural hash of the cluster to check
     */
    public boolean isClusterForced(String structHash) {
        return phase1ReentriesByCluster.getOrDefault(structHash, 0) >= CLUSTER_FORCE_THRESHOLD;
    }

    /**
     * Detects preference/settings activities by activity name heuristic.
     * These activities tend to trap the agent in deep configuration trees.
     */
    private boolean isPreferenceActivity(String activityName) {
        if (activityName == null) return false;
        String lower = activityName.toLowerCase();
        return lower.contains("preference") || lower.contains("setting")
                || lower.contains("config") || lower.contains("about");
    }
}
