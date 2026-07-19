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
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * INV-INS-66 defensive skips for inline-AFTER advice — the exact class of bug
 * behind the cryptoapp {@code VerifyError} regression: a post-call hook reads
 * registers that the matched invoke's {@code move-result*} has already
 * overwritten. Both skip counters were dark; a regression that silently
 * removed either skip would reintroduce verifier-rejected output on every
 * wrapped-callee APK, caught by no other test in this module.
 *
 * <ul>
 *   <li><b>Non-constructor site</b>: AFTER advice matching an
 *       {@code invoke-virtual} (no wrapper registered) must be dropped with
 *       {@code plansSkippedAliasing} — inline emission is categorically unsafe
 *       there because the binding registers may alias the result. The counter
 *       incrementing is itself the positive evidence that the advice DID
 *       match and emit a plan (the skip happens after both).</li>
 *   <li><b>Constructor site, aliasing next instruction</b>: gh52 §5.13(a)
 *       allows inline-AFTER on {@code <init>} invokes (void return, no
 *       move-result in real code) — but the belt-and-suspenders
 *       {@code resultRegisterAliasesBindings} check must still veto a site
 *       whose next instruction overwrites a bound register, under
 *       {@code constructorInlineSkippedAliasing}.</li>
 *   <li><b>Positive control</b>: the same constructor site with a follower
 *       {@code move-result-object} writing a NON-bound register applies
 *       inline — proving the veto keys on register identity, not on the mere
 *       presence of a move-result.</li>
 * </ul>
 */
class DexWeaverAfterAliasingSkipTest {

    private static final String FOO_DESC    = "LFoo;";
    private static final String CIPHER_DESC = "Ljavax/crypto/Cipher;";
    private static final String IV_DESC     = "Ljavax/crypto/spec/IvParameterSpec;";

    // ------------------------------------------------------------------
    // (1) non-constructor AFTER → plansSkippedAliasing
    // ------------------------------------------------------------------

    @Test
    void afterAdviceOnVirtualInvokeIsSkippedDefensively() {
        // idx0: const-class v0, Cipher     (placeholder receiver)
        // idx1: const-class v1, [B         (placeholder arg, bound by args(input))
        // idx2: invoke-virtual {v0, v1}, Cipher.doFinal([B)[B    ← matched
        // idx3: move-result-object v1      (the canonical overwrite of a binding)
        // idx4: return-void
        MethodReference doFinal = new ImmutableMethodReference(
                CIPHER_DESC, "doFinal", List.of("[B"), "[B");
        List<ImmutableInstruction> body = new ArrayList<>();
        body.add(new ImmutableInstruction21c(
                Opcode.CONST_CLASS, 0, new ImmutableTypeReference(CIPHER_DESC)));
        body.add(new ImmutableInstruction21c(
                Opcode.CONST_CLASS, 1, new ImmutableTypeReference("[B")));
        body.add(new ImmutableInstruction35c(
                Opcode.INVOKE_VIRTUAL, 2, 0, 1, 0, 0, 0, doFinal));
        body.add(new ImmutableInstruction11x(Opcode.MOVE_RESULT_OBJECT, 1));
        body.add(new ImmutableInstruction10x(Opcode.RETURN_VOID));
        DexFile dex = dexWithSingleMethod("enc", body);

        AspectDescriptor descriptor = afterDescriptor(
                "javax.crypto.Cipher",
                "call(public byte[] Cipher.doFinal(byte[])) && args(input)");

        Map<String, MutableMethodImplementation> muts = new HashMap<>();
        DexWeaver.WeaveReport report = weave(dex, descriptor, muts);

        // The counter only increments AFTER a successful match + plan emit,
        // so ==1 simultaneously proves the advice matched and was skipped.
        assertEquals(1, report.plansSkippedAliasing(),
                "inline-AFTER on a non-constructor invoke must be dropped");
        assertEquals(0, report.matchesApplied(), "nothing may be woven");
        assertEquals(0, report.constructorInlineApplied());
        assertTrue(muts.isEmpty(),
                "the method must not even be materialised — the skip precedes "
                        + "any supplier access");
    }

    // ------------------------------------------------------------------
    // (2) constructor AFTER + aliasing follower → constructorInlineSkippedAliasing
    // (3) constructor AFTER + non-aliasing follower → applies (positive control)
    // ------------------------------------------------------------------

    @Test
    void constructorAfterIsVetoedWhenFollowerOverwritesBoundRegister() {
        // move-result-object v1 overwrites the args(iv) binding (v1) → veto.
        DexFile dex = dexWithSingleMethod("mk", ctorBody(/*moveResultReg=*/ 1));
        Map<String, MutableMethodImplementation> muts = new HashMap<>();
        DexWeaver.WeaveReport report = weave(dex, ivCtorDescriptor(), muts);

        assertEquals(1, report.constructorInlineSkippedAliasing(),
                "a follower overwriting a bound register must veto the inline hook");
        assertEquals(0, report.constructorInlineApplied());
        assertEquals(0, report.matchesApplied());
        assertEquals(0, report.plansSkippedAliasing(),
                "the ctor route must use its own counter, not the generic one");
        assertTrue(muts.isEmpty(), "vetoed site: no mutation");
    }

