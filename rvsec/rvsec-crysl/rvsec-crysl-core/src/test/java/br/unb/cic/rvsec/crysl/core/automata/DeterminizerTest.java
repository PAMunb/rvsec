package br.unb.cic.rvsec.crysl.core.automata;

import static br.unb.cic.rvsec.crysl.core.automata.Fixtures.automaton;
import static br.unb.cic.rvsec.crysl.core.automata.Fixtures.sig;
import static br.unb.cic.rvsec.crysl.core.automata.Fixtures.word;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.model.Guard;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

/**
 * Determinization, on the shape that makes it necessary.
 *
 * <p>{@code ORDER con, a?, a} is the case the whole step exists for. Its Glushkov construction puts
 * two {@code a} edges on the state reached after {@code con}: one enters the optional occurrence,
 * one skips it and enters the mandatory one. No rule of the current corpus has that shape, so the
 * property is asserted here on a rule written for the purpose rather than looked for in the corpus.
 */
@Tag("automata")
class DeterminizerTest {

    /** The Glushkov automaton of {@code ORDER con, a?, a}: q1 offers a choice on {@code a}. */
    private static Automaton conOptionalAThenA() {
        return automaton("q0", "q3",
                "q0 con q1",
                "q1 a q2",
                "q1 a q3",
                "q2 a q3");
    }

    @Test
    @DisplayName("ORDER con, a?, a is genuinely non-deterministic")
    void test_glushkov_of_optional_repeat_is_non_deterministic() {
        assertFalse(Determinizer.isDeterministic(conOptionalAThenA()),
                "q1 has two outgoing a edges, which is the whole reason M2 determinizes");
    }

    @Test
    @DisplayName("subset construction removes the choice and keeps the language")
    void test_determinization_preserves_the_language() {
        Automaton nfa = conOptionalAThenA();
        Automaton dfa = Determinizer.determinize(nfa);

        assertTrue(Determinizer.isDeterministic(dfa));
        // L = { con a, con a a } and nothing else: closed form, read straight off the rule.
        for (List<br.unb.cic.rvsec.crysl.core.model.Signature> accepted :
                List.of(word("con", "a"), word("con", "a", "a"))) {
            assertTrue(nfa.accepts(accepted), "the hand-built automaton must accept " + accepted);
            assertTrue(dfa.accepts(accepted), "determinization must keep " + accepted);
        }
        for (List<br.unb.cic.rvsec.crysl.core.model.Signature> rejected :
                List.of(word(), word("con"), word("a"), word("con", "a", "a", "a"))) {
            assertFalse(nfa.accepts(rejected));
            assertFalse(dfa.accepts(rejected));
        }
    }

    @Test
    @DisplayName("a deterministic automaton is reported as such and survives the construction")
    void test_deterministic_input_is_a_no_op_for_the_language() {
        Automaton dfa = automaton("q0", "q2", "q0 a q1", "q1 b q2");
        assertTrue(Determinizer.isDeterministic(dfa));

        Automaton again = Determinizer.determinize(dfa);
        assertTrue(again.accepts(word("a", "b")));
        assertFalse(again.accepts(word("a")));
    }

    @Test
    @DisplayName("a partial transition function counts as deterministic")
    void test_missing_edge_is_rejection_not_choice() {
        Automaton partial = automaton("q0", "q1", "q0 a q1");
        assertTrue(Determinizer.isDeterministic(partial),
                "no edge on b is rejection; the counting rule says so explicitly");
    }

    @Test
    @DisplayName("merging two edges with different guards drops the guard")
    void test_guards_merge_only_when_they_agree() {
        Automaton sameGuard = new Automaton(Set.of("q0", "q1", "q2"), "q0", Set.of("q1", "q2"),
                List.of(new Transition("q0", sig("a"), Optional.of(new Guard("x > 0")), "q1"),
                        new Transition("q0", sig("a"), Optional.of(new Guard("x > 0")), "q2")));
        Automaton merged = Determinizer.determinize(sameGuard);
        assertEquals(Optional.of(new Guard("x > 0")), merged.transitions().get(0).guard());

        Automaton differentGuards = new Automaton(Set.of("q0", "q1", "q2"), "q0", Set.of("q1", "q2"),
                List.of(new Transition("q0", sig("a"), Optional.of(new Guard("x > 0")), "q1"),
                        new Transition("q0", sig("a"), Optional.of(new Guard("x < 0")), "q2")));
        Automaton dropped = Determinizer.determinize(differentGuards);
        assertEquals(Optional.empty(), dropped.transitions().get(0).guard(),
                "a disjunction of guards is not a guard this module can write, so it says nothing");
    }

    @Test
    @DisplayName("the census counts and states its counting rule")
    void test_census_reports_a_count_with_its_rule() {
        Determinizer.Census census = Determinizer.census(List.of(
                conOptionalAThenA(),
                automaton("q0", "q1", "q0 a q1"),
                automaton("q0", "q1", "q0 a q1", "q1 b q1")));

        assertEquals(3, census.total());
        assertEquals(2, census.alreadyDeterministic());
        assertEquals(Determinizer.COUNTING_RULE, census.countingRule());
        assertTrue(census.countingRule().startsWith("R-DET:"));
    }

    @Test
    @DisplayName("an empty corpus is a census of zero, not a failure")
    void test_census_of_nothing() {
        assertEquals(0, Determinizer.census(List.of()).total());
    }

    @Test
    @DisplayName("a census cannot be built without its rule or with inconsistent counts")
    void test_census_rejects_a_number_without_a_rule() {
        assertThrows(IllegalArgumentException.class,
                () -> new Determinizer.Census(3, 2, "  "));
        assertThrows(IllegalArgumentException.class,
                () -> new Determinizer.Census(2, 3, Determinizer.COUNTING_RULE));
    }
}
