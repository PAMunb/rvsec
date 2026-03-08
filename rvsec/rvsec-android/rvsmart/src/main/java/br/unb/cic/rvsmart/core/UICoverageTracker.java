package br.unb.cic.rvsmart.core;

import android.graphics.Rect;

import java.util.HashMap;
import java.util.List;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

/**
 * Tracks per-screen UI element coverage during exploration.
 *
 * Each screen (identified by structural hash) has a set of registered elements.
 * Elements use hybrid IDs: "res:{resourceId}" when available, "coords:{cx},{cy}"
 * when bounds exist, or "unknown:{hashCode}" as last resort.
 *
 * Coverage gap = fraction of registered elements NOT yet interacted with (0.0–1.0).
 */
public class UICoverageTracker {

    // screen hash -> set of element IDs on that screen
    private final Map<String, Set<String>> elementsByScreen = new HashMap<>();

    // composite key "screenHash|elementId" -> interaction count (screen-scoped)
    private final Map<String, Integer> interactionCounts = new HashMap<>();

    // element ID -> widget class name
    private final Map<String, String> elementTypes = new HashMap<>();

    /**
     * Compute hybrid element ID for a ScreenItem.
     * Priority: resourceId (if present and non-empty) -> bounds center coords -> identity hashCode.
     */
    public static String elementId(ScreenItem item) {
        String resId = item.getResourceId();
        if (resId != null && !resId.isEmpty()) {
            return "res:" + resId;
        }

        Rect bounds = item.getBounds();
        if (bounds != null) {
            return "coords:" + bounds.centerX() + "," + bounds.centerY();
        }

        // Last resort: use System.identityHashCode to distinguish instances
        return "unknown:" + System.identityHashCode(item);
    }

    /**
     * Register all elements on a screen. Idempotent — re-registering the same
     * screen replaces the element set (same IDs produce same set).
     */
    public void registerScreenElements(String screenHash, List<ScreenItem> items) {
        Set<String> ids = elementsByScreen.get(screenHash);
        if (ids == null) {
            ids = new HashSet<>();
            elementsByScreen.put(screenHash, ids);
        }

        for (ScreenItem item : items) {
            String id = elementId(item);
            ids.add(id);
            elementTypes.put(id, item.getClassName());
        }
    }

    /**
     * Record an interaction with an element on a screen.
     * Uses composite key for screen-scoped tracking (INV-RSM-41).
     */
    public void recordInteraction(String screenHash, String elementId) {
        String key = screenHash + "|" + elementId;
        Integer count = interactionCounts.get(key);
        interactionCounts.put(key, count == null ? 1 : count + 1);
    }

    /**
     * Coverage gap for a screen: fraction of elements NOT yet interacted with.
     * Returns 1.0 for unknown screens (maximally unexplored).
     */
    public float getCoverageGap(String screenHash) {
        Set<String> ids = elementsByScreen.get(screenHash);
        if (ids == null || ids.isEmpty()) {
            return 1.0f;
        }

        int total = ids.size();
        int interacted = 0;
        for (String id : ids) {
            String key = screenHash + "|" + id;
            if (interactionCounts.containsKey(key)) {
                interacted++;
            }
        }

        return 1.0f - ((float) interacted / total);
    }

    /**
     * Total number of unique elements registered across all screens.
     */
    public int getTotalElements() {
        Set<String> all = new HashSet<>();
        for (Set<String> ids : elementsByScreen.values()) {
            all.addAll(ids);
        }
        return all.size();
    }

    /**
     * Total interactions recorded (sum of all counts).
     */
    public int getTotalInteractions() {
        int total = 0;
        for (int count : interactionCounts.values()) {
            total += count;
        }
        return total;
    }
}
