package br.unb.cic.rvsmart.device;

import android.util.Log;
import android.view.accessibility.AccessibilityNodeInfo;

import java.util.Arrays;
import java.util.HashSet;
import java.util.LinkedList;
import java.util.Queue;
import java.util.Set;

/**
 * Detects and dismisses system dialogs (crash, permission, battery optimization)
 * at the start of each iteration cycle, before action selection.
 *
 * Detection: checks if the root window's package matches known system packages.
 * Dismissal: finds and clicks OK/Allow/Deny buttons via InputInjector.
 * After dismissal, the agent re-captures the UI within the same iteration.
 */
public class SystemDialogDetector {

    private static final String TAG = "RVSMART";

    /** System packages that produce dialogs we need to dismiss. */
    private static final Set<String> SYSTEM_PACKAGES = new HashSet<>(Arrays.asList(
            "android",
            "com.android.packageinstaller",
            "com.google.android.packageinstaller",
            "com.android.settings"
    ));

    /** Button labels to click for dismissal (case-insensitive matching). */
    private static final Set<String> DISMISS_LABELS = new HashSet<>(Arrays.asList(
            "ok", "allow", "deny", "close", "wait",
            "open app again", "close app"
    ));

    private final InputInjector injector;

    public SystemDialogDetector(InputInjector injector) {
        this.injector = injector;
    }

    /**
     * Check if the current screen is a system dialog.
     *
     * @param root Root AccessibilityNodeInfo from getRootInActiveWindow()
     * @return true if the root belongs to a known system dialog package
     */
    public boolean isSystemDialog(AccessibilityNodeInfo root) {
        if (root == null) return false;
        CharSequence pkg = root.getPackageName();
        return pkg != null && SYSTEM_PACKAGES.contains(pkg.toString());
    }

    /**
     * Attempt to dismiss a system dialog by finding and clicking a dismiss button.
     * Uses BFS to find buttons with matching labels.
     *
     * @param root Root AccessibilityNodeInfo of the dialog
     * @return true if a dismiss button was found and clicked
     */
    public boolean dismiss(AccessibilityNodeInfo root) {
        if (root == null) return false;

        Queue<AccessibilityNodeInfo> queue = new LinkedList<>();
        queue.add(root);

        while (!queue.isEmpty()) {
            AccessibilityNodeInfo node = queue.poll();
            try {
                if (isDismissButton(node)) {
                    android.graphics.Rect bounds = new android.graphics.Rect();
                    node.getBoundsInScreen(bounds);
                    int x = bounds.centerX();
                    int y = bounds.centerY();
                    boolean clicked = injector.click(x, y);
                    if (clicked) {
                        Log.i(TAG, "Dismissed system dialog by clicking at (" + x + "," + y + ")");
                    }
                    recycleQueue(queue);
                    return clicked;
                }

                int childCount = node.getChildCount();
                for (int i = 0; i < childCount; i++) {
                    AccessibilityNodeInfo child = node.getChild(i);
                    if (child != null) {
                        queue.add(child);
                    }
                }
            } catch (Exception e) {
                // Node may be detached
            }
        }

        Log.w(TAG, "System dialog detected but no dismiss button found");
        return false;
    }

    private boolean isDismissButton(AccessibilityNodeInfo node) {
        if (!node.isClickable()) return false;

        CharSequence text = node.getText();
        if (text != null) {
            String lower = text.toString().toLowerCase().trim();
            return DISMISS_LABELS.contains(lower);
        }

        CharSequence desc = node.getContentDescription();
        if (desc != null) {
            String lower = desc.toString().toLowerCase().trim();
            return DISMISS_LABELS.contains(lower);
        }

        return false;
    }

    private void recycleQueue(Queue<AccessibilityNodeInfo> queue) {
        for (AccessibilityNodeInfo node : queue) {
            try {
                node.recycle();
            } catch (Exception e) {
                // Already recycled
            }
        }
    }
}
