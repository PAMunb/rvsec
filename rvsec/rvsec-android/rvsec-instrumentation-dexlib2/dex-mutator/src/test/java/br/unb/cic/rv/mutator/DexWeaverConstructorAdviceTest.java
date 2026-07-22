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
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.iface.instruction.ReferenceInstruction;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableDexFile;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodImplementation;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction10x;
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
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * gh52 §5.13(a): inline-AFTER advice on constructor invokes.
 *
 * <p>Constructor calls ({@code invoke-direct {recv, ...args}, T.<init>(...)V})
 * return {@code void}, so they are never followed by {@code move-result*} —
 * the receiver and argument registers remain valid for an inline post-call
 * hook. The defensive AFTER-skip in {@link DexWeaver} (INV-INS-66) was over-
 * conservative for this case; the constructor branch lets these advices
 * apply inline (no wrapper, since a wrapper would have to allocate-and-
 * construct, changing call-site semantics).
 *
 * <p>The fixture builds a synthetic 1-class DEX:
 * <pre>
 *   class Foo {
 *     static void bar() {
 *       new IvParameterSpec(<some-byte-array-stored-in-v0>);
 *     }
 *   }
 * </pre>
 * with a descriptor that declares an after-advice on
 * {@code IvParameterSpec.new(byte[])} binding {@code args(iv)} →
 * {@code IvParameterSpecSpec_g1Event(byte[])}, and asserts the inline
 * monitor invoke lands immediately after the constructor.
 */
class DexWeaverConstructorAdviceTest {

    private static final String FOO_DESC = "LFoo;";
    private static final String IV_DESC  = "Ljavax/crypto/spec/IvParameterSpec;";
    private static final String MONITOR_DESC = "Lmop/MultiSpec_1RuntimeMonitor;";

