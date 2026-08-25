package br.unb.cic.rvsec.crysl.core.automata;

import static br.unb.cic.rvsec.crysl.core.automata.Fixtures.automaton;
import static br.unb.cic.rvsec.crysl.core.automata.Fixtures.word;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.model.Normalization;
import br.unb.cic.rvsec.crysl.core.model.Witness;
import br.unb.cic.rvsec.crysl.core.model.WitnessStatus;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.lang.reflect.ParameterizedType;
import java.lang.reflect.Type;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

/**
 * Witness construction, and the structural reason a caller cannot bypass it.
 *
 * <p>INV-CONF-08 is not enforced by remembering to pass the normalizations. The search returns
 * words, the comparison object keeps them private, and every way out of it is a method that takes
 * the normalization list - so there is no path from a comparison to a published word that does not
 * pass through a statement of what the comparison was made modulo.
 */
@Tag("automata")
class WitnessesTest {

    private static final List<Normalization> N1 =
            List.of(new Normalization("N1", "unmapped event erased on the disposition column"));

    @Test
    @DisplayName("a search witness is ABSTRACT and names no harness")
    void test_abstract_witness_shape() {
        Witness witness = Witnesses.abstractWitness(word("a", "b"), N1);

        assertEquals(WitnessStatus.ABSTRACT, witness.status());
        assertEquals(Optional.empty(), witness.harness());
        assertEquals(N1, witness.normalizations());
    }

    @Test
    @DisplayName("an executed witness is CONCRETE and names its harness")
    void test_concrete_witness_shape() {
        Witness witness = Witnesses.concreteWitness(word("a"), List.of(), "CipherSpecHarness#7");

        assertEquals(WitnessStatus.CONCRETE, witness.status());
        assertEquals(Optional.of("CipherSpecHarness#7"), witness.harness());
    }

    @Test
    @DisplayName("a witness cannot be built without saying what it was compared modulo")
    void test_normalizations_are_mandatory() {
        NullPointerException failure = assertThrows(NullPointerException.class,
                () -> Witnesses.abstractWitness(word("a"), null));
        assertTrue(failure.getMessage().contains("INV-CONF-08"));

        assertThrows(NullPointerException.class,
                () -> Witnesses.concreteWitness(word("a"), List.of(), null));
    }

    @Test
    @DisplayName("the comparison carries the normalizations onto the witness it hands out")
    void test_the_comparison_propagates_the_normalizations() {
        ProductSearch.OrderComparison comparison = ProductSearch.compare(
                automaton("q0", "q1", "q0 a q1", "q1 a q1"),
                automaton("p0", "p1", "p0 a p1"));

        Witness witness = comparison.shortestWitness(N1).orElseThrow();
        assertEquals(N1, witness.normalizations());
        assertEquals(WitnessStatus.ABSTRACT, witness.status());
    }

    @Test
    @DisplayName("the comparison exposes no way to obtain a word without the normalizations")
    void test_no_accessor_leaks_a_raw_word() {
        for (Method method : ProductSearch.OrderComparison.class.getDeclaredMethods()) {
            if (!Modifier.isPublic(method.getModifiers()) || method.isSynthetic()) {
                continue;
            }
            if (mentionsSignature(method.getGenericReturnType())) {
                assertTrue(method.getParameterCount() > 0,
                        method.getName() + " hands out a word with no normalizations beside it, "
                                + "which is the one way INV-CONF-08 can still be broken here");
            }
        }
    }

    private static boolean mentionsSignature(Type type) {
        if (type instanceof Class<?> raw) {
            return raw.getName().endsWith("model.Signature") || raw.getName().endsWith("model.Witness");
        }
        if (type instanceof ParameterizedType parameterized) {
            for (Type argument : parameterized.getActualTypeArguments()) {
                if (mentionsSignature(argument)) {
                    return true;
                }
            }
        }
        return false;
    }
}
