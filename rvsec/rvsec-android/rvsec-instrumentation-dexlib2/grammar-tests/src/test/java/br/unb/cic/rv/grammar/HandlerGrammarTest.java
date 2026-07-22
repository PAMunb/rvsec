package br.unb.cic.rv.grammar;

import static org.junit.jupiter.api.Assertions.assertEquals;

import br.unb.cic.rv.grammar.util.DemandCounter;
import br.unb.cic.rv.grammar.util.DemandCounter.Corpus;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * {@code handler(TypePattern)} exception-handler pointcut NOT-NEEDED α assertion test (cited by
 * deferred.md §2.1). Path α: zero source demand across all four corpora. Round-8 reclassification
 * (P-decision) moved {@code handler(...)} from path β to path α — path β requires
 * {@code SourceDemand ≥ 1} AND an upstream absorber consuming an actual source-level use;
 * {@code handler()} has neither (no consumer exists, and there is no DEX-level analogue for an
 * exception-handler join point). The method name is retained from the round-7 framing for cross-commit
 * stability, but the assertion is the path-α zero-demand check.
 */
class HandlerGrammarTest {

    @Test
    @DisplayName("handler(TypePattern) has zero corpus demand (path α)")
    void handlerAbsorbedByNamedRefPC() {
        for (Corpus c : Corpus.values()) {
            assertEquals(0, DemandCounter.countMop(DemandCounter.HANDLER, c),
                    "expected zero source demand for handler(TypePattern) in " + c);
        }
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.HANDLER, Corpus.JCA));
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.HANDLER, Corpus.GENERIC));
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.HANDLER, Corpus.GENERIC_NEW));
    }
}
