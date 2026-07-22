package br.unb.cic.rv.grammar;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.AspectDescriptor;
import br.unb.cic.rv.descriptor.MonitorCallDescriptor;
import br.unb.cic.rv.descriptor.ParameterDescriptor;
import br.unb.cic.rv.emitter.EmitterDispatch;
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
import com.android.tools.smali.dexlib2.iface.ExceptionHandler;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.MethodImplementation;
import com.android.tools.smali.dexlib2.iface.TryBlock;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.iface.instruction.OneRegisterInstruction;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableDexFile;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodImplementation;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodParameter;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction11x;
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
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Backs the matrix row "{@code after() throwing(Id) advice}" (§4.T). Exercises
 * the NON-NESTED baseline: a matched {@code call(* Comparable+.compareTo(..))}
 * invoke that is NOT inside any pre-existing user try-block. The weaver must
 * install a single new try-range over the matched invoke whose handler delivers
 * the monitor event then re-throws.
 *
 * <p>Post-fix bytecode is validated by serialising via {@link DexPool} and
 * reparsing via {@link DexBackedDexFile} (the §6.S device gate is separate):
 * the reparsed method MUST carry a try-block covering the matched invoke, with
 * a handler on the declared throwing type whose code is bracketed
 * {@code move-exception ... invoke-static(monitor) ... throw}.
 */
class AfterThrowingGrammarTest {

    private static final String FOO_DESC = "LFoo;";
    private static final String COMPARABLE_DESC = "Ljava/lang/Comparable;";
    private static final String MONITOR_DESC = "Lmop/MultiSpec_1RuntimeMonitor;";

    @Test
    void installsTryRangeAndHandler() throws Exception {
        DexFile dex = buildNonNestedFixture();
        AspectDescriptor descriptor = afterThrowingDescriptor();

        TypeResolver typeResolver = new TypeResolver(descriptor.getImports());
        AndroidClassIndex emptyAndroid = new AndroidClassIndex(Path.of("/tmp/nope.jar"));
        InheritanceResolver inheritance = new InheritanceResolver(emptyAndroid, dex);

        Supplier supplier = new Supplier();
        DexWeaver weaver = new DexWeaver(new EmitterDispatch(), new RegisterAllocator());
        DexWeaver.WeaveReport report =
                weaver.weave(dex, descriptor, typeResolver, inheritance, supplier);

        assertEquals(1, report.matchesApplied(),
                "the non-nested after-throwing site must weave exactly once");

        Path tmp = Files.createTempFile("gh62-4t-grammar-", ".dex");
        try {
            DexPool.writeTo(tmp.toString(), supplier.toDexFile(dex));
            try (InputStream in = new BufferedInputStream(Files.newInputStream(tmp))) {
                DexBackedDexFile parsed =
                        DexBackedDexFile.fromInputStream(Opcodes.getDefault(), in);
                MethodImplementation impl = findImpl(parsed, "cmp");
                assertNotNull(impl);

                List<? extends TryBlock<? extends ExceptionHandler>> tries =
                        new ArrayList<>(impl.getTryBlocks());
                assertEquals(1, tries.size(),
                        "non-nested baseline installs exactly one new try-range");
                List<? extends ExceptionHandler> handlers =
                        new ArrayList<>(tries.get(0).getExceptionHandlers());
                assertEquals(1, handlers.size(),
                        "the new try-range carries exactly the advice handler");
                assertEquals("Ljava/lang/Exception;", handlers.get(0).getExceptionType(),
                        "handler catches the declared throwing type");

                // Handler bytecode: move-exception ... invoke-static(monitor) ... throw.
                List<Instruction> all = new ArrayList<>();
                for (Instruction i : impl.getInstructions()) all.add(i);
                int handlerIdx = resolveInsnAtAddr(all, handlers.get(0).getHandlerCodeAddress());
                assertEquals(Opcode.MOVE_EXCEPTION, all.get(handlerIdx).getOpcode(),
                        "handler starts with move-exception (ART invariant)");
                int excReg = ((OneRegisterInstruction) all.get(handlerIdx)).getRegisterA();

                boolean sawMonitorInvoke = false;
                boolean sawThrow = false;
                for (int i = handlerIdx + 1; i < all.size(); i++) {
                    Instruction insn = all.get(i);
                    if (insn.getOpcode() == Opcode.INVOKE_STATIC) {
                        MethodReference ref = (MethodReference)
                                ((com.android.tools.smali.dexlib2.iface.instruction.ReferenceInstruction)
                                        insn).getReference();
                        if (MONITOR_DESC.equals(ref.getDefiningClass())) sawMonitorInvoke = true;
                    }
                    if (insn.getOpcode() == Opcode.THROW
                            && ((OneRegisterInstruction) insn).getRegisterA() == excReg) {
                        sawThrow = true;
                        break;
                    }
                }
                assertTrue(sawMonitorInvoke,
                        "handler delivers the monitor event before re-throwing");
                assertTrue(sawThrow,
                        "handler ends with throw of the caught exception (re-throw)");
            }
        } finally {
            Files.deleteIfExists(tmp);
        }
    }

    private static int resolveInsnAtAddr(List<Instruction> all, int codeAddr) {
        int addr = 0;
        for (int i = 0; i < all.size(); i++) {
            if (addr == codeAddr) return i;
            addr += all.get(i).getCodeUnits();
        }
        throw new AssertionError("no instruction at code address " + codeAddr);
    }

    // ------------------------------------------------------------------
    // Fixture: static int cmp() { return a.compareTo(o); } — NO user try-block.
    // ------------------------------------------------------------------

