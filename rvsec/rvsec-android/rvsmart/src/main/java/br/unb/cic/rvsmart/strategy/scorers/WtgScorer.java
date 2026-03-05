package br.unb.cic.rvsmart.strategy.scorers;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.graph.DynamicStateGraph;
import br.unb.cic.rvsmart.staticdata.StaticMap;

/**
 * Scores actions based on WTG (Window Transition Graph) transitions from static analysis.
 * If a widget's action signature matches a known WTG transition from the current activity,
 * the action receives a boost because it is statically known to navigate to a new window.
 *
 * Returns 0 when static data is unavailable (graceful degradation when RVSEC static
 * analysis was not run or produced no WTG transitions).
 */
public class WtgScorer implements Scorer {

    private final int wtgScore;

    public WtgScorer(int wtgScore) {
        this.wtgScore = wtgScore;
    }

    @Override
    public int score(Action candidate, ScreenState screen, DynamicStateGraph graph, StaticMap staticMap) {
        if (staticMap == null || !staticMap.isLoaded()) return 0;

        // TODO(gh29): Implement WTG-based scoring in a separate change/issue.
        // This is a full feature, not a simple activation:
        //   1. Parse WTG transitions from static_analysis.json (sections: windows, transitions)
        //   2. Add StaticMap.hasWtgTransition(currentActivity, actionSignature) API
        //   3. Score actions whose signatures match known WTG transitions from the current activity
        // Until implemented, this scorer is a stub and is NOT wired into ActionSelector.
        return 0;
    }
}
