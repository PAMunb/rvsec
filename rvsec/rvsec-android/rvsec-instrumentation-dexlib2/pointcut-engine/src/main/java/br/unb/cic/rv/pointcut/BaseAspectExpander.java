package br.unb.cic.rv.pointcut;

import java.util.List;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Expands the {@code BaseAspect.notwithin()} named reference into a concrete pointcut: an AND-chain
 * of {@link NotWithinPC} matchers, one per entry of {@code AspectDescriptor.baseAspectExclusions}
 * (the canonical twelve package patterns {@code sun..*}, {@code java..*}, … pre-expanded by
 * {@code DescriptorWriter.defaultBaseAspectExclusions()}). The composed expression matches a class
 * iff it lies outside <em>every</em> excluded package.
 *
 * <p>The input is already pre-expanded, so this is a pure structural fold (round-8 A-decision):
 * no package-list resolution happens here. Returns the single {@link NotWithinPC} for a one-entry
 * list (no degenerate AND-of-one).
 */
public final class BaseAspectExpander {

    private BaseAspectExpander() { }

    /**
     * §4.PERF.P2.2: pure-function memo keyed by the exclusions list. The list is effectively
     * immutable per descriptor (the canonical pre-expanded package patterns), so the 23-node
     * {@link NotWithinPC} AND-tree is built at most once per distinct exclusion list instead of
     * on every {@code matchNamedRef} → {@code expand} call. The map key copies the list defensively
     * so a later mutation of the caller's list cannot corrupt a cached entry; the result tree is
     * immutable (records).
     */
    private static final ConcurrentHashMap<List<String>, PointcutExpression> CACHE =
            new ConcurrentHashMap<>();

    /**
     * @param exclusions the non-empty list of package patterns; the empty case is handled by the
     *                   caller ({@link LegacyDescriptorException}) before reaching here.
     * @return a {@link NotWithinPC} (N=1) or a left-folded {@link CombinedPC} AND-chain (N≥2).
     */
    public static PointcutExpression expand(List<String> exclusions) {
        if (exclusions == null || exclusions.isEmpty()) {
            throw new IllegalArgumentException(
                    "BaseAspectExpander.expand requires a non-empty exclusions list "
                            + "(the empty case is a LegacyDescriptorException at the call site)");
        }
        return CACHE.computeIfAbsent(List.copyOf(exclusions), BaseAspectExpander::build);
    }

    private static PointcutExpression build(List<String> exclusions) {
        PointcutExpression acc = new NotWithinPC(exclusions.get(0).trim());
        for (int i = 1; i < exclusions.size(); i++) {
            acc = new CombinedPC(CombinedPC.Op.AND, acc, new NotWithinPC(exclusions.get(i).trim()));
        }
        return acc;
    }
}
