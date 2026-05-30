package br.unb.cic.rv.grammar;

import br.unb.cic.rv.grammar.util.AbsorbingStage;
import br.unb.cic.rv.grammar.util.DemandCounter;
import br.unb.cic.rv.grammar.util.DemandCounter.Corpus;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Backs the matrix row "positive {@code within(typePattern)} simple" (§4.W'). NOT-NEEDED β: positive
 * {@code within(...)} has zero PipelineDemand in every compiled corpus — the only source-level
 * consumer is {@code aspect/Coverage.aj}'s {@code excludedPackages()} macro, which is absorbed by the
 * dexlib2 {@code coverage-weaver} module (round-11 R11.2 — the absorber is {@code COVERAGE_WEAVER},
 * NOT a "MOP macro-body" stage). This test pins the round-10 AB-decision verdict so a future corpus
 * introducing positive {@code within(...)} as an event predicate trips {@code MatrixIntegrityTest}.
 */
class WithinPositiveGrammarTest {

    /** The pipeline stage that absorbs positive {@code within(...)} before dexlib2 sees it. */
    static final AbsorbingStage ABSORBER = AbsorbingStage.COVERAGE_WEAVER;

    @Test
    void withinPositiveAbsorptionAssertion() {
        // SourceDemand: the only positive within(...) lives in aspect/Coverage.aj's excludedPackages()
        // macro — never in any .mop spec.
        assertEquals(0, DemandCounter.countMop(DemandCounter.WITHIN_POSITIVE, Corpus.JCA),
                "no positive within(...) in any jca .mop spec");
        assertEquals(0, DemandCounter.countMop(DemandCounter.WITHIN_POSITIVE, Corpus.GENERIC),
                "no positive within(...) in any generic .mop spec");
        assertEquals(0, DemandCounter.countMop(DemandCounter.WITHIN_POSITIVE, Corpus.GENERIC_NEW),
                "no positive within(...) in any generic_new .mop spec");
        assertTrue(DemandCounter.countMop(DemandCounter.WITHIN_POSITIVE, Corpus.ASPECT) >= 1,
                "the sole positive within(...) consumer is aspect/Coverage.aj excludedPackages()");

        // PipelineDemand: absorbed before the compiled .aj — zero in every pipeline corpus.
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.WITHIN_POSITIVE, Corpus.JCA),
                "positive within(...) absorbed by coverage-weaver — zero pipeline demand (jca)");
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.WITHIN_POSITIVE, Corpus.GENERIC),
                "positive within(...) absorbed by coverage-weaver — zero pipeline demand (generic)");
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.WITHIN_POSITIVE, Corpus.GENERIC_NEW),
                "positive within(...) absorbed by coverage-weaver — zero pipeline demand (generic_new)");

        // Named absorber (round-11 R11.2).
        assertEquals(AbsorbingStage.COVERAGE_WEAVER, ABSORBER,
                "positive within(...) absorber is coverage-weaver (R11.2), not a MOP macro-body stage");
    }
}
