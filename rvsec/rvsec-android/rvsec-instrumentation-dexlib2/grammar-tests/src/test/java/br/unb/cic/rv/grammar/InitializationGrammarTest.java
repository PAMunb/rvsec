package br.unb.cic.rv.grammar;

import static org.junit.jupiter.api.Assertions.assertEquals;

import br.unb.cic.rv.grammar.util.DemandCounter;
import br.unb.cic.rv.grammar.util.DemandCounter.Corpus;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * {@code initialization(ConstructorPattern)} / {@code preinitialization(ConstructorPattern)}
 * NOT-NEEDED α assertion tests (cited by deferred.md §2.1). Path α: zero demand in every corpus.
 * {@code staticinitialization(...)} is in-change via §4.Y; the constructor-related variants have zero
 * demand and no parser/matcher/emitter implementation. The {@code initialization} pattern excludes the
 * {@code preinitialization} and {@code staticinitialization} forms so the three are counted disjointly.
 */
class InitializationGrammarTest {

    @Test
    @DisplayName("initialization(ConstructorPattern) has zero corpus demand (path α)")
    void initializationHasZeroCorpusDemand() {
        for (Corpus c : Corpus.values()) {
            assertEquals(0, DemandCounter.countMop(DemandCounter.INITIALIZATION, c),
                    "expected zero source demand for initialization(ConstructorPattern) in " + c);
        }
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.INITIALIZATION, Corpus.JCA));
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.INITIALIZATION, Corpus.GENERIC));
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.INITIALIZATION, Corpus.GENERIC_NEW));
    }

    @Test
    @DisplayName("preinitialization(ConstructorPattern) has zero corpus demand (path α)")
    void preInitializationHasZeroCorpusDemand() {
        for (Corpus c : Corpus.values()) {
            assertEquals(0, DemandCounter.countMop(DemandCounter.PREINITIALIZATION, c),
                    "expected zero source demand for preinitialization(ConstructorPattern) in " + c);
        }
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.PREINITIALIZATION, Corpus.JCA));
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.PREINITIALIZATION, Corpus.GENERIC));
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.PREINITIALIZATION, Corpus.GENERIC_NEW));
    }
}
