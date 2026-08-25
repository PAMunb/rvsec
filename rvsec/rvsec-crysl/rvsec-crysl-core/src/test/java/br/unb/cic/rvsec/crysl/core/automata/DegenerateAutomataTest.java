package br.unb.cic.rvsec.crysl.core.automata;

import static br.unb.cic.rvsec.crysl.core.automata.Fixtures.automaton;
import static br.unb.cic.rvsec.crysl.core.automata.Fixtures.sig;
import static br.unb.cic.rvsec.crysl.core.automata.Fixtures.word;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.metric.M2Result;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

/**
 * The five shapes automata code dies on.
 *
 * <p>Every one of them is a case where a plausible implementation returns a confident wrong answer
 * instead of failing: an empty language that swallows every comparison, a universal language that
 * agrees with everything, a self-loop that never terminates the search, a letter nothing can read,
 * and an automaton with nowhere to accept.
 */
@Tag("automata")
class DegenerateAutomataTest {

    /** No accepting state: the language is empty though the automaton has edges. */
    private static Automaton emptyLanguage() {
        return automaton("q0", "", "q0 a q1", "q1 a q1");
    }

    /** One accepting state looping on every letter: the language is everything over {a}. */
    private static Automaton universalOverA() {
        return automaton("u0", "u0", "u0 a u0");
    }

    @Test
    @DisplayName("an empty language accepts nothing and is contained in everything")
    void test_empty_language() {
        Automaton empty = emptyLanguage();
        assertFalse(empty.accepts(word()));
        assertFalse(empty.accepts(word("a")));

        ProductSearch.OrderComparison comparison = ProductSearch.compare(empty, universalOverA());
        assertEquals(M2Result.Verdict.MOP_MORE_RESTRICTIVE, comparison.verdict());
        assertEquals(List.of(), comparison.cryslOnlyWitness(List.of()).orElseThrow().word(),
                "the shortest word the universal language has and the empty one lacks is the "
                        + "empty word");
        assertTrue(comparison.mopOnlyWitness(List.of()).isEmpty());
    }

    @Test
    @DisplayName("two empty languages are equivalent, not incomparable")
    void test_empty_against_empty() {
        assertEquals(M2Result.Verdict.EQUIVALENT,
                ProductSearch.compare(emptyLanguage(), automaton("z0", "")).verdict());
    }

    @Test
    @DisplayName("a universal language accepts every word over its alphabet")
    void test_universal_language() {
        Automaton universal = universalOverA();
        assertTrue(universal.accepts(word()));
        assertTrue(universal.accepts(word("a")));
        assertTrue(universal.accepts(word("a", "a", "a", "a")));
        assertEquals(1, Minimizer.minimize(universal).states().size());
    }

    @Test
    @DisplayName("a single accepting state with a self-loop terminates the search")
    void test_single_state_loop() {
        Automaton loop = universalOverA();
        Automaton onePlus = automaton("q0", "q1", "q0 a q1", "q1 a q1");

        ProductSearch.OrderComparison comparison = ProductSearch.compare(loop, onePlus);
        assertEquals(M2Result.Verdict.MOP_MORE_PERMISSIVE, comparison.verdict());
        assertEquals(List.of(), comparison.mopOnlyWitness(List.of()).orElseThrow().word());
    }

    @Test
    @DisplayName("a letter reachable from no state is in the alphabet and out of the language")
    void test_symbol_reachable_from_no_state() {
        // b appears only on an edge leaving q2, and nothing reaches q2 from the initial state.
        Automaton withOrphan = automaton("q0", "q1",
                "q0 a q1",
                "q2 b q2");

        assertEquals(Set.of(sig("a"), sig("b")), withOrphan.alphabet());
        assertEquals(Set.of("q0", "q1"), withOrphan.reachableStates());
        assertFalse(withOrphan.accepts(word("b")));

        Automaton minimal = Minimizer.minimize(withOrphan);
        assertFalse(minimal.alphabet().contains(sig("b")),
                "the orphan letter reaches no accepting state, so minimization drops it");
        assertEquals(Minimizer.minimize(automaton("s0", "s1", "s0 a s1")), minimal,
                "and what is left is exactly the language the reachable part denoted");
    }

    @Test
    @DisplayName("an empty accepting set minimizes to the canonical empty automaton")
    void test_empty_accepting_set() {
        Automaton minimal = Minimizer.minimize(emptyLanguage());
        assertTrue(minimal.accepting().isEmpty());
        assertEquals(1, minimal.states().size());
        assertTrue(minimal.transitions().isEmpty());
    }

    @Test
    @DisplayName("an automaton with no edges at all is the language of the empty word or nothing")
    void test_no_edges() {
        assertTrue(automaton("q0", "q0").accepts(word()));
        assertFalse(automaton("q0", "").accepts(word()));
        assertTrue(Determinizer.isDeterministic(automaton("q0", "q0")));
    }

    @Test
    @DisplayName("a transition leaving the state set is rejected at construction")
    void test_ill_formed_automaton_is_refused() {
        assertThrows(IllegalArgumentException.class,
                () -> new Automaton(Set.of("q0"), "q0", Set.of("q0"),
                        List.of(new Transition("q0", sig("a"), Optional.empty(), "nowhere"))),
                "an edge into a state that does not exist is not an automaton, and letting it "
                        + "through would make every later traversal quietly incomplete");
    }
}
