package br.unb.cic.rvsmart.device;

import android.app.UiAutomation;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.hardware.input.InputManager;
import android.os.HandlerThread;
import android.os.IBinder;
import android.os.Looper;
import android.util.Log;

import java.lang.reflect.Constructor;
import java.lang.reflect.Method;

/**
 * Connects to Android system services via ServiceManager reflection.
 *
 * Four connections are established:
 *   - ActivityManagerService: app lifecycle (getTasks, forceStopPackage)
 *   - WindowManagerService: reserved for Phase 2
 *   - InputManager: event injection (injectInputEvent)
 *   - UiAutomation: accessibility tree access (getRootInActiveWindow)
 *
 * UiAutomation bootstrap:
 *   HandlerThread + UiAutomation(looper, UiAutomationConnection) + connect().
 *
 * All services are accessed under Shell UID 2000 which has INJECT_EVENTS permission.
 * Reflection targets are validated against API 29 only.
 */
public class DeviceController {

    private static final String TAG = "RVSMART";

    private Object activityManager;     // IActivityManager
    private Object windowManager;       // IWindowManager
    private InputManager inputManager;
    private Method injectInputEventMethod;
    private UiAutomation uiAutomation;
    private HandlerThread handlerThread;

    /**
     * Connect to all system services and UiAutomation.
     * Throws RuntimeException if any connection fails (Go/No-Go gate).
     */
    public void connect() {
        try {
            activityManager = getServiceInterface("activity",
                    "android.app.IActivityManager$Stub");
            Log.i(TAG, "Connected to ActivityManagerService");

            windowManager = getServiceInterface("window",
                    "android.view.IWindowManager$Stub");
            Log.i(TAG, "Connected to WindowManagerService");

            inputManager = getInputManager();
            injectInputEventMethod = inputManager.getClass().getMethod(
                    "injectInputEvent", android.view.InputEvent.class, int.class);
            Log.i(TAG, "Connected to InputManager");

            connectUiAutomation();
            Log.i(TAG, "Connected to UiAutomation");

        } catch (Exception e) {
            throw new RuntimeException("Bootstrap failed: " + e.getMessage(), e);
        }
    }

    /**
     * Bootstrap UiAutomation for accessibility tree access.
     * Creates a HandlerThread, instantiates UiAutomation with UiAutomationConnection,
     * and calls connect(). This gives us getRootInActiveWindow() for UI tree capture.
     *
     * UiAutomationConnection and the UiAutomation(Looper, IUiAutomationConnection) constructor
     * are hidden APIs not in the public android.jar stubs — accessed via reflection.
     * At runtime on device, ART provides these classes.
     */
    private void connectUiAutomation() throws Exception {
        handlerThread = new HandlerThread("rvsmart-uiautomation");
        handlerThread.start();

        // UiAutomationConnection implements IUiAutomationConnection (hidden)
        Class<?> connClass = Class.forName("android.app.UiAutomationConnection");
        Object connection = connClass.newInstance();

        // UiAutomation(Looper looper, IUiAutomationConnection connection) — hidden constructor
        Class<?> iConnClass = Class.forName("android.app.IUiAutomationConnection");
        Constructor<?> uiAutoCtor = UiAutomation.class.getConstructor(Looper.class, iConnClass);
        uiAutomation = (UiAutomation) uiAutoCtor.newInstance(handlerThread.getLooper(), connection);

        // connect() is a hidden API — use reflection
        Method connectMethod = UiAutomation.class.getMethod("connect");
        connectMethod.invoke(uiAutomation);

        // Exclude decorative/non-important views from the accessibility tree
        AccessibilityServiceInfo info = uiAutomation.getServiceInfo();
        info.flags &= ~AccessibilityServiceInfo.FLAG_INCLUDE_NOT_IMPORTANT_VIEWS;
        uiAutomation.setServiceInfo(info);
    }

    /**
     * Get a system service binder and convert to its AIDL interface via Stub.asInterface().
     */
    private Object getServiceInterface(String serviceName, String stubClassName)
            throws Exception {
        // ServiceManager.getService(name) returns IBinder
        Class<?> smClass = Class.forName("android.os.ServiceManager");
        Method getService = smClass.getMethod("getService", String.class);
        IBinder binder = (IBinder) getService.invoke(null, serviceName);

        if (binder == null) {
            throw new RuntimeException("ServiceManager returned null for '" + serviceName + "'");
        }

        // Stub.asInterface(binder) returns the typed interface
        Class<?> stubClass = Class.forName(stubClassName);
        Method asInterface = stubClass.getMethod("asInterface", IBinder.class);
        Object service = asInterface.invoke(null, binder);

        if (service == null) {
            throw new RuntimeException("Stub.asInterface returned null for '" + serviceName + "'");
        }

        return service;
    }

    /**
     * Get InputManager instance via InputManager.getInstance().
     */
    private InputManager getInputManager() throws Exception {
        Method getInstance = InputManager.class.getMethod("getInstance");
        InputManager im = (InputManager) getInstance.invoke(null);
        if (im == null) {
            throw new RuntimeException("InputManager.getInstance() returned null");
        }
        return im;
    }

    public Object getActivityManager() {
        return activityManager;
    }

    public Object getWindowManager() {
        return windowManager;
    }

    public InputManager getInputManager_() {
        return inputManager;
    }

    public Method getInjectInputEventMethod() {
        return injectInputEventMethod;
    }

    public UiAutomation getUiAutomation() {
        return uiAutomation;
    }

    /**
     * Disconnect UiAutomation and stop the handler thread.
     * Should be called on shutdown to release accessibility resources.
     */
    public void disconnect() {
        if (uiAutomation != null) {
            try {
                Method disconnectMethod = UiAutomation.class.getMethod("disconnect");
                disconnectMethod.invoke(uiAutomation);
            } catch (Exception e) {
                Log.w(TAG, "Error disconnecting UiAutomation: " + e.getMessage());
            }
        }
        if (handlerThread != null) {
            handlerThread.quit();
        }
    }
}
