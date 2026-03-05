package br.unb.cic.rvsmart.strategy.scorers;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.graph.DynamicStateGraph;
import br.unb.cic.rvsmart.staticdata.StaticMap;

/**
 * Prioritizes actions based on the type of interaction they represent.
 *
 * Text input (SET_TEXT) receives the highest priority because EditText fields
 * often gate form submission and are required to reach downstream MOP-triggering actions.
 * Clicks and long-clicks on standard interactive widgets receive medium priority.
 * Scroll actions receive low priority since they rarely trigger monitored operations directly.
 */
public class ComponentPriorityScorer implements Scorer {

    private static final int SCORE_TEXT_INPUT = 200;
    private static final int SCORE_CLICK      = 100;
    private static final int SCORE_SCROLL     = 25;

    @Override
    public int score(Action candidate, ScreenState screen, DynamicStateGraph graph, StaticMap staticMap) {
        switch (candidate.getType()) {
            case SET_TEXT:
                return SCORE_TEXT_INPUT;
            case CLICK:
            case LONG_CLICK:
                return SCORE_CLICK;
            case SCROLL:
            case SWIPE:
                return SCORE_SCROLL;
            default:
                // BACK, RESTART, KEY_EVENT — no component-priority boost
                return 0;
        }
    }
}
