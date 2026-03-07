package br.unb.cic.rvsmart.core;

/**
 * Represents a user interaction action to be executed on the device.
 *
 * Action types map to InputInjector methods. The signature() method produces
 * a stable identifier for tracking in the DynamicStateGraph: "type@x,y" for
 * most actions, "SET_TEXT:text@x,y" for text input.
 *
 * The source field ("algorithm" or "llm") is metadata only — both sources
 * follow the identical execution and learning code path (INV-RSM-08).
 */
public class Action {

    public enum Type {
        CLICK,
        LONG_CLICK,
        SET_TEXT,
        SCROLL,
        SWIPE,
        BACK,
        KEY_EVENT,
        RESTART
    }

    private final Type type;
    private final int x;
    private final int y;
    private final String text;        // For SET_TEXT only, null otherwise
    private final String source;      // "algorithm" or "llm" — metadata only (INV-RSM-08)
    private final String widgetClass; // Simple class name for scorer lookup
    private final String packageName; // Package of the widget (e.g., "com.android.systemui")

    public Action(Type type, int x, int y, String text, String source, String widgetClass, String packageName) {
        this.type = type;
        this.x = x;
        this.y = y;
        this.text = text;
        this.source = source;
        this.widgetClass = widgetClass;
        this.packageName = packageName;
    }

    public Action(Type type, int x, int y, String text, String source, String widgetClass) {
        this(type, x, y, text, source, widgetClass, null);
    }

    public Action(Type type, int x, int y, String source, String widgetClass) {
        this(type, x, y, null, source, widgetClass, null);
    }

    /**
     * Create a BACK action (no coordinates needed).
     */
    public static Action back(String source) {
        return new Action(Type.BACK, 0, 0, null, source, "");
    }

    /**
     * Create a RESTART action (no coordinates needed).
     */
    public static Action restart(String source) {
        return new Action(Type.RESTART, 0, 0, null, source, "");
    }

    /**
     * Stable action identifier for graph tracking.
     * Format: "type@x,y" or "SET_TEXT:text@x,y"
     */
    public String signature() {
        String typeName = type.name().toLowerCase();
        if ((type == Type.SET_TEXT || type == Type.SCROLL) && text != null) {
            return typeName + ":" + text + "@" + x + "," + y;
        }
        return typeName + "@" + x + "," + y;
    }

    public Type getType() { return type; }
    public int getX() { return x; }
    public int getY() { return y; }
    public String getText() { return text; }
    public String getSource() { return source; }
    public String getWidgetClass() { return widgetClass; }
    public String getPackageName() { return packageName; }

    @Override
    public String toString() {
        return signature() + " [" + source + "]";
    }
}
