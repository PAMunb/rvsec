package br.unb.cic.rv.emitter;

import com.android.tools.smali.dexlib2.builder.BuilderInstruction;

import java.util.List;

/**
 * Emits the instructions for {@code before(...)} advice: an
 * {@code invoke-static} to the monitor event method, inserted immediately
 * before the matched call site.
 */
public final class BeforeEmitter implements AdviceEmitter {

    @Override
    public EmitPlan emit(EmitContext ctx) {
        List<BuilderInstruction> ins = MonitorInvokeBuilder.buildInvoke(ctx);
        // No scratch registers needed when the match provides all arg bindings
        // directly (the RegisterAllocator handles spill if the matched invoke
        // uses high registers).
        return EmitPlan.of(ins, InsertionPoint.BEFORE);
    }

    @Override
    public String kind() { return "before"; }
}
