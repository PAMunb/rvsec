package br.unb.cic.rv.emitter;

import com.android.tools.smali.dexlib2.builder.BuilderInstruction;

import java.util.List;

/**
 * Emits the instructions for plain {@code after(...)} advice (no returning,
 * no throwing binding): an {@code invoke-static} to the monitor event method,
 * inserted immediately after the matched call site.
 *
 * <p>Plain {@code after} runs on normal completion and when the matched call
 * throws, and the throwable is rethrown unchanged (INV-INS-163). Both weaving
 * paths implement it: a wrapped call ({@link WrapperEmitter}) fires the monitor
 * calls from a catch-all handler around the call and again after it returns; a
 * constructor call, woven inline by the {@code dex-mutator}, runs this plan
 * after the call and from a catch-all handler installed around it that ends in
 * {@code throw}.
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
