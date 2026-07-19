package br.unb.cic.rv.mutator;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.AspectDescriptor;
import br.unb.cic.rv.descriptor.MonitorCallDescriptor;
import br.unb.cic.rv.descriptor.ParameterDescriptor;
import br.unb.cic.rv.emitter.EmitterDispatch;
import br.unb.cic.rv.emitter.WrapperEmitter;
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
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.iface.instruction.ReferenceInstruction;
import com.android.tools.smali.dexlib2.iface.instruction.formats.Instruction35c;
import com.android.tools.smali.dexlib2.iface.instruction.formats.Instruction3rc;
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
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction3rc;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableTypeReference;

import org.junit.jupiter.api.Test;

import java.lang.reflect.Field;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * INV-INS-66 executor side: {@link DexWeaver}'s pass-1 wrapper substitution.
 *
 * <p>{@code DexWeaverWrapperSubtypeTest} only exercises the registration /
 * subtype-expansion bookkeeping; the actual weave-time substitution
 * ({@code findWrapperReplacement} → {@code InstructionInjector.replaceInvoke})
 * and its interaction with pass-2 inline advice were previously untested.
 * These tests lock the full production behaviour:
 * <ol>
 *   <li>an {@code invoke-virtual} whose {@link MethodReference} matches a
 *       registered instance wrapper is rewritten IN PLACE to an
 *       {@code invoke-static} on {@code mop.MonitorWrappers} with the SAME
 *       register operands (receiver becomes the wrapper's first argument) —
 *       the body size and every other instruction stay untouched;</li>
 *   <li>a substituted call site is EXCLUDED from pass-2 inline advice
 *       ({@code substitutedIndices}) — the wrapper already fires the events,
 *       so an inline hook would double-fire them;</li>
 *   <li>positive control: the SAME advice on the SAME site DOES apply inline
 *       when no wrapper is registered (proving the skip in (2) is caused by
 *       the substitution, not by a match failure);</li>
 *   <li>{@code invoke-static/range} sites route through the Format3rc rewrite
 *       (static wrapper: no receiver prepend, start register + count kept);</li>
 *   <li>the lookup-key format covers every primitive, arrays, and void —
 *       the exact contract that makes registration and call-site lookup agree
 *       ({@code fqnToDescriptor} on both sides).</li>
 * </ol>
 */
class DexWeaverWrapperSubstitutionTest {

    private static final String FOO_DESC     = "LFoo;";
    private static final String CIPHER_DESC  = "Ljavax/crypto/Cipher;";
    private static final String WRAPPERS_DESC = WrapperEmitter.WRAPPER_CLASS_DESC;
    private static final String MONITOR_DESC = "Lmop/MultiSpec_1RuntimeMonitor;";

    /** doFinal([B)[B on Cipher — the canonical instance wrapper target. */
    private static final MethodReference DO_FINAL_REF = new ImmutableMethodReference(
            CIPHER_DESC, "doFinal", List.of("[B"), "[B");

    // ------------------------------------------------------------------
    // (1) invoke-virtual → invoke-static wrapper rewrite, registers kept
    // ------------------------------------------------------------------

    @Test
    void instanceInvokeVirtualIsRewrittenToStaticWrapper() {
        // Synthetic caller:
        //   idx0: const-class v0, Cipher      (placeholder receiver)
        //   idx1: const-class v1, [B          (placeholder byte[] arg)
        //   idx2: invoke-virtual {v0, v1}, Cipher.doFinal([B)[B   ← wrapped
        //   idx3: move-result-object v2
        //   idx4: return-void
        DexFile dex = dexWithSingleMethod("bar", doFinalCallBody());

        // Wrapper registered for the instance method Cipher.doFinal(byte[]).
        WrapperEmitter.WrapperEntry entry = new WrapperEmitter.WrapperEntry(
                "Cipher_doFinal", "javax.crypto.Cipher", "doFinal",
                List.of("byte[]"), "byte[]", false /* instance */);
        DexWeaver weaver = new DexWeaver(
                new EmitterDispatch(), new RegisterAllocator(), List.of(entry));

        Map<String, MutableMethodImplementation> muts = new HashMap<>();
        DexWeaver.WeaveReport report = weave(weaver, dex, emptyDescriptor(), muts);

        assertEquals(1, report.wrappersSubstituted(),
                "exactly the doFinal call site must be substituted");
        assertEquals(0, report.matchesApplied(),
                "no inline advice in this descriptor — substitution only");

        MutableMethodImplementation mut = muts.get(FOO_DESC + "->bar()V");
        assertNotNull(mut, "the method must be materialised for the rewrite");
        List<? extends Instruction> after = new ArrayList<>(mut.getInstructions());
        // replaceInstruction is size-stable: still 5 instructions, and the
        // move-result-object stays glued to the (rewritten) invoke.
        assertEquals(5, after.size(), "substitution must not grow or shrink the body");
        assertEquals(Opcode.INVOKE_STATIC, after.get(2).getOpcode(),
                "the invoke-virtual must be rewritten to invoke-static");
        assertEquals(Opcode.MOVE_RESULT_OBJECT, after.get(3).getOpcode(),
                "the original move-result-object must still follow the invoke");

        Instruction35c call = (Instruction35c) after.get(2);
        MethodReference ref = (MethodReference)
                ((ReferenceInstruction) call).getReference();
        assertEquals(WRAPPERS_DESC, ref.getDefiningClass(),
                "the callee must be routed to mop.MonitorWrappers");
        assertEquals("Cipher_doFinal", ref.getName());
        // Instance wrapper signature: receiver prepended so the wrapper's
        // arity matches the invoke's register count under invoke-static.
        assertEquals(List.of(CIPHER_DESC, "[B"),
                new ArrayList<>(ref.getParameterTypes()),
                "instance wrapper takes the receiver as its first formal");
        assertEquals("[B", ref.getReturnType());
        // Register operands preserved byte-identically: {v0 (recv), v1 (arg)}.
        assertEquals(2, call.getRegisterCount());
        assertEquals(0, call.getRegisterC(), "receiver register v0 preserved");
        assertEquals(1, call.getRegisterD(), "argument register v1 preserved");
    }

    // ------------------------------------------------------------------
    // (2)+(3) substituted site skips pass-2 inline advice — with positive
    // control proving the same advice applies inline when no wrapper exists
    // ------------------------------------------------------------------

    @Test
    void substitutedSiteIsSkippedByInlineAdvicePass() {
        DexFile dex = dexWithSingleMethod("bar", doFinalCallBody());
        WrapperEmitter.WrapperEntry entry = new WrapperEmitter.WrapperEntry(
                "Cipher_doFinal", "javax.crypto.Cipher", "doFinal",
                List.of("byte[]"), "byte[]", false);
        DexWeaver weaver = new DexWeaver(
                new EmitterDispatch(), new RegisterAllocator(), List.of(entry));

        Map<String, MutableMethodImplementation> muts = new HashMap<>();
        DexWeaver.WeaveReport report =
                weave(weaver, dex, beforeDoFinalDescriptor(), muts);

        // The before-advice DOES match the doFinal site (the control test
        // below proves it) — but the site was substituted in pass 1, so
        // pass 2 must skip it: the wrapper owns ALL events for that site.
        assertEquals(1, report.wrappersSubstituted());
        assertEquals(0, report.matchesApplied(),
                "a substituted site must not ALSO receive inline advice "
                        + "(double-fire would corrupt the monitor state)");
        MutableMethodImplementation mut = muts.get(FOO_DESC + "->bar()V");
        assertEquals(5, new ArrayList<>(mut.getInstructions()).size(),
                "no inline hook inserted — only the in-place rewrite");
    }

    @Test
    void sameAdviceAppliesInlineWithoutWrapper() {
        DexFile dex = dexWithSingleMethod("bar", doFinalCallBody());
        // No wrapper registered → the no-arg convenience constructor is the
        // production shape for a pure-inline weave.
        DexWeaver weaver = new DexWeaver();

        Map<String, MutableMethodImplementation> muts = new HashMap<>();
        DexWeaver.WeaveReport report =
                weave(weaver, dex, beforeDoFinalDescriptor(), muts);

        assertEquals(0, report.wrappersSubstituted(), "no wrapper registered");
        assertEquals(1, report.matchesApplied(),
                "positive control: the SAME advice on the SAME site applies "
                        + "inline when the site was not substituted");

        MutableMethodImplementation mut = muts.get(FOO_DESC + "->bar()V");
        assertNotNull(mut);
        List<? extends Instruction> after = new ArrayList<>(mut.getInstructions());
        assertEquals(6, after.size(),
                "the inline BEFORE hook adds exactly one monitor invoke");
        // BEFORE advice lands immediately before the matched invoke (idx2 →
        // the hook takes idx2, the original invoke-virtual shifts to idx3).
        assertEquals(Opcode.INVOKE_STATIC, after.get(2).getOpcode(),
                "monitor hook inserted before the matched call");
        MethodReference hookRef = (MethodReference)
                ((ReferenceInstruction) after.get(2)).getReference();
        assertEquals(MONITOR_DESC, hookRef.getDefiningClass());
        assertEquals("CipherSpec_d1Event", hookRef.getName());
        assertEquals(Opcode.INVOKE_VIRTUAL, after.get(3).getOpcode(),
                "the original invoke-virtual is untouched (no substitution)");
    }

    // ------------------------------------------------------------------
    // (4) invoke-static/range → Format3rc rewrite (static wrapper)
    // ------------------------------------------------------------------

    @Test
    void staticInvokeRangeIsRewrittenToRangeWrapper() {
        // Synthetic caller:
        //   idx0: const-class v0, String     (placeholder "AES" transformation)
        //   idx1: invoke-static/range {v0..v0}, Cipher.getInstance(String)Cipher
        //   idx2: move-result-object v1
        //   idx3: return-void
        MethodReference getInstanceRef = new ImmutableMethodReference(
                CIPHER_DESC, "getInstance",
                List.of("Ljava/lang/String;"), CIPHER_DESC);
        List<ImmutableInstruction> body = new ArrayList<>();
        body.add(new ImmutableInstruction21c(
                Opcode.CONST_CLASS, 0,
                new ImmutableTypeReference("Ljava/lang/String;")));
        body.add(new ImmutableInstruction3rc(
                Opcode.INVOKE_STATIC_RANGE, /*startRegister=*/ 0,
                /*registerCount=*/ 1, getInstanceRef));
        body.add(new ImmutableInstruction11x(Opcode.MOVE_RESULT_OBJECT, 1));
        body.add(new ImmutableInstruction10x(Opcode.RETURN_VOID));
        DexFile dex = dexWithSingleMethod("gi", body);

        WrapperEmitter.WrapperEntry entry = new WrapperEmitter.WrapperEntry(
                "Cipher_getInstance", "javax.crypto.Cipher", "getInstance",
                List.of("java.lang.String"), "javax.crypto.Cipher",
                true /* static */);
        DexWeaver weaver = new DexWeaver(
                new EmitterDispatch(), new RegisterAllocator(), List.of(entry));

        Map<String, MutableMethodImplementation> muts = new HashMap<>();
        DexWeaver.WeaveReport report = weave(weaver, dex, emptyDescriptor(), muts);

        assertEquals(1, report.wrappersSubstituted(),
                "range invoke opcodes are accepted by findWrapperReplacement");

        MutableMethodImplementation mut = muts.get(FOO_DESC + "->gi()V");
        assertNotNull(mut);
        List<? extends Instruction> after = new ArrayList<>(mut.getInstructions());
        assertEquals(4, after.size());
        assertEquals(Opcode.INVOKE_STATIC_RANGE, after.get(1).getOpcode(),
                "range form is preserved (Format3rc → Format3rc)");
        Instruction3rc call = (Instruction3rc) after.get(1);
        assertEquals(0, call.getStartRegister(), "range start preserved");
        assertEquals(1, call.getRegisterCount(), "range width preserved");
        MethodReference ref = (MethodReference)
                ((ReferenceInstruction) call).getReference();
        assertEquals(WRAPPERS_DESC, ref.getDefiningClass());
        assertEquals("Cipher_getInstance", ref.getName());
        // Static wrapper: parameter list is the original's, NO receiver.
        assertEquals(List.of("Ljava/lang/String;"),
                new ArrayList<>(ref.getParameterTypes()),
                "static wrapper adds no implicit receiver formal");
        assertEquals(CIPHER_DESC, ref.getReturnType());
    }

    // ------------------------------------------------------------------
    // (5) lookup-key format: primitives, arrays, void
    // ------------------------------------------------------------------

    @Test
    void wrapperLookupKeyEncodesPrimitivesArraysAndVoid() throws Exception {
        // One instance wrapper whose signature exercises every fqnToDescriptor
        // arm: all 8 primitives, a rank-2 object array, and a void return.
        // Registration and call-site lookup both go through fqnToDescriptor /
        // refKey — if the two ever disagree on any of these encodings, the
        // wrapper silently stops matching its call sites (recall drops to 0
        // with no error), so the exact key format is contract, not detail.
        WrapperEmitter.WrapperEntry entry = new WrapperEmitter.WrapperEntry(
                "Sink_m", "com.example.Sink", "m",
                List.of("boolean", "byte", "short", "char", "int",
                        "long", "float", "double", "java.lang.String[][]"),
                "void", false /* instance */);
        DexWeaver weaver = new DexWeaver(
                new EmitterDispatch(), new RegisterAllocator(), List.of(entry));

        Map<String, MethodReference> table = readReplacements(weaver);
        String expectedKey = "Lcom/example/Sink;#m("
                + "Z,B,S,C,I,J,F,D,[[Ljava/lang/String;)V";
        MethodReference ref = table.get(expectedKey);
        assertNotNull(ref, "lookup key must use DEX descriptors: got keys "
                + table.keySet());
        assertEquals("Sink_m", ref.getName());
        // Instance wrapper formals: receiver descriptor first, then the
        // original parameters in DEX-descriptor form.
        assertEquals(
                List.of("Lcom/example/Sink;", "Z", "B", "S", "C", "I", "J",
                        "F", "D", "[[Ljava/lang/String;"),
                new ArrayList<>(ref.getParameterTypes()));
        assertEquals("V", ref.getReturnType(), "void return encodes as V");
    }

    // ------------------------------------------------------------------
    // fixture helpers
    // ------------------------------------------------------------------

    /** const-class v0 Cipher; const-class v1 [B; invoke-virtual {v0,v1} doFinal; move-result-object v2; return-void. */
    private static List<ImmutableInstruction> doFinalCallBody() {
        List<ImmutableInstruction> body = new ArrayList<>();
        body.add(new ImmutableInstruction21c(
                Opcode.CONST_CLASS, 0, new ImmutableTypeReference(CIPHER_DESC)));
        body.add(new ImmutableInstruction21c(
                Opcode.CONST_CLASS, 1, new ImmutableTypeReference("[B")));
        body.add(new ImmutableInstruction35c(
                Opcode.INVOKE_VIRTUAL, /*regCount=*/ 2,
                /*c=*/ 0, /*d=*/ 1, 0, 0, 0, DO_FINAL_REF));
        body.add(new ImmutableInstruction11x(Opcode.MOVE_RESULT_OBJECT, 2));
        body.add(new ImmutableInstruction10x(Opcode.RETURN_VOID));
        return body;
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

    /** Descriptor with no advices — wrapper substitution is descriptor-independent. */
    private static AspectDescriptor emptyDescriptor() {
        AspectDescriptor d = new AspectDescriptor();
        d.setShortName("MultiSpec_1");
        d.setImports(List.of("javax.crypto.Cipher"));
        return d;
    }

    /** One BEFORE advice on Cipher.doFinal(byte[]) binding args(input). */
    private static AspectDescriptor beforeDoFinalDescriptor() {
        AspectDescriptor d = new AspectDescriptor();
        d.setShortName("MultiSpec_1");
        d.setImports(List.of("javax.crypto.Cipher"));
        AdviceDescriptor advice = new AdviceDescriptor();
        advice.setName("d1");
        advice.setSpecName("CipherSpec");
        advice.setPosition("before");
        advice.setAround(false);
        advice.setReturnType("void");
        advice.setExpression(
                "call(public byte[] Cipher.doFinal(byte[])) && args(input)");
        advice.setParameters(List.of(new ParameterDescriptor("byte[]", "input")));
        MonitorCallDescriptor mc = new MonitorCallDescriptor();
        mc.setMethod("MultiSpec_1RuntimeMonitor.CipherSpec_d1Event");
        mc.setSpecName("CipherSpec");
        mc.setEventId("d1");
        mc.setUniqueId("u1");
        mc.setArgs(List.of("input"));
        advice.setMonitorCalls(List.of(mc));
        d.setAdvices(List.of(advice));
        return d;
    }

    private static DexWeaver.WeaveReport weave(
            DexWeaver weaver, DexFile dex, AspectDescriptor descriptor,
            Map<String, MutableMethodImplementation> muts) {
        TypeResolver typeResolver = new TypeResolver(descriptor.getImports());
        AndroidClassIndex emptyAndroid = new AndroidClassIndex(Path.of("/tmp/nope.jar"));
        InheritanceResolver inheritance = new InheritanceResolver(emptyAndroid, dex);
        DexWeaver.MutableImplSupplier supplier = method -> {
            if (method.getImplementation() == null) return null;
            String k = methodKey(method);
            MutableMethodImplementation existing = muts.get(k);
            if (existing != null) return existing;
            MutableMethodImplementation mut =
                    new MutableMethodImplementation(method.getImplementation());
            muts.put(k, mut);
            return mut;
        };
        return weaver.weave(dex, descriptor, typeResolver, inheritance, supplier);
    }

    private static String methodKey(Method m) {
        StringBuilder sb = new StringBuilder(64);
        sb.append(m.getDefiningClass()).append("->").append(m.getName()).append('(');
        for (CharSequence p : m.getParameterTypes()) sb.append(p);
        sb.append(')').append(m.getReturnType());
        return sb.toString();
    }

    @SuppressWarnings("unchecked")
    private static Map<String, MethodReference> readReplacements(DexWeaver w) throws Exception {
        Field f = DexWeaver.class.getDeclaredField("wrapperReplacements");
        f.setAccessible(true);
        return (Map<String, MethodReference>) f.get(w);
    }
}
