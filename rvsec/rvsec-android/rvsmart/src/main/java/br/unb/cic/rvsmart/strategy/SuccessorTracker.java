package br.unb.cic.rvsmart.strategy;

import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

/**
 * Tracks parent-child state transitions and per-widget value saturation
 * to support proactive backtracking and multi-value exploration.
 *
 * Parent-child pairs are recorded each time a state transition occurs.
 * The re-enable mechanism allows the strategy to re-visit a state up to
 * max_re_enables times when new exploration opportunities are discovered
 * (e.g., after a graph-level reward propagation reveals a profitable path).
 *
 * Widget saturation tracks how many distinct values have been tried for
 * multi-value widgets (EditText, Spinner, etc.). A widget is considered
 * saturated once the distinct value count reaches the threshold.
 */
public class SuccessorTracker {

    private static final int DEFAULT_MAX_RE_ENABLES = 6;
    private static final int DEFAULT_WIDGET_SATURATION_THRESHOLD = 4;

    private final int maxReEnables;
    private final int widgetSaturationThreshold;

    // Directed graph edges: hash -> set of child hashes
    private final Map<String, Set<String>> children = new HashMap<>();

    // Reverse edges: hash -> set of parent hashes
    private final Map<String, Set<String>> parents = new HashMap<>();

    // Re-enable counts: hash -> remaining re-enables
    private final Map<String, Integer> reEnableCounts = new HashMap<>();

    // Marks hashes that have been re-enabled at least once
    private final Set<String> reEnabledHashes = new HashSet<>();

    // Widget value tracking: hash -> (widgetSig -> set of distinct values tried)
    private final Map<String, Map<String, Set<String>>> widgetValues = new HashMap<>();

    public SuccessorTracker() {
        this(DEFAULT_MAX_RE_ENABLES, DEFAULT_WIDGET_SATURATION_THRESHOLD);
    }

    public SuccessorTracker(int maxReEnables, int widgetSaturationThreshold) {
        this.maxReEnables = maxReEnables;
        this.widgetSaturationThreshold = widgetSaturationThreshold;
    }

    /**
     * Records a parent-child transition. parentHash is a predecessor of childHash.
     */
    public void record(String parentHash, String childHash) {
        children.computeIfAbsent(parentHash, k -> new HashSet<>()).add(childHash);
        parents.computeIfAbsent(childHash, k -> new HashSet<>()).add(parentHash);
    }

    /**
     * Returns all recorded parent hashes for the given hash.
     */
    public Set<String> getParents(String hash) {
        Set<String> p = parents.get(hash);
        return p != null ? Collections.unmodifiableSet(p) : Collections.emptySet();
    }

    /**
     * Returns all recorded child hashes for the given hash.
     */
    public Set<String> getChildren(String hash) {
        Set<String> c = children.get(hash);
        return c != null ? Collections.unmodifiableSet(c) : Collections.emptySet();
    }

    /**
     * Marks a hash for re-visit by setting its re-enable count to maxReEnables.
     * Has no effect if the hash has already consumed all re-enables.
     */
    public void reEnable(String hash) {
        int current = reEnableCounts.getOrDefault(hash, 0);
        if (current < maxReEnables) {
            reEnableCounts.put(hash, maxReEnables);
            reEnabledHashes.add(hash);
        }
    }

    /**
     * Returns true if this hash has been re-enabled and still has remaining re-enables.
     */
    public boolean isReEnabled(String hash) {
        return reEnabledHashes.contains(hash)
                && reEnableCounts.getOrDefault(hash, 0) > 0;
    }

    /**
     * Decrements the re-enable count for a hash. When count reaches 0,
     * the hash is no longer considered re-enabled.
     */
    public void consumeReEnable(String hash) {
        int current = reEnableCounts.getOrDefault(hash, 0);
        if (current > 0) {
            reEnableCounts.put(hash, current - 1);
            if (current - 1 == 0) {
                reEnabledHashes.remove(hash);
            }
        }
    }

    /**
     * Records a value that was tried for a widget on a specific screen.
     *
     * @param hash      screen hash
     * @param widgetSig widget action signature
     * @param value     the text value that was entered or selected
     */
    public void recordWidgetValue(String hash, String widgetSig, String value) {
        widgetValues
                .computeIfAbsent(hash, k -> new HashMap<>())
                .computeIfAbsent(widgetSig, k -> new HashSet<>())
                .add(value);
    }

    /**
     * Returns true if the number of distinct values tried for a widget on this screen
     * has reached or exceeded the saturation threshold.
     */
    public boolean isWidgetSaturated(String hash, String widgetSig) {
        Map<String, Set<String>> screenWidgets = widgetValues.get(hash);
        if (screenWidgets == null) return false;
        Set<String> values = screenWidgets.get(widgetSig);
        return values != null && values.size() >= widgetSaturationThreshold;
    }
}
