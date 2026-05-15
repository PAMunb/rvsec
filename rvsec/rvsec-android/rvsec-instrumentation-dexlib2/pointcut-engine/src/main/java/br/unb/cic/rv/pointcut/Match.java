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

    /**
     * Argument-name → register index for {@code args(...)} bindings.
     *
     * <p>Keys follow the conventions:
     * <ul>
     *   <li>{@code "arg00".."argNN"} — positional user parameters at
     *       {@code regs[baseOffset + i]} (where {@code baseOffset == 1} for
     *       constructor and virtual instance invokes, {@code 0} for static).
     *   <li>{@code "$return"} — synthetic key; destination register of the
     *       trailing {@code move-result*} instruction following a non-constructor
     *       invoke. Absent for constructors (no {@code move-result*} after
     *       {@code <init>}) and for invokes whose return is discarded by the
     *       caller.
     * </ul>
     */
    public final Map<String, Integer> argBindings;
    /** Register index for {@code target(...)} binding, or {@code -1} when absent. */
    public final int targetRegister;
    /**
     * {@code true} when this match was produced for a constructor invoke
     * ({@code invoke-direct} to an {@code <init>} method) where both the
     * descriptor predicate ({@code CallPC.isConstructor()}) and the method-name
     * predicate ({@code MethodReference.name.equals("<init>")}) agree. The
     * two-predicate gate is defence in depth — {@code invoke-direct} is also
     * used for private non-constructor methods and {@code super.<init>}
     * chaining outside the advice contract, and treating those as constructors
     * would capture an unintended receiver.
     *
     * <p>Consumed by {@code MonitorInvokeBuilder.resolveReturningRegister} to
     * choose between {@code targetRegister} (constructor) and
     * {@code argBindings.get("$return")} (non-constructor).
     */
    public final boolean isConstructor;
    /** The matched PCD as a debugging/audit reference. */
    public final PointcutExpression matchedAgainst;

    public Match(Map<String, Integer> argBindings, int targetRegister,
                 PointcutExpression matchedAgainst, boolean isConstructor) {
        this.argBindings = argBindings == null
                ? Collections.emptyMap()
                : Collections.unmodifiableMap(new LinkedHashMap<>(argBindings));
        this.targetRegister = targetRegister;
        this.matchedAgainst = matchedAgainst;
        this.isConstructor = isConstructor;
    }

    public static Match empty(PointcutExpression pe) {
        return new Match(Collections.emptyMap(), -1, pe, false);
    }

    @Override
    public String toString() {
        return "Match{args=" + argBindings + ", target=" + targetRegister
                + ", isConstructor=" + isConstructor + "}";
    }
}
