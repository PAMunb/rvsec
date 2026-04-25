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
        // The matched invoke's existing `move-result*` already captures the
        // return value into a register; the matcher records that register in
        // `match.argBindings` for the bound `returning(<type> r)` parameter,
        // and `MonitorInvokeBuilder.buildInvoke` forwards it directly. The
        // injector skips past the existing `move-result*` (INV-INS-27) so we
        // land AFTER the capture.
        //
        // Therefore no scratch register is required for the common case where
        // the matched invoke has an existing `move-result*` and its destination
        // is in the 35c-friendly v0..v15 range. A future emitter that needs to
        // capture a return into a fresh register (e.g. when the matched call
        // discards the result, or the destination is at a high index that
        // exceeds Format35c's 4-bit field) will need to coordinate a real
        // spill via the allocator (INV-INS-26 follow-up); raising
        // RegisterRequest.scratch(1) without a corresponding emit-time use of
        // that register only triggered the buggy bumpRegisterCount path
        // (cryptoapp Preconditions VerifyError) without buying anything.
        List<BuilderInstruction> ins = MonitorInvokeBuilder.buildInvoke(ctx);
        return EmitPlan.of(ins, InsertionPoint.AFTER, RegisterRequest.NONE);
    }

    @Override
    public String kind() { return "after-returning"; }
}
