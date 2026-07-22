package br.unb.cic.rvsmart.llm;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.ScreenItem;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Immutable value object holding all context data needed for LLM prompt construction.
 *
 * Supports two prompt versions:
 * - V13: uses only base fields (base64Screenshot, uiElements, currentActivity,
 *         navigationHint, visitedActivities, iterationNumber)
 * - V17: uses all fields; V17-only fields may be null, in which case the prompt
 *         builder falls back gracefully
 *
 * Use the inner Builder to construct instances.
 */
public final class PromptContext {

    // --- Base fields (required for any prompt version) ---

    /** JPEG screenshot encoded as base64, without a data URI prefix. */
    private final String base64Screenshot;

    /** UI elements visible on the current screen. */
    private final List<ScreenItem> uiElements;

    /** Fully-qualified class name of the currently displayed activity. */
    private final String currentActivity;

    /** Optional navigation suggestion for the LLM; null means no hint available. */
    private final String navigationHint;

    /** Set of fully-qualified activity class names visited so far in this session. */
    private final Set<String> visitedActivities;

    /** Current exploration iteration count. */
    private final int iterationNumber;

    // --- V17-only fields (all nullable — null triggers graceful fallback in prompt builder) ---

    /**
     * How many times each UI element has been interacted with, keyed by element ID.
     * Null when V17 enrichment data is not available.
     */
    private final Map<String, Integer> elementInteractionCounts;

    /**
     * Element IDs whose host activity directly reaches a monitored operation.
     * Null when MOP reachability data is not available.
     */
    private final Set<String> directMopElements;

    /**
     * Element IDs whose host activity transitively reaches a monitored operation.
     * Null when MOP reachability data is not available.
     */
    private final Set<String> indirectMopElements;

    /**
     * Raw score breakdown from ActionSelector for each element, keyed by element ID.
     * Null when scoring data is not available.
     */
    private final Map<String, Object> elementScores;

    /**
     * Snapshot of the last N actions taken (ring buffer contents).
     * Empty list when no recent actions are available; never null.
     */
    private final List<Action> recentActions;

    private PromptContext(Builder builder) {
        this.base64Screenshot = builder.base64Screenshot;
        this.uiElements = builder.uiElements != null
                ? Collections.unmodifiableList(builder.uiElements)
                : Collections.emptyList();
        this.currentActivity = builder.currentActivity;
        this.navigationHint = builder.navigationHint;
        this.visitedActivities = builder.visitedActivities != null
                ? Collections.unmodifiableSet(builder.visitedActivities)
                : Collections.emptySet();
        this.iterationNumber = builder.iterationNumber;
        this.elementInteractionCounts = builder.elementInteractionCounts;
        this.directMopElements = builder.directMopElements;
        this.indirectMopElements = builder.indirectMopElements;
        this.elementScores = builder.elementScores;
        this.recentActions = builder.recentActions != null
                ? Collections.unmodifiableList(builder.recentActions)
                : Collections.emptyList();
    }

    // --- Getters ---

    public String getBase64Screenshot() {
        return base64Screenshot;
    }

    public List<ScreenItem> getUiElements() {
        return uiElements;
    }

    public String getCurrentActivity() {
        return currentActivity;
    }

    public String getNavigationHint() {
        return navigationHint;
    }

    public Set<String> getVisitedActivities() {
        return visitedActivities;
    }

    public int getIterationNumber() {
        return iterationNumber;
    }

    public Map<String, Integer> getElementInteractionCounts() {
        return elementInteractionCounts;
    }

    public Set<String> getDirectMopElements() {
        return directMopElements;
    }

    public Set<String> getIndirectMopElements() {
        return indirectMopElements;
    }

    public Map<String, Object> getElementScores() {
        return elementScores;
    }

    public List<Action> getRecentActions() {
        return recentActions;
    }

    // --- Builder ---

    public static Builder builder() {
        return new Builder();
    }

    public static final class Builder {

        private String base64Screenshot;
        private List<ScreenItem> uiElements;
        private String currentActivity;
        private String navigationHint;
        private Set<String> visitedActivities;
        private int iterationNumber;
        private Map<String, Integer> elementInteractionCounts;
        private Set<String> directMopElements;
        private Set<String> indirectMopElements;
        private Map<String, Object> elementScores;
        private List<Action> recentActions;

        private Builder() {}

        public Builder base64Screenshot(String base64Screenshot) {
            this.base64Screenshot = base64Screenshot;
            return this;
        }

        public Builder uiElements(List<ScreenItem> uiElements) {
            this.uiElements = uiElements;
            return this;
        }

        public Builder currentActivity(String currentActivity) {
            this.currentActivity = currentActivity;
            return this;
        }

        public Builder navigationHint(String navigationHint) {
            this.navigationHint = navigationHint;
            return this;
        }

        public Builder visitedActivities(Set<String> visitedActivities) {
            this.visitedActivities = visitedActivities;
            return this;
        }

        public Builder iterationNumber(int iterationNumber) {
            this.iterationNumber = iterationNumber;
            return this;
        }

        public Builder elementInteractionCounts(Map<String, Integer> elementInteractionCounts) {
            this.elementInteractionCounts = elementInteractionCounts;
            return this;
        }

        public Builder directMopElements(Set<String> directMopElements) {
            this.directMopElements = directMopElements;
            return this;
        }

        public Builder indirectMopElements(Set<String> indirectMopElements) {
            this.indirectMopElements = indirectMopElements;
            return this;
        }

        public Builder elementScores(Map<String, Object> elementScores) {
            this.elementScores = elementScores;
            return this;
        }

        public Builder recentActions(List<Action> recentActions) {
            this.recentActions = recentActions;
            return this;
        }

        /**
         * Builds the PromptContext. Throws IllegalStateException if required fields
         * (base64Screenshot, currentActivity) are null.
         */
        public PromptContext build() {
            if (base64Screenshot == null) {
                throw new IllegalStateException("base64Screenshot is required");
            }
            if (currentActivity == null) {
                throw new IllegalStateException("currentActivity is required");
            }
            return new PromptContext(this);
        }
    }
}
