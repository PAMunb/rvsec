package br.unb.cic.rv.grammar;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.AspectDescriptor;
import br.unb.cic.rv.descriptor.MonitorCallDescriptor;
import br.unb.cic.rv.emitter.EmitterDispatch;
import br.unb.cic.rv.mutator.DexFileMutator;
import br.unb.cic.rv.mutator.DexWeaver;
import br.unb.cic.rv.mutator.RegisterAllocator;
import br.unb.cic.rv.pointcut.AndroidClassIndex;
import br.unb.cic.rv.pointcut.InheritanceResolver;
import br.unb.cic.rv.pointcut.TypeResolver;

import com.android.tools.smali.dexlib2.AccessFlags;
import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedClassDef;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedMethod;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.iface.instruction.ReferenceInstruction;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.iface.reference.TypeReference;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableDexFile;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodImplementation;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction10x;
import com.android.tools.smali.dexlib2.writer.pool.DexPool;

import org.junit.jupiter.api.Test;

import java.io.BufferedInputStream;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Backs the matrix row "{@code staticinitialization(T+)} synthesis + Signature
 * delivery" (§4.Y).
 *
 * <p>The generic_new corpus carries three staticinit advices whose body invokes
 * {@code thisJoinPoint.getStaticPart().getSignature()} and forwards the result
 * to {@code *staticinitEvent(Signature)} (see
 * {@code compiled-aj-fixtures/generic_new/MultiSpec_1MonitorAspect.aj:260,319,328}).
 * Because the staticinit matcher gates on a class' {@code <clinit>}, a matching
 * class with no class initializer is never instrumented by the per-method weave
 * loop. §4.Y synthesizes a {@code <clinit>} (and prepends into an existing one)
 * carrying the Signature delivery sequence.
 *
 * <p>These tests run the FULL dexlib2 weave + {@code DexPool} serialization +
 * re-parse so the assertions prove the synthesis genuinely survives DEX
 * serialization (not merely an in-memory mutable view), and that the
 * {@code const-class} operand is exactly the matched class — the legitimate
 * dex-level proof that {@code ClassSignature.getDeclaringType()} returns
 * {@code Foo.class} at runtime.
 */
class StaticInitializationGrammarTest {

    private static final String COLL_DESC = "Ljava/util/Collection;";
    private static final String CLASS_SIGNATURE_DESC = "Lorg/aspectj/lang/ClassSignature;";
    private static final String SIGNATURE_DESC = "Lorg/aspectj/lang/Signature;";
    private static final String MONITOR_DESC = "Lmop/MultiSpec_1RuntimeMonitor;";
    private static final String EVENT = "Collection_HashCode_staticinitEvent";

    /**
     * §4.Y.6: a class implementing {@code java.util.Collection} (a Collection+
     * subtype) with NO {@code <clinit>} gets one synthesized; the synthesized
     * body delivers a {@code ClassSignature} over the matched class to
     * {@code staticinitEvent(Signature)}, and survives serialization.
     */
    @Test
    void signatureDeliveryForStaticinitEvent() throws Exception {
        String matchedClass = "Lcom/example/MyColl;";
        DexFile woven = weaveStaticInit(matchedClass, /*withExistingClinit=*/ false);

        DexBackedClassDef parsed = findClass(woven, matchedClass);
        DexBackedMethod clinit = findMethod(parsed, "<clinit>");
        assertNotNull(clinit,
                "a <clinit> must be synthesized for a Collection+ class that had none "
                        + "(synthesis must genuinely survive DexPool serialization)");

        List<Instruction> body = instructionsOf(clinit);
        // const-class, new-instance, invoke-direct(<init>), invoke-static(event), return-void
        assertEquals(5, body.size(),
                "synthesized <clinit> = const-class + new-instance + invoke-direct + "
                        + "invoke-static + return-void; got " + opcodes(body));

        // (a) const-class operand == the matched class (the dex-level proof that
        // getDeclaringType() == MyColl.class at runtime).
        assertEquals(Opcode.CONST_CLASS, body.get(0).getOpcode());
        TypeReference constClassRef = (TypeReference)
                ((ReferenceInstruction) body.get(0)).getReference();
        assertEquals(matchedClass, constClassRef.getType(),
                "const-class operand MUST be the matched class — proves "
                        + "ClassSignature.getDeclaringType() returns exactly that class");

        // (b) new-instance Lorg/aspectj/lang/ClassSignature;
        assertEquals(Opcode.NEW_INSTANCE, body.get(1).getOpcode());
        assertEquals(CLASS_SIGNATURE_DESC,
                ((TypeReference) ((ReferenceInstruction) body.get(1)).getReference()).getType());

        // (c) invoke-direct ClassSignature.<init>(Ljava/lang/Class;)V
        assertEquals(Opcode.INVOKE_DIRECT, body.get(2).getOpcode());
        MethodReference initRef = (MethodReference)
                ((ReferenceInstruction) body.get(2)).getReference();
        assertEquals(CLASS_SIGNATURE_DESC, initRef.getDefiningClass());
        assertEquals("<init>", initRef.getName());
        assertEquals(List.of("Ljava/lang/Class;"),
                new ArrayList<>(initRef.getParameterTypes()),
                "ClassSignature.<init> takes a live java.lang.Class (NOT a String FQN)");

        // (d) invoke-static <monitor>.<event>(Lorg/aspectj/lang/Signature;)V
        assertEquals(Opcode.INVOKE_STATIC, body.get(3).getOpcode());
        MethodReference eventRef = (MethodReference)
                ((ReferenceInstruction) body.get(3)).getReference();
        assertEquals(MONITOR_DESC, eventRef.getDefiningClass());
        assertEquals(EVENT, eventRef.getName());
        assertEquals(List.of(SIGNATURE_DESC),
                new ArrayList<>(eventRef.getParameterTypes()),
                "staticinitEvent receives a Signature");

        assertEquals(Opcode.RETURN_VOID, body.get(4).getOpcode());
    }

