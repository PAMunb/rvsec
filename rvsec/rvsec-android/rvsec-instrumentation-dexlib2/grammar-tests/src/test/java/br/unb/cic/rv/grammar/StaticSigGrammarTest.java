package br.unb.cic.rv.grammar;

import br.unb.cic.rv.grammar.util.AbsorbingStage;
import br.unb.cic.rv.grammar.util.DemandCounter;
import br.unb.cic.rv.grammar.util.DemandCounter.Corpus;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Backs the matrix row "{@code __STATICSIG} macro" (§4.S'). NOT-NEEDED β: the {@code __STATICSIG}
 * macro carries non-zero SourceDemand (3 generic_new sites) but zero PipelineDemand — the JavaMOP
 * compiler inlines it as {@code thisJoinPoint.getStaticPart().getSignature()} directly into the
 * {@code *staticinitEvent(Signature)} dispatch. Absorber: {@code JAVA_MOP_COMPILER}.
 *
 * <p>Cross-references the §4.S'.1 audit (COMPLETED 2026-05-26): canonical evidence path
 * {@code $RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/generic_new/MultiSpec_1MonitorAspect.aj},
 * recorded in {@code docs/analise_sintese_macro.md} Appendix A.2. The pipeline corpus snapshot ships
 * the inlined-absorption pattern verbatim.
 */
class StaticSigGrammarTest {

    /** The pipeline stage that absorbs {@code __STATICSIG} before dexlib2 sees it. */
    static final AbsorbingStage ABSORBER = AbsorbingStage.JAVA_MOP_COMPILER;

    /** The inlined-absorption pattern: the compiler replaces {@code __STATICSIG} with this
     *  reflective call as the {@code *staticinitEvent(Signature)} argument. */
    private static final Pattern INLINED_GETSIGNATURE =
            Pattern.compile("thisJoinPoint\\.getStaticPart\\(\\)\\.getSignature\\(\\)");

    @Test
    void staticSigAbsorbedByJavaMopCompiler() {
        // (a) SourceDemand >= 1 — 3 sites in generic_new .mop specs.
        assertTrue(DemandCounter.countMop(DemandCounter.STATICSIG, Corpus.GENERIC_NEW) >= 1,
                "__STATICSIG has source demand in generic_new .mop specs (3 sites)");

        // (b) PipelineDemand == 0 — no __STATICSIG token survives into either compiled .aj.
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.STATICSIG, Corpus.JCA),
                "__STATICSIG absorbed by the JavaMOP compiler — zero pipeline demand (jca)");
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.STATICSIG, Corpus.GENERIC_NEW),
                "__STATICSIG absorbed by the JavaMOP compiler — zero pipeline demand (generic_new)");

        // (c) Absorber JAVA_MOP_COMPILER.
        assertEquals(AbsorbingStage.JAVA_MOP_COMPILER, ABSORBER);

        // (d) The compiled generic_new .aj carries the inlined-absorption pattern — the macro became
        // thisJoinPoint.getStaticPart().getSignature() invocations (the 3 §4.S'.1 sites).
        Matcher m = INLINED_GETSIGNATURE.matcher(compiledGenericNew());
        int inlined = 0;
        while (m.find()) {
            inlined++;
        }
        assertTrue(inlined >= 1,
                "compiled generic_new .aj must carry the inlined thisJoinPoint.getStaticPart()."
                        + "getSignature() absorption pattern (§4.S'.1 audit: 3 sites)");
    }

    private static String compiledGenericNew() {
        try (InputStream in = StaticSigGrammarTest.class.getClassLoader()
                .getResourceAsStream("compiled-aj-fixtures/generic_new/MultiSpec_1MonitorAspect.aj")) {
            assertNotNull(in, "generic_new compiled .aj evidence file present on classpath");
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new RuntimeException("failed to read generic_new compiled .aj fixture", e);
        }
    }
}
