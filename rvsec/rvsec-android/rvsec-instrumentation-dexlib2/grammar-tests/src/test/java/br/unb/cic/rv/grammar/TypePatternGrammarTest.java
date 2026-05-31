package br.unb.cic.rv.grammar;

import static org.junit.jupiter.api.Assertions.assertEquals;

import br.unb.cic.rv.grammar.util.DemandCounter;
import br.unb.cic.rv.grammar.util.DemandCounter.Corpus;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;

/**
 * {@code T+} subtype inside {@code !within(...)} NOT-NEEDED α assertion test
 * (cited by deferred.md §2.1).
 *
 * <p>The {@code +} subtype-pattern token inside a negated {@code within} has zero demand in every
 * corpus — {@code matchesTypePattern} strips the {@code +} before the exact-match, and no spec roots
 * a subtype-pattern on the negated-within form (subtype matching is exercised only through
 * {@code call} owner-position, covered separately by {@code CallPointcutGrammarTest}). The
 * designator key excludes the JavaMOP-injected framework baseline
 * {@code !within(com.runtimeverification...RVMObject+)} — that single pipeline token is the
 * auto-generated RVMObject self-exclusion owned by the separate {@code !within(TypePattern)} COVERED
 * row, not a spec-authored subtype filter. Path α: {@code countMop == 0} across all corpora AND
 * {@code countCompiledAj == 0}.</p>
 */
class TypePatternGrammarTest {

    @Test
    @DisplayName("T+ inside !within(...) has zero corpus demand (path α)")
    void tPlusInsideNegativeWithinHasZeroCorpusDemand() {
        for (Corpus c : Corpus.values()) {
            assertEquals(0, DemandCounter.countMop("type_pattern_subtype", c),
                    "expected zero source demand for spec-authored T+ inside !within(...) in " + c);
        }
        assertEquals(0, DemandCounter.countCompiledAj("type_pattern_subtype", Corpus.JCA));
        assertEquals(0, DemandCounter.countCompiledAj("type_pattern_subtype", Corpus.GENERIC));
        assertEquals(0, DemandCounter.countCompiledAj("type_pattern_subtype", Corpus.GENERIC_NEW));
    }
}
