package br.unb.cic.rv.emitter;

import br.unb.cic.rv.descriptor.MonitorCallDescriptor;
import br.unb.cic.rv.descriptor.ParameterDescriptor;

import com.android.tools.smali.dexlib2.builder.BuilderInstruction;

import java.util.ArrayList;
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

        // Position of the throwing(<name>)-bound exception in each monitor
        // invoke's operand list, one entry per invoke and in the same order.
        // MonitorInvokeBuilder mapped that name to a placeholder register (it
        // cannot know the caught-exception register until the executor
        // allocates one); the dex-mutator executor rewrites exactly that
        // operand slot to the move-exception register.
        List<Integer> throwingOperandIndices = throwingOperandIndices(ctx);

        // Catch type: when throwing() binds a specific type, narrow to that;
        // otherwise install a catch-all on Throwable (MOP convention).
        EmitPlan.TryCatchSpec spec;
        if (ctx.advice.getThrowing() != null && !ctx.advice.getThrowing().isEmpty()) {
            String bound = ctx.advice.getThrowing().get(0).getType();
            String desc = ctx.typeResolver.toDescriptor(bound);
            spec = EmitPlan.TryCatchSpec.specific(desc, throwingOperandIndices);
        } else {
            spec = EmitPlan.TryCatchSpec.catchAll(throwingOperandIndices);
        }

        // Needs 1 scratch to hold the caught exception (move-exception vX)
        // before the monitor invoke and subsequent re-throw.
        return EmitPlan.tryCatch(handler, RegisterRequest.scratch(1), spec);
    }

    /**
     * Operand index of the throwing-bound exception in each monitor invoke, in
     * emission order — one entry per invoke {@link MonitorInvokeBuilder}
     * produces.
     *
     * <p>The monitor event is invoked with arguments in {@code monitorCall.args}
     * order (the same order {@link MonitorInvokeBuilder} emits the operand list).
     * The throwing parameter name is the advice's {@code throwing(<name>)}
     * declaration; its index in that args list is the operand slot the executor
     * must rewrite to the {@code move-exception} register. An entry is
     * {@code -1} when there is no throwing parameter or it is absent from that
     * call's args list (catch-any without an exception argument).
     *
     * <p>The index is computed per call rather than once for the advice because
     * two calls fused into one advice can declare different argument lists, so
     * the exception can sit in a different slot in each. Applying one index to
     * every invoke would rewrite an unrelated operand of the others — a
     * type-mismatched register the verifier rejects, which is a worse failure
     * than the truncation this repair removes.
     */
    private static List<Integer> throwingOperandIndices(EmitContext ctx) {
        List<MonitorCallDescriptor> calls = ctx.monitorCalls();
        String name = null;
        if (ctx.advice.getThrowing() != null && !ctx.advice.getThrowing().isEmpty()) {
            ParameterDescriptor throwingParam = ctx.advice.getThrowing().get(0);
            name = throwingParam.getName();
        }

        List<Integer> indices = new ArrayList<>(calls.size());
        for (MonitorCallDescriptor call : calls) {
            indices.add(operandIndex(name, call.getArgs()));
        }
        return indices;
    }

    /** Index of {@code name} in {@code args}, or {@code -1}. */
    private static int operandIndex(String name, List<String> args) {
        if (name == null || args == null) return -1;
        for (int i = 0; i < args.size(); i++) {
            if (name.equals(args.get(i))) return i;
        }
        return -1;
    }

    @Override
    public String kind() { return "after-throwing"; }
}
