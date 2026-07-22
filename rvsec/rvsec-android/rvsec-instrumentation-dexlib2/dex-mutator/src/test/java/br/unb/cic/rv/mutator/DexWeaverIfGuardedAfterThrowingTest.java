package br.unb.cic.rv.mutator;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.AspectDescriptor;
import br.unb.cic.rv.descriptor.MonitorCallDescriptor;
import br.unb.cic.rv.descriptor.ParameterDescriptor;
import br.unb.cic.rv.emitter.EmitterDispatch;
import br.unb.cic.rv.pointcut.AndroidClassIndex;
import br.unb.cic.rv.pointcut.InheritanceResolver;
import br.unb.cic.rv.pointcut.TypeResolver;

import com.android.tools.smali.dexlib2.AccessFlags;
import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction21t;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.iface.instruction.OneRegisterInstruction;
import com.android.tools.smali.dexlib2.iface.instruction.ReferenceInstruction;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableDexFile;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodImplementation;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodParameter;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction11x;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction21c;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction35c;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableTypeReference;

import org.junit.jupiter.api.Test;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * §4.T.2a (round-11 M1) — §4.T × §4.I composition on the shared join point.
 *
 * <p>The corpus's sole {@code after() throwing} site
 * ({@code Comparable_CompareToNullException_badexception}) shares its pointcut
 * with the §4.I {@code if(o == null)} guard. AspectJ binds advice by the FULL
 * pointcut, so the after-throwing advice must fire ONLY when {@code o == null}.
 * This test asserts the §4.I guard gates the handler-side advice invoke: the
 * advice runs when {@code o == null} and is skipped (branched past) when
 * {@code o != null} — yet the {@code throw} re-throw always runs, so the
 * exception still propagates regardless of the guard.
 *
 * <p>Proven at the DEX level (the guard branch's structure): the handler block
 * is {@code move-exception} → {@code if-nez vO, :skip} → advice invoke →
 * {@code :skip throw vO}. A false guard ({@code o != null}) jumps past the
 * invoke to the throw; a true guard ({@code o == null}) falls through into the
 * invoke. (Runtime fire/skip behaviour is the §6.S device gate.)
 */
class DexWeaverIfGuardedAfterThrowingTest {

    private static final String FOO_DESC = "LFoo;";
    private static final String COMPARABLE_DESC = "Ljava/lang/Comparable;";
    private static final String MONITOR_DESC = "Lmop/MultiSpec_1RuntimeMonitor;";

    @Test
    void ifGuardGatesAfterThrowingAdviceInvoke() {
        DexFile dex = buildFixture();
        AspectDescriptor descriptor = guardedAfterThrowingDescriptor();

        TypeResolver typeResolver = new TypeResolver(descriptor.getImports());
        AndroidClassIndex emptyAndroid = new AndroidClassIndex(Path.of("/tmp/nope.jar"));
        InheritanceResolver inheritance = new InheritanceResolver(emptyAndroid, dex);

        DexWeaverNestedTryCatchTest.TrackingSupplier supplier =
                new DexWeaverNestedTryCatchTest.TrackingSupplier();
        DexWeaver weaver = new DexWeaver(new EmitterDispatch(), new RegisterAllocator());
        DexWeaver.WeaveReport report =
                weaver.weave(dex, descriptor, typeResolver, inheritance, supplier);

        assertEquals(1, report.matchesApplied(),
                "the if-guarded after-throwing site must weave exactly once");

        // Inspect the rebuilt method's handler block.
        MutableMethodImplementation mut = supplier.muts.get(FOO_DESC + "->cmp()I");
        assertNotNull(mut, "cmp()I must have been rebuilt by installTryCatch");
        List<BuilderInstruction> ins = new ArrayList<>(mut.getInstructions());

        // Locate move-exception (handler start), the guard branch, the advice
        // invoke, and the throw — in that order.
        int meIdx = indexOf(ins, Opcode.MOVE_EXCEPTION);
        assertTrue(meIdx >= 0, "handler must start with move-exception");
        int excReg = ((OneRegisterInstruction) ins.get(meIdx)).getRegisterA();

        // The very next instruction is the §4.I guard: if-nez vO, :skip
        BuilderInstruction guard = ins.get(meIdx + 1);
        assertEquals(Opcode.IF_NEZ, guard.getOpcode(),
                "if(o == null) lowers to if-nez vO immediately after move-exception, "
                        + "gating the advice invoke");
        int boundReg = ((OneRegisterInstruction) guard).getRegisterA();

        // The advice invoke follows the guard.
        BuilderInstruction adviceInvoke = ins.get(meIdx + 2);
        assertEquals(Opcode.INVOKE_STATIC, adviceInvoke.getOpcode(),
                "the monitor invoke is the guarded block");
        MethodReference ref = (MethodReference)
                ((ReferenceInstruction) adviceInvoke).getReference();
        assertEquals(MONITOR_DESC, ref.getDefiningClass());
        assertEquals("Comparable_CompareToNullException_badexceptionEvent", ref.getName());

        // The guard tests the SAME register that the invoke passes as the
        // args(o) operand (slot 0 of the monitor event (o, e)).
        com.android.tools.smali.dexlib2.iface.instruction.formats.Instruction35c i35 =
                (com.android.tools.smali.dexlib2.iface.instruction.formats.Instruction35c) adviceInvoke;
        assertEquals(boundReg, i35.getRegisterC(),
                "guard tests the args(o) register — the invoke's first operand");
        // The exception (throwing e) is slot 1 of the event, rewritten to the
        // move-exception register.
        assertEquals(excReg, i35.getRegisterD(),
                "throwing(e) operand rewritten to the move-exception register");

        // The throw is the LAST handler instruction and is the guard's skip
        // target — so a false guard (o != null) jumps PAST the invoke straight
        // to throw, re-throwing without firing the advice.
        int throwIdx = -1;
        for (int i = meIdx + 3; i < ins.size(); i++) {
            if (ins.get(i).getOpcode() == Opcode.THROW) { throwIdx = i; break; }
        }
        assertTrue(throwIdx >= 0, "handler must end with throw (re-throw)");
        assertEquals(excReg, ((OneRegisterInstruction) ins.get(throwIdx)).getRegisterA(),
                "throw re-throws the caught exception register");

        int skipTargetIdx = ((BuilderInstruction21t) guard).getTarget().getLocation().getIndex();
        assertTrue(skipTargetIdx > (meIdx + 2),
                "guard-false (o != null) MUST skip past the advice invoke (idx "
                        + (meIdx + 2) + ") but skips to idx " + skipTargetIdx);
        assertEquals(throwIdx, skipTargetIdx,
                "guard-false lands on the throw — advice skipped, exception still re-thrown");
    }

    private static int indexOf(List<BuilderInstruction> ins, Opcode op) {
        for (int i = 0; i < ins.size(); i++) {
            if (ins.get(i).getOpcode() == op) return i;
        }
        return -1;
    }

    // ------------------------------------------------------------------
    // Fixture: non-nested baseline (no user try-block) so the test focuses
    // squarely on the guard×handler composition, not range-splitting.
    //   static int cmp() {
    //     Comparable a = ...; Object o = ...;
    //     return a.compareTo(o);
    //   }
    // ------------------------------------------------------------------

    private static DexFile buildFixture() {
        MethodReference compareTo = new ImmutableMethodReference(
                COMPARABLE_DESC, "compareTo",
                List.of("Ljava/lang/Object;"), "I");

        List<ImmutableInstruction> body = new ArrayList<>();
        // v2 = receiver (Comparable), v3 = arg (Object o)
        body.add(new ImmutableInstruction21c(
                Opcode.CONST_CLASS, /*regA=*/ 2, new ImmutableTypeReference(COMPARABLE_DESC)));
        body.add(new ImmutableInstruction21c(
                Opcode.CONST_CLASS, /*regA=*/ 3, new ImmutableTypeReference("Ljava/lang/Object;")));
        // matched invoke
        body.add(new ImmutableInstruction35c(
                Opcode.INVOKE_INTERFACE, /*regCount=*/ 2,
                /*c=*/ 2, /*d=*/ 3, /*e=*/ 0, /*f=*/ 0, /*g=*/ 0,
                compareTo));
        body.add(new ImmutableInstruction11x(Opcode.MOVE_RESULT, 0));
        body.add(new ImmutableInstruction11x(Opcode.RETURN, 0));

        ImmutableMethodImplementation impl = new ImmutableMethodImplementation(
                /*registerCount=*/ 4, body, Collections.emptyList(), Collections.emptyList());
        ImmutableMethod cmp = new ImmutableMethod(
                FOO_DESC, "cmp",
                Collections.<ImmutableMethodParameter>emptyList(), "I",
                AccessFlags.PUBLIC.getValue() | AccessFlags.STATIC.getValue(),
                null, null, impl);
        ClassDef foo = new ImmutableClassDef(
                FOO_DESC, AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;", Collections.emptyList(),
                null, null, Collections.emptyList(), List.of(cmp));
        return new ImmutableDexFile(Opcodes.getDefault(), List.of(foo));
    }

    private static AspectDescriptor guardedAfterThrowingDescriptor() {
        AspectDescriptor descriptor = new AspectDescriptor();
        descriptor.setShortName("MultiSpec_1");
        descriptor.setImports(List.of("java.lang.Comparable", "java.lang.Exception"));
        AdviceDescriptor advice = new AdviceDescriptor();
        advice.setName("badexception");
        advice.setSpecName("Comparable_CompareToNullException");
        advice.setPosition("after");
        advice.setAround(false);
        advice.setReturnType("void");
        // The corpus pointcut (line :294/:205 share the join point):
        //   after (Object o) throwing (Exception e) :
        //     call(* Comparable+.compareTo(..)) && args(o) && if(o == null)
        // (return type pinned to int — wildcard return matching is orthogonal.)
        advice.setExpression(
                "call(int Comparable+.compareTo(..)) && args(o) && if(o == null)");
        advice.setParameters(List.of(new ParameterDescriptor("Object", "o")));
        advice.setThrowing(List.of(new ParameterDescriptor("Exception", "e")));
        MonitorCallDescriptor mc = new MonitorCallDescriptor();
        mc.setMethod("MultiSpec_1RuntimeMonitor.Comparable_CompareToNullException_badexceptionEvent");
        mc.setSpecName("Comparable_CompareToNullException");
        mc.setEventId("badexception");
        mc.setUniqueId("u1");
        mc.setArgs(List.of("o", "e"));
        advice.setMonitorCalls(List.of(mc));
        descriptor.setAdvices(List.of(advice));
        return descriptor;
    }
}
