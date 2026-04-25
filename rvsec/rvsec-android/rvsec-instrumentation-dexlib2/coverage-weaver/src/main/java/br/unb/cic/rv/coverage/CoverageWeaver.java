package br.unb.cic.rv.coverage;

import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction21c;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction35c;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction3rc;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableStringReference;

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
 * <p>Thread-safety of the generated {@code mop.Coverage} runtime state is the
 * responsibility of the {@code monitor-builder} module, which emits the
 * {@code mop.Coverage} Java source with a {@code ConcurrentHashMap.newKeySet()}
 * backing store (INV-INS-23). This class only injects the invoke; the
 * concurrent-safe collection is a separate concern.
 *
 * <p>Spec-set agnostic: weaves coverage identically whether the MOP advice
 * set is JCA or Generic.
 */
public final class CoverageWeaver {

    private static final String COVERAGE_OWNER = "Lmop/Coverage;";
    private static final String COVERAGE_METHOD = "log";
    private static final String COVERAGE_DESCRIPTOR = "Ljava/lang/String;";

    private final MethodReference coverageMethod = new ImmutableMethodReference(
            COVERAGE_OWNER, COVERAGE_METHOD,
            List.of(COVERAGE_DESCRIPTOR),
            "V");

    /** Callback the caller supplies to expose mutable implementations. */
    public interface MutableImplSupplier {
        MutableMethodImplementation forMethod(Method method);
    }

    public CoverageReport weave(DexFile dexFile, MutableImplSupplier mutableSupplier) {
        Objects.requireNonNull(dexFile);
        int classesSeen = 0;
        int classesSkipped = 0;
        int methodsInstrumented = 0;
        int methodsSkipped = 0;

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
                injectLogCall(classDef, method, impl);
                methodsInstrumented++;
            }
        }
        return new CoverageReport(classesSeen, classesSkipped,
                methodsInstrumented, methodsSkipped);
    }

    private void injectLogCall(ClassDef classDef, Method method, MutableMethodImplementation impl) {
        String signature = SignatureFormatter.format(classDef, method);
        // We need one scratch register to hold the signature string. The
        // dex-mutator's RegisterAllocator would normally grow registerCount;
        // here we bump by 1 to claim a low-range register at the top.
        int oldCount = impl.getRegisterCount();
        // Grow by 1 register so we don't step on any existing ones.
        br.unb.cic.rv.mutator.RegisterShifter.bumpRegisterCount(impl, 1);
        int scratch = oldCount;

        // const-string vScratch, "<sig>"
        // CONST_STRING (Format21c) uses an 8-bit register field (v0-v255),
        // safe for any reasonable scratch index. Larger frames would need
        // CONST_STRING_JUMBO + a 16-bit register (Format31c); deferred.
        BuilderInstruction constStr = new BuilderInstruction21c(
                Opcode.CONST_STRING, scratch,
                new ImmutableStringReference(signature));

        // invoke-static {vScratch}, Lmop/Coverage;->log(Ljava/lang/String;)V
        // Format35c packs up to 5 register references into 4-bit fields each
        // (v0-v15). When the scratch register exceeds the 4-bit window we
        // switch to invoke-static/range (Format3rc), which uses a 16-bit
        // start register + 8-bit count and supports the full register space.
        BuilderInstruction invoke;
        if (scratch < 16) {
            invoke = new BuilderInstruction35c(
                    Opcode.INVOKE_STATIC, 1,
                    scratch, 0, 0, 0, 0,
                    coverageMethod);
        } else {
            invoke = new BuilderInstruction3rc(
                    Opcode.INVOKE_STATIC_RANGE,
                    scratch, 1,
                    coverageMethod);
        }

        impl.addInstruction(0, constStr);
        impl.addInstruction(1, invoke);
    }

    public record CoverageReport(int classesSeen, int classesSkipped,
                                  int methodsInstrumented, int methodsSkipped) {}
}