    @Test
    void constructorAfterAppliesWhenFollowerWritesUnboundRegister() {
        // Same shape, but move-result-object v3 — v3 is not bound by args(iv)
        // (v1) nor is it the ctor receiver (v0): the veto must NOT fire.
        DexFile dex = dexWithSingleMethod("mk", ctorBody(/*moveResultReg=*/ 3));
        Map<String, MutableMethodImplementation> muts = new HashMap<>();
        DexWeaver.WeaveReport report = weave(dex, ivCtorDescriptor(), muts);

        assertEquals(0, report.constructorInlineSkippedAliasing(),
                "positive control: a non-aliasing follower must not trip the veto");
        assertEquals(1, report.constructorInlineApplied(),
                "the ctor inline-AFTER hook must apply");
        assertEquals(1, report.matchesApplied());
        assertEquals(1, muts.size(), "the method was materialised and mutated");
    }

    // ------------------------------------------------------------------
    // fixtures
    // ------------------------------------------------------------------

    /**
     * idx0: new-instance v0, IvParameterSpec
     * idx1: const-class v1, [B                       (bound by args(iv))
     * idx2: invoke-direct {v0, v1}, IvParameterSpec.&lt;init&gt;([B)V  ← matched
     * idx3: move-result-object v{moveResultReg}      (synthetic follower)
     * idx4: return-void
     *
     * <p>Real code never places {@code move-result*} after an {@code <init>}
     * invoke (void return); the follower exists purely to drive the
     * belt-and-suspenders aliasing veto, which reads only register numbers.
     */
    private static List<ImmutableInstruction> ctorBody(int moveResultReg) {
        MethodReference initRef = new ImmutableMethodReference(
                IV_DESC, "<init>", List.of("[B"), "V");
        List<ImmutableInstruction> body = new ArrayList<>();
        body.add(new ImmutableInstruction21c(
                Opcode.NEW_INSTANCE, 0, new ImmutableTypeReference(IV_DESC)));
        body.add(new ImmutableInstruction21c(
                Opcode.CONST_CLASS, 1, new ImmutableTypeReference("[B")));
        body.add(new ImmutableInstruction35c(
                Opcode.INVOKE_DIRECT, 2, 0, 1, 0, 0, 0, initRef));
        body.add(new ImmutableInstruction11x(Opcode.MOVE_RESULT_OBJECT, moveResultReg));
        body.add(new ImmutableInstruction10x(Opcode.RETURN_VOID));
        return body;
    }

    /** After-advice on IvParameterSpec.new(byte[]) binding args(iv). */
    private static AspectDescriptor ivCtorDescriptor() {
        return afterDescriptor(
                "javax.crypto.spec.IvParameterSpec",
                "call(public IvParameterSpec.new(byte[])) && args(iv)");
    }

    private static AspectDescriptor afterDescriptor(String importFqn, String expression) {
        AspectDescriptor d = new AspectDescriptor();
        d.setShortName("MultiSpec_1");
        d.setImports(List.of(importFqn));
        AdviceDescriptor a = new AdviceDescriptor();
        a.setName("a1");
        a.setSpecName("SampleSpec");
        a.setPosition("after");
        a.setAround(false);
        a.setReturnType("void");
        a.setExpression(expression);
        String bound = expression.contains("args(iv)") ? "iv" : "input";
        a.setParameters(List.of(new ParameterDescriptor("byte[]", bound)));
        MonitorCallDescriptor mc = new MonitorCallDescriptor();
        mc.setMethod("MultiSpec_1RuntimeMonitor.SampleSpec_a1Event");
        mc.setSpecName("SampleSpec");
        mc.setEventId("a1");
        mc.setUniqueId("u1");
        mc.setArgs(List.of(bound));
        a.setMonitorCalls(List.of(mc));
        d.setAdvices(List.of(a));
        return d;
    }

    private static DexFile dexWithSingleMethod(String name, List<ImmutableInstruction> body) {
        ImmutableMethodImplementation impl = new ImmutableMethodImplementation(
                /*registerCount=*/ 4, body,
                Collections.emptyList(), Collections.emptyList());
        ImmutableMethod m = new ImmutableMethod(
                FOO_DESC, name, Collections.emptyList(), "V",
                AccessFlags.PUBLIC.getValue() | AccessFlags.STATIC.getValue(),
                null, null, impl);
        ClassDef foo = new ImmutableClassDef(
                FOO_DESC, AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;", Collections.emptyList(),
                null, null, Collections.emptyList(), List.of(m));
        return new ImmutableDexFile(Opcodes.getDefault(), List.of(foo));
    }

    private static DexWeaver.WeaveReport weave(
            DexFile dex, AspectDescriptor descriptor,
            Map<String, MutableMethodImplementation> muts) {
        TypeResolver typeResolver = new TypeResolver(descriptor.getImports());
        InheritanceResolver inheritance = new InheritanceResolver(
                new AndroidClassIndex(Path.of("/tmp/nope.jar")), dex);
        DexWeaver.MutableImplSupplier supplier = method -> {
            if (method.getImplementation() == null) return null;
            String k = methodKey(method);
            return muts.computeIfAbsent(k, kk ->
                    new MutableMethodImplementation(method.getImplementation()));
        };
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
