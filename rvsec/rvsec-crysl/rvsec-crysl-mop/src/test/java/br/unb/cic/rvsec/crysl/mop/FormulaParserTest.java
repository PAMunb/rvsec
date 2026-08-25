package br.unb.cic.rvsec.crysl.mop;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.LiftFailure;
import br.unb.cic.rvsec.crysl.core.automata.LabelAutomaton;
import br.unb.cic.rvsec.crysl.core.automata.LabelTransition;
import br.unb.cic.rvsec.crysl.core.model.Label;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * The {@code ere} and {@code fsm} readers, on hand-built formulas whose languages are known in
 * closed form, plus the refusal of everything else.
 */
class FormulaParserTest {

    private static final Path FILE = Path.of("Synthetic.mop");

    @Test
    @DisplayName("ptltl is refused with a typed error, never parsed as an ere")
    void test_ptltl_is_refused() {
        UnsupportedLogic error = assertThrows(
                UnsupportedLogic.class,
                () -> FormulaParser.parse(FILE, "ptltl", "[*] (a -> <*> b)"));
        assertEquals("ptltl", error.logic());
        assertTrue(error.getMessage().contains("ere"),
                "the message names what is read, so that the refusal is actionable");
    }

    @Test
    @DisplayName("a concatenation accepts exactly its own word")
    void test_ere_concatenation() throws LiftFailure {
        LabelAutomaton automaton = FormulaParser.parse(FILE, "ere", " vo gb ");
        assertTrue(accepts(automaton, "vo", "gb"));
        assertFalse(accepts(automaton), "the language does not contain the empty word");
        assertFalse(accepts(automaton, "vo"));
        assertFalse(accepts(automaton, "gb", "vo"));
        assertFalse(accepts(automaton, "vo", "gb", "gb"));
    }

    @Test
    @DisplayName("star accepts the empty word, plus does not")
    void test_ere_star_and_plus() throws LiftFailure {
        LabelAutomaton star = FormulaParser.parse(FILE, "ere", "e1*");
        assertTrue(accepts(star));
        assertTrue(accepts(star, "e1", "e1", "e1"));

        LabelAutomaton plus = FormulaParser.parse(FILE, "ere", "e1+");
        assertFalse(accepts(plus));
        assertTrue(accepts(plus, "e1"));
        assertTrue(accepts(plus, "e1", "e1"));
    }

    @Test
    @DisplayName("epsilon is the empty word and not a label")
    void test_ere_epsilon() throws LiftFailure {
        LabelAutomaton automaton = FormulaParser.parse(FILE, "ere", "e1* (d | epsilon)");
        assertTrue(accepts(automaton));
        assertTrue(accepts(automaton, "e1", "d"));
        assertTrue(accepts(automaton, "e1", "e1"));
        assertFalse(alphabetOf(automaton).contains("epsilon"),
                "'epsilon' must not become a letter of the alphabet");
    }

    @Test
    @DisplayName("the construction is non-deterministic where the formula is, and stays correct")
    void test_ere_nondeterminism() throws LiftFailure {
        // (g3* g1 | g3* g2) is the shape 22 of the corpus's ere formulas start with: two g3 edges
        // leave the initial state. The construction does not determinize - that is G03's job - and
        // the language must be right anyway.
        LabelAutomaton automaton = FormulaParser.parse(FILE, "ere", "(g3* g1 | g3* g2) i1");
        long fromInitialOnG3 = automaton.transitions().stream()
                .filter(t -> t.from().equals(automaton.initial()))
                .filter(t -> t.symbol().name().equals("g3"))
                .count();
        assertEquals(2, fromInitialOnG3, "genuinely non-deterministic, as the formula is");
        assertTrue(accepts(automaton, "g3", "g3", "g1", "i1"));
        assertTrue(accepts(automaton, "g2", "i1"));
        assertFalse(accepts(automaton, "g3", "i1"));
    }

