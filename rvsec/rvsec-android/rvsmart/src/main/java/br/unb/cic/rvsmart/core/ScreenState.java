package br.unb.cic.rvsmart.core;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;

/**
 * Represents the current UI state: items + activity name + structural hash.
 *
 * The structural hash uses Objects.hash() over deduplicated, sorted widget signatures.
 * Each widget signature encodes 3 structural fields: className, resourceID, interactMask.
 * Widgets with identical signatures are merged (FastBot pattern) to prevent list items
 * from inflating state counts.
 */
public class ScreenState {

    // Interaction flag bitmask positions
    private static final int MASK_CLICKABLE      = 1;
    private static final int MASK_SCROLLABLE     = 2;
    private static final int MASK_CHECKABLE      = 4;
    private static final int MASK_LONG_CLICKABLE = 8;
    private static final int MASK_ENABLED        = 16;

    private final List<ScreenItem> items;
    private final String activity;
    private final String hash;

    public ScreenState(List<ScreenItem> items, String activity) {
        this.items = Collections.unmodifiableList(new ArrayList<>(items));
        this.activity = activity;
        this.hash = computeHash(items, activity);
    }

    public List<ScreenItem> getItems() {
        return items;
    }

    public String getActivity() {
        return activity;
    }

    public String getHash() {
        return hash;
    }

    /**
     * Compute structural hash from deduplicated, sorted widget signatures.
     *
     * Algorithm:
     *   1. Build a signature string per widget: "className|resourceID|interactMask"
     *   2. Deduplicate identical signatures (Set)
     *   3. Sort signatures by natural string ordering (className first, then resourceID)
     *   4. Hash via Objects.hash(activity, sig1, sig2, ...) and format as 8-char hex
     */
    static String computeHash(List<ScreenItem> items, String activity) {
        // Build deduplicated signature set
        Set<String> signatureSet = new LinkedHashSet<>();
        for (ScreenItem item : items) {
            signatureSet.add(widgetSignature(item));
        }

        // Sort for determinism
        List<String> sorted = new ArrayList<>(signatureSet);
        Collections.sort(sorted);

        // Build args array: activity + all sorted signatures
        Object[] hashArgs = new Object[sorted.size() + 1];
        hashArgs[0] = activity;
        for (int i = 0; i < sorted.size(); i++) {
            hashArgs[i + 1] = sorted.get(i);
        }

        int hashCode = Objects.hash(hashArgs);
        return String.format("%08x", hashCode);
    }

    /**
     * Build a structural signature for a widget using only identity-relevant fields.
     * Format: "className|resourceID|interactMask"
     */
    private static String widgetSignature(ScreenItem item) {
        String className = item.getClassName() != null ? item.getClassName() : "";
        String resourceId = item.getResourceId() != null ? item.getResourceId() : "";
        int mask = 0;
        if (item.isClickable())     mask |= MASK_CLICKABLE;
        if (item.isScrollable())    mask |= MASK_SCROLLABLE;
        if (item.isCheckable())     mask |= MASK_CHECKABLE;
        if (item.isLongClickable()) mask |= MASK_LONG_CLICKABLE;
        if (item.isEnabled())       mask |= MASK_ENABLED;
        return className + "|" + resourceId + "|" + mask;
    }
}
