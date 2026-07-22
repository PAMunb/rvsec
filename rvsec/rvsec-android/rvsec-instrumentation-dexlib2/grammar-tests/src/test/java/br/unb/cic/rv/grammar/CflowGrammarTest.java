package br.unb.cic.rv.grammar;

import static org.junit.jupiter.api.Assertions.assertEquals;

import br.unb.cic.rv.grammar.util.DemandCounter;
import br.unb.cic.rv.grammar.util.DemandCounter.Corpus;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * {@code cflow(Pointcut)} / {@code cflowbelow(Pointcut)} NOT-NEEDED α assertion tests (cited by
 * deferred.md §2.1). Path α: zero demand in every corpus. Runtime control-flow tracking requires a
 * thread-local stack of active frames and instrumentation in every method on the candidate flow —
 * substantial runtime cost for zero current use; no parser/matcher/emitter implementation.
 */
class CflowGrammarTest {

    @Test
    @DisplayName("cflow(Pointcut) has zero corpus demand (path α)")
    void cflowHasZeroCorpusDemand() {
        for (Corpus c : Corpus.values()) {
            assertEquals(0, DemandCounter.countMop(DemandCounter.CFLOW, c),
                    "expected zero source demand for cflow(Pointcut) in " + c);
        }
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.CFLOW, Corpus.JCA));
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.CFLOW, Corpus.GENERIC));
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.CFLOW, Corpus.GENERIC_NEW));
    }

    @Test
    @DisplayName("cflowbelow(Pointcut) has zero corpus demand (path α)")
    void cflowBelowHasZeroCorpusDemand() {
        for (Corpus c : Corpus.values()) {
            assertEquals(0, DemandCounter.countMop(DemandCounter.CFLOWBELOW, c),
                    "expected zero source demand for cflowbelow(Pointcut) in " + c);
        }
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.CFLOWBELOW, Corpus.JCA));
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.CFLOWBELOW, Corpus.GENERIC));
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.CFLOWBELOW, Corpus.GENERIC_NEW));
    }
}