    /**
     * §4.Y.3: {@code staticinitialization(Collection+)} matches by SUBTYPE — a
     * class merely implementing the interface (not equal to it) triggers
     * synthesis. Asserts the synthesis path via the same serialize+reparse
     * proof.
     */
    @Test
    void staticinitializationTSubtype() throws Exception {
        // MySubColl extends MyColl which implements Collection — a transitive
        // subtype, so Collection+ must still match.
        String matchedClass = "Lcom/example/MySubColl;";
        DexFile woven = weaveSubtypeChain(matchedClass);

        DexBackedClassDef parsed = findClass(woven, matchedClass);
        DexBackedMethod clinit = findMethod(parsed, "<clinit>");
        assertNotNull(clinit,
                "Collection+ must match a transitive subtype and synthesize its <clinit>");
        List<Instruction> body = instructionsOf(clinit);
        assertEquals(Opcode.CONST_CLASS, body.get(0).getOpcode());
        TypeReference constClassRef = (TypeReference)
                ((ReferenceInstruction) body.get(0)).getReference();
        assertEquals(matchedClass, constClassRef.getType(),
                "const-class operand MUST be the transitive-subtype class itself");
        assertEquals(Opcode.INVOKE_STATIC, body.get(3).getOpcode());
    }

    // --- fixture -----------------------------------------------------------------------------------

