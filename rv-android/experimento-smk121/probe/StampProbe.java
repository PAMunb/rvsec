import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.app.UiAutomation;
import android.graphics.Rect;
import android.os.Bundle;
import android.os.HandlerThread;
import android.os.Looper;
import android.view.accessibility.AccessibilityNodeInfo;

import java.io.PrintStream;
import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.TimeoutException;

/**
 * Reads the accessibility tree through {@code UiAutomation}, as APE-RV does, and
 * prints the {@code rvsec.click} / {@code rvsec.longClick} extras of every node,
 * so the handler stamp can be compared with the app's {@code RVSEC-BIND} lines.
 *
 * <p>Run under {@code app_process}, as the only {@code UiAutomation} client:
 * <pre>
 * CLASSPATH=/data/local/tmp/stampprobe.jar app_process /data/local/tmp \
 *     --nice-name=stampprobe StampProbe &lt;package&gt; &lt;activity&gt; &lt;budget-seconds&gt;
 * </pre>
 *
 * <p>It navigates one level: it dumps the first screen; then, for each
 * clickable node of that screen (at most {@link #MAX_CLICKS}), it clicks the
 * node, waits for the screen to settle, dumps the screen reached, presses BACK,
 * and relaunches {@code package/activity} when the app has left the
 * foreground. It stops clicking once the budget is spent.
 *
 * <p>Output (stdout, tab-separated), one {@code APP} line first, then one dump
 * per step:
 * <pre>
 * APP   package  activity
 * STEP  index  time  foreground-package  action  class  view-id  bounds
 * NODE  class  view-id  bounds  rvsec.click  rvsec.longClick
 * </pre>
 * {@code action} is {@code start} (class, view-id and bounds are {@code -}),
 * {@code click} (the clicked node of the first screen), or {@code missing}
 * (that node was not found on the screen the probe was on, so nothing was
 * clicked and no node follows). Absent values are {@code -}. {@code time} is the
 * device wall clock in logcat's {@code threadtime} form ({@code MM-dd
 * HH:mm:ss.SSS}), taken after the tree was read: Compose writes its
 * {@code RVSEC-BIND} lines while the client reads the nodes, so lines produced
 * by this very read precede the time.
 *
 * <p>The {@code UiAutomation} constructor, {@code UiAutomationConnection} and
 * {@code connect()} are hidden API; this class compiles against
 * {@code android.jar} alone and reaches them by reflection. A process started by
 * {@code app_process} runs without hidden-API enforcement.
 */
public final class StampProbe {

    static final String KEY_CLICK = "rvsec.click";
    static final String KEY_LONG_CLICK = "rvsec.longClick";
    static final int MAX_CLICKS = 20;
    static final long IDLE_MS = 500;
    static final long IDLE_TIMEOUT_MS = 5000;

    private static final PrintStream OUT = System.out;
    private static final SimpleDateFormat CLOCK =
            new SimpleDateFormat("MM-dd HH:mm:ss.SSS", Locale.US);

    private StampProbe() {}

    public static void main(String[] args) {
        int status = 0;
        HandlerThread thread = new HandlerThread("StampProbe");
        UiAutomation ua = null;
        try {
            String pkg = args[0];
            String activity = args[1];
            long deadline = System.currentTimeMillis() + Long.parseLong(args[2]) * 1000L;
            thread.start();
            ua = connect(thread.getLooper());
            OUT.println("APP\t" + pkg + "\t" + activity);
            run(ua, pkg, activity, deadline);
        } catch (Throwable t) {
            t.printStackTrace();
            status = 1;
        } finally {
            OUT.flush();
            disconnect(ua);
            thread.quit();
        }
        // The binder threads of the connection are not daemons; exit explicitly.
        System.exit(status);
    }

    /**
     * Connect as APE-RV does ({@code MonkeySourceApe.connect}): a
     * {@code UiAutomation} on a {@code HandlerThread} looper over a new
     * {@code UiAutomationConnection}, then {@code connect()}, then the service
     * info with {@code FLAG_INCLUDE_NOT_IMPORTANT_VIEWS} cleared. View ids are
     * requested explicitly, since the dump keys View nodes by them.
     */
    static UiAutomation connect(Looper looper) throws Exception {
        Class<?> connectionClass = Class.forName("android.app.UiAutomationConnection");
        Class<?> connectionInterface = Class.forName("android.app.IUiAutomationConnection");
        Constructor<?> newConnection = connectionClass.getDeclaredConstructor();
        newConnection.setAccessible(true);
        Object connection = newConnection.newInstance();

        Constructor<UiAutomation> newUiAutomation =
                UiAutomation.class.getDeclaredConstructor(Looper.class, connectionInterface);
        newUiAutomation.setAccessible(true);
        UiAutomation ua = newUiAutomation.newInstance(looper, connection);

        Method connect = UiAutomation.class.getDeclaredMethod("connect");
        connect.setAccessible(true);
        connect.invoke(ua);

        AccessibilityServiceInfo info = ua.getServiceInfo();
        info.flags &= ~AccessibilityServiceInfo.FLAG_INCLUDE_NOT_IMPORTANT_VIEWS;
        info.flags |= AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS;
        ua.setServiceInfo(info);
        return ua;
    }

