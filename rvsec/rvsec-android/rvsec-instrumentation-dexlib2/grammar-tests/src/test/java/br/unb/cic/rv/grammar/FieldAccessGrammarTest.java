package br.unb.cic.rv.grammar;

import static org.junit.jupiter.api.Assertions.assertEquals;

import br.unb.cic.rv.grammar.util.DemandCounter;
import br.unb.cic.rv.grammar.util.DemandCounter.Corpus;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * {@code get(FieldPattern)} / {@code set(FieldPattern)} field-access pointcut NOT-NEEDED α assertion
 * tests (cited by deferred.md §2.1). Path α: zero demand in every corpus (source AND pipeline) and no
 * parser/matcher/emitter implementation. A field-access pointcut would require a new join-point family
 * (iget/iput/sget/sput DEX opcodes); the corpora never exercise it. The earlier draft's substring grep
 * conflated {@code call(* Foo.get(...))} method-name calls with field-access pointcuts — corrected to
 * zero by anchoring the {@code get(}/{@code set(} pattern to a clause boundary (start or after a
 * composition operator).
 */
class FieldAccessGrammarTest {

    @Test
    @DisplayName("get(FieldPattern) field-access pointcut has zero corpus demand (path α)")
    void getFieldAccessHasZeroCorpusDemand() {
        for (Corpus c : Corpus.values()) {
            assertEquals(0, DemandCounter.countMop(DemandCounter.GET_FIELD, c),
                    "expected zero source demand for get(FieldPattern) in " + c);
        }
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.GET_FIELD, Corpus.JCA));
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.GET_FIELD, Corpus.GENERIC));
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.GET_FIELD, Corpus.GENERIC_NEW));
    }

    @Test
    @DisplayName("set(FieldPattern) field-access pointcut has zero corpus demand (path α)")
    void setFieldAccessHasZeroCorpusDemand() {
        for (Corpus c : Corpus.values()) {
            assertEquals(0, DemandCounter.countMop(DemandCounter.SET_FIELD, c),
                    "expected zero source demand for set(FieldPattern) in " + c);
        }
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.SET_FIELD, Corpus.JCA));
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.SET_FIELD, Corpus.GENERIC));
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.SET_FIELD, Corpus.GENERIC_NEW));
    }
}
