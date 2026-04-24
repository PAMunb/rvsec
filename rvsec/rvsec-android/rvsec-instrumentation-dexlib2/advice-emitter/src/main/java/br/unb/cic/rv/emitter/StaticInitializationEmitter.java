package br.unb.cic.rv.emitter;

import com.android.tools.smali.dexlib2.builder.BuilderInstruction;

import java.util.List;

/**
 * Emits the instructions for {@code staticinitialization(<TypePattern>)}
 * advice.
 *
 * <p>Matches only on a class' {@code <clinit>}. When the class has no
 * {@code <clinit>}, the {@code dex-mutator} executor synthesizes one
 * (empty body + {@code return-void}) before inserting the monitor invoke at
 * method entry; when a {@code <clinit>} exists, the invoke is prepended.
 *
 * <p>The presence/synthesis decision is the executor's responsibility
 * because it owns the {@code ClassDef} mutation API; this emitter only
 * expresses "run this invoke at the very start of {@code <clinit>}" via
 * {@link InsertionPoint#METHOD_ENTRY}.
 */
public final class StaticInitializationEmitter implements AdviceEmitter {

    @Override
    public EmitPlan emit(EmitContext ctx) {
        List<BuilderInstruction> ins = MonitorInvokeBuilder.buildInvoke(ctx);
        return EmitPlan.of(ins, InsertionPoint.METHOD_ENTRY);
    }

    @Override
    public String kind() { return "staticinitialization"; }
}
