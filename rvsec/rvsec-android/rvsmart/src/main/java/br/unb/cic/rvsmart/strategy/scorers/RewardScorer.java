package br.unb.cic.rvsmart.strategy.scorers;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.graph.DynamicStateGraph;
import br.unb.cic.rvsmart.staticdata.StaticMap;
import br.unb.cic.rvsmart.strategy.RewardPropagator;

/**
 * Scores actions based on accumulated reward from N-step TD propagation.
 *
 * Screens that previously led to coverage events accumulate positive rewards
 * via RewardPropagator. This scorer boosts all actions on such screens,
 * encouraging the agent to revisit productive regions.
 *
 * The weight factor (default 0.3) controls how much accumulated reward
 * influences action selection relative to other scorers.
 */
public class RewardScorer implements Scorer {

    private final RewardPropagator rewardPropagator;
    private final float weight;

    public RewardScorer(RewardPropagator rewardPropagator, float weight) {
        this.rewardPropagator = rewardPropagator;
        this.weight = weight;
    }

    @Override
    public int score(Action candidate, ScreenState screen, DynamicStateGraph graph, StaticMap staticMap) {
        if (rewardPropagator == null) return 0;
        double accumulated = rewardPropagator.getAccumulatedReward(screen.getHash());
        return (int) (accumulated * weight);
    }
}
