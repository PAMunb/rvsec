package br.unb.cic.rvsmart.recovery;

import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

/**
 * Detects "tarpit" screens where the agent accumulates many iterations
 * without making progress. Unlike sterile screens (UIAutomator failure),
 * tarpit screens parse fine but the agent makes no algorithmic progress.
 *
 * Per-hash counter increments each iteration with no progress (no new state,
 * no new MOP, same hash). Resets on any progress event.
 */
public class TarpitDetector {

    private final int threshold;
    private final Map<String, Integer> counters = new HashMap<>();
    private final Set<String> tarpitHashes = new HashSet<>();
    private String lastHash;

    public TarpitDetector(int threshold) {
        this.threshold = threshold;
    }

    /**
     * Record an iteration outcome for the given screen hash.
     *
     * @param hash current screen content hash
     * @param hasNewState true if a new content state was discovered this iteration
     * @param hasNewMop true if new MOP coverage was gained this iteration
     * @param hadEffect true if the previous action caused a screen hash change
     * @return true if the hash was just declared a tarpit
     */
    public boolean recordIteration(String hash, boolean hasNewState, boolean hasNewMop,
                                   boolean hadEffect) {
        if (hash == null) return false;

        boolean hashChanged = !hash.equals(lastHash);
        lastHash = hash;

        if (hasNewState || hasNewMop || hashChanged || hadEffect) {
            counters.put(hash, 0);
            return false;
        }

        int count = counters.getOrDefault(hash, 0) + 1;
        counters.put(hash, count);

        if (count >= threshold && !tarpitHashes.contains(hash)) {
            tarpitHashes.add(hash);
            return true;
        }
        return false;
    }

    public boolean isTarpit(String hash) {
        return hash != null && tarpitHashes.contains(hash);
    }

    public Set<String> getTarpitHashes() {
        return Collections.unmodifiableSet(tarpitHashes);
    }
}
