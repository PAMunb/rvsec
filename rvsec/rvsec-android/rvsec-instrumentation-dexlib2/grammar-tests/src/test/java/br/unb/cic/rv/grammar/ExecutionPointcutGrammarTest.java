package br.unb.cic.rv.grammar;

import br.unb.cic.rv.grammar.util.AbsorbingStage;
import br.unb.cic.rv.grammar.util.DemandCounter;
import br.unb.cic.rv.grammar.util.DemandCounter.Corpus;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Backs the matrix row "positive {@code execution(...)}" (§4.E'). NOT-NEEDED β: positive
 * {@code execution(...)} has zero PipelineDemand in every compiled corpus — the sole source consumer
 * is {@code aspect/Coverage.aj:50} {@code execution(* *.*(..))}, absorbed by the dexlib2
 * {@code coverage-weaver} module (round-11 R11.2 — the absorber is {@code COVERAGE_WEAVER}, NOT
 * "JavaMOP call-rewrite"; JavaMOP emits {@code execution()} verbatim and the only positive form lives
 * in Coverage.aj). Pins the round-10 AA-decision verdict.
 */
class ExecutionPointcutGrammarTest {

    /** The pipeline stage that absorbs positive {@code execution(...)} before dexlib2 sees it. */
    static final AbsorbingStage ABSORBER = AbsorbingStage.COVERAGE_WEAVER;

    @Test
    void executionPositiveAbsorptionAssertion() {
        // SourceDemand: the sole positive execution(* *.*(..)) lives in aspect/Coverage.aj:50.
        assertEquals(0, DemandCounter.countMop(DemandCounter.EXECUTION_POSITIVE, Corpus.JCA),
                "no positive execution(...) in any jca .mop spec");
        assertEquals(0, DemandCounter.countMop(DemandCounter.EXECUTION_POSITIVE, Corpus.GENERIC),
                "no positive execution(...) in any generic .mop spec");
        assertEquals(0, DemandCounter.countMop(DemandCounter.EXECUTION_POSITIVE, Corpus.GENERIC_NEW),
                "no positive execution(...) in any generic_new .mop spec");
        assertTrue(DemandCounter.countMop(DemandCounter.EXECUTION_POSITIVE, Corpus.ASPECT) >= 1,
                "the sole positive execution(...) consumer is aspect/Coverage.aj:50 execution(* *.*(..))");

        // PipelineDemand: absorbed before the compiled .aj — zero in every pipeline corpus.
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.EXECUTION_POSITIVE, Corpus.JCA),
                "positive execution(...) absorbed by coverage-weaver — zero pipeline demand (jca)");
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.EXECUTION_POSITIVE, Corpus.GENERIC),
                "positive execution(...) absorbed by coverage-weaver — zero pipeline demand (generic)");
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.EXECUTION_POSITIVE, Corpus.GENERIC_NEW),
                "positive execution(...) absorbed by coverage-weaver — zero pipeline demand (generic_new)");

        // Named absorber (round-11 R11.2).
        assertEquals(AbsorbingStage.COVERAGE_WEAVER, ABSORBER,
                "positive execution(...) absorber is coverage-weaver (R11.2), not JavaMOP call-rewrite");

        // The empirical-monitors evidence (the compiled-.aj corpus snapshot) is present on the
        // classpath for every pipeline corpus — the absorption is asserted against real files.
        assertNotNull(ExecutionPointcutGrammarTest.class.getClassLoader()
                        .getResource("compiled-aj-fixtures/jca/MultiSpec_1MonitorAspect.aj"),
                "jca empirical-monitors evidence file present");
        assertNotNull(ExecutionPointcutGrammarTest.class.getClassLoader()
                        .getResource("compiled-aj-fixtures/generic/MultiSpec_1MonitorAspect.aj"),
                "generic empirical-monitors evidence file present");
        assertNotNull(ExecutionPointcutGrammarTest.class.getClassLoader()
                        .getResource("compiled-aj-fixtures/generic_new/MultiSpec_1MonitorAspect.aj"),
                "generic_new empirical-monitors evidence file present");
    }
}
