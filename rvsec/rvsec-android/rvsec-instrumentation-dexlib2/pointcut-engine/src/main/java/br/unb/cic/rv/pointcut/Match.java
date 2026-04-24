package br.unb.cic.rv.pointcut;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Result of a successful {@link PointcutMatcher#match} call.
 *
 * <p>Carries the dynamic-binding information the weaver needs to emit the
 * monitor invocation: which register holds the bound argument for each
 * {@code args(name)} entry, and which register holds the receiver for
 * {@code target(name)}.
 */
public final class Match {

    /** Argument-name → register index for {@code args(...)} bindings. */
    public final Map<String, Integer> argBindings;
    /** Register index for {@code target(...)} binding, or {@code -1} when absent. */
    public final int targetRegister;
    /** The matched PCD as a debugging/audit reference. */
    public final PointcutExpression matchedAgainst;

    public Match(Map<String, Integer> argBindings, int targetRegister,
                 PointcutExpression matchedAgainst) {
        this.argBindings = argBindings == null
                ? Collections.emptyMap()
                : Collections.unmodifiableMap(new LinkedHashMap<>(argBindings));
        this.targetRegister = targetRegister;
        this.matchedAgainst = matchedAgainst;
    }

    public static Match empty(PointcutExpression pe) {
        return new Match(Collections.emptyMap(), -1, pe);
    }

    @Override
    public String toString() {
        return "Match{args=" + argBindings + ", target=" + targetRegister + "}";
    }
}
