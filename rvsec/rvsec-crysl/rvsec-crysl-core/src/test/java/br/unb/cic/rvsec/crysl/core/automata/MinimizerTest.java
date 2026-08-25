package br.unb.cic.rvsec.crysl.core.automata;

import static br.unb.cic.rvsec.crysl.core.automata.Fixtures.automaton;
import static br.unb.cic.rvsec.crysl.core.automata.Fixtures.word;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.metric.M2Result;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

/**
 * Minimization, on the pair that motivates it.
 *
 * <p>{@code a,(b|c)} and {@code (a,b)|(a,c)} are the same language written two ways. A comparison
 * made over the shape of the formula would report them as divergent, and the specification and the
 * rule would be accused of disagreeing about an order they agree about.
 */
@Tag("automata")
class MinimizerTest {

    /** {@code a,(b|c)}: one a edge, then a choice of letter. */
    private static Automaton factored() {
        return automaton("q0", "q2",
                "q0 a q1",
                "q1 b q2",
                "q1 c q2");
    }

    /** {@code (a,b)|(a,c)}: two a edges from the initial state, hence non-deterministic. */
    private static Automaton distributed() {
        return automaton("p0", "p3,p4",
                "p0 a p1",
                "p1 b p3",
                "p0 a p2",
                "p2 c p4");
    }

    @Test
    @DisplayName("a,(b|c) and (a,b)|(a,c) minimize to the same automaton")
    void test_two_spellings_of_one_language_compare_equal() {
        assertEquals(Minimizer.minimize(factored()), Minimizer.minimize(distributed()),
                "the minimal trimmed DFA of a language is unique, and the canonical renaming is "
                        + "what turns that uniqueness into an assertion a test can make");
    }

    @Test
    @DisplayName("and the product search agrees with the minimizer about them")
    void test_the_two_spellings_are_language_equivalent() {
        assertEquals(M2Result.Verdict.EQUIVALENT,
                ProductSearch.compare(factored(), distributed()).verdict());
    }

    @Test
    @DisplayName("minimization preserves the language")
    void test_minimization_preserves_the_language() {
        Automaton minimal = Minimizer.minimize(distributed());
        assertTrue(minimal.accepts(word("a", "b")));
        assertTrue(minimal.accepts(word("a", "c")));
        assertFalse(minimal.accepts(word("a")));
        assertFalse(minimal.accepts(word("b")));
        assertFalse(minimal.accepts(word("a", "b", "c")));
    }

    @Test
    @DisplayName("equivalent states collapse")
    void test_redundant_states_are_merged() {
        // Two distinct b-successors that are indistinguishable: both accept nothing further.
        Automaton redundant = automaton("q0", "q1,q2",
                "q0 a q1",
                "q0 b q2");
        Automaton minimal = Minimizer.minimize(redundant);
        assertEquals(2, minimal.states().size(),
                "q1 and q2 are Myhill-Nerode equivalent, so the minimal automaton has one of them");
        assertTrue(minimal.accepts(word("a")));
        assertTrue(minimal.accepts(word("b")));
    }

    @Test
    @DisplayName("every empty language collapses to the same one-state record")
    void test_the_empty_language_has_one_canonical_form() {
        Automaton emptyOverA = automaton("q0", "", "q0 a q1");
        Automaton emptyOverB = automaton("s0", "", "s0 b s1", "s1 b s1");
        assertEquals(Minimizer.minimize(emptyOverA), Minimizer.minimize(emptyOverB),
                "an empty language is the empty language whatever alphabet it was written over");
        assertTrue(Minimizer.minimize(emptyOverA).accepting().isEmpty());
    }

    @Test
    @DisplayName("minimization is idempotent")
    void test_minimizing_a_minimal_automaton_changes_nothing() {
        Automaton once = Minimizer.minimize(distributed());
        assertEquals(once, Minimizer.minimize(once));
    }
}
