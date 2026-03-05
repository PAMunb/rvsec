package br.unb.cic.rvsmart.strategy;

import br.unb.cic.rvsmart.graph.DynamicStateGraph;
import br.unb.cic.rvsmart.graph.ScreenNode;

import java.util.ArrayDeque;
import java.util.Deque;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;

/**
 * N-step Temporal Difference reward propagation for the DynamicStateGraph.
 *
 * Maintains a sliding window of recent (hash, reward) pairs. After each step,
 * propagate() walks back through the trajectory and distributes discounted rewards
 * to predecessors. This gives states that led to valuable outcomes higher cumulative
 * rewards, making the agent prefer paths through proven-productive regions.
 *
 * Parameters: N=5 (window size), gamma=0.8 (discount factor).
 * Special propagation for logcat-confirmed coverage boosts the entire trajectory
 * that led to the coverage event.
 */
public class RewardPropagator {

    private static final int N = 5;
    private static final double GAMMA = 0.8;
    private static final double CONFIRMED_COVERAGE_BOOST = 10.0;

    // Sliding window of recent (hash) steps — capacity N
    private final Deque<String> trajectory = new ArrayDeque<>();

    // Accumulated rewards per screen hash
    private final Map<String, Double> accumulatedRewards = new HashMap<>();

    // Per-hash per-step rewards recorded for propagation
    private final Deque<Double> rewards = new ArrayDeque<>();

    /**
     * Records a step in the trajectory with its immediate reward.
     * Maintains a fixed-size sliding window of capacity N.
     *
     * @param hash   screen hash for this step
     * @param reward immediate reward received at this step
     */
    public void recordStep(String hash, double reward) {
        trajectory.addLast(hash);
        rewards.addLast(reward);

        // Evict oldest entry if window exceeds N
        if (trajectory.size() > N) {
            trajectory.removeFirst();
            rewards.removeFirst();
        }
    }

    /**
     * Applies N-step TD propagation over the current trajectory window.
     * Walks backwards through the trajectory, applying discounted rewards
     * to predecessor states using gamma^k decay.
     *
     * G_t = r_t + gamma*r_{t+1} + gamma^2*r_{t+2} + ...
     * Each state in the window accumulates a portion of the total discounted return.
     */
    public void propagate() {
        if (trajectory.isEmpty()) return;

        // Convert deques to arrays for indexed access
        String[] hashes = trajectory.toArray(new String[0]);
        Double[] rewardArr = rewards.toArray(new Double[0]);
        int len = hashes.length;

        // For each position i, compute discounted return looking forward
        for (int i = 0; i < len; i++) {
            double G = 0.0;
            double discount = 1.0;
            for (int j = i; j < len; j++) {
                G += discount * rewardArr[j];
                discount *= GAMMA;
            }
            String hash = hashes[i];
            double current = accumulatedRewards.getOrDefault(hash, 0.0);
            accumulatedRewards.put(hash, current + G);
        }
    }

    /**
     * Special propagation for logcat-confirmed MOP coverage.
     * Boosts all hashes in the recent trajectory that contributed to this discovery.
     * Also updates cumulative rewards in the DynamicStateGraph nodes.
     *
     * @param hash    screen hash where coverage was confirmed
     * @param methods set of confirmed method signatures
     * @param graph   the DynamicStateGraph to update
     */
    public void propagateConfirmedCoverage(String hash, Set<String> methods, DynamicStateGraph graph) {
        if (methods == null || methods.isEmpty()) return;

        double boost = CONFIRMED_COVERAGE_BOOST * methods.size();
        double discount = 1.0;

        // Walk backwards through the trajectory, boosting each predecessor
        String[] hashes = trajectory.toArray(new String[0]);
        for (int i = hashes.length - 1; i >= 0; i--) {
            String h = hashes[i];
            double current = accumulatedRewards.getOrDefault(h, 0.0);
            double contribution = boost * discount;
            accumulatedRewards.put(h, current + contribution);

            // Also update graph node cumulative reward (using hash as signature proxy)
            ScreenNode node = graph.get(h);
            if (node != null) {
                double nodeReward = node.getCumulativeReward(h) + contribution;
                node.setCumulativeReward(h, nodeReward);
            }

            discount *= GAMMA;
        }

        // Boost the confirmed hash itself at full value
        double confirmed = accumulatedRewards.getOrDefault(hash, 0.0);
        accumulatedRewards.put(hash, confirmed + boost);
    }

    /**
     * Returns the accumulated propagated reward for a screen hash.
     * Returns 0.0 if the hash has not been part of any recorded trajectory.
     */
    public double getAccumulatedReward(String hash) {
        return accumulatedRewards.getOrDefault(hash, 0.0);
    }

    /**
     * Clears all trajectory and reward data. Used when the app restarts.
     */
    public void reset() {
        trajectory.clear();
        rewards.clear();
        accumulatedRewards.clear();
    }
}
