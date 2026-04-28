package br.unb.cic.rv.pointcut;

/**
 * Advice position emitted by JavaMOP {@code DescriptorWriter} as the JSON string
 * {@code "before" | "after" | "around"}.
 *
 * <p>The descriptor POJO holds the position as a raw {@code String} — this enum is
 * the pointcut-engine's typed view, derived on demand via {@link #fromWire(String)}.
 * Keeping the POJO string-based lets {@code descriptor-reader} stay dependency-free
 * (design D1).
 */
public enum Position {
    BEFORE, AFTER, AROUND;

    /**
     * @throws IllegalArgumentException if {@code s} is not exactly
     *     {@code "before" | "after" | "around"} (case-sensitive, matches
     *     the JavaMOP emission).
     */
    public static Position fromWire(String s) {
        if (s == null) {
            throw new IllegalArgumentException("position is null");
        }
        switch (s) {
            case "before": return BEFORE;
            case "after":  return AFTER;
            case "around": return AROUND;
            default: throw new IllegalArgumentException("unknown advice position: " + s);
        }
    }
}
