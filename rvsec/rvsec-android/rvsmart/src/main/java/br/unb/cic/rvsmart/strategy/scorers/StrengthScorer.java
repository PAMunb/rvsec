package br.unb.cic.rvsmart.strategy.scorers;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.staticdata.StaticMap;

import java.util.List;

/**
 * Aggregates multiple scorers with corresponding integer weights.
 *
 * This is the master scorer when a weighted combination of all sub-scorers is needed.
 * The final score is the sum of (weight_i * scorer_i.score(...)). It allows the caller
 * to tune relative importance of each signal (MOP reachability, decay, saturation, etc.)
 * without changing scorer internals.
 */
public class StrengthScorer implements Scorer {

    private final List<Scorer> scorers;
    private final List<Integer> weights;

    /**
     * @param scorers list of sub-scorers
     * @param weights corresponding integer weights (must be same size as scorers)
     */
    public StrengthScorer(List<Scorer> scorers, List<Integer> weights) {
        if (scorers.size() != weights.size()) {
            throw new IllegalArgumentException(
                    "scorers and weights must have the same size");
        }
        this.scorers = scorers;
        this.weights = weights;
    }

    @Override
    public int score(Action candidate, ScreenState screen, ContentGraph graph, StaticMap staticMap) {
        int total = 0;
        for (int i = 0; i < scorers.size(); i++) {
            total += weights.get(i) * scorers.get(i).score(candidate, screen, graph, staticMap);
        }
        return total;
    }
}
