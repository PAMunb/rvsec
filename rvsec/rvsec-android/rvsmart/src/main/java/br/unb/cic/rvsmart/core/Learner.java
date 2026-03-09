package br.unb.cic.rvsmart.core;

import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.recovery.StuckDetector;
import br.unb.cic.rvsmart.output.RvTrack;

import java.util.List;
import java.util.Set;
import java.util.HashSet;

/**
 * Assigns rewards and updates graph state after each action.
 * Source-agnostic: does NOT inspect action source (INV-RSM-08).
 */
public class Learner {
    static final double NEW_ACTIVITY_REWARD = 2.0;
    static final double NEW_STATE_REWARD = 1.0;
    static final double NO_EFFECT_PENALTY = -0.1;
    static final double COVERAGE_REWARD_PER_METHOD = 0.5;

    private final ContentGraph graph;
    private final StuckDetector stuckDetector;
    private final Set<String> uniqueActivities = new HashSet<>();
    private final Set<String> confirmedMethods = new HashSet<>();
    private int totalCoverageEvents;

    public Learner(ContentGraph graph, StuckDetector stuckDetector) {
        this.graph = graph;
        this.stuckDetector = stuckDetector;
    }

    /**
     * Update graph state and assign reward after action execution.
     *
     * @param action The executed action
     * @param hadEffect Whether the action changed screen state
     * @param beforeHash Screen hash before action
     * @param afterHash Screen hash after action
     * @param beforeActivity Activity before action
     * @param afterActivity Activity after action
     * @param coveredMethods Newly covered methods from logcat (may be empty)
     * @param iteration Current iteration number
     * @param retries Number of multi-attempt retries
     * @return Computed reward value
     */
    public double update(Action action, boolean hadEffect,
                         String beforeHash, String afterHash,
                         String beforeActivity, String afterActivity,
                         List<String> coveredMethods, int iteration, int retries) {
        double reward = 0.0;

        // Track unique activities
        uniqueActivities.add(afterActivity);

        // Reward: new activity
        boolean newActivity = !beforeActivity.equals(afterActivity);
        if (newActivity) {
            reward += NEW_ACTIVITY_REWARD;
        }

        // Reward: new state
        boolean newState = !beforeHash.equals(afterHash);
        if (newState) {
            reward += NEW_STATE_REWARD;
        }

        // Penalty: no effect
        if (!hadEffect) {
            reward += NO_EFFECT_PENALTY;
        }

        // Reward: confirmed coverage
        for (String method : coveredMethods) {
            totalCoverageEvents++;
            if (confirmedMethods.add(method)) {
                reward += COVERAGE_REWARD_PER_METHOD;
            }
        }

        // Update graph: record transition and action success
        graph.recordTransition(beforeHash, afterHash);
        graph.recordActionSuccess(beforeHash, action.signature(), hadEffect);

        // Update stuck detector
        boolean stuck = stuckDetector.update(afterHash);

        // RVTRACK logging
        RvTrack.state(iteration, hadEffect, beforeHash, afterHash, beforeActivity, afterActivity);
        RvTrack.learn(iteration, reward, stuck ? 1 : 0, hadEffect, retries);

        for (String method : coveredMethods) {
            RvTrack.coverage(iteration, method, totalCoverageEvents, "logcat");
        }

        return reward;
    }

    public Set<String> getUniqueActivities() { return uniqueActivities; }
    public Set<String> getConfirmedMethods() { return confirmedMethods; }
    public int getTotalCoverageEvents() { return totalCoverageEvents; }
    public boolean isStuck() { return stuckDetector.getConsecutiveUnchanged() >= 10; }
}
