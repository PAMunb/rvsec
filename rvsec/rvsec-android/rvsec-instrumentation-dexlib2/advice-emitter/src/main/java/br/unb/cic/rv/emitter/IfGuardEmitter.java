package br.unb.cic.rv.emitter;

import java.util.Objects;

/**
 * Wraps another {@link AdviceEmitter} with a runtime guard derived from an
 * {@code if(<expr>)} pointcut clause.
 *
 * <p>Emission shape: the underlying emitter produces its invoke-plan; this
 * wrapper prepends an {@code if-eqz vGuard, :skip} where {@code vGuard} is
 * a scratch register whose value is the result of evaluating the guard
 * expression. The guard expression is evaluated by a compiler-generated
 * static helper method that the {@code advice-emitter} stages during
 * monitor-builder time (task 7.x); here we only allocate the scratch
 * register and mark where the skip-label lands (the executor places the
 * label after the monitor invoke).
 */
public final class IfGuardEmitter implements AdviceEmitter {

    private final AdviceEmitter delegate;

    public IfGuardEmitter() { this.delegate = null; }
    private IfGuardEmitter(AdviceEmitter d) { this.delegate = d; }

    public IfGuardEmitter wrapping(AdviceEmitter base) {
        return new IfGuardEmitter(Objects.requireNonNull(base));
    }

    @Override
    public EmitPlan emit(EmitContext ctx) {
        if (delegate == null) {
            throw new IllegalStateException(
                    "IfGuardEmitter must be used via wrapping(base); raw emit() is unsupported");
        }
        EmitPlan inner = delegate.emit(ctx);
        // Allocate 1 extra scratch for the guard result; the executor synthesizes
        // the invoke-static to the guard helper + if-eqz around the inner plan.
        RegisterRequest req = new RegisterRequest(
                inner.registers().scratchCount() + 1,
                inner.registers().needsWidePair(),
                inner.registers().mustBeLowRange());
        return new EmitPlan(inner.toInsert(), inner.insertionPoint(), req, inner.tryCatchSpec());
    }

    @Override
    public String kind() { return "if-guarded[" + (delegate == null ? "-" : delegate.kind()) + "]"; }
}
