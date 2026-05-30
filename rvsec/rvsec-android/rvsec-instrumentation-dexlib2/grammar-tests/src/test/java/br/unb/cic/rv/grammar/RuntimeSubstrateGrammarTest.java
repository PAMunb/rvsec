package br.unb.cic.rv.grammar;

import br.unb.cic.rv.grammar.util.AbsorbingStage;

import com.android.tools.smali.dexlib2.iface.DexFile;

import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Backs the matrix row "AspectJ runtime substrate / {@code org.aspectj.lang.JoinPoint} family"
 * (§4.RT'). NOT-NEEDED β: the round-7 plan to ship an {@code aspectjlang/} POJO substrate is dropped.
 * The sole consumer of the AspectJ runtime linkage is {@code Coverage.aj}, whose behaviour is emitted
 * directly by the dexlib2 {@code coverage-weaver} module — which injects a plain
 * {@code Lmop/Coverage;->log(Ljava/lang/String;)V} call with a weave-time-computed signature string
 * and references NO {@code org.aspectj.lang.*} type. Absorber: {@code COVERAGE_WEAVER}.
 */
class RuntimeSubstrateGrammarTest {

    /** The pipeline stage that absorbs the AspectJ runtime substrate. */
    static final AbsorbingStage ABSORBER = AbsorbingStage.COVERAGE_WEAVER;

    @Test
    void aspectJSubstrateAbsorbedByCoverageWeaver() throws Exception {
        DexFile woven = CoverageWeaveFixture.weaveAppClass();

        // (a) coverage-weaver emits the mop.Coverage runtime call directly into application code.
        List<String> invoked = CoverageWeaveFixture.invokedMethodRefs(woven);
        assertTrue(invoked.contains("Lmop/Coverage;->log"),
                "coverage-weaver must inject the Lmop/Coverage;->log(...) runtime call directly");

        // (b) The woven DEX references NO org.aspectj.lang.* type — the substrate is absorbed, not
        // linked. (Coverage.aj is the only source consumer and it is not on the dexlib2 path.)
        List<String> allRefs = CoverageWeaveFixture.allReferenceStrings(woven);
        assertTrue(allRefs.stream().noneMatch(r -> r.contains("Lorg/aspectj/lang/")),
                "no org.aspectj.lang.* reference may appear in coverage-woven DEX");
        assertTrue(allRefs.stream().noneMatch(r -> r.contains("Lorg/aspectj/runtime/")),
                "no org.aspectj.runtime.* reference may appear in coverage-woven DEX");

        // (c) Empirical evidence file present: the experimento-20260508 RVSEC-COV report.
        Path relatorio = Paths.get(home(), "rv-android", "experimento-20260508", "RELATORIO.md");
        assertTrue(Files.isRegularFile(relatorio),
                "experimento-20260508/RELATORIO.md empirical evidence present at " + relatorio);

        // Named absorber.
        assertEquals(AbsorbingStage.COVERAGE_WEAVER, ABSORBER);
    }

    private static String home() {
        String h = System.getenv("RVSEC_HOME");
        assertTrue(h != null && !h.isBlank(), "RVSEC_HOME must be set to locate the empirical evidence");
        return h;
    }
}
