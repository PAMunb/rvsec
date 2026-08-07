package br.unb.cic.rv.mutator;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.AspectDescriptor;
import br.unb.cic.rv.descriptor.MonitorCallDescriptor;
import br.unb.cic.rv.descriptor.ParameterDescriptor;
import br.unb.cic.rv.emitter.EmitterDispatch;
import br.unb.cic.rv.emitter.UnsupportedAspectConstructError;
import br.unb.cic.rv.pointcut.AndroidClassIndex;
import br.unb.cic.rv.pointcut.InheritanceResolver;
import br.unb.cic.rv.pointcut.TypeResolver;

import com.android.tools.smali.dexlib2.AccessFlags;
import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableDexFile;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodImplementation;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction10x;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction11x;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction21c;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction35c;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableTypeReference;

import org.junit.jupiter.api.Test;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * DexWeaver graceful-degradation semantics: a weave pass never aborts on a
 * per-advice problem — it drops exactly the affected emission, counts it, and
 * keeps weaving everything else. All three routes were dark:
 *
 * <ul>
 *   <li><b>around advice</b> (out of gh52 scope): {@code EmitterDispatch.select}
 *       throws {@code UnsupportedOperationException} AFTER the match — the
 *       weaver must absorb it under {@code plansSkipped} while the OTHER
 *       advice of the same descriptor still applies inline. A regression here
 *       would make one around advice in a merged descriptor kill the whole
 *       weave.</li>
 *   <li><b>malformed commonPointcut</b> (§4.D.0): an unparseable
 *       {@code commonPointcut} degrades to advice-only matching — weaving
 *       proceeds as if no commonPointcut existed, rather than dropping every
 *       advice on the floor.</li>
 *   <li><b>supplier returning null</b> for a matched method: the emission is
 *       dropped under {@code plansSkipped} — never applied against a missing
 *       mutable view, never fatal.</li>
 * </ul>
 */
class DexWeaverDegradationTest {

    private static final String FOO_DESC    = "LFoo;";
    private static final String CIPHER_DESC = "Ljavax/crypto/Cipher;";

    // ------------------------------------------------------------------
    // (1) around advice → plansSkipped, sibling advice still applies
    // ------------------------------------------------------------------

    @Test
    void aroundAdviceIsCountedSkippedWhileSiblingBeforeApplies() {
        DexFile dex = dexWithDoFinalCall();
        AspectDescriptor descriptor = beforeDoFinalDescriptor();

        // Prepend an around advice on the SAME site. Both advices match the
        // invoke; only the before one has an emitter.
        AdviceDescriptor around = new AdviceDescriptor();
        around.setName("ar1");
        around.setSpecName("SampleSpec");
        around.setPosition("around");
        around.setAround(true);
        around.setReturnType("byte[]");
        around.setExpression(
                "call(public byte[] Cipher.doFinal(byte[])) && args(input)");
        around.setParameters(List.of(new ParameterDescriptor("byte[]", "input")));
        MonitorCallDescriptor amc = new MonitorCallDescriptor();
        amc.setMethod("MultiSpec_1RuntimeMonitor.SampleSpec_ar1Event");
        amc.setSpecName("SampleSpec");
        amc.setEventId("ar1");
        amc.setUniqueId("u2");
        amc.setArgs(List.of("input"));
        around.setMonitorCalls(List.of(amc));
        List<AdviceDescriptor> advices = new ArrayList<>(descriptor.getAdvices());
        advices.add(0, around);
        descriptor.setAdvices(advices);

        Map<String, MutableMethodImplementation> muts = new HashMap<>();
        DexWeaver.WeaveReport report = weave(dex, descriptor, mapSupplier(muts));

        assertEquals(1, report.plansSkipped(),
                "the around advice must be absorbed as a counted skip");
        assertEquals(1, report.matchesApplied(),
                "the sibling before advice must still weave — one bad advice "
                        + "must not kill the descriptor");
        MutableMethodImplementation mut = muts.get(FOO_DESC + "->enc()V");
        assertEquals(6, new ArrayList<>(mut.getInstructions()).size(),
                "exactly the before hook was inserted (5 original + 1)");
    }

    // ------------------------------------------------------------------
    // (2) malformed commonPointcut → the weave fails loud (gh100 task 5.5)
    // ------------------------------------------------------------------

    @Test
    void malformedCommonPointcutFailsTheWeave() {
        // This test used to assert the opposite — that an unparseable
        // commonPointcut degrades to advice-only matching "rather than dropping
        // all weaving". That reading treats the commonPointcut as an optional
        // refinement. It is not: it carries the class-level exclusions
        // (BaseAspect.notwithin(), !within(...RVMObject+)), which appear in no
        // advice's own expression. Degrading to advice-only matching weaves
        // every site those clauses exist to exclude, with neither error nor
        // warning, over machine-generated source no reviewer reads. The delta
        // spec's Fail-Closed Pointcut Parsing requirement replaces the old
        // behaviour; the assertion is inverted rather than deleted so the
        // record shows the contract changed deliberately.
        DexFile dex = dexWithDoFinalCall();
        AspectDescriptor descriptor = beforeDoFinalDescriptor();
        descriptor.setCommonPointcut("!!within(((garbage");  // unparseable

        Map<String, MutableMethodImplementation> muts = new HashMap<>();
        UnsupportedAspectConstructError error = assertThrows(
                UnsupportedAspectConstructError.class,
                () -> weave(dex, descriptor, mapSupplier(muts)));

        assertTrue(error.getMessage().contains("!!within(((garbage"),
                "the message must name the expression that failed to parse, so the parser "
                        + "gets extended deliberately: " + error.getMessage());
        assertTrue(muts.isEmpty(),
                "nothing may be woven against an aspect whose exclusions could not be read");
    }

