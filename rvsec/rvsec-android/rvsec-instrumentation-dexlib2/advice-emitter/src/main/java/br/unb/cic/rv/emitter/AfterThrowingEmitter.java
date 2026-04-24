package br.unb.cic.rv.emitter;

import com.android.tools.smali.dexlib2.builder.BuilderInstruction;

import java.util.List;

/**
 * Emits the instructions for {@code after() throwing(<type> t)} advice.
 *
 * <p>Wraps the matched instruction in a {@code try}/{@code catch} whose
 * handler invokes the monitor event method with the caught exception bound
 * to the advice parameter, then re-throws ({@code throw} instruction) to
 * preserve semantics.
 *
 * <p>The plan's {@link EmitPlan.TryCatchSpec} carries the catch-type
 * descriptor (either the declared throwing parameter type, or
 * {@code Ljava/lang/Throwable;} when none declared — MOP convention). The
 * {@code dex-mutator} executor installs the try range + handler label at
 * injection time.
 */
public final class AfterThrowingEmitter implements AdviceEmitter {

    @Override
    public EmitPlan emit(EmitContext ctx) {
        List<BuilderInstruction> handler = MonitorInvokeBuilder.buildInvoke(ctx);

        // Catch type: when throwing() binds a specific type, narrow to that;
        // otherwise install a catch-all on Throwable (MOP convention).
        EmitPlan.TryCatchSpec spec;
        if (ctx.advice.getThrowing() != null && !ctx.advice.getThrowing().isEmpty()) {
            String bound = ctx.advice.getThrowing().get(0).getType();
            String desc = ctx.typeResolver.toDescriptor(bound);
            spec = EmitPlan.TryCatchSpec.specific(desc);
        } else {
            spec = EmitPlan.TryCatchSpec.catchAll();
        }

        // Needs 1 scratch to hold the caught exception (move-exception vX)
        // before the monitor invoke and subsequent re-throw.
        return EmitPlan.tryCatch(handler, RegisterRequest.scratch(1), spec);
    }

    @Override
    public String kind() { return "after-throwing"; }
}
