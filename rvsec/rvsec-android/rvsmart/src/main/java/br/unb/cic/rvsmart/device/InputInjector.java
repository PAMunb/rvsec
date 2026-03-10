package br.unb.cic.rvsmart.device;

import android.hardware.input.InputManager;
import android.os.SystemClock;
import android.util.Log;
import android.view.InputDevice;
import android.view.InputEvent;
import android.view.KeyEvent;
import android.view.MotionEvent;

import java.lang.reflect.Method;

/**
 * Injects touch and key events via InputManager.injectInputEvent() reflection.
 *
 * All action types flow through injectInputEvent() with INJECT_INPUT_EVENT_MODE_ASYNC (D3).
 * The source field on actions is metadata only — injection path is identical (INV-RSM-08).
 *
 * Supported actions:
 *   CLICK:      MotionEvent DOWN+UP at (x,y)
 *   LONG_CLICK: MotionEvent DOWN, 1s delay, UP at (x,y)
 *   SCROLL:     MotionEvent DOWN+MOVE+UP sequence
 *   SWIPE:      MotionEvent DOWN+MOVE+UP sequence
 *   BACK:       KeyEvent KEYCODE_BACK DOWN+UP
 *   KEY_EVENT:  KeyEvent with custom keycode DOWN+UP
 *   SET_TEXT:    Focus click + clear + key events per character
 */
public class InputInjector {

    private static final String TAG = "RVSMART";

    // InputManager.INJECT_INPUT_EVENT_MODE_ASYNC = 0
    private static final int INJECT_INPUT_EVENT_MODE_ASYNC = 0;
    private static final long LONG_CLICK_DURATION_MS = 1000;
    private static final int SWIPE_STEPS = 10;
    private static final long SWIPE_STEP_DELAY_MS = 20;

    private final InputManager inputManager;
    private final Method injectMethod;

    public InputInjector(InputManager inputManager, Method injectMethod) {
        this.inputManager = inputManager;
        this.injectMethod = injectMethod;
    }

    /**
     * Inject a click (ACTION_DOWN + ACTION_UP) at device pixel coordinates.
     * Target latency: <3ms.
     */
    public boolean click(int x, int y) {
        long now = SystemClock.uptimeMillis();
        MotionEvent down = MotionEvent.obtain(now, now, MotionEvent.ACTION_DOWN, x, y, 0);
        MotionEvent up = MotionEvent.obtain(now, now, MotionEvent.ACTION_UP, x, y, 0);
        try {
            return inject(down) && inject(up);
        } finally {
            down.recycle();
            up.recycle();
        }
    }