    // ------------------------------------------------------------------
    // (3) supplier returns null for a matched method → plansSkipped
    // ------------------------------------------------------------------

    @Test
    void nullSupplierDropsThePlanUnderCounter() {
        DexFile dex = dexWithDoFinalCall();

        Map<String, MutableMethodImplementation> muts = new HashMap<>();
        DexWeaver.WeaveReport report = weave(
                dex, beforeDoFinalDescriptor(), method -> null);

        assertEquals(1, report.plansSkipped(),
                "a matched+emitted plan with no mutable view is dropped, counted");
        assertEquals(0, report.matchesApplied(), "nothing may count as applied");
        assertTrue(muts.isEmpty());
    }

    // ------------------------------------------------------------------
    // fixtures (doFinal call shape shared with the substitution tests)
    // ------------------------------------------------------------------

    private static DexFile dexWithDoFinalCall() {
        MethodReference doFinal = new ImmutableMethodReference(
                CIPHER_DESC, "doFinal", List.of("[B"), "[B");
        List<ImmutableInstruction> body = new ArrayList<>();
        body.add(new ImmutableInstruction21c(
                Opcode.CONST_CLASS, 0, new ImmutableTypeReference(CIPHER_DESC)));
        body.add(new ImmutableInstruction21c(
                Opcode.CONST_CLASS, 1, new ImmutableTypeReference("[B")));
        body.add(new ImmutableInstruction35c(
                Opcode.INVOKE_VIRTUAL, 2, 0, 1, 0, 0, 0, doFinal));
        body.add(new ImmutableInstruction11x(Opcode.MOVE_RESULT_OBJECT, 2));
        body.add(new ImmutableInstruction10x(Opcode.RETURN_VOID));
        ImmutableMethodImplementation impl = new ImmutableMethodImplementation(
                /*registerCount=*/ 4, body,
                Collections.emptyList(), Collections.emptyList());
        ImmutableMethod m = new ImmutableMethod(
                FOO_DESC, "enc", Collections.emptyList(), "V",
                AccessFlags.PUBLIC.getValue() | AccessFlags.STATIC.getValue(),
                null, null, impl);
        ClassDef foo = new ImmutableClassDef(
                FOO_DESC, AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;", Collections.emptyList(),
                null, null, Collections.emptyList(), List.of(m));
        return new ImmutableDexFile(Opcodes.getDefault(), List.of(foo));
    }

    /** One BEFORE advice on Cipher.doFinal(byte[]) binding args(input). */
    private static AspectDescriptor beforeDoFinalDescriptor() {
        AspectDescriptor d = new AspectDescriptor();
        d.setShortName("MultiSpec_1");
        d.setImports(List.of("javax.crypto.Cipher"));
        AdviceDescriptor a = new AdviceDescriptor();
        a.setName("d1");
        a.setSpecName("SampleSpec");
        a.setPosition("before");
        a.setAround(false);
        a.setReturnType("void");
        a.setExpression(
                "call(public byte[] Cipher.doFinal(byte[])) && args(input)");
        a.setParameters(List.of(new ParameterDescriptor("byte[]", "input")));
        MonitorCallDescriptor mc = new MonitorCallDescriptor();
        mc.setMethod("MultiSpec_1RuntimeMonitor.SampleSpec_d1Event");
        mc.setSpecName("SampleSpec");
        mc.setEventId("d1");
        mc.setUniqueId("u1");
        mc.setArgs(List.of("input"));
        a.setMonitorCalls(List.of(mc));
        d.setAdvices(List.of(a));
        return d;
    }

    private static DexWeaver.MutableImplSupplier mapSupplier(
            Map<String, MutableMethodImplementation> muts) {
        return method -> {
            if (method.getImplementation() == null) return null;
            String k = methodKey(method);
            return muts.computeIfAbsent(k, kk ->
                    new MutableMethodImplementation(method.getImplementation()));
        };
    }

    private static DexWeaver.WeaveReport weave(
            DexFile dex, AspectDescriptor descriptor,
            DexWeaver.MutableImplSupplier supplier) {
        TypeResolver typeResolver = new TypeResolver(descriptor.getImports());
        InheritanceResolver inheritance = new InheritanceResolver(
                new AndroidClassIndex(Path.of("/tmp/nope.jar")), dex);
        return new DexWeaver(new EmitterDispatch(), new RegisterAllocator())
                .weave(dex, descriptor, typeResolver, inheritance, supplier);
    }

    private static String methodKey(Method m) {
        StringBuilder sb = new StringBuilder(64);
        sb.append(m.getDefiningClass()).append("->").append(m.getName()).append('(');
        for (CharSequence p : m.getParameterTypes()) sb.append(p);
        sb.append(')').append(m.getReturnType());
        return sb.toString();
    }
}
