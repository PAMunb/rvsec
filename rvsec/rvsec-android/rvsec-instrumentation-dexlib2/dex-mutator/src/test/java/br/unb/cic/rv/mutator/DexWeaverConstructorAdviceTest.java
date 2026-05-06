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

    private static String methodKey(Method m) {
        StringBuilder sb = new StringBuilder(64);
        sb.append(m.getDefiningClass()).append("->").append(m.getName()).append('(');
        for (CharSequence p : m.getParameterTypes()) sb.append(p);
        sb.append(')').append(m.getReturnType());
        return sb.toString();
    }
}
