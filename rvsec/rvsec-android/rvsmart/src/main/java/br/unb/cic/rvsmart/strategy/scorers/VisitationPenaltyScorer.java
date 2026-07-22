package br.unb.cic.rvsmart.strategy.scorers;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.graph.ContentNode;
import br.unb.cic.rvsmart.staticdata.StaticMap;

/**
 * Penalizes frequently visited actions to encourage breadth-first exploration.
 *
 * Each execution of an action on a screen increases its penalty, making the agent
 * prefer actions it has executed fewer times. This complements GradualDecayScorer:
 * while GradualDecayScorer zeroes out high-visit actions, VisitationPenaltyScorer
 * applies a continuous linear penalty without a hard cutoff.
 *
 * Formula: -(visits * penaltyPerVisit)
 */
public class VisitationPenaltyScorer implements Scorer {

    private final int penaltyPerVisit;

    public VisitationPenaltyScorer(int penaltyPerVisit) {
        this.penaltyPerVisit = penaltyPerVisit;
    }

    @Override
    public int score(Action candidate, ScreenState screen, ContentGraph graph, StaticMap staticMap) {
        ContentNode node = graph.get(screen.getContentHash());
        if (node == null) return 0;
        int visits = node.getExecutionCount(candidate.signature());
        return -(visits * penaltyPerVisit);
    }
}
