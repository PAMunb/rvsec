package br.unb.cic.rv.grammar;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.MonitorCallDescriptor;
import br.unb.cic.rv.descriptor.ParameterDescriptor;
import br.unb.cic.rv.emitter.BeforeEmitter;
import br.unb.cic.rv.emitter.EmitContext;
import br.unb.cic.rv.emitter.EmitPlan;
import br.unb.cic.rv.emitter.IfGuardEmitter;
import br.unb.cic.rv.emitter.UnsupportedAspectConstructError;
import br.unb.cic.rv.grammar.util.DemandCounter;
import br.unb.cic.rv.grammar.util.DemandCounter.Corpus;
import br.unb.cic.rv.mutator.InstructionInjector;
import br.unb.cic.rv.pointcut.Match;
import br.unb.cic.rv.pointcut.TypeResolver;

import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction10x;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction21t;
import com.android.tools.smali.dexlib2.iface.instruction.formats.Instruction21t;
import com.android.tools.smali.dexlib2.iface.instruction.formats.Instruction35c;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Backs the matrix row "{@code if(BooleanExpression)}" (§4.I). COVERED: the {@code if(...)} PCD is
 * lowered <b>entirely in the dexlib2 weaver</b> (round-11 R11.5, fork-free) by {@link IfGuardEmitter}
 * + {@code InstructionInjector.installGuard}, for the two corpus shapes — {@code <bound> == null}
 * (→ {@code if-nez}) and {@code !Thread.holdsLock(<bound>)} (→ {@code invoke-static Thread.holdsLock}
 * + {@code if-nez}). A third shape fails loud ({@link UnsupportedAspectConstructError}).
 *
 * <p>The emitter attaches an {@code EmitPlan.GuardSpec}; the injector materialises the guard around
 * the monitor invoke. We install against a real {@link MutableMethodImplementation} and assert the
 * lowered DEX genuinely gates the invoke (a false guard branches past it). This is the matrix row's
 * grammar-tests evidence so the Evidence FQN resolves on the grammar-tests classpath; the
 * complementary weaver round-trip proof lives in {@code dex-mutator}'s {@code IfGuardLoweringTest}.
 */
class IfGrammarTest {

    private static final int BOUND_REG = 3;
    private static final int SCRATCH_REG = 4;

    @Test
    void nullCheckShapeLowersToIfNez() {
        Installed installed = installGuard(adviceNullCheck(), -1);
        BuilderInstruction guard = installed.instructions.get(installed.blockStart - 1);
        assertEquals(Opcode.IF_NEZ, guard.getOpcode(),
                "if(it == null) lowers to a single if-nez on the bound register");
        assertEquals(BOUND_REG, ((Instruction21t) guard).getRegisterA(),
                "if-nez tests the target(it)-bound register");
        assertEquals(Opcode.INVOKE_STATIC, installed.instructions.get(installed.blockStart).getOpcode(),
                "the monitor invoke immediately follows the null-check guard");
    }

    @Test
    void holdsLockShapeLowersToInvokeStaticAndBranch() {
        Installed installed = installGuard(adviceHoldsLock(), SCRATCH_REG);
        int p = installed.blockStart - 3;
        BuilderInstruction call = installed.instructions.get(p);
        assertEquals(Opcode.INVOKE_STATIC, call.getOpcode());
        MethodReference ref = (MethodReference) ((Instruction35c) call).getReference();
        assertEquals("Ljava/lang/Thread;", ref.getDefiningClass());
        assertEquals("holdsLock", ref.getName());
        assertEquals(BOUND_REG, ((Instruction35c) call).getRegisterC(),
                "holdsLock is invoked on the target(it)-bound register");
        assertEquals(Opcode.MOVE_RESULT, installed.instructions.get(p + 1).getOpcode());
        assertEquals(Opcode.IF_NEZ, installed.instructions.get(p + 2).getOpcode(),
                "the holdsLock boolean is tested by if-nez");
    }

    @Test
    void unsupportedShapeFailsLoud() {
        IfGuardEmitter guard = new IfGuardEmitter().wrapping(new BeforeEmitter());
        assertThrows(UnsupportedAspectConstructError.class, () -> guard.emit(ctx(adviceUnsupported())));
    }

    @Test
    void guardSkipsMonitorWhenFalse() {
        assertSkipsMonitor(installGuard(adviceNullCheck(), -1));
        assertSkipsMonitor(installGuard(adviceHoldsLock(), SCRATCH_REG));
    }

    /** §4.I pipeline survival: the {@code if(...)} PCD reaches dexlib2 with non-zero pipeline demand
     *  in {@code generic_new} (3 sites) — so the row is genuinely COVERED, not absorbed. */
    @Test
    void ifPcdHasPipelineDemandInGenericNew() {
        assertEquals(3, DemandCounter.countCompiledAj(DemandCounter.IF_PCD, Corpus.GENERIC_NEW),
                "if(...) PCD has 3 pipeline sites in generic_new — the COVERED §4.I demand");
    }

    private void assertSkipsMonitor(Installed installed) {
        List<BuilderInstruction> ins = installed.instructions;
        int branchIdx = -1;
        for (int i = installed.blockStart - 1; i >= 0; i--) {
            if (ins.get(i).getOpcode() == Opcode.IF_NEZ) { branchIdx = i; break; }
        }
        assertTrue(branchIdx >= 0, "guard branch present");
        int monitorIdx = installed.blockStart;
        assertEquals(Opcode.INVOKE_STATIC, ins.get(monitorIdx).getOpcode());
        int target = ((BuilderInstruction21t) ins.get(branchIdx)).getTarget().getLocation().getIndex();
        assertTrue(target > monitorIdx,
                "guard-false branch must skip the monitor invoke (branch idx=" + branchIdx
                        + ", monitor idx=" + monitorIdx + ", target idx=" + target + ")");
        assertEquals(installed.blockStart + installed.blockLen, target,
                "skip lands immediately after the guarded block");
    }

    private record Installed(List<BuilderInstruction> instructions, int blockStart, int blockLen) {}

    private Installed installGuard(AdviceDescriptor advice, int scratchReg) {
        EmitPlan plan = new IfGuardEmitter().wrapping(new BeforeEmitter()).emit(ctx(advice));
        MutableMethodImplementation impl = new MutableMethodImplementation(SCRATCH_REG + 1);
        impl.addInstruction(new BuilderInstruction10x(Opcode.RETURN_VOID)); // idx 0 — matched-site tail
        InstructionInjector inj = new InstructionInjector(impl);
        if (scratchReg >= 0) {
            inj.withGuardScratch(scratchReg);
        }
        inj.insertBefore(0, plan);
        List<BuilderInstruction> ins = new ArrayList<>(impl.getInstructions());
        int blockLen = plan.toInsert().size();
        int prefixLen = ins.size() - blockLen - 1;
        return new Installed(ins, prefixLen, blockLen);
    }

    private static EmitContext ctx(AdviceDescriptor advice) {
        Map<String, Integer> bindings = new LinkedHashMap<>();
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
        a.setExpression("call(public boolean Iterator.hasNext()) && target(it) && if(it.size() > 0)");
        return a;
    }
}
