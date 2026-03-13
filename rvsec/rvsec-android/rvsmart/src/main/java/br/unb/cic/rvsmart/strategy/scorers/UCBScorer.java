package br.unb.cic.rvsmart.strategy.scorers;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.graph.ContentNode;
import br.unb.cic.rvsmart.staticdata.StaticMap;

/**
 * UCB exploration bonus: C * sqrt(ln(N_state) / N_action).
 * Scaled to match other scorers (GradualDecay=200, MOP=500).
 * Complements GradualDecayScorer: UCB handles exploration/exploitation
 * balance while GradualDecay handles per-action visit decay.
 */
public class UCBScorer implements Scorer {

    private final float c;

    public UCBScorer(float c) {
        this.c = c;
    }

    @Override
    public int score(Action candidate, ScreenState screen, ContentGraph graph, StaticMap staticMap) {
        ContentNode node = graph.get(screen.getContentHash());
        if (node == null) return 0;

        int nState = node.getVisitCount();
        if (nState <= 0) return 0;

        int nAction = node.getExecutionCount(candidate.signature());
        if (nAction == 0) {
            // Max exploration bonus for never-visited actions
            return (int) (c * Math.sqrt(Math.log(Math.max(1, nState))));
        }

        return (int) (c * Math.sqrt(Math.log(nState) / nAction));
    }
}
