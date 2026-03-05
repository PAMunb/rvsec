package br.unb.cic.rvsmart.core;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.TreeMap;

/**
 * Represents the current UI state: items + activity name + structural hash.
 *
 * The structural hash (INV-RSM-03) MUST produce identical output to the Python agent's
 * compute_screen_hash_from_description(). Algorithm:
 *   1. Extract 9 structural attributes per item (class, resource_id, package,
 *      clickable, scrollable, checkable, enabled, long_clickable, editable)
 *   2. Sort items by (resource_id || "zzz", class)
 *   3. Create canonical JSON with sorted keys and compact separators
 *   4. SHA-256 of UTF-8 bytes, truncated to 12 hex characters
 */
public class ScreenState {

    private static final Gson GSON = new GsonBuilder().create();

    private final List<ScreenItem> items;
    private final String activity;
    private final String hash;

    public ScreenState(List<ScreenItem> items, String activity) {
        this.items = Collections.unmodifiableList(new ArrayList<>(items));
        this.activity = activity;
        this.hash = computeHash(items, activity);
    }

    public List<ScreenItem> getItems() {
        return items;
    }

    public String getActivity() {
        return activity;
    }

    public String getHash() {
        return hash;
    }

    /**
     * Compute structural hash matching the Python agent's algorithm.
     *
     * Uses TreeMap at every nesting level to guarantee sorted keys in Gson output.
     * Python uses json.dumps(sort_keys=True, separators=(",", ":")).
     * Gson serializing TreeMap produces the same ordered compact JSON.
     */
    static String computeHash(List<ScreenItem> items, String activity) {
        // Build structural representation for each item
        List<TreeMap<String, Object>> structuralItems = new ArrayList<>(items.size());

        for (ScreenItem item : items) {
            TreeMap<String, Object> view = new TreeMap<>();
            view.put("checkable", item.isCheckable());
            view.put("class", item.getClassName());
            view.put("clickable", item.isClickable());
            view.put("editable", item.isEditable());
            view.put("enabled", item.isEnabled());
            view.put("long_clickable", item.isLongClickable());
            view.put("package", item.getPackageName());
            view.put("resource_id", item.getResourceId() != null ? item.getResourceId() : "");
            view.put("scrollable", item.isScrollable());
            structuralItems.add(view);
        }

        // Sort by (resource_id || "zzz", class)
        Collections.sort(structuralItems, new Comparator<TreeMap<String, Object>>() {
            @Override
            public int compare(TreeMap<String, Object> a, TreeMap<String, Object> b) {
                String ridA = (String) a.get("resource_id");
                String ridB = (String) b.get("resource_id");
                String sortKeyA = ridA.isEmpty() ? "zzz" : ridA;
                String sortKeyB = ridB.isEmpty() ? "zzz" : ridB;
                int cmp = sortKeyA.compareTo(sortKeyB);
                if (cmp != 0) return cmp;
                return ((String) a.get("class")).compareTo((String) b.get("class"));
            }
        });

        // Build top-level TreeMap for sorted keys
        TreeMap<String, Object> canonical = new TreeMap<>();
        canonical.put("activity", activity);
        canonical.put("items", structuralItems);

        // Gson with TreeMap produces compact JSON with sorted keys
        String json = GSON.toJson(canonical);

        // SHA-256 → first 12 hex chars
        return sha256Hex(json).substring(0, 12);
    }

    private static String sha256Hex(String input) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] digest = md.digest(input.getBytes(java.nio.charset.StandardCharsets.UTF_8));
            StringBuilder hex = new StringBuilder(64);
            for (byte b : digest) {
                hex.append(String.format("%02x", b & 0xff));
            }
            return hex.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("SHA-256 not available", e);
        }
    }
}
