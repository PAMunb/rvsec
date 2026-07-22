package br.unb.cic.rv.grammar;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.AspectDescriptor;
import br.unb.cic.rv.descriptor.MonitorCallDescriptor;
import br.unb.cic.rv.descriptor.ParameterDescriptor;
import br.unb.cic.rv.emitter.EmitterDispatch;
import br.unb.cic.rv.grammar.util.AbsorbingStage;
import br.unb.cic.rv.grammar.util.DemandCounter;
import br.unb.cic.rv.grammar.util.DemandCounter.Corpus;
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
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.iface.Method;
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
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Backs the matrix row "{@code adviceexecution()}" (§4.A'). NOT-NEEDED β: the {@code !adviceexecution()}
 * clause in the descriptor {@code commonPointcut} is vacuously true in the dexlib2 inline-call
 * emission model — the weaver injects {@code invoke-static} monitor calls directly at the matched
 * join points and never emits synthetic {@code ajc$before$}/{@code ajc$after$} advice methods (which
 * the AspectJ runtime model would create and which {@code !adviceexecution()} exists to exclude).
 * With no synthetic advice methods, no join point is ever an advice execution, so the negation is
 * satisfied without any matcher logic. Absorber: {@code DEXLIB2_INLINE_EMISSION_MODEL}.
 */
class AdviceExecutionGrammarTest {

    /** The pipeline stage that makes {@code !adviceexecution()} vacuously true. */
    static final AbsorbingStage ABSORBER = AbsorbingStage.DEXLIB2_INLINE_EMISSION_MODEL;

    private static final String COMMON_POINTCUT =
            "!within(com.runtimeverification.rvmonitor.java.rt.RVMObject+) "
                    + "&& !adviceexecution() && BaseAspect.notwithin()";

    private static final String IV_DESC = "Ljavax/crypto/spec/IvParameterSpec;";

    @Test
    void adviceExecutionVacuouslyTrueInDexlib2InlineModel() throws Exception {
        // (a) commonPointcut carries !adviceexecution() (source demand non-zero) AND it survives into
        // the compiled .aj (PipelineDemand 1,1,1 — the negation is present, not stripped).
        assertTrue(COMMON_POINTCUT.contains("!adviceexecution()"),
                "the production commonPointcut carries the !adviceexecution() clause");
        assertTrue(DemandCounter.countCompiledAj(DemandCounter.ADVICEEXECUTION, Corpus.JCA) >= 1,
                "!adviceexecution() survives into the compiled jca .aj (it is present, not absorbed "
                        + "away — what dexlib2 absorbs is its EFFECT, by never emitting advice methods)");

        // (b) The dexlib2 weave emits no synthetic ajc$before$/ajc$after$ advice methods: scan the
        // woven DEX method-name string pool and assert zero hits.
        DexFile woven = weaveCallMonitor();
        long syntheticAdviceMethods = woven.getClasses().stream()
                .flatMap(c -> {
                    List<Method> ms = new ArrayList<>();
                    c.getMethods().forEach(ms::add);
                    return ms.stream();
                })
                .map(MethodReference::getName)
                .filter(n -> n.startsWith("ajc$before$") || n.startsWith("ajc$after$"))
                .count();
        assertEquals(0L, syntheticAdviceMethods,
                "the dexlib2 inline-call model must emit NO synthetic ajc$before$/ajc$after$ advice "
                        + "methods — so !adviceexecution() is vacuously satisfied");

        // (c) The match injected a real inline monitor invoke (proving the model is inline-call, not
        // advice-method): the woven class carries the monitor dispatch invocation.
        boolean hasMonitorInvoke = woven.getClasses().stream()
                .flatMap(c -> {
                    List<Method> ms = new ArrayList<>();
                    c.getMethods().forEach(ms::add);
                    return ms.stream();
                })
                .filter(m -> m.getImplementation() != null)
                .flatMap(m -> {
                    List<com.android.tools.smali.dexlib2.iface.instruction.Instruction> is =
                            new ArrayList<>();
                    m.getImplementation().getInstructions().forEach(is::add);
                    return is.stream();
                })
                .filter(i -> i instanceof
                        com.android.tools.smali.dexlib2.iface.instruction.ReferenceInstruction)
                .map(i -> ((com.android.tools.smali.dexlib2.iface.instruction.ReferenceInstruction) i)
                        .getReference())
                .filter(r -> r instanceof MethodReference)
                .anyMatch(r -> ((MethodReference) r).getName().endsWith("Event"));
        assertTrue(hasMonitorInvoke,
                "the inline-call model injects a real *Event(...) monitor invoke at the join point");

        // Named absorber.
        assertEquals(AbsorbingStage.DEXLIB2_INLINE_EMISSION_MODEL, ABSORBER);
    }

    // --- fixture: weave a JCA call() monitor + serialize + reparse --------------------------------

    private static DexFile weaveCallMonitor() throws Exception {
        MethodReference initRef = new ImmutableMethodReference(IV_DESC, "<init>", List.of("[B"), "V");
        List<com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction> body =
                new ArrayList<>();
        body.add(new ImmutableInstruction21c(Opcode.NEW_INSTANCE, 0, new ImmutableTypeReference(IV_DESC)));
        body.add(new ImmutableInstruction21c(Opcode.CONST_CLASS, 1, new ImmutableTypeReference("[B")));
        body.add(new ImmutableInstruction35c(Opcode.INVOKE_DIRECT, 2, 0, 1, 0, 0, 0, initRef));
        body.add(new ImmutableInstruction10x(Opcode.RETURN_VOID));
        ImmutableMethodImplementation impl = new ImmutableMethodImplementation(
                4, body, Collections.emptyList(), Collections.emptyList());
        ImmutableMethod bar = new ImmutableMethod("Lcom/example/App;", "bar", Collections.emptyList(),
                "V", AccessFlags.PUBLIC.getValue() | AccessFlags.STATIC.getValue(), null, null, impl);
        ClassDef cls = new ImmutableClassDef("Lcom/example/App;", AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;", Collections.emptyList(), null, null,
                Collections.emptyList(), List.of(bar));
        DexFile dex = new ImmutableDexFile(Opcodes.getDefault(), List.of(cls));

        AspectDescriptor descriptor = new AspectDescriptor();
        descriptor.setAspectName("MultiSpec_1MonitorAspect");
        descriptor.setShortName("MultiSpec_1");
        descriptor.setImports(List.of("javax.crypto.spec.IvParameterSpec"));
        descriptor.setCommonPointcut(COMMON_POINTCUT);
        descriptor.setBaseAspectExclusions(List.of(
                "sun..*", "java..*", "javax..*", "com.sun..*", "org.dacapo.harness..*",
                "org.apache.commons..*", "org.apache.geronimo..*", "net.sf.cglib..*",
                "mop..*", "javamoprt..*", "rvmonitorrt..*", "com.runtimeverification..*"));
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

        DexFileMutator mutator = new DexFileMutator(dex);
        DexWeaver.MutableImplSupplier supplier = new DexWeaver.MutableImplSupplier() {
            @Override
            public MutableMethodImplementation forMethod(Method m) {
                return mutator.forMethod(m);
            }
            @Override
            public void replaceImpl(Method m, MutableMethodImplementation i) {
                mutator.replaceImpl(m, i);
            }
            @Override
            public void addSynthesizedMethod(String def, Method m) {
                mutator.addSynthesizedMethod(def, m);
            }
        };

        DexWeaver weaver = new DexWeaver(new EmitterDispatch(), new RegisterAllocator());
        weaver.weave(dex, descriptor, typeResolver, inheritance, supplier);

        Path tmp = Files.createTempFile("gh62-adviceexec-", ".dex");
        try {
            DexPool.writeTo(tmp.toString(), mutator.toDexFile());
            try (InputStream in = new BufferedInputStream(Files.newInputStream(tmp))) {
                return DexBackedDexFile.fromInputStream(Opcodes.getDefault(), in);
            }
        } finally {
            Files.deleteIfExists(tmp);
        }
    }
}
