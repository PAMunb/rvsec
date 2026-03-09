package br.unb.cic.rvsmart.strategy.scorers;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.staticdata.StaticMap;

/**
 * Applies a heavy penalty to actions targeting Android system UI elements,
 * preventing the agent from interacting with the notification shade, status bar, etc.
 */
public class SystemElementFilter implements Scorer {

    private static final int SYSTEM_UI_PENALTY = -5000;
    private static final String SYSTEM_UI_PACKAGE = "com.android.systemui";

    @Override
    public int score(Action candidate, ScreenState screen, ContentGraph graph, StaticMap staticMap) {
        if (SYSTEM_UI_PACKAGE.equals(candidate.getPackageName())) return SYSTEM_UI_PENALTY;
        return 0;
    }
}
