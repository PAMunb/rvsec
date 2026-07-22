package br.unb.cic.rvsmart.strategy.scorers;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.core.UICoverageTracker;
import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.staticdata.StaticMap;

/**
 * Scores actions based on UI element coverage gap on the current screen.
 *
 * Score = coverageGap * weight, where coverageGap is the fraction of
 * untested elements (0.0 = all tested, 1.0 = none tested).
 * This directs the agent toward screens with many unexplored elements.
 *
 * Returns 0 when UICoverageTracker is null (graceful degradation).
 */
public class CoverageDensityScorer implements Scorer {

    private final int weight;
    private final UICoverageTracker tracker;

    /**
     * Legacy constructor — no tracker, always returns 0.
     */
    public CoverageDensityScorer(int weight) {
        this(weight, null);
    }

    public CoverageDensityScorer(int weight, UICoverageTracker tracker) {
        this.weight = weight;
        this.tracker = tracker;
    }

    @Override
    public int score(Action candidate, ScreenState screen, ContentGraph graph, StaticMap staticMap) {
        if (tracker == null) return 0;

        float coverageGap = tracker.getCoverageGap(screen.getContentHash());
        return (int) (coverageGap * weight);
    }
}
