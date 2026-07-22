package br.unb.cic.rvsmart.strategy.scorers;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.graph.ContentNode;
import br.unb.cic.rvsmart.staticdata.StaticMap;

/**
 * Exponentially decays an action's score based on how many times it has been executed.
 * Formula: if visits >= minVisits then 0 else base * (decayRate ^ visits).
 * Never-visited actions receive full base score.
 */
public class GradualDecayScorer implements Scorer {

    private final int base;
    private final double decayRate;
    private final int minVisits;

    public GradualDecayScorer(int base, double decayRate, int minVisits) {
        this.base = base;
        this.decayRate = decayRate;
        this.minVisits = minVisits;
    }

    @Override
    public int score(Action candidate, ScreenState screen, ContentGraph graph, StaticMap staticMap) {
        ContentNode node = graph.get(screen.getContentHash());
        if (node == null) return base; // Never visited = full score
        int visits = node.getExecutionCount(candidate.signature());
        if (visits >= minVisits) return 0;
        return (int) (base * Math.pow(decayRate, visits));
    }
}
