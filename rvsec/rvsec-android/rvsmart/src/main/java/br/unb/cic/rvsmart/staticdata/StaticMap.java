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
            parseReachability(json);
            parseWindows(json);
            parseTransitions(json);
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
}
