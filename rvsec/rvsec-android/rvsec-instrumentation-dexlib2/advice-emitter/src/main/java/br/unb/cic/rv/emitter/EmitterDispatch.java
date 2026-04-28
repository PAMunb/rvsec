package br.unb.cic.rv.emitter;

import br.unb.cic.rv.descriptor.AdviceDescriptor;

import java.util.Objects;

/**
 * Selects the right {@link AdviceEmitter} for a given
 * {@link AdviceDescriptor}, following the dispatch table declared in
 * {@code design.md §API Design}:
 *
 * <pre>
 *   position  returning  throwing  other                → emitter
 *   before    null       null      —                    → BeforeEmitter
 *   after     null       null      —                    → AfterEmitter
 *   after     not null   null      —                    → AfterReturningEmitter
 *   after     null       not null  —                    → AfterThrowingEmitter
 *   any       any        any       staticinitialization → StaticInitializationEmitter
 *   any       any        any       if(...) in expression → IfGuardEmitter wraps the
 *                                                        emitter chosen above
 * </pre>
 *
 * <p>The {@code around} position is explicitly unsupported (listed in
 * {@code LIMITATIONS.md}); dispatch throws
 * {@link UnsupportedOperationException} on encounter so the caller can surface
 * a clean {@code UnsupportedAspectConstructError} upstream.
 */
public final class EmitterDispatch {

    private final BeforeEmitter before;
    private final AfterEmitter after;
    private final AfterReturningEmitter afterReturning;
    private final AfterThrowingEmitter afterThrowing;
    private final StaticInitializationEmitter staticInit;
    private final IfGuardEmitter ifGuard;
    private final ThisJoinPointEmitter thisJoinPoint;

    public EmitterDispatch() {
        this(new BeforeEmitter(), new AfterEmitter(), new AfterReturningEmitter(),
                new AfterThrowingEmitter(), new StaticInitializationEmitter(),
                new IfGuardEmitter(), new ThisJoinPointEmitter());
    }

    public EmitterDispatch(BeforeEmitter b, AfterEmitter a, AfterReturningEmitter ar,
                           AfterThrowingEmitter at, StaticInitializationEmitter si,
                           IfGuardEmitter ig, ThisJoinPointEmitter tjp) {
        this.before = Objects.requireNonNull(b);
        this.after = Objects.requireNonNull(a);
        this.afterReturning = Objects.requireNonNull(ar);
        this.afterThrowing = Objects.requireNonNull(at);
        this.staticInit = Objects.requireNonNull(si);
        this.ifGuard = Objects.requireNonNull(ig);
        this.thisJoinPoint = Objects.requireNonNull(tjp);
    }

    public AdviceEmitter select(AdviceDescriptor advice) {
        String expr = advice.getExpression() != null ? advice.getExpression() : "";
        if (expr.contains("staticinitialization(")) {
            return staticInit;
        }
        if (advice.isAround()) {
            throw new UnsupportedOperationException(
                    "around advice is out of scope for gh52 (see LIMITATIONS.md); "
                            + "advice name: " + advice.getName());
        }
        AdviceEmitter base = selectByPosition(advice);
        // thisJoinPoint injects the signature constant; the base emitter folds it
        // into its EmitPlan via ThisJoinPointEmitter.augment(ctx, plan) at
        // injection time (see BeforeEmitter/AfterEmitter bodies).
        if (expr.contains("if(")) {
            // if-guard wraps the base emission: the base plan runs only when the
            // guard evaluates truthy. IfGuardEmitter delegates to the base.
            return ifGuard.wrapping(base);
        }
        return base;
    }

    private AdviceEmitter selectByPosition(AdviceDescriptor advice) {
        String position = advice.getPosition();
        if ("before".equals(position)) return before;
        if ("after".equals(position)) {
            boolean hasReturning = advice.getReturning() != null
                    && !advice.getReturning().isEmpty();
            boolean hasThrowing = advice.getThrowing() != null
                    && !advice.getThrowing().isEmpty();
            if (hasReturning && !hasThrowing) return afterReturning;
            if (hasThrowing && !hasReturning) return afterThrowing;
            if (hasReturning && hasThrowing) {
                throw new IllegalStateException(
                        "advice declares both returning and throwing: " + advice.getName());
            }
            return after;
        }
        throw new UnsupportedOperationException("unknown advice position: " + position);
    }

    public ThisJoinPointEmitter thisJoinPointEmitter() {
        return thisJoinPoint;
    }
}
