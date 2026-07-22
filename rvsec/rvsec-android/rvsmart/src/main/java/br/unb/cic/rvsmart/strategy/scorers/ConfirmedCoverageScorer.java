package br.unb.cic.rvsmart.strategy.scorers;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.graph.ContentNode;
import br.unb.cic.rvsmart.staticdata.StaticMap;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

/**
 * Boosts actions in screens that previously produced logcat-confirmed MOP coverage.
 *
 * When a screen hash is associated with confirmed MOP method executions (discovered
 * via LogcatReader drain), subsequent visits to that screen receive a bonus score.
 * This creates a positive feedback loop: screens that produced real coverage are
 * re-visited more aggressively to exploit known-productive paths.
 *
 * The confirmedHashes map is populated externally by the agent loop via addConfirmed().
 */
public class ConfirmedCoverageScorer implements Scorer {

    private final int confirmedBase;

    // Tracks which screen hashes produced logcat-confirmed MOP coverage.
    // Key = screen hash, value = set of confirmed method signatures.
    private final Map<String, Set<String>> confirmedHashes = new HashMap<>();

    public ConfirmedCoverageScorer(int confirmedBase) {
        this.confirmedBase = confirmedBase;
    }

    /**
     * Register that a screen hash produced confirmed MOP coverage.
     * Called by the agent loop when LogcatReader drains coverage tags
     * while the agent was on a specific screen.
     *
     * @param hash    screen hash where coverage was confirmed
     * @param methods set of confirmed method signatures
     */
    public void addConfirmed(String hash, Set<String> methods) {
        if (hash == null || methods == null || methods.isEmpty()) return;
        confirmedHashes.computeIfAbsent(hash, k -> new HashSet<>()).addAll(methods);
    }

    /**
     * Returns true if this screen hash has at least one confirmed method execution.
     */
    public boolean hasConfirmed(String hash) {
        Set<String> methods = confirmedHashes.get(hash);
        return methods != null && !methods.isEmpty();
    }

    @Override
    public int score(Action candidate, ScreenState screen, ContentGraph graph, StaticMap staticMap) {
        if (hasConfirmed(screen.getContentHash())) {
            // Decay with revisits: preserves "this screen has MOP" signal on first visits
            // but diminishes on revisits to push exploration toward new screens
            int revisits = 0;
            ContentNode node = graph.get(screen.getContentHash());
            if (node != null) {
                revisits = Math.max(0, node.getVisitCount() - 1);
            }
            return confirmedBase / (1 + revisits);
        }
        return 0;
    }
}
