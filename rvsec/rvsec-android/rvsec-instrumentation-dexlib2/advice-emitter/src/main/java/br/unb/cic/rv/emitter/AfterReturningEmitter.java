package br.unb.cic.rv.emitter;

import com.android.tools.smali.dexlib2.builder.BuilderInstruction;

import java.util.List;

/**
 * Emits the instructions for {@code after() returning(<type> r)} advice.
 *
 * <p>Binds the matched call's return value into the bound advice parameter,
 * then invokes the monitor event method. The bind is typically realized by a
 * {@code move-result(-object|-wide)} placed directly after the matched
 * invoke; this emitter's {@link EmitPlan} carries the subsequent invoke.
 *
 * <p>When the advice signature would cause the bound return register to
 * alias the receiver or another argument at the matched site, the
 * {@code dex-mutator} falls through to {@code WrapperEmitter} which generates
 * a static wrapper in {@code mop.MonitorWrappers} that breaks the alias; that
 * choice is owned by the mutator's register allocator, not by this emitter.
 */
public final class AfterReturningEmitter implements AdviceEmitter {

    @Override
    public EmitPlan emit(EmitContext ctx) {
        // The return-value capture (move-result/-object/-wide) is emitted by
        // InstructionInjector — it knows the matched invoke's return shape.
        // This emitter contributes only the monitor invoke, which the injector
        // places immediately after the return capture.
        List<BuilderInstruction> ins = MonitorInvokeBuilder.buildInvoke(ctx);
        RegisterRequest req = ctx.advice.getReturning() != null
                && !ctx.advice.getReturning().isEmpty()
                ? RegisterRequest.scratch(1)
                : RegisterRequest.NONE;
        return EmitPlan.of(ins, InsertionPoint.AFTER, req);
    }

    @Override
    public String kind() { return "after-returning"; }
}