    /**
     * Inject a long click (ACTION_DOWN, 1s hold, ACTION_UP) at device pixel coordinates.
     */
    public boolean longClick(int x, int y) {
        long now = SystemClock.uptimeMillis();
        MotionEvent down = MotionEvent.obtain(now, now, MotionEvent.ACTION_DOWN, x, y, 0);
        try {
            if (!inject(down)) {
                return false;
            }
        } finally {
            down.recycle();
        }

        try {
            Thread.sleep(LONG_CLICK_DURATION_MS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }

        long upTime = SystemClock.uptimeMillis();
        MotionEvent up = MotionEvent.obtain(now, upTime, MotionEvent.ACTION_UP, x, y, 0);
        try {
            return inject(up);
        } finally {
            up.recycle();
        }
    }

    /**
     * Inject a swipe from (startX, startY) to (endX, endY).
     * Uses linear interpolation over SWIPE_STEPS steps.
     */
    public boolean swipe(int startX, int startY, int endX, int endY) {
        long now = SystemClock.uptimeMillis();

        MotionEvent down = MotionEvent.obtain(now, now, MotionEvent.ACTION_DOWN, startX, startY, 0);
        try {
            if (!inject(down)) return false;
        } finally {
            down.recycle();
        }

        for (int i = 1; i <= SWIPE_STEPS; i++) {
            float fraction = (float) i / SWIPE_STEPS;
            int moveX = startX + (int) ((endX - startX) * fraction);
            int moveY = startY + (int) ((endY - startY) * fraction);
            long moveTime = SystemClock.uptimeMillis();
            MotionEvent move = MotionEvent.obtain(now, moveTime, MotionEvent.ACTION_MOVE, moveX, moveY, 0);
            try {
                if (!inject(move)) return false;
            } finally {
                move.recycle();
            }
            try {
                Thread.sleep(SWIPE_STEP_DELAY_MS);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return false;
            }
        }

        long upTime = SystemClock.uptimeMillis();
        MotionEvent up = MotionEvent.obtain(now, upTime, MotionEvent.ACTION_UP, endX, endY, 0);
        try {
            return inject(up);
        } finally {
            up.recycle();
        }
    }

    /**
     * Inject a scroll gesture. Same as swipe but semantically different
     * (scroll uses vertical displacement from a starting point).
     */
    public boolean scroll(int x, int y, int deltaY) {
        return swipe(x, y, x, y + deltaY);
    }

    /**
     * Inject a BACK key press (ACTION_DOWN + ACTION_UP).
     * Target latency: <1ms.
     */
    public boolean pressBack() {
        return pressKey(KeyEvent.KEYCODE_BACK);
    }

    /**
     * Inject a key press with the given keycode (ACTION_DOWN + ACTION_UP).
     */
    public boolean pressKey(int keyCode) {
        long now = SystemClock.uptimeMillis();
        KeyEvent down = new KeyEvent(now, now, KeyEvent.ACTION_DOWN, keyCode, 0);
        KeyEvent up = new KeyEvent(now, now, KeyEvent.ACTION_UP, keyCode, 0);
        try {
            return inject(down) && inject(up);
        } finally {
            // KeyEvent does not have recycle() like MotionEvent
        }
    }

    /**
     * Inject text by sending key events for each character.
     * Used for SET_TEXT action type: focus field first (click), then type.
     */
    public boolean setText(int x, int y, String text) {
        // Focus the field
        if (!click(x, y)) {
            return false;
        }

        // Small delay for focus to take effect
        try {
            Thread.sleep(50);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return false;
        }

        // Clear existing text: select all (Ctrl+A) then delete
        pressKey(KeyEvent.KEYCODE_MOVE_HOME);
        long now = SystemClock.uptimeMillis();
        KeyEvent shiftDown = new KeyEvent(now, now, KeyEvent.ACTION_DOWN, KeyEvent.KEYCODE_SHIFT_LEFT, 0);
        inject(shiftDown);
        pressKey(KeyEvent.KEYCODE_MOVE_END);
        KeyEvent shiftUp = new KeyEvent(now, now, KeyEvent.ACTION_UP, KeyEvent.KEYCODE_SHIFT_LEFT, 0);
        inject(shiftUp);
        pressKey(KeyEvent.KEYCODE_DEL);

        // Type each character
        for (char c : text.toCharArray()) {
            KeyEvent[] events = charToKeyEvents(c);
            if (events != null) {
                for (KeyEvent event : events) {
                    inject(event);
                }
            }
        }

        return true;
    }

    /**
     * Low-level injection via InputManager.injectInputEvent() reflection.
     */
    private boolean inject(InputEvent event) {
        // MotionEvents must have SOURCE_TOUCHSCREEN for the WindowManager to dispatch
        // them to the correct window. Without this, events are silently ignored.
        if (event instanceof MotionEvent) {
            ((MotionEvent) event).setSource(InputDevice.SOURCE_TOUCHSCREEN);
        }
        try {
            return (Boolean) injectMethod.invoke(inputManager, event, INJECT_INPUT_EVENT_MODE_ASYNC);
        } catch (Exception e) {
            Log.w(TAG, "Failed to inject event: " + e.getMessage());
            return false;
        }
    }

    /**
     * Convert a character to KeyEvent sequence.
     * Uses KeyCharacterMap.getEvents() for proper character-to-keycode mapping.
     */
    private KeyEvent[] charToKeyEvents(char c) {
        try {
            android.view.KeyCharacterMap kcm = android.view.KeyCharacterMap.load(
                    android.view.KeyCharacterMap.VIRTUAL_KEYBOARD);
            return kcm.getEvents(new char[]{c});
        } catch (Exception e) {
            Log.w(TAG, "Cannot map character '" + c + "' to key events");
            return null;
        }
    }
}
