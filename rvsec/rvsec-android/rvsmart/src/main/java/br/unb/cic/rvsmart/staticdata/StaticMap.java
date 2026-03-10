package br.unb.cic.rvsmart.staticdata;

import android.util.Log;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;

import java.io.FileReader;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Loads static analysis data from a JSON file produced by RvsecAnalysisClient.
 * The JSON has 3 top-level JsonArray sections: reachability, windows, transitions.
 *
 * Reachability: array of class objects with className and methods array.
 * Each method has signature, reachable, reachesMop, directlyReachesMop.
 *
 * Windows: array of window objects with id and name (fully qualified activity).
 * Used to cross-reference transition sourceId/targetId with activity names.
 *
 * Transitions: array of {sourceId, targetId, events} referencing window IDs.
 *
 * Activity names are matched by simple class name (last segment after dot),
 * which handles both fully-qualified names from JSON and trace-format names
 * from the agent (e.g., "uiactivitiesSplashActivity" -> "SplashActivity").
 * Android convention: package segments are lowercase, class names start uppercase.
 *
 * Graceful degradation: if the file is missing, null, or unparseable,
 * isLoaded=false and all query methods return false/empty.
 */
public class StaticMap {

    private static final String TAG = "StaticMap";

    private boolean isLoaded;

    // Simple class name -> true if any method in that class directly reaches MOP
    private Map<String, Boolean> activityDirectMop;
    // Simple class name -> true if any method in that class reaches MOP (transitive)
    private Map<String, Boolean> activityTransitiveMop;
    // Simple class name -> list of target simple class names (WTG edges)
    private Map<String, List<String>> activityTransitions;
    // Window ID -> simple class name (for transition cross-reference)
    private Map<Integer, String> windowIdToActivity;
    // Activity -> resourceId -> WidgetStaticData
    private Map<String, Map<String, WidgetStaticData>> activityWidgets;
    // Activity -> widgetResourceId -> target activity (from WTG transitions)
    private Map<String, Map<String, String>> widgetTransitions;
    // Method signature -> directlyReachesMop
    private Map<String, Boolean> methodDirectMop;
    // Method signature -> reachesMop
    private Map<String, Boolean> methodTransitiveMop;

    private String codePackage;

    public StaticMap(String jsonPath) {
        if (jsonPath == null || jsonPath.isEmpty()) {
            this.isLoaded = false;
            return;
        }
        try {
            JsonObject json = new Gson().fromJson(new FileReader(jsonPath), JsonObject.class);
            activityDirectMop = new HashMap<>();
            activityTransitiveMop = new HashMap<>();
            activityTransitions = new HashMap<>();
            windowIdToActivity = new HashMap<>();
            activityWidgets = new HashMap<>();
            widgetTransitions = new HashMap<>();
            methodDirectMop = new HashMap<>();
            methodTransitiveMop = new HashMap<>();
            parseReachability(json);
            parseWindows(json);
            parseTransitions(json);
            parseWidgets(json);
            parseWidgetTransitions(json);
            this.isLoaded = true;
        } catch (Exception e) {
            this.isLoaded = false;
            Log.i(TAG, "Graceful degradation, no static analysis: " + e.getMessage());
        }
    }

    /**
     * Parse reachability from JsonArray format produced by RvsecAnalysisClient.
     * Each element: {className, isActivity, methods: [{signature, reachable, reachesMop, directlyReachesMop}]}
     */
    private void parseReachability(JsonObject json) {
        JsonArray reach = json.getAsJsonArray("reachability");
        if (reach == null) return;

        for (JsonElement elem : reach) {
            JsonObject classObj = elem.getAsJsonObject();
            String className = classObj.get("className").getAsString();
            String simpleName = extractSimpleClassName(className);

            JsonArray methods = classObj.getAsJsonArray("methods");
            if (methods == null) continue;

            for (JsonElement methodElem : methods) {
                JsonObject method = methodElem.getAsJsonObject();
                if (method.has("directlyReachesMop")
                        && method.get("directlyReachesMop").getAsBoolean()) {
                    activityDirectMop.put(simpleName, true);
                }
                if (method.has("reachesMop")
                        && method.get("reachesMop").getAsBoolean()) {
                    activityTransitiveMop.put(simpleName, true);
                }
                // Store per-method MOP data for widget-level cross-referencing
                String methodSig = method.has("signature")
                        ? method.get("signature").getAsString() : "";
                if (!methodSig.isEmpty()) {
                    if (method.has("directlyReachesMop")
                            && method.get("directlyReachesMop").getAsBoolean()) {
                        methodDirectMop.put(methodSig, true);
                    }
                    if (method.has("reachesMop")
                            && method.get("reachesMop").getAsBoolean()) {
                        methodTransitiveMop.put(methodSig, true);
                    }
                }
            }
        }
    }

