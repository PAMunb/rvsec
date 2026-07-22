package br.unb.cic.rv.mutator;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.MonitorCallDescriptor;
import br.unb.cic.rv.descriptor.ParameterDescriptor;
import br.unb.cic.rv.emitter.BeforeEmitter;
import br.unb.cic.rv.emitter.EmitContext;
import br.unb.cic.rv.emitter.EmitPlan;
import br.unb.cic.rv.emitter.IfGuardEmitter;
import br.unb.cic.rv.emitter.UnsupportedAspectConstructError;
import br.unb.cic.rv.pointcut.Match;
import br.unb.cic.rv.pointcut.TypeResolver;

import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction10x;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction11x;
import com.android.tools.smali.dexlib2.iface.instruction.formats.Instruction21t;
import com.android.tools.smali.dexlib2.iface.instruction.formats.Instruction35c;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * End-to-end lowering of the two {@code if(<expr>)} guard shapes: emit the plan
 * via {@link IfGuardEmitter}, install the guard against a real
 * {@link MutableMethodImplementation} via {@link InstructionInjector}, and
 * assert the resulting DEX instruction sequence genuinely gates the monitor
 * invoke (the invoke is bypassed exactly when the guard is false).
 *
 * <p>Asserting on the materialised instruction list (not a mocked stand-in) is
 * the point: the guard branch's target must land strictly after the monitor
 * invoke, so a false guard skips the invoke.
 */
class IfGuardLoweringTest {

    private static final int BOUND_REG = 3;
    private static final int SCRATCH_REG = 4;

    @Test
    void nullCheckShapeLowersToIfNez() {
        Installed installed = installGuard(adviceNullCheck(), -1);
        List<BuilderInstruction> ins = installed.instructions;

        // Sequence at the head: [if-nez vBound, :skip][invoke-static monitor]...
        BuilderInstruction guard = ins.get(installed.blockStart - 1);
        assertEquals(Opcode.IF_NEZ, guard.getOpcode(),
                "null-check lowers to a single if-nez on the bound register");
        assertEquals(BOUND_REG, ((Instruction21t) guard).getRegisterA(),
                "if-nez tests the target(it) register");

        // The instruction right after the guard is the monitor invoke (the block).
        assertEquals(Opcode.INVOKE_STATIC, ins.get(installed.blockStart).getOpcode());
    }

    @Test
    void holdsLockShapeLowersToInvokeStaticAndBranch() {
        Installed installed = installGuard(adviceHoldsLock(), SCRATCH_REG);
        List<BuilderInstruction> ins = installed.instructions;

        // Prefix occupies 3 instructions before the block:
        //   invoke-static {vBound}, Thread.holdsLock(Object)Z
        //   move-result vGuard
        //   if-nez vGuard, :skip
        int p = installed.blockStart - 3;
        BuilderInstruction call = ins.get(p);
        assertEquals(Opcode.INVOKE_STATIC, call.getOpcode());
        MethodReference ref = (MethodReference) ((Instruction35c) call).getReference();
        assertEquals("Ljava/lang/Thread;", ref.getDefiningClass());
        assertEquals("holdsLock", ref.getName());
        assertEquals(BOUND_REG, ((Instruction35c) call).getRegisterC(),
                "holdsLock is invoked on the target(it) register");

        BuilderInstruction move = ins.get(p + 1);
        assertEquals(Opcode.MOVE_RESULT, move.getOpcode());
        assertEquals(SCRATCH_REG, ((BuilderInstruction11x) move).getRegisterA());

        BuilderInstruction branch = ins.get(p + 2);
        assertEquals(Opcode.IF_NEZ, branch.getOpcode());
        assertEquals(SCRATCH_REG, ((Instruction21t) branch).getRegisterA(),
                "if-nez tests the holdsLock boolean, not the bound register");

        assertEquals(Opcode.INVOKE_STATIC, ins.get(installed.blockStart).getOpcode(),
                "the monitor invoke follows the guard prefix");
    }

    @Test
    void unsupportedShapeFailsLoud() {
        IfGuardEmitter guard = new IfGuardEmitter().wrapping(new BeforeEmitter());
        // if(it.size() > 0) is neither null-check nor holdsLock.
        assertThrows(UnsupportedAspectConstructError.class,
                () -> guard.emit(ctx(adviceUnsupported())));
    }

    @Test
    void guardSkipsMonitorWhenFalse() {
        // For BOTH shapes the guard branch must target an instruction strictly
        // AFTER the monitor invoke, so a false guard bypasses the invoke.
        assertSkipBypassesMonitor(installGuard(adviceNullCheck(), -1));
        assertSkipBypassesMonitor(installGuard(adviceHoldsLock(), SCRATCH_REG));
    }

