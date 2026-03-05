package br.unb.cic.rvsmart.staticdata;

import android.util.Log;

import com.google.gson.Gson;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;

import java.io.FileReader;
import java.util.HashMap;
import java.util.Map;

/**
 * Loads static analysis data from a JSON file produced by RvsecAnalysisClient.
 * The JSON has 3 sections: reachability, windows, transitions.
 * Only reachability is parsed (used by MopScorer).
 *
 * Graceful degradation: if the file is missing, null, or unparseable,
 * isLoaded=false and all query methods return false.
 */
public class StaticMap {

    private static final String TAG = "StaticMap";

    private boolean isLoaded;
    private Map<String, Boolean> directlyReachesMop;
    private Map<String, Boolean> reachesMop;

    public StaticMap(String jsonPath) {
        if (jsonPath == null || jsonPath.isEmpty()) {
            this.isLoaded = false;
            return;
        }
        try {
            JsonObject json = new Gson().fromJson(new FileReader(jsonPath), JsonObject.class);
            parseReachability(json);
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
}
