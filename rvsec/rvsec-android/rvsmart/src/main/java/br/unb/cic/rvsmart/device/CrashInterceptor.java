package br.unb.cic.rvsmart.device;

import android.util.Log;

import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;

/**
 * Detects app crashes via ActivityController callback registration (INV-RSM-06).
 *
 * Registers an IActivityController proxy with IActivityManager.setActivityController().
 * When the target app crashes (Java exception), Android calls appCrashed() on the callback.
 * The interceptor marks the last action as crash-causing and signals the agent to restart.
 *
 * This provides instant crash detection (~0ms) compared to the Python agent's
 * indirect detection via UIAutomator timeout (1-2 iterations).
 *
 * INV-RSM-06: appCrashed() MUST immediately mark the preceding action as crash-causing
 * and initiate app restart. No additional actions before restart completes.
 */
public class CrashInterceptor implements InvocationHandler {

    private static final String TAG = "RVSMART";

    private final String targetPackage;
    private volatile boolean crashDetected;
    private volatile String crashProcessName;
    private volatile String crashStackTrace;

    public CrashInterceptor(String targetPackage) {
        this.targetPackage = targetPackage;
    }

    /**
     * Register this interceptor with IActivityManager.setActivityController().
     *
     * Creates a dynamic proxy implementing IActivityController interface and registers
     * it via reflection. The proxy intercepts appCrashed(), appEarlyNotResponding(),
     * and appNotResponding() callbacks.
     */
    public void register(Object activityManager) {
        try {
            // Load the IActivityController interface
            Class<?> controllerInterface = Class.forName("android.app.IActivityController");

            // Create a dynamic proxy implementing IActivityController
            Object proxy = Proxy.newProxyInstance(
                    controllerInterface.getClassLoader(),
                    new Class<?>[]{controllerInterface},
                    this
            );

            // IActivityManager.setActivityController(IActivityController controller, boolean imAMonkey)
            Method setController = activityManager.getClass().getMethod(
                    "setActivityController", controllerInterface, boolean.class);
            setController.invoke(activityManager, proxy, true);

            Log.i(TAG, "CrashInterceptor registered");
        } catch (Exception e) {
            Log.w(TAG, "Failed to register CrashInterceptor: " + e.getMessage()
                    + ". Crash detection will use fallback (null root check).");
        }
    }

    /**
     * Dynamic proxy invocation handler for IActivityController.
     *
     * IActivityController methods:
     *   boolean activityStarting(Intent intent, String pkg) → return true (allow)
     *   boolean activityResuming(String pkg) → return true (allow)
     *   boolean appCrashed(String processName, int pid, String shortMsg, String longMsg,
     *                       long timeMillis, String stackTrace) → return false (don't show dialog)
     *   int appEarlyNotResponding(String processName, int pid, String annotation) → return 0
     *   int appNotResponding(String processName, int pid, String processStats) → return -1 (kill)
     *   int systemNotResponding(String msg) → return -1
     */
    @Override
    public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
        String name = method.getName();

        switch (name) {
            case "appCrashed":
                return handleAppCrashed(args);

            case "appEarlyNotResponding":
                return handleAppEarlyNotResponding(args);

            case "appNotResponding":
                return handleAppNotResponding(args);

            case "activityStarting":
            case "activityResuming":
                return true;  // Allow all activities

            case "systemNotResponding":
                Log.w(TAG, "System not responding: " + (args != null && args.length > 0 ? args[0] : "unknown"));
                return -1;  // Kill

            // Object methods (toString, hashCode, equals)
            case "toString":
                return "CrashInterceptor[" + targetPackage + "]";
            case "hashCode":
                return System.identityHashCode(proxy);
            case "equals":
                return proxy == args[0];

            default:
                // Unknown method — return safe default
                Class<?> returnType = method.getReturnType();
                if (returnType == boolean.class) return true;
                if (returnType == int.class) return 0;
                return null;
        }
    }

    /**
     * Handle appCrashed callback.
     * Args: processName, pid, shortMsg, longMsg, timeMillis, stackTrace
     *
     * Returns false to suppress the crash dialog (we handle recovery ourselves).
     */
    private boolean handleAppCrashed(Object[] args) {
        if (args == null || args.length < 6) return false;

        String processName = (String) args[0];
        String shortMsg = args.length > 2 ? (String) args[2] : "unknown";
        String stackTrace = args.length > 5 ? (String) args[5] : "";

        if (processName != null && processName.contains(targetPackage)) {
            crashDetected = true;
            crashProcessName = processName;
            crashStackTrace = stackTrace;
            Log.w(TAG, "CRASH detected in " + processName + ": " + shortMsg);
            if (stackTrace != null && !stackTrace.isEmpty()) {
                // Log first 500 chars of stack trace
                Log.w(TAG, "Stack: " + stackTrace.substring(0, Math.min(500, stackTrace.length())));
            }
        } else {
            Log.d(TAG, "Crash in non-target process: " + processName);
        }

        return false;  // Don't show crash dialog
    }

    /**
     * Handle appEarlyNotResponding callback.
     * Returns 0 to continue waiting.
     */
    private int handleAppEarlyNotResponding(Object[] args) {
        if (args != null && args.length > 0) {
            String processName = (String) args[0];
            if (processName != null && processName.contains(targetPackage)) {
                Log.d(TAG, "Early ANR warning for " + processName);
            }
        }
        return 0;  // Continue waiting
    }

    /**
     * Handle appNotResponding callback.
     * Returns -1 to kill the ANR process (we'll restart it ourselves).
     */
    private int handleAppNotResponding(Object[] args) {
        if (args != null && args.length > 0) {
            String processName = (String) args[0];
            if (processName != null && processName.contains(targetPackage)) {
                crashDetected = true;
                crashProcessName = processName;
                crashStackTrace = "ANR";
                Log.w(TAG, "ANR detected in " + processName);
            }
        }
        return -1;  // Kill the process
    }

    /**
     * Check if a crash has been detected since last reset.
     * Thread-safe: called from the agent loop, set from the system callback thread.
     */
    public boolean hasCrash() {
        return crashDetected;
    }

    /**
     * Consume the crash state and return crash info.
     * Resets the crash flag so subsequent calls return null until a new crash occurs.
     *
     * @return CrashInfo with process name and stack trace, or null if no crash pending
     */
    public CrashInfo consumeCrash() {
        if (!crashDetected) return null;
        CrashInfo info = new CrashInfo(crashProcessName, crashStackTrace);
        crashDetected = false;
        crashProcessName = null;
        crashStackTrace = null;
        return info;
    }

    /**
     * Crash information container.
     */
    public static class CrashInfo {
        public final String processName;
        public final String stackTrace;

        CrashInfo(String processName, String stackTrace) {
            this.processName = processName;
            this.stackTrace = stackTrace;
        }

        public boolean isAnr() {
            return "ANR".equals(stackTrace);
        }
    }
}