    /**
     * Parse windows from JsonArray to build windowId -> activity name map.
     * Each element: {id, name (fully qualified), type, isMain}
     */
    private void parseWindows(JsonObject json) {
        JsonArray windows = json.getAsJsonArray("windows");
        if (windows == null) return;

        for (JsonElement elem : windows) {
            JsonObject window = elem.getAsJsonObject();
            int id = window.get("id").getAsInt();
            String name = window.get("name").getAsString();
            windowIdToActivity.put(id, extractSimpleClassName(name));
        }
    }

    /**
     * Parse transitions from JsonArray using window ID cross-reference.
     * Each element: {sourceId, targetId, events: [{type, widgetClass}]}
     * Self-transitions (sourceId == targetId) are skipped.
     */
    private void parseTransitions(JsonObject json) {
        JsonArray trans = json.getAsJsonArray("transitions");
        if (trans == null) return;

        for (JsonElement elem : trans) {
            JsonObject transition = elem.getAsJsonObject();
            int sourceId = transition.get("sourceId").getAsInt();
            int targetId = transition.get("targetId").getAsInt();

            // Skip self-transitions (implicit_power_event, etc.)
            if (sourceId == targetId) continue;

            String sourceActivity = windowIdToActivity.get(sourceId);
            String targetActivity = windowIdToActivity.get(targetId);
            if (sourceActivity == null || targetActivity == null) continue;

            activityTransitions
                    .computeIfAbsent(sourceActivity, k -> new ArrayList<>())
                    .add(targetActivity);
        }

        // Deduplicate target lists
        for (Map.Entry<String, List<String>> entry : activityTransitions.entrySet()) {
            List<String> unique = new ArrayList<>(new HashSet<>(entry.getValue()));
            entry.setValue(unique);
        }
    }

    public void setCodePackage(String codePackage) {
        this.codePackage = codePackage;
    }

    public boolean isLoaded() { return isLoaded; }

    /**
     * Check if the given activity has any method that directly reaches a MOP.
     * Activity name can be fully-qualified, simple, or trace-format.
     */
    public boolean activityHasDirectMop(String activityName) {
        if (!isLoaded || activityDirectMop == null) return false;
        return activityDirectMop.getOrDefault(extractSimpleClassName(activityName), false);
    }

    /**
     * Check if the given activity has any method that transitively reaches a MOP.
     */
    public boolean activityHasMop(String activityName) {
        if (!isLoaded || activityTransitiveMop == null) return false;
        return activityTransitiveMop.getOrDefault(extractSimpleClassName(activityName), false);
    }

    /**
     * Get WTG transitions from the given activity.
     * Returns simple class names of target activities.
     */
    public List<String> getTransitions(String activityName) {
        if (!isLoaded || activityTransitions == null) return Collections.emptyList();
        return activityTransitions.getOrDefault(
                extractSimpleClassName(activityName), Collections.emptyList());
    }

    /**
     * Extract simple class name from various formats:
     * - Fully qualified: "com.example.ui.MainActivity" -> "MainActivity"
     * - Trace format (dots stripped): "uiactivitiesMainActivity" -> "MainActivity"
     * - Already simple: "MainActivity" -> "MainActivity"
     *
     * Android convention: package segments are lowercase, class names start uppercase.
     * The simple class name starts at the last dot (if qualified) or at the first
     * uppercase character (if trace-format with no dots).
     */
    static String extractSimpleClassName(String name) {
        if (name == null || name.isEmpty()) return name;

        // Fully qualified: extract after last dot
        int lastDot = name.lastIndexOf('.');
        if (lastDot >= 0) {
            return name.substring(lastDot + 1);
        }

        // Trace format (no dots): find first uppercase letter (class name boundary)
        for (int i = 0; i < name.length(); i++) {
            if (Character.isUpperCase(name.charAt(i))) {
                return name.substring(i);
            }
        }

        return name;
    }

    // -------------------------------------------------------------------------
    // Widget-level static analysis parsing and queries
    // -------------------------------------------------------------------------

    /**
     * Per-widget static analysis data extracted from the JSON.
     */
    public static class WidgetStaticData {
        public final String resourceId;
        public final String type;
        public final boolean directMop;
        public final boolean transitiveMop;
        public final int inputType;
        public final String hint;
        public final String targetActivity;  // from transitions

        public WidgetStaticData(String resourceId, String type, boolean directMop,
                                boolean transitiveMop, int inputType, String hint,
                                String targetActivity) {
            this.resourceId = resourceId;
            this.type = type;
            this.directMop = directMop;
            this.transitiveMop = transitiveMop;
            this.inputType = inputType;
            this.hint = hint;
            this.targetActivity = targetActivity;
        }
    }

