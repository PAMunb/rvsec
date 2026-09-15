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
import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.iface.instruction.ReferenceInstruction;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableDexFile;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodImplementation;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodParameter;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction11x;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction35c;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIf;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * INV-INS-160 at the invoke: a call whose static owner is a framework subtype of a
 * wrapped owner, with no wrapper of its own, is routed to the wrapper that carries
 * the advices admitting it — the one registered for the most specific wrapped owner
 * — and never trips the rebinding guard of {@code DexWeaver.registerWrapper}.
 */
class DexWeaverFrameworkSubtypeAliasTest {

    private static Path androidJar;

    @BeforeAll
    static void resolveAndroidJar() {
        String home = System.getenv("ANDROID_HOME");
        if (home == null || home.isEmpty()) return;
        Path platforms = Path.of(home, "platforms");
        if (!Files.isDirectory(platforms)) return;
        try (Stream<Path> levels = Files.list(platforms)) {
            androidJar = levels
                    .filter(Files::isDirectory)
                    .map(p -> p.resolve("android.jar"))
                    .filter(Files::isRegularFile)
                    .max((a, b) -> a.getParent().getFileName().toString()
                            .compareTo(b.getParent().getFileName().toString()))
                    .orElse(null);
        } catch (IOException ex) {
            androidJar = null;
        }
    }

    static boolean hasAndroidJar() {
        return androidJar != null;
    }

    /** Spec scenario "a framework subtype of a wrapped owner is aliased". */
    @Test
    @EnabledIf("hasAndroidJar")
    void publicKeyGetEncodedIsWovenWithTheKeyAdvice(@TempDir Path wrappersDir) throws Exception {
        AspectDescriptor descriptor = descriptor(List.of(keyGetEncodedAdvice()));
        AndroidClassIndex index = new AndroidClassIndex(androidJar);
        WrapperEmitter.EmitResult emitted = WrapperEmitter.generate(descriptor, wrappersDir, index);

        DexFile dex = getEncodedCaller("Ljava/security/PublicKey;", Opcode.INVOKE_INTERFACE);
        DexWeaverNestedTryCatchTest.TrackingSupplier supplier =
                new DexWeaverNestedTryCatchTest.TrackingSupplier();
        DexWeaver weaver = new DexWeaver(new EmitterDispatch(), new RegisterAllocator(),
                emitted.wrappers());
        InheritanceResolver inheritance = new InheritanceResolver(index, dex);
        weaver.expandWrapperReplacementsForApk(inheritance);
        DexWeaver.WeaveReport report = weaver.weave(dex, descriptor,
                new TypeResolver(descriptor.getImports()), inheritance, supplier);

        assertEquals(1, report.wrappersSubstituted(), "the PublicKey invoke is replaced");
        assertEquals(1, report.wrappersAliasedToSubtype());
        assertEquals(0, report.wrapperAliasesUnmerged());

        MethodReference routed = substitutedCall(supplier);
        assertEquals(WrapperEmitter.WRAPPER_CLASS_DESC, routed.getDefiningClass());
        assertEquals(List.of("Ljava/security/Key;"), List.copyOf(routed.getParameterTypes()),
                "the wrapper's receiver formal is the wrapped owner, a supertype of PublicKey");
        String source = Files.readString(
                wrappersDir.resolve("mop").resolve("MonitorWrappers.java"));
        assertTrue(wrapperBody(source, routed.getName()).contains("KeySpec_ge1Event("),
                "the routed wrapper fires KeySpec_ge1Event");
    }

    @Test
    @EnabledIf("hasAndroidJar")
    void theMostSpecificWrappedOwnerIsChosen() {
        // SecretKeySpec is assignable to both SecretKey and Key; SecretKey is the most
        // specific wrapped owner, and its wrapper carries the Key+ advices too.
        List<WrapperEmitter.WrapperEntry> wrappers = List.of(
                new WrapperEmitter.WrapperEntry("wrapKey", "java.security.Key",
                        "getEncoded", List.of(), "byte[]", false),
                new WrapperEmitter.WrapperEntry("wrapSecretKey", "javax.crypto.SecretKey",
                        "getEncoded", List.of(), "byte[]", false));
        DexFile dex = getEncodedCaller("Ljavax/crypto/spec/SecretKeySpec;", Opcode.INVOKE_VIRTUAL);
        DexWeaverNestedTryCatchTest.TrackingSupplier supplier =
                new DexWeaverNestedTryCatchTest.TrackingSupplier();
        DexWeaver weaver = new DexWeaver(new EmitterDispatch(), new RegisterAllocator(), wrappers);
        DexWeaver.WeaveReport report = weaver.weave(dex, descriptor(List.of()),
                new TypeResolver(List.of()),
                new InheritanceResolver(new AndroidClassIndex(androidJar), dex), supplier);

        assertEquals(1, report.wrappersSubstituted());
        assertEquals("wrapSecretKey", substitutedCall(supplier).getName());
    }

