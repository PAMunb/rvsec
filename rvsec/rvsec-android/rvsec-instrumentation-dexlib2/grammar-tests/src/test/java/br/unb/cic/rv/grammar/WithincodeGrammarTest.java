package br.unb.cic.rv.grammar;

import static org.junit.jupiter.api.Assertions.assertEquals;

import br.unb.cic.rv.grammar.util.DemandCounter;
import br.unb.cic.rv.grammar.util.DemandCounter.Corpus;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * {@code withincode(MethodPattern)} NOT-NEEDED α assertion test (cited by deferred.md §2.1). Path α:
 * zero demand in every corpus. {@code withincode} would filter join points by enclosing method
 * signature — a niche use case the corpora never exercise; no parser/matcher/emitter implementation.
 */
class WithincodeGrammarTest {

    @Test
    @DisplayName("withincode(MethodPattern) has zero corpus demand (path α)")
    void withincodeHasZeroCorpusDemand() {
        for (Corpus c : Corpus.values()) {
            assertEquals(0, DemandCounter.countMop(DemandCounter.WITHINCODE, c),
                    "expected zero source demand for withincode(MethodPattern) in " + c);
        }
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.WITHINCODE, Corpus.JCA));
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.WITHINCODE, Corpus.GENERIC));
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.WITHINCODE, Corpus.GENERIC_NEW));
    }
}
