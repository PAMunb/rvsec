package br.unb.cic.rvsmart.recovery;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.strategy.SuccessorTracker;

import java.util.List;

/**
 * Detects when the app is stuck on the same screen by tracking
 * consecutive iterations with unchanged screen hash.
 *
 * Level 1 (stuck detected): when consecutiveUnchanged >= stuckMaxBlocks,
 * signals that a forced BACK action should be triggered.
 *
 * Level 2 (BFS recovery): when Level 1 triggers, BacktrackBfs searches
 * ancestor states for an unsaturated one. If found, returns a BACK action
 * so AgentLoop can execute BacktrackStrategy replay. If no unsaturated
 * ancestor exists, a RESTART action is returned.
 */
public class StuckDetector {

    private static final int DEFAULT_SATURATION_THRESHOLD = 5;
    private static final long TIME_STUCK_MS = 30_000;
    private static final int MIN_DYNAMIC_THRESHOLD = 8;

    private String lastHash;
    private int consecutiveUnchanged;
    private final int stuckMaxBlocks;

    // Time-based stuck detection
    private long lastNewScreenTime;

    // Level 2 dependencies (optional — null means Level 2 is disabled)
    private final BacktrackBfs backtrackBfs;

    public StuckDetector(int stuckMaxBlocks) {
        this(stuckMaxBlocks, null);
    }

    public StuckDetector(int stuckMaxBlocks, BacktrackBfs backtrackBfs) {
        this.stuckMaxBlocks = stuckMaxBlocks;
        this.backtrackBfs = backtrackBfs;
    }

    /**
     * Update with current screen hash.
     * @return true if stuck detected (should trigger forced BACK)
     */
    public boolean update(String currentHash) {
        if (currentHash == null) {
            // After crash, reset
            lastHash = null;
            consecutiveUnchanged = 0;
            return false;
        }
        if (currentHash.equals(lastHash)) {
            consecutiveUnchanged++;
            return consecutiveUnchanged >= stuckMaxBlocks;
        } else {
            lastHash = currentHash;
            consecutiveUnchanged = 0;
            return false;
        }
    }

    /**
     * Level 2 recovery: use BacktrackBfs to find a path to an unsaturated ancestor.
     * If found, returns a BACK action so AgentLoop can execute BacktrackStrategy replay.
     * If not found, returns RESTART action.
     *
     * When backtrackBfs is not configured, always returns RESTART.
     *
     * @param currentHash  the screen hash where the agent is stuck
     * @param tracker      parent-child edge store for BFS
     * @param graph        the ContentGraph for visit counts
     * @return Action (either BACK as first step toward unsaturated ancestor, or RESTART)
     */
    public Action recover(String currentHash, SuccessorTracker tracker, ContentGraph graph) {
        if (backtrackBfs == null) {
            return Action.restart("algorithm");
        }

        List<String> path = backtrackBfs.findPathToUnsaturated(
                currentHash, tracker, graph, DEFAULT_SATURATION_THRESHOLD);

        if (path != null && !path.isEmpty()) {
            return Action.back("algorithm");
        }

        return Action.restart("algorithm");
    }

    /**
     * Update with action type awareness. SET_TEXT and checkable toggle actions
     * do not increment the stuck counter — they change field content but not
     * the screen hash, so counting them as "no progress" triggers premature BACK.
     */
    public boolean updateWithActionType(String currentHash, Action.Type actionType) {
        if (currentHash == null) {
            lastHash = null;
            consecutiveUnchanged = 0;
            return false;
        }
        if (currentHash.equals(lastHash)) {
            // Form action exemption: SET_TEXT doesn't increment stuck counter
            if (actionType == Action.Type.SET_TEXT) {
                return consecutiveUnchanged >= stuckMaxBlocks;
            }
            consecutiveUnchanged++;
            return consecutiveUnchanged >= stuckMaxBlocks;
        } else {
            lastHash = currentHash;
            consecutiveUnchanged = 0;
            return false;
        }
    }

    /**
     * Record new screen discovery (resets time-based stuck timer).
     */
    public void recordNewScreen(long currentTimeMs) {
        lastNewScreenTime = currentTimeMs;
    }

    /**
     * Time-based stuck detection: stuck when > 30 seconds since last new screen.
     */
    public boolean isTimeStuck(long currentTimeMs) {
        return (currentTimeMs - lastNewScreenTime) > TIME_STUCK_MS;
    }

    /**
     * Dynamic threshold: max(8, numElements * 1.5).
     * Screens with many elements deserve more patience.
     */
    public boolean isStuckWithDynamicThreshold(int numElements) {
        int threshold = Math.max(MIN_DYNAMIC_THRESHOLD, (int) (numElements * 1.5));
        return consecutiveUnchanged >= threshold;
    }

    /** Reset all state (e.g., after app restart). */
    public void reset() {
        lastHash = null;
        consecutiveUnchanged = 0;
    }

    public int getConsecutiveUnchanged() { return consecutiveUnchanged; }
    public String getLastHash() { return lastHash; }
}
