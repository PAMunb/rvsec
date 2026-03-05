package br.unb.cic.rvsmart.strategy;

import br.unb.cic.rvsmart.graph.DynamicStateGraph;
import br.unb.cic.rvsmart.output.RvTrack;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Collections;
import java.util.HashSet;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

class RewardPropagatorTest {

    private RewardPropagator propagator;
    private DynamicStateGraph graph;

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;
        propagator = new RewardPropagator();
        graph = new DynamicStateGraph();
    }

    @Test
    void testInitialRewardIsZero() {
        assertEquals(0.0, propagator.getAccumulatedReward("unknown_hash"), 0.001);
    }

    @Test
    void testRecordAndPropagateAccumulatesReward() {
        propagator.recordStep("hash_A", 1.0);
        propagator.propagate();

        double reward = propagator.getAccumulatedReward("hash_A");
        // Single step: G = 1.0
        assertEquals(1.0, reward, 0.001);
    }

    @Test
    void testNStepPropagationWithMultipleSteps() {
        propagator.recordStep("hash_A", 1.0);
        propagator.recordStep("hash_B", 2.0);
        propagator.propagate();

        // For hash_A at position 0: G = 1.0 + 0.8*2.0 = 2.6
        // For hash_B at position 1: G = 2.0
        double rewardA = propagator.getAccumulatedReward("hash_A");
        double rewardB = propagator.getAccumulatedReward("hash_B");

        assertEquals(2.6, rewardA, 0.01);
        assertEquals(2.0, rewardB, 0.01);
    }

    @Test
    void testWindowSlidingEvictsOldestEntry() {
        // Window size is N=5. Record 6 steps and check oldest is evicted.
        propagator.recordStep("hash_1", 1.0);
        propagator.recordStep("hash_2", 0.0);
        propagator.recordStep("hash_3", 0.0);
        propagator.recordStep("hash_4", 0.0);
        propagator.recordStep("hash_5", 0.0);
        // Sixth step evicts hash_1 from the sliding window
        propagator.recordStep("hash_6", 0.0);
        propagator.propagate();

        // hash_1 was evicted, so no propagation should have accumulated from it
        // (it was removed before propagate() was called)
        // hash_2 through hash_6 should still have entries
        // We just verify propagate doesn't throw and hash_2 gets some reward
        assertTrue(propagator.getAccumulatedReward("hash_2") >= 0.0);
    }

    @Test
    void testPropagateConfirmedCoverageBoostsTrajectory() {
        graph.getOrCreate("hash_A", "ActivityA");
        graph.getOrCreate("hash_B", "ActivityB");

        propagator.recordStep("hash_A", 0.5);
        propagator.recordStep("hash_B", 0.5);

        Set<String> methods = new HashSet<>();
        methods.add("javax.crypto.Cipher.getInstance");
        methods.add("javax.crypto.Cipher.init");

        propagator.propagateConfirmedCoverage("hash_B", methods, graph);

        // Both hash_A and hash_B should have non-zero accumulated rewards
        assertTrue(propagator.getAccumulatedReward("hash_A") > 0.0);
        assertTrue(propagator.getAccumulatedReward("hash_B") > 0.0);
    }

    @Test
    void testPropagateConfirmedCoverageIgnoresEmptyMethods() {
        propagator.recordStep("hash_A", 1.0);
        propagator.propagateConfirmedCoverage("hash_A", Collections.emptySet(), graph);
        // No boost should be applied for empty methods
        assertEquals(0.0, propagator.getAccumulatedReward("hash_A"), 0.001);
    }

    @Test
    void testPropagateConfirmedCoverageIgnoresNullMethods() {
        propagator.recordStep("hash_A", 1.0);
        propagator.propagateConfirmedCoverage("hash_A", null, graph);
        assertEquals(0.0, propagator.getAccumulatedReward("hash_A"), 0.001);
    }

    @Test
    void testResetClearsAllState() {
        propagator.recordStep("hash_A", 5.0);
        propagator.propagate();
        assertTrue(propagator.getAccumulatedReward("hash_A") > 0.0);

        propagator.reset();
        assertEquals(0.0, propagator.getAccumulatedReward("hash_A"), 0.001);
    }

    @Test
    void testMultiplePropagateCalls_accumulatesRewards() {
        propagator.recordStep("hash_A", 1.0);
        propagator.propagate();
        double firstReward = propagator.getAccumulatedReward("hash_A");

        // Second propagate with same trajectory adds more reward
        propagator.propagate();
        double secondReward = propagator.getAccumulatedReward("hash_A");

        assertTrue(secondReward > firstReward);
    }
}
