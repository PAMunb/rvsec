package br.unb.cic.rvsmart.strategy.scorers;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.graph.DynamicStateGraph;
import br.unb.cic.rvsmart.staticdata.StaticMap;

/**
 * Scores actions based on MOP (monitored operation) reachability from static analysis.
 *
 * Uses activity-based lookup: if the current activity has any method that reaches
 * a monitored operation, ALL actions on that screen get a MOP boost. This is a
 * coarser but functional approach since action signatures (coordinate-based) don't
 * match the method signatures in the static analysis JSON.
 *
 * Direct reachability scores higher than transitive. Returns 0 when static data
 * is unavailable or the activity does not reach any monitored operation.
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

        // Activity-based MOP lookup: boost all actions on screens with reachable MOP methods
        String activity = screen.getActivity();
        if (staticMap.activityHasDirectMop(activity)) return directScore;
        if (staticMap.activityHasMop(activity)) return transitiveScore;
        return 0;
    }
}
