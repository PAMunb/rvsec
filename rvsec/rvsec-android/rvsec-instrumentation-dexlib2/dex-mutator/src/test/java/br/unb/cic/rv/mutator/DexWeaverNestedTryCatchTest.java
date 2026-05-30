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
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile;
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
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction10x;
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
 * §4.T (D14 F-decision) — {@code after() throwing(...)} install with
 * range-splitting under a pre-existing user try-block.
 *
 * <p>The fixture mirrors the corpus's sole {@code after-throwing} site
 * ({@code Comparable_CompareToNullException_badexception}): a
 * {@code call(* Comparable+.compareTo(..)) && args(o)} matched invoke that sits
 * INSIDE a user {@code try { ... } catch (RuntimeException) { ... }}. The
 * weaver must split that user block at the matched invoke into head/matched/
 * tail ranges (NOT nest a new inner range, which ART rejects), with the new
 * advice handler listed FIRST on the matched range.
 *
 * <p>Validity is proven at the DEX level: serialise via {@link DexPool} and
 * reparse via {@link DexBackedDexFile}, then assert the parsed try-blocks are
 * strictly-nested / non-overlapping (the ART verifier invariant), the matched
 * code unit carries the advice handler before the user catch, and the handler
 * block is bracketed by {@code move-exception ... throw}. (On-device ART
 * verification is the §6.S smoke gate, not this unit.)
 */
class DexWeaverNestedTryCatchTest {

    private static final String FOO_DESC = "LFoo;";
    private static final String COMPARABLE_DESC = "Ljava/lang/Comparable;";
    private static final String MONITOR_DESC = "Lmop/MultiSpec_1RuntimeMonitor;";

    @Test
    void afterThrowingInsideExistingTryBlockSplitsRangesCleanly() throws Exception {
        DexFile dex = buildFixtureWithUserTryBlock();
        AspectDescriptor descriptor = afterThrowingDescriptor();

        TypeResolver typeResolver = new TypeResolver(descriptor.getImports());
        AndroidClassIndex emptyAndroid = new AndroidClassIndex(Path.of("/tmp/nope.jar"));
        InheritanceResolver inheritance = new InheritanceResolver(emptyAndroid, dex);

        TrackingSupplier supplier = new TrackingSupplier();
        DexWeaver weaver = new DexWeaver(new EmitterDispatch(), new RegisterAllocator());
        DexWeaver.WeaveReport report =
                weaver.weave(dex, descriptor, typeResolver, inheritance, supplier);

        assertEquals(1, report.matchesApplied(),
                "exactly one after-throwing match expected");

        // Serialise the woven method and reparse — the ART-shaped validity
        // assertions run against the reparsed (canonical) try-block table.
        Path tmp = Files.createTempFile("gh62-4t-nested-", ".dex");
        try {
            DexFile woven = supplier.toDexFile(dex);
            DexPool.writeTo(tmp.toString(), woven);
            try (InputStream in = new BufferedInputStream(Files.newInputStream(tmp))) {
                DexBackedDexFile parsed =
                        DexBackedDexFile.fromInputStream(Opcodes.getDefault(), in);
                MethodImplementation impl = findImpl(parsed, "cmp");
                assertNotNull(impl);

                List<? extends TryBlock<? extends ExceptionHandler>> tries =
                        new ArrayList<>(impl.getTryBlocks());
                // The user block split into head + matched + tail; the matched
                // range carries TWO handlers (advice + user catch). dexlib2
                // serialises one TryBlock per (range, handler-list); after the
                // split there are 3 code ranges.
                assertEquals(3, tries.size(),
                        "user try-block must split into head/matched/tail (3 ranges)");

                // (a) Strictly-nested / non-overlapping — the ART invariant.
                assertNoOverlap(tries);

                // (b) The matched range (single code unit) lists the advice
                // handler FIRST, then the user catch.
                TryBlock<? extends ExceptionHandler> matched = findSingleUnitRange(tries);
                assertNotNull(matched, "a single-code-unit matched range must exist");
                List<? extends ExceptionHandler> handlers =
                        new ArrayList<>(matched.getExceptionHandlers());
                assertEquals(2, handlers.size(),
                        "matched range carries advice handler + user catch");
                // Advice handler is catch-all on the declared throwing type
                // (Exception); ART scans declaration order, so it must be first.
                assertEquals("Ljava/lang/Exception;", handlers.get(0).getExceptionType(),
                        "advice handler (throwing type) MUST be listed FIRST");
                assertEquals("Ljava/lang/RuntimeException;", handlers.get(1).getExceptionType(),
                        "user catch (RuntimeException) MUST follow the advice handler");

                // (c) The advice handler block is bracketed move-exception ... throw.
                int handlerIdx = handlers.get(0).getHandlerCodeAddress();
                assertHandlerBracketed(impl, handlerIdx);
            }
        } finally {
            Files.deleteIfExists(tmp);
        }
    }

