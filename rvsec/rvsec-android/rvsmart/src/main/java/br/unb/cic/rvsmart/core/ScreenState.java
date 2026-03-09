package br.unb.cic.rvsmart.core;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;

/**
 * Represents the current UI state: items + activity name + two hashes.
 *
 * Two hashes serve different purposes:
 *
 * contentHash: includes activity, className, resourceID, text (≤ 50 chars), enabled, checkable
 *   per widget. Used as the primary state identity for ContentGraph.
 *   Text is included only for interactive non-EditText widgets (e.g. Button, CheckBox labels).
 *   EditText text is excluded to prevent agent-typed input from creating false state loops.
 *   Non-interactive widget text (output TextViews, status displays) is excluded to prevent
 *   dynamic display content from creating spurious content hash changes.
 *   Text is capped at 50 chars to prevent long dynamic content from creating false distinctions.
 *
 * structHash: identical to the former computeHash() — className|resourceID|interactMask only.
 *   Used as the cluster key for StructuralGraph (groups structurally identical screen layouts).
 *   Widgets with identical structural signatures are merged (FastBot pattern).
 */
public class ScreenState {

    // Interaction flag bitmask positions
    private static final int MASK_CLICKABLE      = 1;
    private static final int MASK_SCROLLABLE     = 2;
    private static final int MASK_CHECKABLE      = 4;
    private static final int MASK_LONG_CLICKABLE = 8;
    private static final int MASK_ENABLED        = 16;

    // Maximum text length included in content hash (prevents dynamic content false distinctions)
    private static final int MAX_TEXT_LENGTH = 50;

    private final List<ScreenItem> items;
    private final String activity;
    private final String contentHash;
    private final String structHash;

    public ScreenState(List<ScreenItem> items, String activity) {
        this.items = Collections.unmodifiableList(new ArrayList<>(items));
        this.activity = activity;
        this.contentHash = computeContentHash(items, activity);
        this.structHash = computeStructHash(items, activity);
    }

    public List<ScreenItem> getItems() {
        return items;
    }

    public String getActivity() {
        return activity;
    }

    public String getContentHash() {
        return contentHash;
    }

    public String getStructHash() {
        return structHash;
    }

    /**
     * Compute content hash: includes activity, className, resourceID, text (≤ 50 chars,
     * excluding EditText), enabled, checkable per widget.
     *
     * Algorithm:
     *   1. Build a signature per widget: "className|resourceID|text|enabled|checkable"
     *      (text omitted for EditText; text truncated to 50 chars for other widgets)
     *   2. Deduplicate identical signatures (Set)
     *   3. Sort signatures for determinism
     *   4. Hash via Objects.hash(activity, sig1, sig2, ...) formatted as 8-char hex
     */
    static String computeContentHash(List<ScreenItem> items, String activity) {
        Set<String> signatureSet = new LinkedHashSet<>();
        for (ScreenItem item : items) {
            signatureSet.add(contentSignature(item));
        }

        List<String> sorted = new ArrayList<>(signatureSet);
        Collections.sort(sorted);

        Object[] hashArgs = new Object[sorted.size() + 1];
        hashArgs[0] = activity;
        for (int i = 0; i < sorted.size(); i++) {
            hashArgs[i + 1] = sorted.get(i);
        }

        int hashCode = Objects.hash(hashArgs);
        return String.format("%08x", hashCode);
    }

    /**
     * Compute structural hash from deduplicated, sorted widget signatures.
     * Same logic as the former computeHash() — no behavioral change, renamed for clarity.
     *
     * Algorithm:
     *   1. Build a signature string per widget: "className|resourceID|interactMask"
     *   2. Deduplicate identical signatures (Set)
     *   3. Sort signatures by natural string ordering
     *   4. Hash via Objects.hash(activity, sig1, sig2, ...) formatted as 8-char hex
     */
    static String computeStructHash(List<ScreenItem> items, String activity) {
        Set<String> signatureSet = new LinkedHashSet<>();
        for (ScreenItem item : items) {
            signatureSet.add(structSignature(item));
        }

        List<String> sorted = new ArrayList<>(signatureSet);
        Collections.sort(sorted);

        Object[] hashArgs = new Object[sorted.size() + 1];
        hashArgs[0] = activity;
        for (int i = 0; i < sorted.size(); i++) {
            hashArgs[i + 1] = sorted.get(i);
        }

        int hashCode = Objects.hash(hashArgs);
        return String.format("%08x", hashCode);
    }

    /**
     * Build a content signature for a widget.
     * Includes: className, resourceID, text (trimmed, ≤ 50 chars), enabled, checkable.
     *
     * Text inclusion rules:
     * - EditText (user-typed content): always excluded — prevents agent input from creating
     *   state loops (each keystroke would produce a new content hash)
     * - Non-interactive widgets (output-only TextViews, labels, status displays): excluded —
     *   prevents dynamic display text (cipher output, counters, timestamps) from creating
     *   spurious content hash changes that trap Phase 1 in a single screen
     * - Interactive non-EditText (Buttons, CheckBoxes, tabs with text labels): included —
     *   button/tab text is semantic state content that legitimately distinguishes UI states
     */
    private static String contentSignature(ScreenItem item) {
        String className = item.getClassName() != null ? item.getClassName() : "";
        String resourceId = item.getResourceId() != null ? item.getResourceId() : "";

        String text = "";
        boolean isEditText = isEditTextClass(className);
        // Include text only for interactive non-EditText widgets (e.g. Button, CheckBox).
        // Output-only widgets (e.g. result TextViews) are excluded via isInteractive() check.
        if (!isEditText && item.isInteractive() && item.getText() != null) {
            String raw = item.getText().trim();
            text = raw.length() > MAX_TEXT_LENGTH ? raw.substring(0, MAX_TEXT_LENGTH) : raw;
        }

        boolean enabled = item.isEnabled();
        boolean checkable = item.isCheckable();

        return className + "|" + resourceId + "|" + text
                + "|" + enabled + "|" + checkable;
    }

    /**
     * Build a structural signature for a widget using only identity-relevant fields.
     * Format: "className|resourceID|interactMask"
     */
    private static String structSignature(ScreenItem item) {
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

    /**
     * Returns true if className represents an EditText widget.
     * Covers the common subclasses used by support and material design libraries.
     */
    private static boolean isEditTextClass(String className) {
        return "EditText".equals(className)
                || "TextInputEditText".equals(className)
                || "AppCompatEditText".equals(className)
                || "AutoCompleteTextView".equals(className)
                || "AppCompatAutoCompleteTextView".equals(className)
                || "MultiAutoCompleteTextView".equals(className);
    }
}