    /**
     * Parse widget-level data from windows[].widgets[].
     * Cross-references widget listeners with reachability data to determine per-widget MOP flags.
     */
    private void parseWidgets(JsonObject json) {
        JsonArray windows = json.getAsJsonArray("windows");
        if (windows == null) return;

        for (JsonElement winElem : windows) {
            JsonObject window = winElem.getAsJsonObject();
            String windowName = window.has("name") ? window.get("name").getAsString() : "";
            String activityName = extractSimpleClassName(windowName);

            JsonArray widgets = window.getAsJsonArray("widgets");
            if (widgets == null) continue;

            Map<String, WidgetStaticData> widgetMap = activityWidgets
                    .computeIfAbsent(activityName, k -> new HashMap<>());

            for (JsonElement wElem : widgets) {
                JsonObject widget = wElem.getAsJsonObject();
                String idName = widget.has("idName") ? widget.get("idName").getAsString() : null;
                if (idName == null || idName.isEmpty()) continue;

                String type = widget.has("type") ? widget.get("type").getAsString() : "";
                int inputType = widget.has("inputType") ? widget.get("inputType").getAsInt() : 0;
                String hint = widget.has("hint") ? widget.get("hint").getAsString() : null;

                boolean directMop = false;
                boolean transitiveMop = false;

                JsonArray listeners = widget.getAsJsonArray("listeners");
                if (listeners != null) {
                    for (JsonElement lElem : listeners) {
                        JsonObject listener = lElem.getAsJsonObject();
                        String handler = listener.has("handler")
                                ? listener.get("handler").getAsString() : "";
                        if (!handler.isEmpty()) {
                            if (isMethodDirectMop(handler)) directMop = true;
                            if (isMethodTransitiveMop(handler)) transitiveMop = true;
                        }
                    }
                }

                widgetMap.put(idName, new WidgetStaticData(
                        idName, type, directMop, transitiveMop, inputType, hint, null));
            }
        }
    }

    /**
     * Parse widget-level transition data from transitions[].events[].
     * Maps widgetId to target activity for widget-specific WTG targeting.
     */
    private void parseWidgetTransitions(JsonObject json) {
        JsonArray trans = json.getAsJsonArray("transitions");
        if (trans == null) return;

        for (JsonElement elem : trans) {
            JsonObject transition = elem.getAsJsonObject();
            int sourceId = transition.get("sourceId").getAsInt();
            int targetId = transition.get("targetId").getAsInt();
            if (sourceId == targetId) continue;

            String sourceActivity = windowIdToActivity.get(sourceId);
            String targetActivity = windowIdToActivity.get(targetId);
            if (sourceActivity == null || targetActivity == null) continue;

            JsonArray events = transition.getAsJsonArray("events");
            if (events == null) continue;

            Map<String, String> transMap = widgetTransitions
                    .computeIfAbsent(sourceActivity, k -> new HashMap<>());

            for (JsonElement evElem : events) {
                JsonObject event = evElem.getAsJsonObject();
                String widgetId = event.has("widgetId")
                        ? event.get("widgetId").getAsString() : null;
                if (widgetId != null && !widgetId.isEmpty()) {
                    transMap.put(widgetId, targetActivity);
                }
            }
        }
    }

    private boolean isMethodDirectMop(String handler) {
        if (methodDirectMop == null) return false;
        for (Map.Entry<String, Boolean> entry : methodDirectMop.entrySet()) {
            if (entry.getKey().contains(handler) && entry.getValue()) return true;
        }
        return false;
    }

    private boolean isMethodTransitiveMop(String handler) {
        if (methodTransitiveMop == null) return false;
        for (Map.Entry<String, Boolean> entry : methodTransitiveMop.entrySet()) {
            if (entry.getKey().contains(handler) && entry.getValue()) return true;
        }
        return false;
    }

    /**
     * Get widget-level static data for a specific widget on a given activity.
     * Returns null if no data available.
     */
    public WidgetStaticData getWidgetData(String activityName, String resourceId) {
        if (!isLoaded || activityWidgets == null) return null;
        Map<String, WidgetStaticData> widgets = activityWidgets.get(
                extractSimpleClassName(activityName));
        if (widgets == null) return null;
        return widgets.get(resourceId);
    }

    /**
     * Get the target activity for a widget-level WTG transition.
     * Returns null if no transition data available.
     */
    public String getWidgetTransitionTarget(String activityName, String widgetResourceId) {
        if (!isLoaded || widgetTransitions == null) return null;
        Map<String, String> transMap = widgetTransitions.get(
                extractSimpleClassName(activityName));
        if (transMap == null) return null;
        return transMap.get(widgetResourceId);
    }

    /**
     * Look up static inputType for a widget by resourceId across all activities.
     * Returns 0 if not found.
     */
    public int getWidgetInputType(String resourceId) {
        if (!isLoaded || activityWidgets == null || resourceId == null) return 0;
        for (Map<String, WidgetStaticData> widgets : activityWidgets.values()) {
            WidgetStaticData data = widgets.get(resourceId);
            if (data != null && data.inputType != 0) return data.inputType;
        }
        return 0;
    }
}