    @Test
    void constructorAfterAdviceLandsInline() throws Exception {
        // 1. Synthetic method bar()V:
        //   new-instance v0, Ljavax/crypto/spec/IvParameterSpec;
        //   const v1, 0  (placeholder for byte[] reference; verifier-irrelevant
        //                  for our weave assertions — DexWeaver only inspects
        //                  the invoke's MethodReference + opcode)
        //   invoke-direct {v0, v1}, IvParameterSpec.<init>([B)V
        //   return-void
        //
        // We don't run the verifier on the synthetic — the test asserts the
        // weave report and the post-mutation instruction shape, which is what
        // gh52 §5.13(a) gates on.
        MethodReference initRef = new ImmutableMethodReference(
                IV_DESC, "<init>", List.of("[B"), "V");

        List<com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction> body = new ArrayList<>();
        body.add(new ImmutableInstruction21c(
                Opcode.NEW_INSTANCE, /*regA=*/ 0,
                new ImmutableTypeReference(IV_DESC)));
        body.add(new ImmutableInstruction21c(
                Opcode.CONST_CLASS, /*regA=*/ 1,
                new ImmutableTypeReference("[B")));
        body.add(new ImmutableInstruction35c(
                Opcode.INVOKE_DIRECT, /*regCount=*/ 2,
                /*c=*/ 0, /*d=*/ 1, /*e=*/ 0, /*f=*/ 0, /*g=*/ 0,
                initRef));
        body.add(new ImmutableInstruction10x(Opcode.RETURN_VOID));

        ImmutableMethodImplementation impl = new ImmutableMethodImplementation(
                /*registerCount=*/ 4,
                body,
                Collections.emptyList(),
                Collections.emptyList());
        ImmutableMethod barMethod = new ImmutableMethod(
                FOO_DESC, "bar",
                Collections.emptyList(),
                "V",
                AccessFlags.PUBLIC.getValue() | AccessFlags.STATIC.getValue(),
                null, null, impl);
        ClassDef foo = new ImmutableClassDef(
                FOO_DESC, AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;",
                Collections.emptyList(),
                null, null,
                Collections.emptyList(),
                List.of(barMethod));
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), List.of(foo));

        // 2. Descriptor: one after-advice on IvParameterSpec.new(byte[])
        AspectDescriptor descriptor = new AspectDescriptor();
        descriptor.setShortName("MultiSpec_1");
        descriptor.setImports(List.of("javax.crypto.spec.IvParameterSpec"));
        AdviceDescriptor advice = new AdviceDescriptor();
        advice.setName("a1");
        advice.setSpecName("IvParameterSpecSpec");
        advice.setPosition("after");
        advice.setAround(false);
        advice.setReturnType("void");
        advice.setExpression(
                "call(public IvParameterSpec.new(byte[])) && args(iv)");
        advice.setParameters(List.of(new ParameterDescriptor("byte[]", "iv")));
        MonitorCallDescriptor mc = new MonitorCallDescriptor();
        mc.setMethod("MultiSpec_1RuntimeMonitor.IvParameterSpecSpec_g1Event");
        mc.setSpecName("IvParameterSpecSpec");
        mc.setEventId("g1");
        mc.setUniqueId("u1");
        mc.setArgs(List.of("iv"));
        advice.setMonitorCalls(List.of(mc));
        descriptor.setAdvices(List.of(advice));

        // 3. Type resolver from descriptor imports; inheritance over the
        //    synthetic DEX with an empty android.jar (the matcher only needs
        //    descriptor-driven resolution for this advice).
        TypeResolver typeResolver = new TypeResolver(descriptor.getImports());
        AndroidClassIndex emptyAndroid = new AndroidClassIndex(Path.of("/tmp/nope.jar"));
        InheritanceResolver inheritance = new InheritanceResolver(emptyAndroid, dex);

        // 4. Mutable supplier — a tiny stand-in for DexFileMutator that just
        //    keeps a per-method MutableMethodImplementation. We assert against
        //    the mutable view directly to avoid a DexPool round-trip.
        Map<String, MutableMethodImplementation> mutsByKey = new HashMap<>();
        DexWeaver.MutableImplSupplier supplier = method -> {
            if (method.getImplementation() == null) return null;
            String k = methodKey(method);
            MutableMethodImplementation existing = mutsByKey.get(k);
            if (existing != null) return existing;
            MutableMethodImplementation mut =
                    new MutableMethodImplementation(method.getImplementation());
            mutsByKey.put(k, mut);
            return mut;
        };

        DexWeaver weaver = new DexWeaver(new EmitterDispatch(), new RegisterAllocator());
        DexWeaver.WeaveReport report = weaver.weave(
                dex, descriptor, typeResolver, inheritance, supplier);

        // 5. Assert the report counters.
        assertEquals(1, report.matchesApplied(),
                "exactly one constructor match expected");
        assertEquals(1, report.constructorInlineApplied(),
                "the matched ctor must take the inline-AFTER path");
        assertEquals(0, report.plansSkippedAliasing(),
                "no defensive skip for ctors (they don't alias move-result)");
        assertEquals(0, report.constructorInlineSkippedAliasing(),
                "the belt-and-suspenders alias check must not trigger for ctors");

        // 6. Assert the mutated method shape: 5 instructions
        //    (new-instance, const-class, invoke-direct, invoke-static, return-void).
        MutableMethodImplementation mut = mutsByKey.get(
                FOO_DESC + "->bar()V");
        assertNotNull(mut, "bar()V must have been materialized for mutation");
        List<? extends Instruction> after = new ArrayList<>(mut.getInstructions());
        assertEquals(5, after.size(),
                "expected new-instance, const-class, invoke-direct, "
                        + "invoke-static (monitor), return-void; got " + after.size());
        assertEquals(Opcode.NEW_INSTANCE, after.get(0).getOpcode());
        assertEquals(Opcode.INVOKE_DIRECT, after.get(2).getOpcode());
        // The inline-AFTER hook must land immediately after the constructor's
        // invoke-direct (no move-result intervenes — ctors return void).
        assertEquals(Opcode.INVOKE_STATIC, after.get(3).getOpcode(),
                "the monitor invoke-static must land at index 3");
        Instruction monitorInvoke = after.get(3);
        assertTrue(monitorInvoke instanceof ReferenceInstruction);
        MethodReference monitorRef = (MethodReference)
                ((ReferenceInstruction) monitorInvoke).getReference();
        assertEquals(MONITOR_DESC, monitorRef.getDefiningClass(),
                "monitor invoke must target the runtime monitor");
        assertEquals("IvParameterSpecSpec_g1Event", monitorRef.getName());
        assertEquals(Opcode.RETURN_VOID, after.get(4).getOpcode());
    }

    // ------------------------------------------------------------------
    // gh56 task 3.3: SecretKeySpec.<init> + returning(spec) — the canonical
    // bug shape from docs/20260514_erro.md. Before the fix the monitor invoke
    // emitted {v4, v3, v0} (with arg shift and literal-0 for returning),
    // producing VerifyError. After the fix the emit must be {v3, v0, v4}.
    // ------------------------------------------------------------------

    private static final String SECRET_KEY_SPEC_DESC =
            "Ljavax/crypto/spec/SecretKeySpec;";

    @Test
    void constructorAfterReturningEmitsRegistersInMonitorSignatureOrder() throws Exception {
        // Synthetic method shape mirrors br.unb.cic.cryptoapp.CipherUtil.aes:
        //
        //   new-instance v4, Ljavax/crypto/spec/SecretKeySpec;
        //   const-class v3, [B       (placeholder for the byte[] key)
        //   const-class v0, String   (placeholder for "AES")
        //   invoke-direct {v4, v3, v0}, SecretKeySpec.<init>([B, String)V
        //   return-void
        //
        // The const-class instructions stand in for whatever real expression
        // populated the registers; DexWeaver only reads the invoke's regs+ref
        // (verifier is not run against this synthetic).
        MethodReference initRef = new ImmutableMethodReference(
                SECRET_KEY_SPEC_DESC, "<init>",
                List.of("[B", "Ljava/lang/String;"),
                "V");

        List<com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction> body =
                new ArrayList<>();
        // new-instance v4
        body.add(new ImmutableInstruction21c(
                Opcode.NEW_INSTANCE, /*regA=*/ 4,
                new ImmutableTypeReference(SECRET_KEY_SPEC_DESC)));
        // placeholders for v3 (byte[]) and v0 (String) — values don't matter
        // to the matcher; only register numbers do.
        body.add(new ImmutableInstruction21c(
                Opcode.CONST_CLASS, /*regA=*/ 3,
                new ImmutableTypeReference("[B")));
        body.add(new ImmutableInstruction21c(
                Opcode.CONST_CLASS, /*regA=*/ 0,
                new ImmutableTypeReference("Ljava/lang/String;")));
        // invoke-direct {v4, v3, v0}, SecretKeySpec.<init>([B, String)V
        body.add(new ImmutableInstruction35c(
                Opcode.INVOKE_DIRECT, /*regCount=*/ 3,
                /*c=*/ 4, /*d=*/ 3, /*e=*/ 0, /*f=*/ 0, /*g=*/ 0,
                initRef));
        body.add(new ImmutableInstruction10x(Opcode.RETURN_VOID));

        ImmutableMethodImplementation impl = new ImmutableMethodImplementation(
                /*registerCount=*/ 8,
                body,
                Collections.emptyList(),
                Collections.emptyList());
        ImmutableMethod aesMethod = new ImmutableMethod(
                FOO_DESC, "aes",
                Collections.emptyList(), "V",
                AccessFlags.PUBLIC.getValue() | AccessFlags.STATIC.getValue(),
                null, null, impl);
        ClassDef foo = new ImmutableClassDef(
                FOO_DESC, AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;",
                Collections.emptyList(),
                null, null,
                Collections.emptyList(),
                List.of(aesMethod));
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), List.of(foo));

        // Descriptor: after-advice on SecretKeySpec.new(byte[], String) with
        // args(keyMaterial, keyAlgorithm) and returning(secretKeySpec).
        AspectDescriptor descriptor = new AspectDescriptor();
        descriptor.setShortName("MultiSpec_1");
        descriptor.setImports(List.of("javax.crypto.spec.SecretKeySpec"));
        AdviceDescriptor advice = new AdviceDescriptor();
        advice.setName("c1");
        advice.setSpecName("SecretKeySpecSpec");
        advice.setPosition("after");
        advice.setAround(false);
        advice.setReturnType("void");
        advice.setExpression(
                "call(public SecretKeySpec.new(byte[], String)) "
                        + "&& args(keyMaterial, keyAlgorithm)");
        advice.setParameters(List.of(
                new ParameterDescriptor("byte[]", "keyMaterial"),
                new ParameterDescriptor("String", "keyAlgorithm")));
        advice.setReturning(List.of(
                new ParameterDescriptor("SecretKeySpec", "secretKeySpec")));
        MonitorCallDescriptor mc = new MonitorCallDescriptor();
        mc.setMethod("MultiSpec_1RuntimeMonitor.SecretKeySpecSpec_c1Event");
        mc.setSpecName("SecretKeySpecSpec");
        mc.setEventId("c1");
        mc.setUniqueId("u1");
        mc.setArgs(List.of("keyMaterial", "keyAlgorithm", "secretKeySpec"));
        advice.setMonitorCalls(List.of(mc));
        descriptor.setAdvices(List.of(advice));

        TypeResolver typeResolver = new TypeResolver(descriptor.getImports());
        AndroidClassIndex emptyAndroid = new AndroidClassIndex(Path.of("/tmp/nope.jar"));
        InheritanceResolver inheritance = new InheritanceResolver(emptyAndroid, dex);

        Map<String, MutableMethodImplementation> mutsByKey = new HashMap<>();
        DexWeaver.MutableImplSupplier supplier = method -> {
            if (method.getImplementation() == null) return null;
            String k = methodKey(method);
            MutableMethodImplementation existing = mutsByKey.get(k);
            if (existing != null) return existing;
            MutableMethodImplementation mut =
                    new MutableMethodImplementation(method.getImplementation());
            mutsByKey.put(k, mut);
            return mut;
        };

        DexWeaver weaver = new DexWeaver(new EmitterDispatch(), new RegisterAllocator());
        DexWeaver.WeaveReport report = weaver.weave(
                dex, descriptor, typeResolver, inheritance, supplier);

        // Report assertions — the constructor + returning advice must apply
        // inline (NOT be skipped by plansSkippedUnresolvedBinding, which would
        // signal that resolveReturningRegister still failed for the ctor path).
        assertEquals(1, report.matchesApplied(),
                "the constructor+returning match must produce one emit");
        assertEquals(1, report.constructorInlineApplied(),
                "the constructor takes the inline-AFTER path");
        assertEquals(0, report.plansSkippedUnresolvedBinding(),
                "gh56 INV-INS-71: no binding may go unresolved for this fixture");

        // Mutated shape: 6 instructions (3 placeholders + invoke-direct +
        // invoke-static + return-void). Critical assertion: the monitor
        // invoke's register array MUST equal {3, 0, 4} (byte[], String,
        // SecretKeySpec) — NOT {4, 3, 0} which was the bug.
        MutableMethodImplementation mut = mutsByKey.get(FOO_DESC + "->aes()V");
        assertNotNull(mut, "aes()V must have been materialised for mutation");
        List<? extends Instruction> after = new ArrayList<>(mut.getInstructions());
        // The monitor invoke must land immediately after invoke-direct.
        int monitorIdx = -1;
        for (int i = 0; i < after.size(); i++) {
            if (after.get(i).getOpcode() == Opcode.INVOKE_STATIC) {
                monitorIdx = i;
                break;
            }
        }
        assertTrue(monitorIdx >= 0, "expected one invoke-static (the monitor) in the mutated body");
        Instruction monitorInvoke = after.get(monitorIdx);
        assertTrue(monitorInvoke instanceof ReferenceInstruction);
        MethodReference monitorRef = (MethodReference)
                ((ReferenceInstruction) monitorInvoke).getReference();
        assertEquals(MONITOR_DESC, monitorRef.getDefiningClass());
        assertEquals("SecretKeySpecSpec_c1Event", monitorRef.getName());
        // The monitor signature MUST be (byte[], String, SecretKeySpec)V —
        // matching the monitorCall.args order.
        assertEquals(List.of("[B", "Ljava/lang/String;", SECRET_KEY_SPEC_DESC),
                new ArrayList<>(monitorRef.getParameterTypes()),
                "monitor signature follows monitorCall.args order");

        // Type-to-register correspondence — the canonical anti-regression
        // assertion. The emitter is Format35c (3-arg, all regs < v16).
        assertTrue(monitorInvoke instanceof com.android.tools.smali.dexlib2.iface.instruction.formats.Instruction35c,
                "expected Format35c for a 3-arg invoke with low registers");
        com.android.tools.smali.dexlib2.iface.instruction.formats.Instruction35c i35 =
                (com.android.tools.smali.dexlib2.iface.instruction.formats.Instruction35c) monitorInvoke;
        assertEquals(3, i35.getRegisterCount());
        assertEquals(3, i35.getRegisterC(), "slot 0 (byte[]) MUST be v3, not v4 (the bug pattern)");
        assertEquals(0, i35.getRegisterD(), "slot 1 (String) MUST be v0, not v3");
        assertEquals(4, i35.getRegisterE(),
                "slot 2 (SecretKeySpec, returning) MUST be v4 — the freshly-constructed instance");
    }

    // ------------------------------------------------------------------
    // gh56 task 3.4 parity: IvParameterSpec.<init> + returning(iv) ensures
    // the fix applies to every constructor-typed spec, not only the
    // canonical SecretKeySpec shape. IvParameterSpec was documented as
    // affected in docs/20260514_erro.md §2.4 but absent from existing tests.
    // ------------------------------------------------------------------

    @Test
    void ivParameterSpecConstructorWithReturningResolvesToNewInstance() throws Exception {
        // Synthetic shape:
        //   new-instance v2, Ljavax/crypto/spec/IvParameterSpec;
        //   const-class v1, [B
        //   invoke-direct {v2, v1}, IvParameterSpec.<init>([B)V
        //   return-void
        MethodReference initRef = new ImmutableMethodReference(
                IV_DESC, "<init>", List.of("[B"), "V");

        List<com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction> body =
                new ArrayList<>();
        body.add(new ImmutableInstruction21c(
                Opcode.NEW_INSTANCE, /*regA=*/ 2,
                new ImmutableTypeReference(IV_DESC)));
        body.add(new ImmutableInstruction21c(
                Opcode.CONST_CLASS, /*regA=*/ 1,
                new ImmutableTypeReference("[B")));
        body.add(new ImmutableInstruction35c(
                Opcode.INVOKE_DIRECT, /*regCount=*/ 2,
                /*c=*/ 2, /*d=*/ 1, /*e=*/ 0, /*f=*/ 0, /*g=*/ 0,
                initRef));
        body.add(new ImmutableInstruction10x(Opcode.RETURN_VOID));

        ImmutableMethodImplementation impl = new ImmutableMethodImplementation(
                /*registerCount=*/ 4,
                body, Collections.emptyList(), Collections.emptyList());
        ImmutableMethod m = new ImmutableMethod(
                FOO_DESC, "iv",
                Collections.emptyList(), "V",
                AccessFlags.PUBLIC.getValue() | AccessFlags.STATIC.getValue(),
                null, null, impl);
        ClassDef foo = new ImmutableClassDef(
                FOO_DESC, AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;", Collections.emptyList(),
                null, null, Collections.emptyList(),
                List.of(m));
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), List.of(foo));

        AspectDescriptor descriptor = new AspectDescriptor();
        descriptor.setShortName("MultiSpec_1");
        descriptor.setImports(List.of("javax.crypto.spec.IvParameterSpec"));
        AdviceDescriptor advice = new AdviceDescriptor();
        advice.setName("g1");
        advice.setSpecName("IvParameterSpecSpec");
        advice.setPosition("after");
        advice.setAround(false);
        advice.setReturnType("void");
        advice.setExpression(
                "call(public IvParameterSpec.new(byte[])) && args(iv)");
        advice.setParameters(List.of(new ParameterDescriptor("byte[]", "iv")));
        advice.setReturning(List.of(
                new ParameterDescriptor("IvParameterSpec", "ivSpec")));
        MonitorCallDescriptor mc = new MonitorCallDescriptor();
        mc.setMethod("MultiSpec_1RuntimeMonitor.IvParameterSpecSpec_g1Event");
        mc.setSpecName("IvParameterSpecSpec");
        mc.setEventId("g1");
        mc.setUniqueId("u1");
        mc.setArgs(List.of("iv", "ivSpec"));
        advice.setMonitorCalls(List.of(mc));
        descriptor.setAdvices(List.of(advice));

        TypeResolver typeResolver = new TypeResolver(descriptor.getImports());
        AndroidClassIndex emptyAndroid = new AndroidClassIndex(Path.of("/tmp/nope.jar"));
        InheritanceResolver inheritance = new InheritanceResolver(emptyAndroid, dex);

        Map<String, MutableMethodImplementation> mutsByKey = new HashMap<>();
        DexWeaver.MutableImplSupplier supplier = method -> {
            if (method.getImplementation() == null) return null;
            String k = methodKey(method);
            MutableMethodImplementation existing = mutsByKey.get(k);
            if (existing != null) return existing;
            MutableMethodImplementation mutImpl =
                    new MutableMethodImplementation(method.getImplementation());
            mutsByKey.put(k, mutImpl);
            return mutImpl;
        };

        DexWeaver weaver = new DexWeaver(new EmitterDispatch(), new RegisterAllocator());
        DexWeaver.WeaveReport report = weaver.weave(
                dex, descriptor, typeResolver, inheritance, supplier);

        assertEquals(1, report.matchesApplied());
        assertEquals(1, report.constructorInlineApplied());
        assertEquals(0, report.plansSkippedUnresolvedBinding(),
                "no unresolved binding for IvParameterSpec.<init>+returning");

        MutableMethodImplementation mut = mutsByKey.get(FOO_DESC + "->iv()V");
        assertNotNull(mut);
        List<? extends Instruction> after = new ArrayList<>(mut.getInstructions());
        int monitorIdx = -1;
        for (int i = 0; i < after.size(); i++) {
            if (after.get(i).getOpcode() == Opcode.INVOKE_STATIC) {
                monitorIdx = i;
                break;
            }
        }
        assertTrue(monitorIdx >= 0);
        com.android.tools.smali.dexlib2.iface.instruction.formats.Instruction35c i35 =
                (com.android.tools.smali.dexlib2.iface.instruction.formats.Instruction35c)
                        after.get(monitorIdx);
        assertEquals(2, i35.getRegisterCount());
        assertEquals(1, i35.getRegisterC(), "slot 0 (byte[] iv) MUST be v1");
        assertEquals(2, i35.getRegisterD(),
                "slot 1 (IvParameterSpec ivSpec, returning) MUST be v2 — the new instance");
    }

    private static String methodKey(Method m) {
        StringBuilder sb = new StringBuilder(64);
        sb.append(m.getDefiningClass()).append("->").append(m.getName()).append('(');
        for (CharSequence p : m.getParameterTypes()) sb.append(p);
        sb.append(')').append(m.getReturnType());
        return sb.toString();
    }
}
