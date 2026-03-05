package br.unb.cic.rvsmart.strategy.scorers;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.graph.DynamicStateGraph;
import br.unb.cic.rvsmart.staticdata.StaticMap;

/**
 * Scores actions inversely proportional to the density of MOP-reaching actions
 * on the current screen.
 *
 * When many actions on a screen reach monitored operations, each individual one is less
 * critical — the agent already has multiple paths to MOP coverage from that screen.
 * On screens with fewer MOP-reaching actions, each such action is more valuable because
 * it is a scarcer opportunity.
 *
 * Approximation: StaticMap only supports per-signature lookups (not per-screen enumeration),
 * so this scorer returns mopDensityBase for any action that directly reaches a MOP,
 * and 0 for all others. The density denominator defaults to 1 (one known MOP path).
 * This provides a simpler but effective signal that consistently boosts MOP-reaching
 * actions without requiring a full per-screen MOP enumeration.
 *
 * Returns 0 if StaticMap is null, not loaded, or the action does not reach any MOP.
 */
public class CoverageDensityScorer implements Scorer {

    private final int mopDensityBase;

    public CoverageDensityScorer(int mopDensityBase) {
        this.mopDensityBase = mopDensityBase;
    }

    @Override
    public int score(Action candidate, ScreenState screen, DynamicStateGraph graph, StaticMap staticMap) {
        if (staticMap == null || !staticMap.isLoaded()) return 0;

        boolean candidateReachesMop = staticMap.hasDirectMop(candidate.signature())
                || staticMap.hasMop(candidate.signature());
        if (!candidateReachesMop) return 0;

        // TODO(gh29): Review whether this scorer should be kept, reworked, or removed.
        // Current behavior: returns flat mopDensityBase (+200) for any MOP-reaching action.
        // This is redundant with MopScorer, which already gives +500 (direct) / +300 (indirect)
        // for the same trigger condition (hasDirectMop || hasMop). The only difference is the
        // score value. Without real per-screen density calculation (counting how many actions
        // on the current screen reach MOPs), this scorer adds no differentiation signal.
        // Options: (a) implement real density calculation, (b) remove entirely.
        // Until resolved, this scorer is NOT wired into ActionSelector.
        return mopDensityBase;
    }
}
