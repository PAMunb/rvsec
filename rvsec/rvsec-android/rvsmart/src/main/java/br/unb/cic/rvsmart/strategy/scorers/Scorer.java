package br.unb.cic.rvsmart.strategy.scorers;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.staticdata.StaticMap;

/**
 * Scores a candidate action on the current screen.
 * Higher score = more attractive action.
 * Returns 0 when required data is unavailable (graceful degradation).
 */
public interface Scorer {
    int score(Action candidate, ScreenState screen, ContentGraph graph, StaticMap staticMap);
}
