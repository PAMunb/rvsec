package br.unb.cic.rvsmart.core;

import android.graphics.Rect;

/**
 * Single UI element extracted from AccessibilityNodeInfo during BFS traversal.
 *
 * Fields map directly to AccessibilityNodeInfo methods (see spec field mapping table).
 * Nine fields participate in the structural hash (INV-RSM-03):
 *   class, resource_id, package, clickable, scrollable, checkable, enabled, long_clickable, editable.
 * Four fields are excluded from the hash: text, contentDescription, bounds, parentIndex.
 */
public class ScreenItem {

    private final String className;
    private final String resourceId;
    private final String text;
    private final String contentDescription;
    private final Rect bounds;
    private final String packageName;
    private final boolean clickable;
    private final boolean scrollable;
    private final boolean checkable;
    private final boolean enabled;
    private final boolean longClickable;
    private final boolean editable;
    private final int parentIndex;

    public ScreenItem(String className, String resourceId, String text,
                      String contentDescription, Rect bounds, String packageName,
                      boolean clickable, boolean scrollable, boolean checkable,
                      boolean enabled, boolean longClickable, boolean editable,
                      int parentIndex) {
        this.className = className;
        this.resourceId = resourceId;
        this.text = text;
        this.contentDescription = contentDescription;
        this.bounds = bounds;
        this.packageName = packageName;
        this.clickable = clickable;
        this.scrollable = scrollable;
        this.checkable = checkable;
        this.enabled = enabled;
        this.longClickable = longClickable;
        this.editable = editable;
        this.parentIndex = parentIndex;
    }

    public String getClassName() { return className; }
    public String getResourceId() { return resourceId; }
    public String getText() { return text; }
    public String getContentDescription() { return contentDescription; }
    public Rect getBounds() { return bounds; }
    public String getPackageName() { return packageName; }
    public boolean isClickable() { return clickable; }
    public boolean isScrollable() { return scrollable; }
    public boolean isCheckable() { return checkable; }
    public boolean isEnabled() { return enabled; }
    public boolean isLongClickable() { return longClickable; }
    public boolean isEditable() { return editable; }
    public int getParentIndex() { return parentIndex; }

    /**
     * Whether this item represents an interactive widget.
     * Interactive = clickable OR scrollable OR checkable OR editable.
     */
    public boolean isInteractive() {
        return clickable || scrollable || checkable || editable;
    }
}
