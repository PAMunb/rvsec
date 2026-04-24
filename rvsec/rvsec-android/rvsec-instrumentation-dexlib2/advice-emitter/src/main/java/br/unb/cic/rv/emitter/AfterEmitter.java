package br.unb.cic.rv.emitter;

import com.android.tools.smali.dexlib2.builder.BuilderInstruction;

import java.util.List;

/**
 * Emits the instructions for plain {@code after(...)} advice (no returning,
 * no throwing binding): an {@code invoke-static} to the monitor event method,
 * inserted immediately after the matched call site. Runs on both normal
 * completion and exception propagation of the matched call — semantically
 * identical to {@code finally}.
 */
public final class AfterEmitter implements AdviceEmitter {

    @Override
    public EmitPlan emit(EmitContext ctx) {
        List<BuilderInstruction> ins = MonitorInvokeBuilder.buildInvoke(ctx);
        return EmitPlan.of(ins, InsertionPoint.AFTER);
    }

    @Override
    public String kind() { return "after"; }
}
