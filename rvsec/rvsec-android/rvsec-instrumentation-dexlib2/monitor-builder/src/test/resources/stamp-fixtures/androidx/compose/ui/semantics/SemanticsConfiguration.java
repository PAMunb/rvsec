package androidx.compose.ui.semantics;

import java.util.HashMap;
import java.util.Map;

/** The members of a semantics configuration the stamp helper calls by reflection. */
public final class SemanticsConfiguration {
    private final Map<SemanticsPropertyKey, Object> props = new HashMap<SemanticsPropertyKey, Object>();

    public boolean contains(SemanticsPropertyKey key) {
        return props.containsKey(key);
    }

    public Object get(SemanticsPropertyKey key) {
        return props.get(key);
    }

    public void set(SemanticsPropertyKey key, Object value) {
        props.put(key, value);
    }
}
