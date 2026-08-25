package br.unb.cic.rvsec.crysl.core.automata;

import static br.unb.cic.rvsec.crysl.core.automata.Fixtures.automaton;
import static br.unb.cic.rvsec.crysl.core.automata.Fixtures.word;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.metric.M2Result;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import br.unb.cic.rvsec.crysl.core.model.Witness;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

/**
 * Product search on hand-built pairs whose shortest witness is known in advance.
 *
 * <p>Shortest is asserted rather than assumed: the witness is the part of a verdict a reader checks
 * by hand, and a search that returned some separating word instead of the shortest one would still
 * pass an emptiness test while publishing something nobody can read.
 */
@Tag("automata")
class ProductSearchTest {

    /** One or more a. */
    private static Automaton onePlusA() {
        return automaton("q0", "q1", "q0 a q1", "q1 a q1");
    }

    /** Exactly three a. */
    private static Automaton exactlyThreeA() {
        return automaton("p0", "p3", "p0 a p1", "p1 a p2", "p2 a p3");
    }

    /** Any number of a, the empty word included. */
    private static Automaton anyNumberOfA() {
        return automaton("u0", "u0", "u0 a u0");
    }

    /** At most two a. */
    private static Automaton atMostTwoA() {
        return automaton("t0", "t0,t1,t2", "t0 a t1", "t1 a t2");
    }

    @Test
    @DisplayName("containment in one direction gives one verdict and one witness")
    void test_more_permissive_side_is_named() {
        ProductSearch.OrderComparison comparison =
                ProductSearch.compare(onePlusA(), exactlyThreeA());

        assertEquals(M2Result.Verdict.MOP_MORE_PERMISSIVE, comparison.verdict());
        assertEquals(word("a"), witnessWord(comparison),
                "the shortest word accepted by a+ and rejected by aaa is a single a");
        assertTrue(comparison.cryslOnlyWitness(List.of()).isEmpty(),
                "aaa is contained in a+, so the other direction has nothing to show");
    }

    @Test
    @DisplayName("the search returns the shortest word, not merely some word")
    void test_the_witness_is_the_shortest_one() {
        ProductSearch.OrderComparison comparison =
                ProductSearch.compare(anyNumberOfA(), atMostTwoA());

        assertEquals(M2Result.Verdict.MOP_MORE_PERMISSIVE, comparison.verdict());
        assertEquals(word("a", "a", "a"), witnessWord(comparison),
                "three a is the first word a* has and 'at most two a' lacks");
    }

    @Test
    @DisplayName("two languages that each accept what the other rejects are incomparable")
    void test_incomparable_pair_reports_both_directions() {
        Automaton ab = automaton("q0", "q2", "q0 a q1", "q1 b q2");
        Automaton a = automaton("p0", "p1", "p0 a p1");

        ProductSearch.OrderComparison comparison = ProductSearch.compare(ab, a);
        assertEquals(M2Result.Verdict.INCOMPARABLE, comparison.verdict());
        assertEquals(word("a", "b"), comparison.mopOnlyWitness(List.of()).orElseThrow().word());
        assertEquals(word("a"), comparison.cryslOnlyWitness(List.of()).orElseThrow().word());
        assertEquals(word("a"), witnessWord(comparison),
                "the single published witness is the shorter of the two directions");
    }

    @Test
    @DisplayName("equivalent languages publish no witness")
    void test_equivalence_has_nothing_to_show() {
        ProductSearch.OrderComparison comparison =
                ProductSearch.compare(exactlyThreeA(), automaton("z0", "z3",
                        "z0 a z1", "z1 a z2", "z2 a z3"));

        assertEquals(M2Result.Verdict.EQUIVALENT, comparison.verdict());
        assertEquals(Optional.empty(), comparison.shortestWitness(List.of()));
    }

    @Test
    @DisplayName("the comparison runs over the union of the two alphabets")
    void test_a_letter_only_one_side_mentions_still_separates() {
        Automaton onlyA = automaton("q0", "q1", "q0 a q1");
        Automaton onlyB = automaton("p0", "p1", "p0 b p1");

        ProductSearch.OrderComparison comparison = ProductSearch.compare(onlyA, onlyB);
        assertEquals(M2Result.Verdict.INCOMPARABLE, comparison.verdict(),
                "completing over either alphabet alone would make the two agree about the letter "
                        + "the other side never mentions");
        assertEquals(word("a"), comparison.mopOnlyWitness(List.of()).orElseThrow().word());
        assertEquals(word("b"), comparison.cryslOnlyWitness(List.of()).orElseThrow().word());
    }

    @Test
    @DisplayName("the empty word separates when only one side accepts it")
    void test_the_empty_word_is_a_witness_like_any_other()  {
        ProductSearch.OrderComparison comparison =
                ProductSearch.compare(anyNumberOfA(), onePlusA());

        assertEquals(M2Result.Verdict.MOP_MORE_PERMISSIVE, comparison.verdict());
        assertEquals(List.of(), witnessWord(comparison),
                "a* accepts the empty word and a+ does not; the witness is that empty word");
    }

    private static List<Signature> witnessWord(ProductSearch.OrderComparison comparison) {
        Witness witness = comparison.shortestWitness(List.of()).orElseThrow();
        return witness.word();
    }
}
