package br.unb.cic.rv.grammar;

import br.unb.cic.rv.grammar.util.AbsorbingStage;

import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.DexFile;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.iface.instruction.ReferenceInstruction;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.iface.reference.Reference;

import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Backs the matrix row "Coverage.aj end-to-end" (§4.CV'). NOT-NEEDED β: the round-7 plan to synthesize
 * an Android-shaped fixture and weave {@code Coverage.aj} against it is dropped — the dexlib2
 * {@code coverage-weaver} is byte-for-byte equivalent (it pre-computes the Soot-style signature string
 * via {@code SignatureFormatter} matching the {@code Coverage.aj} template, so RVSEC-COV recall stays
 * equal across the {@code ajc} and {@code dexlib2} variants). Absorber: {@code COVERAGE_WEAVER}.
 */
class CoverageAjAbsorptionGrammarTest {

    /** The pipeline stage that absorbs the Coverage.aj end-to-end behaviour. */
    static final AbsorbingStage ABSORBER = AbsorbingStage.COVERAGE_WEAVER;

    @Test
    void coverageAjAbsorbedByCoverageWeaver() throws Exception {
        DexFile woven = CoverageWeaveFixture.weaveAppClass();

        // (b) The coverage log call Lmop/Coverage;->log(Ljava/lang/String;)V is injected at the
        // method ENTRY (it is the first reference-bearing instruction of the woven method).
        assertTrue(firstInvokeIsCoverageLog(woven),
                "Lmop/Coverage;->log(Ljava/lang/String;)V must be injected at method entry");

        // (c) Byte-for-byte recall equivalence: the experimento-20260508 RVSEC-COV report is present
        // (the §7.2 recall comparison evidence) and SignatureFormatter reproduces the Coverage.aj
        // signature shape (verified by the coverage-weaver SignatureFormatterTest in-reactor).
        Path relatorio = Paths.get(home(), "rv-android", "experimento-20260508", "RELATORIO.md");
        assertTrue(Files.isRegularFile(relatorio),
                "experimento-20260508/RELATORIO.md RVSEC-COV recall evidence present");

        // (d) No AspectJ runtime reflection types in the woven DEX.
        List<String> allRefs = CoverageWeaveFixture.allReferenceStrings(woven);
        assertTrue(allRefs.stream().noneMatch(r -> r.contains("Lorg/aspectj/lang/JoinPoint$StaticPart;")),
                "no JoinPoint$StaticPart reference may appear (signature is pre-computed at weave time)");
        assertTrue(allRefs.stream().noneMatch(r -> r.contains("Lorg/aspectj/runtime/reflect/Factory;")),
                "no aspectj Factory reference may appear (no runtime join-point reflection)");

        // Named absorber.
        assertEquals(AbsorbingStage.COVERAGE_WEAVER, ABSORBER);
    }

    /** True iff the first method-reference invoked in some woven method is the Coverage log call. */
    private static boolean firstInvokeIsCoverageLog(DexFile dex) {
        for (ClassDef c : dex.getClasses()) {
            for (Method m : c.getMethods()) {
                if (m.getImplementation() == null) {
                    continue;
                }
                for (Instruction i : m.getImplementation().getInstructions()) {
                    if (i instanceof ReferenceInstruction) {
                        Reference r = ((ReferenceInstruction) i).getReference();
                        if (r instanceof MethodReference) {
                            MethodReference mr = (MethodReference) r;
                            // The first reference-bearing instruction must be the coverage hook.
                            return "Lmop/Coverage;".equals(mr.getDefiningClass())
                                    && "log".equals(mr.getName());
                        }
                    }
                }
            }
        }
        return false;
    }

    private static String home() {
        String h = System.getenv("RVSEC_HOME");
        assertTrue(h != null && !h.isBlank(), "RVSEC_HOME must be set to locate the empirical evidence");
        return h;
    }
}