    static void disconnect(UiAutomation ua) {
        if (ua == null) {
            return;
        }
        try {
            Method disconnect = UiAutomation.class.getDeclaredMethod("disconnect");
            disconnect.setAccessible(true);
            disconnect.invoke(ua);
        } catch (Throwable ignored) {
            // The process exits next, which releases the connection anyway.
        }
    }

    static void run(UiAutomation ua, String pkg, String activity, long deadline)
            throws Exception {
        int step = 0;
        AccessibilityNodeInfo root = settledRoot(ua);
        List<String> nodes = new ArrayList<String>();
        List<String[]> targets = new ArrayList<String[]>();
        walk(root, nodes, targets);
        dump(step++, packageOf(root), "start", null, nodes);
        if (!pkg.equals(packageOf(root))) {
            return;
        }

        for (int i = 0; i < targets.size() && i < MAX_CLICKS; i++) {
            if (System.currentTimeMillis() >= deadline) {
                break;
            }
            String[] target = targets.get(i);
            root = settledRoot(ua);
            AccessibilityNodeInfo node = find(root, target);
            if (node == null) {
                dump(step++, packageOf(root), "missing", target, new ArrayList<String>());
                continue;
            }
            node.performAction(AccessibilityNodeInfo.ACTION_CLICK);
            root = settledRoot(ua);
            nodes = new ArrayList<String>();
            walk(root, nodes, null);
            dump(step++, packageOf(root), "click", target, nodes);

            ua.performGlobalAction(AccessibilityService.GLOBAL_ACTION_BACK);
            root = settledRoot(ua);
            if (!pkg.equals(packageOf(root))) {
                Runtime.getRuntime()
                        .exec(new String[] {"am", "start", "-W", "-n", pkg + "/" + activity})
                        .waitFor();
            }
        }
    }

    static AccessibilityNodeInfo settledRoot(UiAutomation ua) {
        try {
            ua.waitForIdle(IDLE_MS, IDLE_TIMEOUT_MS);
        } catch (TimeoutException ignored) {
            // A screen that never idles (an animation) is read as it is.
        }
        return ua.getRootInActiveWindow();
    }

    static String packageOf(AccessibilityNodeInfo root) {
        return root == null || root.getPackageName() == null
                ? "-" : root.getPackageName().toString();
    }

    /**
     * Append one {@code NODE} line per node under {@code node}, depth first,
     * and, when {@code targets} is not null, the {@code (class, view-id,
     * bounds)} of each clickable node.
     */
    static void walk(AccessibilityNodeInfo node, List<String> lines, List<String[]> targets) {
        if (node == null) {
            return;
        }
        String[] key = keyOf(node);
        Bundle extras = node.getExtras();
        lines.add("NODE\t" + key[0] + "\t" + key[1] + "\t" + key[2]
                + "\t" + orDash(extras.getString(KEY_CLICK))
                + "\t" + orDash(extras.getString(KEY_LONG_CLICK)));
        if (targets != null && node.isClickable()) {
            targets.add(key);
        }
        for (int i = 0; i < node.getChildCount(); i++) {
            walk(node.getChild(i), lines, targets);
        }
    }

    /** The clickable node under {@code node} whose class, view-id and bounds equal {@code target}. */
    static AccessibilityNodeInfo find(AccessibilityNodeInfo node, String[] target) {
        if (node == null) {
            return null;
        }
        String[] key = keyOf(node);
        if (node.isClickable() && key[0].equals(target[0]) && key[1].equals(target[1])
                && key[2].equals(target[2])) {
            return node;
        }
        for (int i = 0; i < node.getChildCount(); i++) {
            AccessibilityNodeInfo found = find(node.getChild(i), target);
            if (found != null) {
                return found;
            }
        }
        return null;
    }

    static String[] keyOf(AccessibilityNodeInfo node) {
        Rect bounds = new Rect();
        node.getBoundsInScreen(bounds);
        CharSequence cls = node.getClassName();
        return new String[] {
            cls == null ? "-" : cls.toString(),
            orDash(node.getViewIdResourceName()),
            bounds.toShortString()
        };
    }

    static void dump(int step, String foreground, String action, String[] target,
            List<String> nodes) {
        String time = CLOCK.format(new Date());
        String[] t = target == null ? new String[] {"-", "-", "-"} : target;
        OUT.println("STEP\t" + step + "\t" + time + "\t" + foreground + "\t" + action
                + "\t" + t[0] + "\t" + t[1] + "\t" + t[2]);
        for (String line : nodes) {
            OUT.println(line);
        }
        OUT.flush();
    }

    static String orDash(String s) {
        return s == null || s.isEmpty() ? "-" : s;
    }
}
