package br.unb.cic.rvsmart.strategy;

import br.unb.cic.rvsmart.core.ScreenItem;
import br.unb.cic.rvsmart.staticdata.StaticMap;

import java.util.HashMap;
import java.util.Map;

/**
 * Generates context-appropriate input values for editable UI elements.
 *
 * Detects the input category from hint text, resource ID, and inputType,
 * then rotates through predefined values per element. Category detection
 * is case-insensitive.
 *
 * Value rotation is tracked per element using a hybrid ID:
 * resourceId when present, otherwise coordinates-based fallback.
 */
public class InputValueGenerator {

    // Android InputType constants (from android.text.InputType)
    private static final int TYPE_CLASS_NUMBER = 2;
    private static final int TYPE_CLASS_PHONE = 3;

    private static final String[] EMAIL_VALUES = {"test@test.com", "user@example.org", "a@b.c"};
    private static final String[] PASSWORD_VALUES = {"Test1234!", "password123", "Aa1!aaaa"};
    private static final String[] NUMBER_VALUES = {"42", "0", "999"};
    private static final String[] PHONE_VALUES = {"+5561999999999", "123456789"};
    private static final String[] URL_VALUES = {"https://example.com", "http://test.org"};
    private static final String[] GENERIC_VALUES = {"test", "", "a very long text string for testing", "12345"};

    // Tracks rotation index per element ID
    private final Map<String, Integer> rotationIndex = new HashMap<>();

    private StaticMap staticMap;

    public void setStaticMap(StaticMap staticMap) {
        this.staticMap = staticMap;
    }

    /**
     * Generate a context-appropriate input value for the given screen item.
     * Rotates through values on repeated calls for the same element.
     */
    public String generateInput(ScreenItem item) {
        String category = getCategory(item);
        String[] values = getValuesForCategory(category);
        String elementId = elementId(item);

        int index = rotationIndex.getOrDefault(elementId, 0);
        String value = values[index % values.length];
        rotationIndex.put(elementId, index + 1);

        return value;
    }

    /**
     * Detect the input category from hint, resourceId, and inputType.
     * Pattern matching is case-insensitive.
     *
     * @return category name: "email", "password", "number", "phone", "url", or "generic"
     */
    public String getCategory(ScreenItem item) {
        String hint = item.getHint() != null ? item.getHint().toLowerCase() : "";
        String resourceId = item.getResourceId() != null ? item.getResourceId().toLowerCase() : "";
        int inputType = item.getInputType();

        // Fallback to static inputType when runtime value is unset
        if (inputType == 0 && staticMap != null && staticMap.isLoaded() && item.getResourceId() != null) {
            int staticInputType = staticMap.getWidgetInputType(item.getResourceId());
            if (staticInputType != 0) {
                inputType = staticInputType;
            }
        }

        // Check inputType-based categories first (most reliable signal)
        if (inputType == TYPE_CLASS_NUMBER) return "number";
        if (inputType == TYPE_CLASS_PHONE) return "phone";

        // Check hint and resourceId patterns
        if (containsAny(hint, resourceId, "email", "mail")) return "email";
        if (containsAny(hint, resourceId, "password", "pass")) return "password";
        if (containsAny(hint, resourceId, "url", "website")) return "url";
        if (containsAny(hint, resourceId, "phone", "tel")) return "phone";
        if (containsAny(hint, resourceId, "number", "amount", "age")) return "number";

        return "generic";
    }

    /**
     * Hybrid element ID: uses resourceId when present, otherwise falls back
     * to coordinate-based ID. Matches UICoverageTracker.elementId() logic.
     */
    static String elementId(ScreenItem item) {
        String resourceId = item.getResourceId();
        if (resourceId != null && !resourceId.isEmpty()) {
            return "res:" + resourceId;
        }
        // Fallback to coordinates from bounds center
        if (item.getBounds() != null) {
            return "coords:" + item.getBounds().centerX() + "," + item.getBounds().centerY();
        }
        // No bounds available (test environment) — use className as last resort
        return "coords:0,0";
    }

    private String[] getValuesForCategory(String category) {
        switch (category) {
            case "email": return EMAIL_VALUES;
            case "password": return PASSWORD_VALUES;
            case "number": return NUMBER_VALUES;
            case "phone": return PHONE_VALUES;
            case "url": return URL_VALUES;
            default: return GENERIC_VALUES;
        }
    }

    /**
     * Check if either hint or resourceId contains any of the given keywords.
     */
    private boolean containsAny(String hint, String resourceId, String... keywords) {
        for (String keyword : keywords) {
            if (hint.contains(keyword) || resourceId.contains(keyword)) {
                return true;
            }
        }
        return false;
    }
}