    /** Run the §4.Y weave on a single Collection+ class and return the serialized+reparsed dex. */
    private static DexFile weaveStaticInit(String matchedClass, boolean withExistingClinit)
            throws Exception {
        List<Method> methods = new ArrayList<>();
        // A trivial no-op instance method so the class is non-empty.
        methods.add(noopMethod(matchedClass, "m"));
        if (withExistingClinit) {
            methods.add(existingClinit(matchedClass));
        }
        ClassDef coll = new ImmutableClassDef(
                matchedClass, AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;",
                List.of(COLL_DESC),   // implements java.util.Collection
                null, null,
                Collections.emptyList(),
                methods);
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), List.of(coll));
        return runWeave(dex);
    }

    /** Build a Collection+ → subclass chain and weave the leaf subtype. */
    private static DexFile weaveSubtypeChain(String leafClass) throws Exception {
        String parent = "Lcom/example/MyColl;";
        ClassDef collParent = new ImmutableClassDef(
                parent, AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;",
                List.of(COLL_DESC),
                null, null, Collections.emptyList(),
                List.of(noopMethod(parent, "m")));
        ClassDef leaf = new ImmutableClassDef(
                leafClass, AccessFlags.PUBLIC.getValue(),
                parent,                // extends MyColl
                null, null, null, Collections.emptyList(),
                List.of(noopMethod(leafClass, "n")));
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), List.of(collParent, leaf));
        return runWeave(dex);
    }

    private static DexFile runWeave(DexFile dex) throws Exception {
        AspectDescriptor descriptor = new AspectDescriptor();
        descriptor.setShortName("MultiSpec_1");
        descriptor.setImports(List.of("java.util.Collection"));
        AdviceDescriptor advice = new AdviceDescriptor();
        advice.setName("Collection_HashCode_staticinit");
        advice.setSpecName("Collection_HashCode");
        advice.setPosition("after");
        advice.setAround(false);
        advice.setReturnType("void");
        advice.setParameters(Collections.emptyList());
        advice.setExpression("staticinitialization(java.util.Collection+)");
        MonitorCallDescriptor mc = new MonitorCallDescriptor();
        mc.setMethod("MultiSpec_1RuntimeMonitor." + EVENT);
        mc.setSpecName("Collection_HashCode");
        mc.setEventId("staticinit");
        mc.setUniqueId("u1");
        mc.setArgs(List.of("thisJoinPoint.getStaticPart().getSignature()"));
        advice.setMonitorCalls(List.of(mc));
        descriptor.setAdvices(List.of(advice));

        TypeResolver typeResolver = new TypeResolver(descriptor.getImports());
        AndroidClassIndex emptyAndroid = new AndroidClassIndex(Path.of("/tmp/nope.jar"));
        InheritanceResolver inheritance = new InheritanceResolver(emptyAndroid, dex);

        DexFileMutator mutator = new DexFileMutator(dex);
        // Bridge the weaver's supplier to the mutator (production wiring shape).
        DexWeaver.MutableImplSupplier supplier = new DexWeaver.MutableImplSupplier() {
            @Override
            public MutableMethodImplementation forMethod(Method m) {
                return mutator.forMethod(m);
            }
            @Override
            public void replaceImpl(Method m, MutableMethodImplementation impl) {
                mutator.replaceImpl(m, impl);
            }
            @Override
            public void addSynthesizedMethod(String def, Method m) {
                mutator.addSynthesizedMethod(def, m);
            }
        };

        DexWeaver weaver = new DexWeaver(new EmitterDispatch(), new RegisterAllocator());
        weaver.weave(dex, descriptor, typeResolver, inheritance, supplier);

        Path tmp = Files.createTempFile("gh62-staticinit-", ".dex");
        try {
            DexPool.writeTo(tmp.toString(), mutator.toDexFile());
            try (InputStream in = new BufferedInputStream(Files.newInputStream(tmp))) {
                return DexBackedDexFile.fromInputStream(Opcodes.getDefault(), in);
            }
        } finally {
            Files.deleteIfExists(tmp);
        }
    }

    private static Method noopMethod(String owner, String name) {
        ImmutableMethodImplementation impl = new ImmutableMethodImplementation(
                1, List.of(new ImmutableInstruction10x(Opcode.RETURN_VOID)),
                Collections.emptyList(), Collections.emptyList());
        return new ImmutableMethod(owner, name, Collections.emptyList(), "V",
                AccessFlags.PUBLIC.getValue(), null, null, impl);
    }

    private static Method existingClinit(String owner) {
        ImmutableMethodImplementation impl = new ImmutableMethodImplementation(
                1, List.of(new ImmutableInstruction10x(Opcode.RETURN_VOID)),
                Collections.emptyList(), Collections.emptyList());
        return new ImmutableMethod(owner, "<clinit>", Collections.emptyList(), "V",
                AccessFlags.STATIC.getValue() | AccessFlags.CONSTRUCTOR.getValue(),
                null, null, impl);
    }

    private static DexBackedClassDef findClass(DexFile dex, String desc) {
        for (ClassDef cd : dex.getClasses()) {
            if (desc.equals(cd.getType())) return (DexBackedClassDef) cd;
        }
        throw new AssertionError("class " + desc + " not found in parsed dex");
    }

    private static DexBackedMethod findMethod(DexBackedClassDef cd, String name) {
        for (DexBackedMethod m : cd.getMethods()) {
            if (name.equals(m.getName())) return m;
        }
        return null;
    }

    private static List<Instruction> instructionsOf(Method m) {
        List<Instruction> out = new ArrayList<>();
        for (Instruction ins : m.getImplementation().getInstructions()) out.add(ins);
        return out;
    }

    private static List<Opcode> opcodes(List<Instruction> body) {
        List<Opcode> ops = new ArrayList<>();
        for (Instruction i : body) ops.add(i.getOpcode());
        return ops;
    }
}
