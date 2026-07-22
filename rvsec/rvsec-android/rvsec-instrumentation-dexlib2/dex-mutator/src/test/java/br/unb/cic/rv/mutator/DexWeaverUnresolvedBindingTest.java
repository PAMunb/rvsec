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
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction10x;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction35c;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;

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
 * Positive regression guard for {@code WeaveReport.plansSkippedUnresolvedBinding}
 * (INV-INS-71). Existing DexWeaver tests only assert the counter is {@code 0}
 * on the happy path; none drives it to {@code 1}. That leaves the counter — and
 * the skip behaviour it records — unguarded: a re-introduced literal-{@code v0}
 * fallback for unresolved bindings (the {@code docs/20260514_erro.md} VerifyError
 * vector) would drop the counter to {@code 0}, emit a type-mismatched monitor
 * invoke, and pass every existing test.
 *
 * <p>Here a {@code before} advice on {@code Cipher.init(int, Key)} binds
 * {@code args(opmode, key)}, but its {@code monitorCall.args} lists a third name
 * ({@code ghostBinding}) that no pointcut binding produces. {@code registersFor}
 * returns {@code null} for that name, {@code MonitorInvokeBuilder.buildInvoke}
 * raises {@code UnresolvedBindingException}, and {@code DexWeaver} MUST skip the
 * advice, increment the counter, and emit NO monitor invoke — never substitute
 * {@code v0}.
 */
class DexWeaverUnresolvedBindingTest {

    private static final String FOO_DESC = "LFoo;";
    private static final String CIPHER_DESC = "Ljavax/crypto/Cipher;";

    @Test
    void unresolvedMonitorCallArgIsSkippedAndCounted() {
        // Synthetic bar()V:
        //   invoke-virtual {v2, v3, v4}, Cipher.init(I, Key)V   (returns void)
        //   return-void
        // The verifier is not run — DexWeaver reads only the invoke's regs+ref.
        MethodReference initRef = new ImmutableMethodReference(
                CIPHER_DESC, "init",
                List.of("I", "Ljava/security/Key;"), "V");

        List<com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction> body =
                new ArrayList<>();
        body.add(new ImmutableInstruction35c(
                Opcode.INVOKE_VIRTUAL, /*regCount=*/ 3,
                /*c=*/ 2, /*d=*/ 3, /*e=*/ 4, /*f=*/ 0, /*g=*/ 0,
                initRef));
        body.add(new ImmutableInstruction10x(Opcode.RETURN_VOID));

        ImmutableMethodImplementation impl = new ImmutableMethodImplementation(
                /*registerCount=*/ 6, body,
                Collections.emptyList(), Collections.emptyList());
        ImmutableMethod bar = new ImmutableMethod(
                FOO_DESC, "bar", Collections.emptyList(), "V",
                AccessFlags.PUBLIC.getValue() | AccessFlags.STATIC.getValue(),
                null, null, impl);
        ClassDef foo = new ImmutableClassDef(
                FOO_DESC, AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;", Collections.emptyList(),
                null, null, Collections.emptyList(), List.of(bar));
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), List.of(foo));

        // before-advice on Cipher.init(int, Key) with args(opmode, key), but the
        // monitorCall references a THIRD name that no binding produces.
        AspectDescriptor descriptor = new AspectDescriptor();
        descriptor.setShortName("MultiSpec_1");
        descriptor.setImports(List.of("javax.crypto.Cipher", "java.security.Key"));
        AdviceDescriptor advice = new AdviceDescriptor();
        advice.setName("e1");
        advice.setSpecName("CipherSpec");
        advice.setPosition("before");
        advice.setAround(false);
        advice.setReturnType("void");
        advice.setExpression("call(public void Cipher.init(int, Key)) && args(opmode, key)");
        advice.setParameters(List.of(
                new ParameterDescriptor("int", "opmode"),
                new ParameterDescriptor("Key", "key")));
        MonitorCallDescriptor mc = new MonitorCallDescriptor();
        mc.setMethod("MultiSpec_1RuntimeMonitor.CipherSpec_e1Event");
        mc.setSpecName("CipherSpec");
        mc.setEventId("e1");
        mc.setUniqueId("u1");
        mc.setArgs(List.of("opmode", "key", "ghostBinding"));
        advice.setMonitorCalls(List.of(mc));
        descriptor.setAdvices(List.of(advice));

        TypeResolver typeResolver = new TypeResolver(descriptor.getImports());
        AndroidClassIndex emptyAndroid = new AndroidClassIndex(Path.of("/tmp/nope.jar"));
        InheritanceResolver inheritance = new InheritanceResolver(emptyAndroid, dex);

        Map<String, MutableMethodImplementation> mutsByKey = new HashMap<>();
        DexWeaver.MutableImplSupplier supplier = method -> {
            if (method.getImplementation() == null) return null;
            String k = FOO_DESC + "->bar()V";
            return mutsByKey.computeIfAbsent(k,
                    kk -> new MutableMethodImplementation(method.getImplementation()));
        };

        DexWeaver weaver = new DexWeaver(new EmitterDispatch(), new RegisterAllocator());
        DexWeaver.WeaveReport report = weaver.weave(
                dex, descriptor, typeResolver, inheritance, supplier);

        // The counter records exactly one skip.
        assertEquals(1, report.plansSkippedUnresolvedBinding(),
                "the unresolvable monitorCall arg must be counted, not v0-substituted");
        assertEquals(0, report.matchesApplied(),
                "a skipped advice must not count as an applied match");

        // No monitor invoke may be emitted. DexWeaver only asks the supplier to
        // materialise a mutable body when an advice is actually applied; the
        // skip short-circuits before that, so the supplier is never touched. A
        // v0-fallback regression would instead apply the advice and inject an
        // invoke-static, materialising the method here.
        assertTrue(mutsByKey.isEmpty(),
                "a skipped advice must not materialise or mutate the method body");
    }
}
