package br.unb.cic.rv.coverage;

import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction21c;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction35c;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableStringReference;
import com.android.tools.smali.dexlib2.util.MethodUtil;

import java.util.List;
import java.util.Objects;

/**
 * Prepends {@code invoke-static Lmop/Coverage;.log(Ljava/lang/String;)V} to
 * every non-excluded application-code method.
 *
 * <p>Semantically equivalent to the AspectJ rule in {@code Coverage.aj}:
 * <pre>
 *   pointcut coverage() : execution(* *.*(..)) &amp;&amp; !within(mop..*) ... ;
 *   before() : coverage() { mop.Coverage.log(thisJoinPoint.getSignature()); }
 * </pre>
 *
 * <p>The signature string is pre-computed at weave time (no runtime reflection)
 * via {@link SignatureFormatter}, matching the Soot-style shape the legacy
 * {@code Coverage.aj} emits so Layer-5 RVSEC-COV recall comparisons align
 * without special-case handling.
 *
 * <h2>Register allocation strategy</h2>
 * The {@code const-string} + {@code invoke-static} pair needs one scratch
 * register at v0 (Format35c uses 4-bit register fields). Two cases:
 * <ul>
 *   <li><b>{@code localCount &ge; 1}</b>: at least one local register exists, so
 *       v0 is already a free local — emit the hook at index 0 with
 *       {@code scratch=v0}, no frame manipulation needed.</li>
 *   <li><b>{@code localCount == 0}</b>: every register is a parameter
 *       (Android DEX places params in the highest {@code paramRegs} slots).
 *       Call {@link br.unb.cic.rv.mutator.RegisterShifter#spillLowRegisters}
 *       to shift every existing register reference up by 1 and grow the frame
 *       — this slides params from {@code r[N-paramRegs..N-1]} to
 *       {@code r[N+1-paramRegs..N]} (matching where the runtime now writes them
 *       under the new {@code registerCount}) and frees v0 for use as scratch.</li>
 * </ul>
 *
 * <p>Without this strategy, naively calling {@link
 * br.unb.cic.rv.mutator.RegisterShifter#bumpRegisterCount} alone produced
 * {@code java.lang.VerifyError: tried to get class from non-reference register
 * vN (type=Undefined)} on every instrumented method that had no locals
 * (extremely common — getters / setters / one-liners). The bug surfaced in
 * the gh52 smoke run against cryptoapp + 3 small JCA-400 APKs (boot crash on
 * MainActivity / androidx.core.util.Preconditions). Fixed by porting the
 * {@code spillOneLocal} approach from {@code prototipo-dexlib2/dex-weaver}.
 *
 * <h2>Thread-safety of {@code mop.Coverage}</h2>
 * The generated runtime class uses {@code ConcurrentHashMap.newKeySet()}
 * (INV-INS-60). Emitted by {@code monitor-builder.CoverageSourceEmitter}.
 *
 * <h2>Spec-set agnostic</h2>
 * Weaves coverage identically whether the MOP advice set is JCA or Generic.
 */
public final class CoverageWeaver {

    private static final String COVERAGE_OWNER = "Lmop/Coverage;";
    private static final String COVERAGE_METHOD = "log";
    private static final String COVERAGE_DESCRIPTOR = "Ljava/lang/String;";

    private final MethodReference coverageMethod = new ImmutableMethodReference(
            COVERAGE_OWNER, COVERAGE_METHOD,
            List.of(COVERAGE_DESCRIPTOR),
            "V");

    /**
     * Callback the caller supplies to expose mutable implementations.
     *
     * <p>{@link #replaceImpl(Method, MutableMethodImplementation)} is the
     * companion update hook used by {@code injectLogCall} when
     * {@code RegisterShifter.spillLowRegisters} returns a fresh MMI to
     * grow the register frame. The caller MUST notify the supplier so
     * subsequent {@link #forMethod} lookups return the new MMI; otherwise
     * the serialised dex would drop the frame growth and the injected
     * {@code invoke-static} (gh59 5-APK {@code VerifyError} residual,
     * design.md D5). Default no-op for in-process test suppliers; the
     * canonical implementation lives in {@code DexFileMutator.replaceImpl}.
     */
    public interface MutableImplSupplier {
        MutableMethodImplementation forMethod(Method method);

        default void replaceImpl(Method method, MutableMethodImplementation newImpl) { }
    }

    public CoverageReport weave(DexFile dexFile, MutableImplSupplier mutableSupplier) {
        Objects.requireNonNull(dexFile);
        int classesSeen = 0;
        int classesSkipped = 0;
        int methodsInstrumented = 0;
        int methodsSkipped = 0;
        int methodsSpillFailed = 0;

        for (ClassDef classDef : dexFile.getClasses()) {
            classesSeen++;
            if (PackageFilter.isExcluded(classDef.getType())) {
                classesSkipped++;
                continue;
            }
            for (Method method : classDef.getMethods()) {
                if (method.getImplementation() == null) {
                    methodsSkipped++;
                    continue;
                }
                MutableMethodImplementation impl = mutableSupplier.forMethod(method);
                if (impl == null) {
                    methodsSkipped++;
                    continue;
                }
                if (!injectLogCall(classDef, method, impl)) {
                    methodsSpillFailed++;
                    continue;
                }
                methodsInstrumented++;
            }
        }
        return new CoverageReport(classesSeen, classesSkipped,
                methodsInstrumented, methodsSkipped, methodsSpillFailed);
    }

    /**
     * Insert the coverage hook at method entry. Returns {@code false} when the
     * method needs a low-register spill but the spill cannot be performed
     * (e.g. an instruction format we cannot widen has registers at v15) — the
     * caller skips the method without aborting the rest of the pass.
     */
    private boolean injectLogCall(ClassDef classDef, Method method,
                                   MutableMethodImplementation impl) {
        String signature = SignatureFormatter.format(classDef, method);
        int paramRegs = MethodUtil.getParameterRegisterCount(method);
        int regCount = impl.getRegisterCount();
        int localCount = regCount - paramRegs;

        if (localCount < 1) {
            // No free local register — params occupy the entire frame. Spill v0
            // by shifting all existing instructions and growing registerCount;
            // this preserves the calling convention (params slide to the new
            // high slots) and frees v0 for the hook.
            try {
                br.unb.cic.rv.mutator.RegisterShifter.spillLowRegisters(impl, 1);
            } catch (RuntimeException ex) {
                // Spill failed — typically a 4-bit format with both operands
                // already at v15, or a non-move 12x op. Skip this method; the
                // pass continues with the rest of the class.
                return false;
            }
        }

        // After the optional spill, v0 is guaranteed free.
        // Format21c (const-string) uses 8-bit dest register, safe.
        // Format35c (invoke-static) packs registers in 4-bit fields, so a
        // single scratch at v0 is always within range.
        BuilderInstruction constStr = new BuilderInstruction21c(
                Opcode.CONST_STRING, /*regA=*/ 0,
                new ImmutableStringReference(signature));
        BuilderInstruction invoke = new BuilderInstruction35c(
                Opcode.INVOKE_STATIC, /*regCount=*/ 1,
                /*C=*/ 0, /*D=*/ 0, /*E=*/ 0, /*F=*/ 0, /*G=*/ 0,
                coverageMethod);

        impl.addInstruction(0, constStr);
        impl.addInstruction(1, invoke);
        return true;
    }

    public record CoverageReport(int classesSeen, int classesSkipped,
                                  int methodsInstrumented, int methodsSkipped,
                                  int methodsSpillFailed) {}
}