    private static DexFile buildNonNestedFixture() {
        MethodReference compareTo = new ImmutableMethodReference(
                COMPARABLE_DESC, "compareTo", List.of("Ljava/lang/Object;"), "I");
        List<ImmutableInstruction> body = new ArrayList<>();
        body.add(new ImmutableInstruction21c(
                Opcode.CONST_CLASS, 2, new ImmutableTypeReference(COMPARABLE_DESC)));
        body.add(new ImmutableInstruction21c(
                Opcode.CONST_CLASS, 3, new ImmutableTypeReference("Ljava/lang/Object;")));
        body.add(new ImmutableInstruction35c(
                Opcode.INVOKE_INTERFACE, 2, 2, 3, 0, 0, 0, compareTo));
        body.add(new ImmutableInstruction11x(Opcode.MOVE_RESULT, 0));
        body.add(new ImmutableInstruction11x(Opcode.RETURN, 0));

        ImmutableMethodImplementation impl = new ImmutableMethodImplementation(
                4, body, Collections.emptyList(), Collections.emptyList());
        ImmutableMethod cmp = new ImmutableMethod(
                FOO_DESC, "cmp",
                Collections.<ImmutableMethodParameter>emptyList(), "I",
                AccessFlags.PUBLIC.getValue() | AccessFlags.STATIC.getValue(),
                null, null, impl);
        ClassDef foo = new ImmutableClassDef(
                FOO_DESC, AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;", Collections.emptyList(),
                null, null, Collections.emptyList(), List.of(cmp));
        return new ImmutableDexFile(Opcodes.getDefault(), List.of(foo));
    }

    private static AspectDescriptor afterThrowingDescriptor() {
        AspectDescriptor descriptor = new AspectDescriptor();
        descriptor.setShortName("MultiSpec_1");
        descriptor.setImports(List.of("java.lang.Comparable", "java.lang.Exception"));
        AdviceDescriptor advice = new AdviceDescriptor();
        advice.setName("badexception");
        advice.setSpecName("Comparable_CompareToNullException");
        advice.setPosition("after");
        advice.setAround(false);
        advice.setReturnType("void");
        // return type pinned to int — wildcard return matching is a separate
        // closure, orthogonal to the §4.T try-range install under test.
        advice.setExpression("call(int Comparable+.compareTo(..)) && args(o)");
        advice.setParameters(List.of(new ParameterDescriptor("Object", "o")));
        advice.setThrowing(List.of(new ParameterDescriptor("Exception", "e")));
        MonitorCallDescriptor mc = new MonitorCallDescriptor();
        mc.setMethod("MultiSpec_1RuntimeMonitor.Comparable_CompareToNullException_badexceptionEvent");
        mc.setSpecName("Comparable_CompareToNullException");
        mc.setEventId("badexception");
        mc.setUniqueId("u1");
        mc.setArgs(List.of("o", "e"));
        advice.setMonitorCalls(List.of(mc));
        descriptor.setAdvices(List.of(advice));
        return descriptor;
    }

    private static MethodImplementation findImpl(DexBackedDexFile parsed, String name) {
        for (DexBackedClassDef cd : parsed.getClasses()) {
            if (!FOO_DESC.equals(cd.getType())) continue;
            for (DexBackedMethod m : cd.getMethods()) {
                if (name.equals(m.getName())) return m.getImplementation();
            }
        }
        throw new AssertionError("method " + name + " not found in parsed dex");
    }

    private static String methodKey(Method m) {
        StringBuilder sb = new StringBuilder(64);
        sb.append(m.getDefiningClass()).append("->").append(m.getName()).append('(');
        for (CharSequence p : m.getParameterTypes()) sb.append(p);
        sb.append(')').append(m.getReturnType());
        return sb.toString();
    }

    /** Tracking supplier honouring replaceImpl (the §4.T rebuilt MMI). */
    private static final class Supplier implements DexWeaver.MutableImplSupplier {
        final Map<String, MutableMethodImplementation> muts = new HashMap<>();

        @Override
        public MutableMethodImplementation forMethod(Method method) {
            if (method.getImplementation() == null) return null;
            String k = methodKey(method);
            MutableMethodImplementation existing = muts.get(k);
            if (existing != null) return existing;
            MutableMethodImplementation mut =
                    new MutableMethodImplementation(method.getImplementation());
            muts.put(k, mut);
            return mut;
        }

        @Override
        public void replaceImpl(Method method, MutableMethodImplementation newImpl) {
            muts.put(methodKey(method), newImpl);
        }

        DexFile toDexFile(DexFile original) {
            List<ClassDef> classes = new ArrayList<>();
            for (ClassDef cd : original.getClasses()) {
                List<Method> methods = new ArrayList<>();
                for (Method m : cd.getMethods()) {
                    MutableMethodImplementation mut = muts.get(methodKey(m));
                    MethodImplementation impl = mut != null ? mut : m.getImplementation();
                    methods.add(new ImmutableMethod(
                            m.getDefiningClass(), m.getName(), m.getParameters(),
                            m.getReturnType(), m.getAccessFlags(), m.getAnnotations(),
                            m.getHiddenApiRestrictions(), impl));
                }
                classes.add(new ImmutableClassDef(
                        cd.getType(), cd.getAccessFlags(), cd.getSuperclass(),
                        cd.getInterfaces(), cd.getSourceFile(), cd.getAnnotations(),
                        cd.getFields(), methods));
            }
            return new ImmutableDexFile(Opcodes.getDefault(), classes);
        }
    }
}