    @Test
    @DisplayName("the formula's automaton is over labels, and says so in its type")
    void test_ere_alphabet_is_labels() throws LiftFailure {
        // The parser can only see the names the formula writes, so what it returns is a language
        // over Label. Nothing here encodes a label as a signature: the step to signatures is the
        // inverse morphism and it happens once, in MopLifter (design D-20).
        LabelAutomaton automaton = FormulaParser.parse(FILE, "ere", "a b");
        assertEquals(Set.of("a", "b"), alphabetOf(automaton));
        assertEquals(new Label("a"), automaton.transitions().get(0).symbol());
    }

    @Test
    @DisplayName("a malformed ere is refused rather than read as far as it goes")
    void test_ere_malformed() {
        assertThrows(LiftFailure.class, () -> FormulaParser.parse(FILE, "ere", "(a b"));
        assertThrows(LiftFailure.class, () -> FormulaParser.parse(FILE, "ere", "a & b"));
    }

    @Test
    @DisplayName("fsm: the first block is the initial state, and a match alias fixes the accepting set")
    void test_fsm_with_match_alias() throws LiftFailure {
        LabelAutomaton automaton = FormulaParser.parse(FILE, "fsm", """
                  start [
                     c1 -> init
                  ]
                  init [
                     c1 -> init
                     next -> end
                  ]
                  end [
                     next -> end
                  ]
                  alias match1 = init
                """);
        assertEquals("start", automaton.initial(), "JavaMOP's initial state is the first declared");
        assertEquals(Set.of("init"), automaton.accepting(),
                "only the state the match alias names accepts");
        assertTrue(accepts(automaton, "c1"));
        assertTrue(accepts(automaton, "c1", "c1"));
        assertFalse(accepts(automaton, "c1", "next"), "'end' is not an accepting state");
    }

    @Test
    @DisplayName("fsm without an alias: every declared state accepts, and leaving the machine fails")
    void test_fsm_without_alias() throws LiftFailure {
        // The 118 generic specifications are of this shape: no alias, only @fail. The property they
        // state is "the trace never leaves the machine", so every declared state accepts and a
        // transition into a state no block declares is the sink.
        LabelAutomaton automaton = FormulaParser.parse(FILE, "fsm", """
                  s0 [
                    a -> s1
                    b -> sink
                  ]
                  s1 [
                    a -> s1
                  ]
                """);
        assertEquals(Set.of("s0", "s1"), automaton.accepting());
        assertTrue(automaton.states().contains("sink"),
                "a referenced state must be in the state set for the automaton to be well-formed");
        assertTrue(accepts(automaton));
        assertTrue(accepts(automaton, "a", "a"));
        assertFalse(accepts(automaton, "b"), "the sink is declared by no block, so it rejects");
        assertFalse(accepts(automaton, "a", "b"), "and there is no b edge out of s1 at all");
    }

    @Test
    @DisplayName("a specification with no formula constrains nothing")
    void test_unconstrained() {
        LabelAutomaton automaton = FormulaParser.unconstrained(
                List.of(new Label("a"), new Label("b")));
        assertTrue(accepts(automaton));
        assertTrue(accepts(automaton, "a", "b", "b", "a"));
        assertEquals(1, automaton.states().size());
    }

    @Test
    @DisplayName("an fsm with no state block is refused")
    void test_fsm_empty() {
        assertThrows(LiftFailure.class, () -> FormulaParser.parse(FILE, "fsm", "   "));
    }

    /** Runs the (possibly non-deterministic) automaton over a word of labels. */
    private static boolean accepts(LabelAutomaton automaton, String... word) {
        Set<String> current = new LinkedHashSet<>(List.of(automaton.initial()));
        for (String letter : word) {
            Set<String> next = new LinkedHashSet<>();
            for (LabelTransition transition : automaton.transitions()) {
                if (current.contains(transition.from())
                        && transition.symbol().name().equals(letter)) {
                    next.add(transition.to());
                }
            }
            current = next;
        }
        return current.stream().anyMatch(automaton.accepting()::contains);
    }

    private static Set<String> alphabetOf(LabelAutomaton automaton) {
        List<String> letters = new ArrayList<>();
        automaton.transitions().forEach(t -> letters.add(t.symbol().name()));
        return new LinkedHashSet<>(letters);
    }
}
