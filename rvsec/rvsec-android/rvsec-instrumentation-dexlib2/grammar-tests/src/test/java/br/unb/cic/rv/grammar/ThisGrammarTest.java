package br.unb.cic.rv.grammar;

import static org.junit.jupiter.api.Assertions.assertEquals;

import br.unb.cic.rv.grammar.util.DemandCounter;
import br.unb.cic.rv.grammar.util.DemandCounter.Corpus;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * {@code this(name)} value-binding and {@code this(Type)} type-matching NOT-NEEDED α assertion tests
 * (cited by deferred.md §2.1). Path α: zero demand in every corpus. The dexlib2 binding form
 * {@code target(name)} covers the common receiver-binding case; {@code this()} distinguishes the bound
 * aspect instance from the join-point receiver, which the corpora never exercise.
 */
class ThisGrammarTest {

    @Test
    @DisplayName("this(name) binding has zero corpus demand (path α)")
    void thisBindingHasZeroCorpusDemand() {
        for (Corpus c : Corpus.values()) {
            assertEquals(0, DemandCounter.countMop(DemandCounter.THIS_BINDING, c),
                    "expected zero source demand for this(name) binding in " + c);
        }
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.THIS_BINDING, Corpus.JCA));
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.THIS_BINDING, Corpus.GENERIC));
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.THIS_BINDING, Corpus.GENERIC_NEW));
    }

    @Test
    @DisplayName("this(Type) type-matching has zero corpus demand (path α)")
    void thisTypeMatchingHasZeroCorpusDemand() {
        for (Corpus c : Corpus.values()) {
            assertEquals(0, DemandCounter.countMop(DemandCounter.THIS_TYPE, c),
                    "expected zero source demand for this(Type) type-matching in " + c);
        }
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.THIS_TYPE, Corpus.JCA));
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.THIS_TYPE, Corpus.GENERIC));
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.THIS_TYPE, Corpus.GENERIC_NEW));
    }
}
