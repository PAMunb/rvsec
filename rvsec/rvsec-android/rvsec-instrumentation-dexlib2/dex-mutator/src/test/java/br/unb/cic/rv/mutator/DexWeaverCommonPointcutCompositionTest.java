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

/**
 * §4.D.0: the weaver AND-composes the descriptor's {@code commonPointcut} onto every advice match,
 * so the {@code BaseAspect.notwithin()} exclusions gate weaving by the woven class's package. A
 * class under an excluded package ({@code mop..*}) yields zero matches even when its call-site
 * signature matches the advice; a class outside all exclusions still matches; with no
 * {@code commonPointcut} the exclusion does not apply (proving the gate is the composition, not
 * something else).
 *
 * <p>This is a weaver unit test ({@code *Test}, not {@code *GrammarTest}) — outside INV-INS-92's
 * matrix-row bijection, mirroring {@code DexWeaverNestedTryCatchTest}.
 */
class DexWeaverCommonPointcutCompositionTest {

    private static final String IV_DESC = "Ljavax/crypto/spec/IvParameterSpec;";

    private static final List<String> CANONICAL_TWELVE = List.of(
            "sun..*", "java..*", "javax..*", "com.sun..*", "org.dacapo.harness..*",
            "org.apache.commons..*", "org.apache.geronimo..*", "net.sf.cglib..*",
            "mop..*", "javamoprt..*", "rvmonitorrt..*", "com.runtimeverification..*");

    @Test
    void classUnderExcludedPackageYieldsZeroMatches() {
        // mop..* is excluded by BaseAspect.notwithin() → the call-site match is filtered out.
        assertEquals(0, weave("Lmop/Internal;", true).matchesApplied(),
                "a class under mop..* must yield zero matches once commonPointcut is composed");
    }

    @Test
    void classOutsideExclusionsStillMatches() {
        // com.example..* is outside every exclusion → the match survives the composition.
        assertEquals(1, weave("Lcom/example/App;", true).matchesApplied(),
                "a class outside all exclusions must still match");
    }

    @Test
    void withoutCommonPointcutExclusionDoesNotApply() {
        // The SAME excluded-package class matches when no commonPointcut is composed — proving the
        // gate above is the commonPointcut composition, not an unrelated filter.
        assertEquals(1, weave("Lmop/Internal;", false).matchesApplied(),
                "without commonPointcut composition, even a mop..* class matches");
    }

    // --- fixture ---------------------------------------------------------------------------------

    /** Weave a one-class DEX whose {@code bar()} does {@code new IvParameterSpec([B])}, against an
     *  after-advice on that constructor. {@code withCommonPointcut} toggles the
     *  {@code BaseAspect.notwithin()} composition (§4.D.0). */
    private static DexWeaver.WeaveReport weave(String classDesc, boolean withCommonPointcut) {
        MethodReference initRef = new ImmutableMethodReference(IV_DESC, "<init>", List.of("[B"), "V");
        List<com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction> body =
                new ArrayList<>();
        body.add(new ImmutableInstruction21c(Opcode.NEW_INSTANCE, 0, new ImmutableTypeReference(IV_DESC)));
        body.add(new ImmutableInstruction21c(Opcode.CONST_CLASS, 1, new ImmutableTypeReference("[B")));
        body.add(new ImmutableInstruction35c(Opcode.INVOKE_DIRECT, 2, 0, 1, 0, 0, 0, initRef));
        body.add(new ImmutableInstruction10x(Opcode.RETURN_VOID));
        ImmutableMethodImplementation impl = new ImmutableMethodImplementation(
                4, body, Collections.emptyList(), Collections.emptyList());
        ImmutableMethod bar = new ImmutableMethod(classDesc, "bar", Collections.emptyList(), "V",
                AccessFlags.PUBLIC.getValue() | AccessFlags.STATIC.getValue(), null, null, impl);
        ClassDef cls = new ImmutableClassDef(classDesc, AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;", Collections.emptyList(), null, null,
                Collections.emptyList(), List.of(bar));
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), List.of(cls));

        AspectDescriptor descriptor = new AspectDescriptor();
        descriptor.setAspectName("MultiSpec_1MonitorAspect");
        descriptor.setShortName("MultiSpec_1");
        descriptor.setImports(List.of("javax.crypto.spec.IvParameterSpec"));
        if (withCommonPointcut) {
            descriptor.setCommonPointcut(
                    "!within(com.runtimeverification.rvmonitor.java.rt.RVMObject+) "
                            + "&& !adviceexecution() && BaseAspect.notwithin()");
            descriptor.setBaseAspectExclusions(CANONICAL_TWELVE);
        }
        AdviceDescriptor advice = new AdviceDescriptor();
        advice.setName("a1");
        advice.setSpecName("IvParameterSpecSpec");
        advice.setPosition("after");
        advice.setAround(false);
        advice.setReturnType("void");
        advice.setExpression("call(public IvParameterSpec.new(byte[])) && args(iv)");
        advice.setParameters(List.of(new ParameterDescriptor("byte[]", "iv")));
        MonitorCallDescriptor mc = new MonitorCallDescriptor();
        mc.setMethod("MultiSpec_1RuntimeMonitor.IvParameterSpecSpec_g1Event");
        mc.setSpecName("IvParameterSpecSpec");
        mc.setEventId("g1");
        mc.setUniqueId("u1");
        mc.setArgs(List.of("iv"));
        advice.setMonitorCalls(List.of(mc));
        descriptor.setAdvices(List.of(advice));

        TypeResolver typeResolver = new TypeResolver(descriptor.getImports());
        AndroidClassIndex emptyAndroid = new AndroidClassIndex(Path.of("/tmp/nope.jar"));
        InheritanceResolver inheritance = new InheritanceResolver(emptyAndroid, dex);
        Map<String, MutableMethodImplementation> muts = new HashMap<>();
        DexWeaver.MutableImplSupplier supplier = method -> {
            if (method.getImplementation() == null) return null;
            return muts.computeIfAbsent(method.getName(),
                    k -> new MutableMethodImplementation(method.getImplementation()));
        };

        DexWeaver weaver = new DexWeaver(new EmitterDispatch(), new RegisterAllocator());
        return weaver.weave(dex, descriptor, typeResolver, inheritance, supplier);
    }
}
