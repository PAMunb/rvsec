package br.unb.cic.rvsmart.device;

import android.content.ComponentName;
import android.util.Log;

import java.lang.reflect.Method;
import java.util.List;

/**
 * App lifecycle management via IActivityManager reflection.
 *
 * Provides three capabilities:
 *   1. getCurrentActivity(): IActivityManager.getRunningTasks(1) → topActivity ComponentName
 *   2. forceStop(package):   IActivityManager.forceStopPackage(package, userId)
 *   3. startApp(package):    IActivityManager.startActivity() with launcher intent
 *
 * All methods use Shell UID 2000 which has the necessary permissions.
 * Restart sequence (forceStop + startApp) takes ~50-100ms total (INV-RSM-06).
 */
public class AppController {

    private static final String TAG = "RVSMART";

    private final Object activityManager;  // IActivityManager
    private Method getTasksMethod;
    private Method forceStopPackageMethod;

    public AppController(Object activityManager) {
        this.activityManager = activityManager;
        resolveReflectionTargets();
    }

    /**
     * Resolve reflection targets for IActivityManager methods.
     * Called once at construction; failures are fatal (Go/No-Go gate).
     */
    private void resolveReflectionTargets() {
        try {
            Class<?> amClass = activityManager.getClass();

            // API 29: getTasks(int maxNum) → List<ActivityManager.RunningTaskInfo>
            // (getRunningTasks is deprecated and removed from IActivityManager AIDL)
            getTasksMethod = amClass.getMethod("getTasks", int.class);

            // forceStopPackage(String packageName, int userId)
            forceStopPackageMethod = amClass.getMethod("forceStopPackage", String.class, int.class);

        } catch (Exception e) {
            throw new RuntimeException("Failed to resolve IActivityManager methods: " + e.getMessage(), e);
        }
    }

    /**
     * Get the ComponentName of the currently visible Activity.
     * Uses IActivityManager.getRunningTasks(1) to get the top task.
     *
     * @return ComponentName of the top Activity, or null if unavailable
     */
    public ComponentName getCurrentActivity() {
        try {
            @SuppressWarnings("unchecked")
            List<?> tasks = (List<?>) getTasksMethod.invoke(activityManager, 1);
            if (tasks == null || tasks.isEmpty()) {
                return null;
            }
            Object taskInfo = tasks.get(0);
            // RunningTaskInfo.topActivity — try field access, then getDeclaredField on superclass
            return getTopActivity(taskInfo);
        } catch (Exception e) {
            Log.w(TAG, "Failed to get current activity: " + e.getMessage());
            return null;
        }
    }

    /**
     * Extract topActivity ComponentName from a RunningTaskInfo object.
     * The field may be declared in the class itself or in a superclass (TaskInfo).
     */
    private ComponentName getTopActivity(Object taskInfo) {
        // Walk the class hierarchy looking for topActivity
        Class<?> clazz = taskInfo.getClass();
        while (clazz != null) {
            try {
                java.lang.reflect.Field field = clazz.getDeclaredField("topActivity");
                field.setAccessible(true);
                return (ComponentName) field.get(taskInfo);
            } catch (NoSuchFieldException e) {
                clazz = clazz.getSuperclass();
            } catch (Exception e) {
                Log.w(TAG, "Error accessing topActivity: " + e.getMessage());
                return null;
            }
        }
        Log.w(TAG, "topActivity field not found in " + taskInfo.getClass().getName());
        return null;
    }

    /**
     * Get the short class name of the currently visible Activity.
     * e.g., "com.example.app/.MainActivity" → "MainActivity"
     *
     * @return Simple activity class name, or "unknown" if unavailable
     */
    public String getCurrentActivityName() {
        ComponentName cn = getCurrentActivity();
        if (cn == null) return "unknown";
        return cn.getShortClassName().replace(".", "");
    }

    /**
     * Check if the target app process is currently running.
     * Used to distinguish native crash (process gone) from ANR (process alive).
     */
    public boolean isAppRunning(String packageName) {
        try {
            @SuppressWarnings("unchecked")
            List<?> tasks = (List<?>) getTasksMethod.invoke(activityManager, 20);
            if (tasks == null) return false;
            for (Object taskInfo : tasks) {
                ComponentName cn = getTopActivity(taskInfo);
                if (cn != null && packageName.equals(cn.getPackageName())) {
                    return true;
                }
            }
            return false;
        } catch (Exception e) {
            Log.w(TAG, "Failed to check running tasks: " + e.getMessage());
            return false;
        }
    }

    /**
     * Force-stop the target app. Takes ~50ms.
     * userId 0 = primary user (standard for emulator).
     */
    public void forceStop(String packageName) {
        try {
            forceStopPackageMethod.invoke(activityManager, packageName, 0);
            Log.d(TAG, "Force-stopped: " + packageName);
        } catch (Exception e) {
            Log.e(TAG, "Failed to force-stop " + packageName + ": " + e.getMessage());
        }
    }

    /**
     * Start the target app's launcher activity.
     * Uses `monkey -p <package> 1` which reliably launches the app's default activity
     * without needing to know the component name. Works from app_process context.
     * Takes ~200-400ms.
     */
    public void startApp(String packageName) {
        try {
            ProcessBuilder pb = new ProcessBuilder(
                    "monkey", "-p", packageName,
                    "-c", "android.intent.category.LAUNCHER", "1"
            );
            pb.redirectErrorStream(true);
            Process proc = pb.start();
            int exitCode = proc.waitFor();
            if (exitCode == 0) {
                Log.d(TAG, "Started app: " + packageName);
            } else {
                Log.w(TAG, "monkey start returned exit code " + exitCode + " for " + packageName);
            }
        } catch (Exception e) {
            Log.e(TAG, "Failed to start " + packageName + ": " + e.getMessage());
        }
    }

    /**
     * Restart the target app: forceStop + startApp.
     * Total time: ~50-100ms (vs ~1-2s for adb shell commands).
     */
    public void restartApp(String packageName) {
        forceStop(packageName);
        try {
            // Brief pause for process cleanup
            Thread.sleep(50);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        startApp(packageName);
    }
}
