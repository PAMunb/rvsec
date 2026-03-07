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
import java.util.List;
import java.util.Map;

/**
 * Loads static analysis data from a JSON file produced by RvsecAnalysisClient.
 * The JSON has 3 sections: reachability, windows, transitions.
 *
 * Reachability keys are method signatures like "pkg.ClassName.methodName(params)".
 * Activity-based lookup groups these by class name to determine if any method
 * on the current activity reaches a monitored operation.
 *
 * Transitions map activity names to lists of target activities (WTG edges).
 *
 * Graceful degradation: if the file is missing, null, or unparseable,
 * isLoaded=false and all query methods return false/empty.
 */
public class StaticMap {

    private static final String TAG = "StaticMap";

    private boolean isLoaded;
    private Map<String, Boolean> directlyReachesMop;
    private Map<String, Boolean> reachesMop;
    private Map<String, List<String>> transitions;

    // Code package for activity name matching against JSON keys
    private String codePackage;

    public StaticMap(String jsonPath) {
        if (jsonPath == null || jsonPath.isEmpty()) {
            this.isLoaded = false;
            return;
        }
        try {
            JsonObject json = new Gson().fromJson(new FileReader(jsonPath), JsonObject.class);
            parseReachability(json);
            parseTransitions(json);
            this.isLoaded = true;
        } catch (Exception e) {
            this.isLoaded = false;
            Log.i(TAG, "Graceful degradation, no static analysis: " + e.getMessage());
        }
    }

    private void parseReachability(JsonObject json) {
        JsonObject reach = json.getAsJsonObject("reachability");
        if (reach == null) {
            return;
        }

        JsonObject directObj = reach.getAsJsonObject("directly_reaches_mop");
        if (directObj != null) {
            directlyReachesMop = new HashMap<>();
            for (Map.Entry<String, JsonElement> entry : directObj.entrySet()) {
                directlyReachesMop.put(entry.getKey(), entry.getValue().getAsBoolean());
            }
        }

        JsonObject transitiveObj = reach.getAsJsonObject("reaches_mop");
        if (transitiveObj != null) {
            reachesMop = new HashMap<>();
            for (Map.Entry<String, JsonElement> entry : transitiveObj.entrySet()) {
                reachesMop.put(entry.getKey(), entry.getValue().getAsBoolean());
            }
        }
    }

    private void parseTransitions(JsonObject json) {
        JsonObject transObj = json.getAsJsonObject("transitions");
        if (transObj == null) {
            return;
        }
        transitions = new HashMap<>();
        for (Map.Entry<String, JsonElement> entry : transObj.entrySet()) {
            List<String> targets = new ArrayList<>();
            JsonElement val = entry.getValue();
            if (val.isJsonArray()) {
                JsonArray arr = val.getAsJsonArray();
                for (int i = 0; i < arr.size(); i++) {
                    targets.add(arr.get(i).getAsString());
                }
            }
            transitions.put(entry.getKey(), targets);
        }
    }

    public void setCodePackage(String codePackage) {
        this.codePackage = codePackage;
    }

    public boolean isLoaded() { return isLoaded; }

    /** @return true if the action signature directly reaches a monitored operation. */
    public boolean hasDirectMop(String actionSignature) {
        if (!isLoaded || directlyReachesMop == null) return false;
        return directlyReachesMop.getOrDefault(actionSignature, false);
    }

    /** @return true if the action signature transitively reaches a monitored operation. */
    public boolean hasMop(String actionSignature) {
        if (!isLoaded || reachesMop == null) return false;
        return reachesMop.getOrDefault(actionSignature, false);
    }

    /**
     * Check if the given activity has any method that directly reaches a MOP.
     * Matches by checking if any reachability key starts with the qualified activity name.
     */
    public boolean activityHasDirectMop(String activityName) {
        if (!isLoaded || directlyReachesMop == null) return false;
        String prefix = qualifiedPrefix(activityName);
        for (Map.Entry<String, Boolean> entry : directlyReachesMop.entrySet()) {
            if (entry.getKey().startsWith(prefix) && entry.getValue()) {
                return true;
            }
        }
        return false;
    }

    /**
     * Check if the given activity has any method that transitively reaches a MOP.
     */
    public boolean activityHasMop(String activityName) {
        if (!isLoaded || reachesMop == null) return false;
        String prefix = qualifiedPrefix(activityName);
        for (Map.Entry<String, Boolean> entry : reachesMop.entrySet()) {
            if (entry.getKey().startsWith(prefix) && entry.getValue()) {
                return true;
            }
        }
        return false;
    }

    /**
     * Get WTG transitions from the given activity.
     * Returns empty list if no transitions are available.
     */
    public List<String> getTransitions(String activityName) {
        if (!isLoaded || transitions == null) return Collections.emptyList();
        // Try qualified name first
        String qualified = (codePackage != null ? codePackage + "." : "") + activityName;
        List<String> result = transitions.get(qualified);
        if (result != null) return result;
        // Try simple name
        result = transitions.get(activityName);
        return result != null ? result : Collections.emptyList();
    }

    private String qualifiedPrefix(String activityName) {
        return (codePackage != null ? codePackage + "." : "") + activityName + ".";
    }
}
