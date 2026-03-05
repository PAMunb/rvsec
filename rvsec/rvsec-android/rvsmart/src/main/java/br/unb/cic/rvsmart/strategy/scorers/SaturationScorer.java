package br.unb.cic.rvsmart.strategy.scorers;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.graph.DynamicStateGraph;
import br.unb.cic.rvsmart.graph.ScreenNode;
import br.unb.cic.rvsmart.staticdata.StaticMap;

/**
 * Penalizes screens that are heavily explored to encourage exploration of less-visited states.
 *
 * Uses the screen's visit count as a proxy for exploration saturation. When a screen
 * has been visited more times than the threshold, each additional visit incurs a
 * growing penalty. This naturally steers the agent toward under-explored areas.
 *
 * Formula: -(visitCount - threshold) * penaltyPerExcess when visitCount > threshold, else 0.
 */
public class SaturationScorer implements Scorer {

    private final int threshold;
    private final int penaltyPerExcess;

    public SaturationScorer(int threshold, int penaltyPerExcess) {
        this.threshold = threshold;
        this.penaltyPerExcess = penaltyPerExcess;
    }

    @Override
    public int score(Action candidate, ScreenState screen, DynamicStateGraph graph, StaticMap staticMap) {
        ScreenNode node = graph.get(screen.getHash());
        if (node == null) return 0;
        int totalExecutions = node.getVisitCount();
        if (totalExecutions <= threshold) return 0;
        return -(totalExecutions - threshold) * penaltyPerExcess;
    }
}