    @Test
    void ownersWithoutAMostSpecificWrapperAreCountedAndLeftUnwoven() {
        // T implements A and B, both wrapped for m()V, and neither is a subtype of the
        // other: no registered wrapper fires both advices. APK-defined types stand in
        // for framework types, which reach the same lookup when expansion has not keyed
        // them.
        ClassDef a = type("LA;", "Ljava/lang/Object;", List.of(), AccessFlags.INTERFACE.getValue());
        ClassDef b = type("LB;", "Ljava/lang/Object;", List.of(), AccessFlags.INTERFACE.getValue());
        ClassDef t = type("LT;", "Ljava/lang/Object;", List.of("LA;", "LB;"), 0);
        DexFile caller = getEncodedCaller("LT;", Opcode.INVOKE_VIRTUAL);
        List<ClassDef> classes = new ArrayList<>(List.of(a, b, t));
        caller.getClasses().forEach(classes::add);
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), classes);

        List<WrapperEmitter.WrapperEntry> wrappers = List.of(
                new WrapperEmitter.WrapperEntry("wrapA", "A", "getEncoded", List.of(), "byte[]", false),
                new WrapperEmitter.WrapperEntry("wrapB", "B", "getEncoded", List.of(), "byte[]", false));
        DexWeaver weaver = new DexWeaver(new EmitterDispatch(), new RegisterAllocator(), wrappers);
        DexWeaver.WeaveReport report = weaver.weave(dex, descriptor(List.of()),
                new TypeResolver(List.of()),
                new InheritanceResolver(new AndroidClassIndex(Path.of("/tmp/nope.jar")), dex),
                new DexWeaverNestedTryCatchTest.TrackingSupplier());

        assertEquals(0, report.wrappersSubstituted());
        assertEquals(1, report.wrapperAliasesUnmerged());
    }

    // --- fixtures -----------------------------------------------------------

    /** {@code static byte[] enc(Owner k) { return k.getEncoded(); }} in class {@code LFoo;}. */
    private static DexFile getEncodedCaller(String ownerDesc, Opcode invoke) {
        MethodReference getEncoded = new ImmutableMethodReference(ownerDesc, "getEncoded",
                List.of(), "[B");
        List<ImmutableInstruction> body = List.of(
                new ImmutableInstruction35c(invoke, 1, 1, 0, 0, 0, 0, getEncoded),
                new ImmutableInstruction11x(Opcode.MOVE_RESULT_OBJECT, 0),
                new ImmutableInstruction11x(Opcode.RETURN_OBJECT, 0));
        ImmutableMethod enc = new ImmutableMethod("LFoo;", "enc",
                List.of(new ImmutableMethodParameter(ownerDesc, null, null)), "[B",
                AccessFlags.PUBLIC.getValue() | AccessFlags.STATIC.getValue(), null, null,
                new ImmutableMethodImplementation(2, body, null, null));
        ClassDef foo = new ImmutableClassDef("LFoo;", AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;", Collections.emptyList(), null, null,
                Collections.emptyList(), List.of(enc));
        return new ImmutableDexFile(Opcodes.getDefault(), List.of(foo));
    }

    private static ClassDef type(String desc, String superclass, List<String> interfaces, int flags) {
        return new ImmutableClassDef(desc, AccessFlags.PUBLIC.getValue() | flags, superclass,
                interfaces, null, null, null, null);
    }

    private static MethodReference substitutedCall(DexWeaverNestedTryCatchTest.TrackingSupplier supplier) {
        MutableMethodImplementation mut = supplier.muts.get("LFoo;->enc(" + firstParam(supplier) + ")[B");
        BuilderInstruction first = mut.getInstructions().get(0);
        assertEquals(Opcode.INVOKE_STATIC, first.getOpcode());
        return (MethodReference) ((ReferenceInstruction) first).getReference();
    }

    private static String firstParam(DexWeaverNestedTryCatchTest.TrackingSupplier supplier) {
        String key = supplier.muts.keySet().iterator().next();
        return key.substring(key.indexOf('(') + 1, key.indexOf(')'));
    }

    private static String wrapperBody(String source, String wrapperName) {
        int start = source.indexOf(" " + wrapperName + "(");
        assertTrue(start >= 0, "wrapper " + wrapperName + " is in MonitorWrappers.java");
        int end = source.indexOf("\n    }", start);
        return source.substring(start, end);
    }

    /** {@code after(Key k) returning(byte[] material): call(public byte[] Key+.getEncoded()) && target(k)}. */
    private static AdviceDescriptor keyGetEncodedAdvice() {
        AdviceDescriptor advice = new AdviceDescriptor();
        advice.setName("ge1");
        advice.setSpecName("KeySpec");
        advice.setPosition("after");
        advice.setAround(false);
        advice.setReturnType("void");
        advice.setExpression("call(public byte[] Key+.getEncoded()) && target(k)");
        advice.setParameters(List.of(new ParameterDescriptor("Key", "k")));
        advice.setReturning(List.of(new ParameterDescriptor("byte[]", "material")));
        MonitorCallDescriptor mc = new MonitorCallDescriptor();
        mc.setMethod("MultiSpec_1RuntimeMonitor.KeySpec_ge1Event");
        mc.setSpecName("KeySpec");
        mc.setEventId("ge1");
        mc.setUniqueId("u1");
        mc.setArgs(List.of("k", "material"));
        advice.setMonitorCalls(List.of(mc));
        return advice;
    }

    private static AspectDescriptor descriptor(List<AdviceDescriptor> advices) {
        AspectDescriptor descriptor = new AspectDescriptor();
        descriptor.setShortName("MultiSpec_1");
        descriptor.setImports(List.of("java.security.Key"));
        descriptor.setAdvices(advices);
        return descriptor;
    }
}
