package br.unb.cic.rvsmart.graph;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

/**
 * Represents a unique UI state in ContentGraph, identified by content hash.
 *
 * Tracks action execution by coordinate-based signatures (not volatile IDs),
 * enabling stable coverage tracking. Actions are tracked by execution count
 * for continuous exploration — the agent never "exhausts" actions, it
 * prioritizes least-executed ones until timeout (INV-RSM-01).
 *
 * Multi-value widgets (EditText, Spinner, SeekBar) use a higher saturation
 * threshold because each interaction can produce different input/state.
 */
public class ContentNode {

    /** Single-action widget saturation threshold. */
    private static final int DEFAULT_SATURATION_THRESHOLD = 4;

    /** Widget classes that need more executions before saturation. */
    private static final Set<String> MULTI_VALUE_WIDGETS = new HashSet<>();
    static {
        MULTI_VALUE_WIDGETS.add("EditText");
        MULTI_VALUE_WIDGETS.add("TextInputEditText");
        MULTI_VALUE_WIDGETS.add("AppCompatEditText");
        MULTI_VALUE_WIDGETS.add("AutoCompleteTextView");
        MULTI_VALUE_WIDGETS.add("AppCompatAutoCompleteTextView");
        MULTI_VALUE_WIDGETS.add("MultiAutoCompleteTextView");
        MULTI_VALUE_WIDGETS.add("Spinner");
        MULTI_VALUE_WIDGETS.add("AppCompatSpinner");
        MULTI_VALUE_WIDGETS.add("SeekBar");
        MULTI_VALUE_WIDGETS.add("AppCompatSeekBar");
        MULTI_VALUE_WIDGETS.add("RatingBar");
        MULTI_VALUE_WIDGETS.add("AppCompatRatingBar");
        MULTI_VALUE_WIDGETS.add("NumberPicker");
    }

    /** System action types excluded from saturation calculation. */
    private static final Set<String> SYSTEM_ACTION_TYPES = new HashSet<>();
    static {
        SYSTEM_ACTION_TYPES.add("back");
        SYSTEM_ACTION_TYPES.add("restart");
        SYSTEM_ACTION_TYPES.add("unknown");
        SYSTEM_ACTION_TYPES.add("key_event");
    }

    private final String contentHash;
    private final String activity;

    private int visitCount;
    private int totalActions;    // Total available actions on first visit

    // Action tracking by signature string (e.g., "click@540,960")
    private final Map<String, Integer> executionCounts = new HashMap<>();
    private final Map<String, Integer> successCounts = new HashMap<>();
    private final Map<String, String> widgetClasses = new HashMap<>();
    private final Set<String> transitions = new HashSet<>();

    private int multiValueThreshold = 6;

    public ContentNode(String contentHash, String activity) {
        this.contentHash = contentHash;
        this.activity = activity;
    }

    public String getContentHash() { return contentHash; }
    public String getActivity() { return activity; }
    public int getVisitCount() { return visitCount; }
    public int getTotalActions() { return totalActions; }
    public Set<String> getTransitions() { return java.util.Collections.unmodifiableSet(transitions); }

    public void setMultiValueThreshold(int threshold) {
        this.multiValueThreshold = threshold;
    }

    public void incrementVisitCount() {
        visitCount++;
    }

    public void setTotalActions(int totalActions) {
        this.totalActions = Math.max(this.totalActions, totalActions);
    }

    public void addTransition(String targetHash) {
        transitions.add(targetHash);
    }

    /**
     * Record action execution. Called BEFORE execution for crash safety —
     * if the app crashes during execution, the graph still records the attempt.
     */
    public void recordAction(String signature, String widgetClass) {
        executionCounts.put(signature, getExecutionCount(signature) + 1);
        if (widgetClass != null && !widgetClass.isEmpty()
                && !widgetClasses.containsKey(signature)) {
            widgetClasses.put(signature, widgetClass);
        }
    }

    /**
     * Record whether an action caused a state transition (screen hash changed).
     */
    public void recordActionSuccess(String signature, boolean success) {
        if (success) {
            successCounts.put(signature, successCounts.getOrDefault(signature, 0) + 1);
        }
    }

    public int getExecutionCount(String signature) {
        return executionCounts.getOrDefault(signature, 0);
    }

    public boolean isActionExecuted(String signature) {
        return executionCounts.containsKey(signature);
    }

    /**
     * Action coverage: executed / total (0.0-1.0).
     */
    public float getCoverage() {
        if (totalActions == 0) return 0.0f;
        return (float) executionCounts.size() / totalActions;
    }

    /**
     * Action strength: successes / executions (0.0-1.0).
     * Untested actions return 0.5 (neutral).
     */
    public float getActionStrength(String signature) {
        int executions = getExecutionCount(signature);
        if (executions == 0) return 0.5f;
        int successes = successCounts.getOrDefault(signature, 0);
        return (float) successes / executions;
    }

    /**
     * Check if action has been sufficiently explored based on widget type.
     */
    public boolean isActionSaturated(String signature) {
        return getExecutionCount(signature) >= getEffectiveThreshold(signature);
    }

    private int getEffectiveThreshold(String signature) {
        String wc = widgetClasses.getOrDefault(signature, "");
        if (MULTI_VALUE_WIDGETS.contains(wc)) {
            return multiValueThreshold;
        }
        return DEFAULT_SATURATION_THRESHOLD;
    }

    /**
     * Saturation rate: saturated widget actions / total actions (0.0-1.0).
     * System actions (BACK, RESTART) are excluded from the numerator.
     */
    public float getSaturationRate() {
        if (totalActions == 0) return 1.0f;
        int saturated = 0;
        for (Map.Entry<String, Integer> entry : executionCounts.entrySet()) {
            String sig = entry.getKey();
            // Extract action type from signature "type@x,y" or "type:text@x,y"
            String actionType = sig.contains("@") ? sig.substring(0, sig.indexOf('@')) : sig;
            if (actionType.contains(":")) {
                actionType = actionType.substring(0, actionType.indexOf(':'));
            }
            if (!SYSTEM_ACTION_TYPES.contains(actionType) && isActionSaturated(sig)) {
                saturated++;
            }
        }
        return Math.min(1.0f, (float) saturated / totalActions);
    }

    /**
     * Get the set of all executed action signatures.
     */
    public Set<String> getExecutedActions() {
        return executionCounts.keySet();
    }
}