    private void assertSkipBypassesMonitor(Installed installed) {
        List<BuilderInstruction> ins = installed.instructions;
        // Locate the guard branch (the last if-nez before the block) and the
        // monitor invoke (the block's invoke-static).
        int branchIdx = -1;
        for (int i = installed.blockStart - 1; i >= 0; i--) {
            if (ins.get(i).getOpcode() == Opcode.IF_NEZ) { branchIdx = i; break; }
        }
        assertTrue(branchIdx >= 0, "guard branch present");

        int monitorIdx = installed.blockStart;
        assertEquals(Opcode.INVOKE_STATIC, ins.get(monitorIdx).getOpcode());

        Instruction21t branch = (Instruction21t) ins.get(branchIdx);
        int targetIdx = ((com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction21t)
                branch).getTarget().getLocation().getIndex();

        // The branch must jump PAST the monitor invoke: target > monitorIdx.
        assertTrue(targetIdx > monitorIdx,
                "guard-false branch (idx=" + branchIdx + ") must skip the monitor invoke (idx="
                        + monitorIdx + ") but targets idx=" + targetIdx);
        // And the skip target must be the instruction right after the block.
        assertEquals(installed.blockStart + installed.blockLen, targetIdx,
                "skip lands immediately after the guarded block");
        // The instruction at the skip target is the original method tail
        // (return-void), proving the invoke is bypassed, not the whole method.
        assertSame(installed.tail, ins.get(targetIdx),
                "skip target is the method tail that follows the guarded invoke");
    }

    // --- harness -----------------------------------------------------------

    private record Installed(List<BuilderInstruction> instructions, int blockStart,
                             int blockLen, BuilderInstruction tail) {}

    /**
     * Emit the guarded plan and install it into a fresh method whose only
     * pre-existing instruction is a {@code return-void} tail, mirroring a
     * {@code before}-advice insertion just ahead of the matched site.
     */
    private Installed installGuard(AdviceDescriptor advice, int scratchReg) {
        EmitPlan plan = new IfGuardEmitter().wrapping(new BeforeEmitter()).emit(ctx(advice));

        MutableMethodImplementation impl = new MutableMethodImplementation(SCRATCH_REG + 1);
        BuilderInstruction tail = new BuilderInstruction10x(Opcode.RETURN_VOID);
        impl.addInstruction(tail); // idx 0 — the matched-site tail

        InstructionInjector inj = new InstructionInjector(impl);
        if (scratchReg >= 0) inj.withGuardScratch(scratchReg);
        // before-advice inserts at index 0 (ahead of the tail).
        inj.insertBefore(0, plan);

        List<BuilderInstruction> ins = new ArrayList<>(impl.getInstructions());
        int blockLen = plan.toInsert().size();
        // The guarded block (monitor invoke) starts after the guard prefix; the
        // prefix length is total inserted minus block minus original tail.
        int prefixLen = ins.size() - blockLen - 1;
        return new Installed(ins, prefixLen, blockLen, tail);
    }

    private static EmitContext ctx(AdviceDescriptor advice) {
        Map<String, Integer> bindings = new LinkedHashMap<>();
        bindings.put("arg00", BOUND_REG);
        bindings.put("it", BOUND_REG);
        Match match = new Match(bindings, BOUND_REG, null, false);
        TypeResolver resolver = new TypeResolver(List.of("java.util.Iterator"));
        return new EmitContext(advice, match, resolver, "Lmop/MultiSpec_1RuntimeMonitor;");
    }

    private static AdviceDescriptor baseAdvice() {
        AdviceDescriptor a = new AdviceDescriptor();
        a.setName("guarded");
        a.setSpecName("SampleSpec");
        a.setPosition("before");
        a.setAround(false);
        a.setParameters(List.of(new ParameterDescriptor("Iterator", "it")));
        MonitorCallDescriptor mc = new MonitorCallDescriptor();
        mc.setMethod("MultiSpec_1RuntimeMonitor.hasNextEvent");
        mc.setSpecName("SampleSpec");
        mc.setEventId("hasNextEvent");
        mc.setUniqueId("hasNextEvent");
        mc.setArgs(List.of("it"));
        a.setMonitorCalls(List.of(mc));
        return a;
    }

    private static AdviceDescriptor adviceNullCheck() {
        AdviceDescriptor a = baseAdvice();
        a.setExpression("call(public boolean Iterator.hasNext()) && target(it) && if(it == null)");
        return a;
    }

    private static AdviceDescriptor adviceHoldsLock() {
        AdviceDescriptor a = baseAdvice();
        a.setExpression("call(public boolean Iterator.hasNext()) && target(it)"
                + " && if(!Thread.holdsLock(it))");
        return a;
    }

    private static AdviceDescriptor adviceUnsupported() {
        AdviceDescriptor a = baseAdvice();
        a.setExpression("call(public boolean Iterator.hasNext()) && target(it)"
                + " && if(it.size() > 0)");
        return a;
    }
}
