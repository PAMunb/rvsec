package br.unb.cic.rvsmart.device;

import android.graphics.Rect;
import android.util.Log;
import android.view.accessibility.AccessibilityNodeInfo;

import br.unb.cic.rvsmart.core.ScreenItem;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedList;
import java.util.List;
import java.util.Queue;

/**
 * Captures the UI tree via AccessibilityNodeInfo BFS traversal.
 *
 * Every node obtained via getChild() MUST be recycled in a finally block (INV-RSM-02).
 * BFS is capped at MAX_ITEMS nodes (INV-RSM-11) with priority-based retention:
 * interactive widgets first, shallower depth second.
 */
public class UiCapture {

    private static final String TAG = "RVSMART";
    private static final int DEFAULT_MAX_ITEMS = 2000;

    private int maxItems;

    public UiCapture(int maxItems) {
        this.maxItems = maxItems;
    }

    public UiCapture() {
        this(DEFAULT_MAX_ITEMS);
    }

    public void setMaxItems(int maxItems) {
        this.maxItems = maxItems;
    }

    /**
     * Capture the current UI tree from the root AccessibilityNodeInfo.
     *
     * @param root The root node (from getRootInActiveWindow). Caller is responsible
     *             for recycling the root node after this method returns.
     * @return List of ScreenItems extracted from the UI tree, or empty list if root is null.
     */
    public List<ScreenItem> capture(AccessibilityNodeInfo root) {
        if (root == null) {
            return Collections.emptyList();
        }

        List<NodeEntry> allNodes = new ArrayList<>();
        Queue<NodeEntry> queue = new LinkedList<>();
        queue.add(new NodeEntry(root, 0, -1, false));  // root: depth 0, no parent, don't recycle root

        while (!queue.isEmpty()) {
            NodeEntry entry = queue.poll();
            AccessibilityNodeInfo node = entry.node;

            try {
                // Extract ScreenItem from this node
                ScreenItem item = extractScreenItem(node, entry.parentIndex);
                entry.item = item;
                entry.isInteractive = isInteractive(node);
                allNodes.add(entry);

                // Traverse children
                int childCount = node.getChildCount();
                int currentIndex = allNodes.size() - 1;

                for (int i = 0; i < childCount; i++) {
                    AccessibilityNodeInfo child = null;
                    try {
                        child = node.getChild(i);
                        if (child != null) {
                            queue.add(new NodeEntry(child, entry.depth + 1,
                                    currentIndex, true));  // mark for recycling
                        }
                    } catch (Exception e) {
                        // Child access can fail for detached nodes
                        if (child != null) {
                            child.recycle();
                        }
                    }
                }
            } catch (Exception e) {
                Log.w(TAG, "Error extracting node at depth " + entry.depth + ": " + e.getMessage());
            }
        }

        // Apply MAX_ITEMS cap with priority-based retention (INV-RSM-11)
        List<ScreenItem> result;
        if (allNodes.size() > maxItems) {
            Log.w(TAG, "UI tree has " + allNodes.size() + " nodes, capping at " + maxItems);
            result = retainByPriority(allNodes, maxItems);
        } else {
            result = new ArrayList<>(allNodes.size());
            for (NodeEntry entry : allNodes) {
                if (entry.item != null) {
                    result.add(entry.item);
                }
            }
        }

        // Recycle all child nodes (not root — caller manages root lifecycle)
        for (NodeEntry entry : allNodes) {
            if (entry.shouldRecycle && entry.node != null) {
                try {
                    entry.node.recycle();
                } catch (Exception e) {
                    // Already recycled or detached
                }
            }
        }

        return result;
    }

    /**
     * Retain top N nodes by priority: interactive widgets first, shallower depth second.
     */
    private List<ScreenItem> retainByPriority(List<NodeEntry> allNodes, int limit) {
        // Sort by priority: interactive first, then shallower depth
        Collections.sort(allNodes, new Comparator<NodeEntry>() {
            @Override
            public int compare(NodeEntry a, NodeEntry b) {
                // Interactive nodes first
                if (a.isInteractive != b.isInteractive) {
                    return a.isInteractive ? -1 : 1;
                }
                // Shallower depth second
                return Integer.compare(a.depth, b.depth);
            }
        });

        List<ScreenItem> result = new ArrayList<>(limit);
        for (int i = 0; i < Math.min(limit, allNodes.size()); i++) {
            NodeEntry entry = allNodes.get(i);
            if (entry.item != null) {
                result.add(entry.item);
            }
        }
        return result;
    }

    private ScreenItem extractScreenItem(AccessibilityNodeInfo node, int parentIndex) {
        Rect bounds = new Rect();
        node.getBoundsInScreen(bounds);

        CharSequence className = node.getClassName();
        CharSequence text = node.getText();
        CharSequence contentDesc = node.getContentDescription();
        CharSequence pkgName = node.getPackageName();
        CharSequence resId = node.getViewIdResourceName();

        return new ScreenItem(
                className != null ? simplifyClassName(className.toString()) : "",
                resId != null ? normalizeResourceId(resId.toString()) : null,
                text != null ? text.toString() : null,
                contentDesc != null ? contentDesc.toString() : null,
                bounds,
                pkgName != null ? pkgName.toString() : "",
                node.isClickable(),
                node.isScrollable(),
                node.isCheckable(),
                node.isEnabled(),
                node.isLongClickable(),
                isEditable(node),
                parentIndex
        );
    }

    /**
     * Simplify fully-qualified class name to simple name.
     * e.g., "android.widget.Button" -> "Button"
     */
    private String simplifyClassName(String fqcn) {
        int lastDot = fqcn.lastIndexOf('.');
        return lastDot >= 0 ? fqcn.substring(lastDot + 1) : fqcn;
    }

    /**
     * Normalize resource ID to match Python agent's format.
     * AccessibilityNodeInfo may return "package:id/name" or "id/name".
     * Python's UIAutomator2 XML uses "package:id/name" format.
     * We keep the full format as-is — validated in PoC Task 2.8.
     */
    String normalizeResourceId(String resourceId) {
        return resourceId;
    }

    private boolean isInteractive(AccessibilityNodeInfo node) {
        return node.isClickable() || node.isScrollable()
                || node.isCheckable() || isEditable(node);
    }

    private boolean isEditable(AccessibilityNodeInfo node) {
        // AccessibilityNodeInfo.isEditable() was added in API 18
        try {
            return node.isEditable();
        } catch (NoSuchMethodError e) {
            return false;
        }
    }

    /**
     * Internal tracking entry for BFS traversal and priority-based retention.
     */
    private static class NodeEntry {
        final AccessibilityNodeInfo node;
        final int depth;
        final int parentIndex;
        final boolean shouldRecycle;
        ScreenItem item;
        boolean isInteractive;

        NodeEntry(AccessibilityNodeInfo node, int depth, int parentIndex, boolean shouldRecycle) {
            this.node = node;
            this.depth = depth;
            this.parentIndex = parentIndex;
            this.shouldRecycle = shouldRecycle;
        }
    }
}
