package br.unb.cic.rvsmart.strategy.scorers;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.graph.DynamicStateGraph;
import br.unb.cic.rvsmart.staticdata.StaticMap;

/**
 * Scores actions based on MOP (monitored operation) reachability from static analysis.
 * Direct reachability scores higher than transitive. Returns 0 when static data
 * is unavailable or the action does not reach any monitored operation.
 */
public class MopScorer implements Scorer {

    private final int directScore;
    private final int transitiveScore;

    public MopScorer(int directScore, int transitiveScore) {
        this.directScore = directScore;
        this.transitiveScore = transitiveScore;
    }

    @Override
    public int score(Action candidate, ScreenState screen, DynamicStateGraph graph, StaticMap staticMap) {
        if (staticMap == null || !staticMap.isLoaded()) return 0;
        String sig = candidate.signature();
        if (staticMap.hasDirectMop(sig)) return directScore;
        if (staticMap.hasMop(sig)) return transitiveScore;
        return 0;
    }
}