    /** Assert no two try ranges overlap unless strictly nested (ART invariant). */
    private static void assertNoOverlap(
            List<? extends TryBlock<? extends ExceptionHandler>> tries) {
        for (int i = 0; i < tries.size(); i++) {
            TryBlock<?> a = tries.get(i);
            int aStart = a.getStartCodeAddress();
            int aEnd = aStart + a.getCodeUnitCount();
            for (int j = i + 1; j < tries.size(); j++) {
                TryBlock<?> b = tries.get(j);
                int bStart = b.getStartCodeAddress();
                int bEnd = bStart + b.getCodeUnitCount();
                boolean disjoint = aEnd <= bStart || bEnd <= aStart;
                boolean aInB = bStart <= aStart && aEnd <= bEnd;
                boolean bInA = aStart <= bStart && bEnd <= aEnd;
                assertTrue(disjoint || aInB || bInA,
                        "try ranges [" + aStart + "," + aEnd + ") and ["
                                + bStart + "," + bEnd + ") overlap without nesting "
                                + "— ART verifier rejects this");
            }
        }
    }

    /** The matched range covers exactly one code unit (the matched invoke). */
    private static TryBlock<? extends ExceptionHandler> findSingleUnitRange(
            List<? extends TryBlock<? extends ExceptionHandler>> tries) {
        for (TryBlock<? extends ExceptionHandler> tb : tries) {
            // The matched invoke is one instruction. Its code-unit size depends
            // on the invoke encoding (35c = 3 units). The matched range is the
            // one carrying two handlers — that is the unambiguous marker.
            if (tb.getExceptionHandlers().size() == 2) return tb;
        }
        return null;
    }

    /** The handler at code address must start with move-exception and end with throw. */
    private static void assertHandlerBracketed(MethodImplementation impl, int handlerCodeAddr) {
        List<Instruction> all = new ArrayList<>();
        for (Instruction in : impl.getInstructions()) all.add(in);
        // Walk to the instruction at handlerCodeAddr.
        int addr = 0;
        int handlerInsnIdx = -1;
        for (int i = 0; i < all.size(); i++) {
            if (addr == handlerCodeAddr) { handlerInsnIdx = i; break; }
            addr += all.get(i).getCodeUnits();
        }
        assertTrue(handlerInsnIdx >= 0, "handler code address resolves to an instruction");
        assertEquals(Opcode.MOVE_EXCEPTION, all.get(handlerInsnIdx).getOpcode(),
                "handler MUST start with move-exception (ART invariant)");
        int excReg = ((OneRegisterInstruction) all.get(handlerInsnIdx)).getRegisterA();
        // The block ends with throw of the same exception register. Scan
        // forward from the handler for the first throw on excReg.
        boolean foundThrow = false;
        for (int i = handlerInsnIdx + 1; i < all.size(); i++) {
            if (all.get(i).getOpcode() == Opcode.THROW
                    && ((OneRegisterInstruction) all.get(i)).getRegisterA() == excReg) {
                foundThrow = true;
                break;
            }
        }
        assertTrue(foundThrow,
                "handler MUST end with throw of the move-exception register (re-throw)");
    }

    // ------------------------------------------------------------------
    // Fixture builders.
    // ------------------------------------------------------------------

    /**
     * Build {@code static int cmp(Comparable a, Object o)} whose
     * {@code a.compareTo(o)} invoke sits in the MIDDLE of a user
     * {@code try { } catch (RuntimeException) { }} (so the range genuinely
     * splits into a non-empty head + matched + tail):
     * <pre>
     *   0: const-class v3, Object             ; inside try, before invoke (head)
     *   1: invoke-interface {v2, v3}, Comparable.compareTo(Object)I   ; matched
     *   2: move-result v0                      ; inside try, after invoke (tail)
     *   3: return v0
     *   4: move-exception v1                   ; user handler
     *   5: const-class v0, Object
     *   6: return v0
     * </pre>
     * Try range covers idx 0..2 (start=0, end=3) with handler at idx 4.
     */
    private static DexFile buildFixtureWithUserTryBlock() {
        MethodReference compareTo = new ImmutableMethodReference(
                COMPARABLE_DESC, "compareTo",
                List.of("Ljava/lang/Object;"), "I");

        List<ImmutableInstruction> body = new ArrayList<>();
        // idx 0: head — an op inside the try, before the matched invoke
        body.add(new ImmutableInstruction21c(
                Opcode.CONST_CLASS, /*regA=*/ 3,
                new ImmutableTypeReference("Ljava/lang/Object;")));
        // idx 1: matched invoke
        body.add(new ImmutableInstruction35c(
                Opcode.INVOKE_INTERFACE, /*regCount=*/ 2,
                /*c=*/ 2, /*d=*/ 3, /*e=*/ 0, /*f=*/ 0, /*g=*/ 0,
                compareTo));
        // idx 2: move-result v0 (tail — inside try, after invoke)
        body.add(new ImmutableInstruction11x(Opcode.MOVE_RESULT, 0));
        // idx 3: return v0
        body.add(new ImmutableInstruction11x(Opcode.RETURN, 0));
        // idx 4: user handler — move-exception v1
        body.add(new ImmutableInstruction11x(Opcode.MOVE_EXCEPTION, 1));
        // idx 5: const-class v0
        body.add(new ImmutableInstruction21c(
                Opcode.CONST_CLASS, /*regA=*/ 0,
                new ImmutableTypeReference("Ljava/lang/Object;")));
        // idx 6: return v0
        body.add(new ImmutableInstruction11x(Opcode.RETURN, 0));

        // User try block: protect idx 0..2 (head + invoke + move-result),
        // handler at idx 4, catching RuntimeException.
        com.android.tools.smali.dexlib2.immutable.ImmutableTryBlock userTry =
                buildUserTry(body, /*startIdx=*/ 0, /*endIdx=*/ 3, /*handlerIdx=*/ 4,
                        "Ljava/lang/RuntimeException;");

        ImmutableMethodImplementation impl = new ImmutableMethodImplementation(
                /*registerCount=*/ 4,
                body,
                List.of(userTry),
                Collections.emptyList());
        ImmutableMethod cmp = new ImmutableMethod(
                FOO_DESC, "cmp",
                List.of(
                        new com.android.tools.smali.dexlib2.immutable.ImmutableMethodParameter(
                                "Ljava/lang/Comparable;", null, null),
                        new com.android.tools.smali.dexlib2.immutable.ImmutableMethodParameter(
                                "Ljava/lang/Object;", null, null)),
                "I",
                AccessFlags.PUBLIC.getValue() | AccessFlags.STATIC.getValue(),
                null, null, impl);
        ClassDef foo = new ImmutableClassDef(
                FOO_DESC, AccessFlags.PUBLIC.getValue(),
                "Ljava/lang/Object;",
                Collections.emptyList(),
                null, null,
                Collections.emptyList(),
                List.of(cmp));
        return new ImmutableDexFile(Opcodes.getDefault(), List.of(foo));
    }

    /** Build an immutable try-block by mapping instruction indices to code addresses. */
    private static com.android.tools.smali.dexlib2.immutable.ImmutableTryBlock buildUserTry(
            List<ImmutableInstruction> body, int startIdx, int endIdx, int handlerIdx,
            String catchType) {
        int startAddr = codeAddr(body, startIdx);
        int endAddr = codeAddr(body, endIdx);
        int handlerAddr = codeAddr(body, handlerIdx);
        com.android.tools.smali.dexlib2.immutable.ImmutableExceptionHandler handler =
                new com.android.tools.smali.dexlib2.immutable.ImmutableExceptionHandler(
                        catchType, handlerAddr);
        return new com.android.tools.smali.dexlib2.immutable.ImmutableTryBlock(
                startAddr, endAddr - startAddr, List.of(handler));
    }

    private static int codeAddr(List<ImmutableInstruction> body, int idx) {
        int addr = 0;
        for (int i = 0; i < idx; i++) addr += body.get(i).getCodeUnits();
        return addr;
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
        // Mirrors the corpus pointcut (sans the if() for the base nesting test).
        // The corpus spells the return type as a `*` wildcard; the in-weaver
        // matcher's return-type check is exact, so we pin the concrete return
        // type (compareTo returns int) — return-type wildcard matching is a
        // separate closure and orthogonal to the §4.T installer under test:
        //   after (Object o) throwing (Exception e) :
        //       call(int Comparable+.compareTo(..)) && args(o)
        advice.setExpression(
                "call(int Comparable+.compareTo(..)) && args(o)");
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
        for (com.android.tools.smali.dexlib2.dexbacked.DexBackedClassDef cd : parsed.getClasses()) {
            if (!FOO_DESC.equals(cd.getType())) continue;
            for (com.android.tools.smali.dexlib2.dexbacked.DexBackedMethod m : cd.getMethods()) {
                if (name.equals(m.getName())) return m.getImplementation();
            }
        }
        throw new AssertionError("method " + name + " not found in parsed dex");
    }

    static String methodKey(Method m) {
        StringBuilder sb = new StringBuilder(64);
        sb.append(m.getDefiningClass()).append("->").append(m.getName()).append('(');
        for (CharSequence p : m.getParameterTypes()) sb.append(p);
        sb.append(')').append(m.getReturnType());
        return sb.toString();
    }

    /**
     * A {@link DexWeaver.MutableImplSupplier} that tracks per-method mutable
     * implementations AND honours {@code replaceImpl} (so the frame-grown MMI
     * produced by the after-throwing scratch allocation survives into
     * serialisation — the production {@code DexFileMutator} does the same).
     */
    static final class TrackingSupplier implements DexWeaver.MutableImplSupplier {
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

        /** Re-emit the dex with every tracked (woven) implementation in place. */
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
