package br.unb.cic.rvsec.crysl.core;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import br.unb.cic.rvsec.crysl.core.model.Polarity;
import br.unb.cic.rvsec.crysl.core.model.PredicateRef;
import br.unb.cic.rvsec.crysl.core.model.Provenance;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * Polarity is mandatory on a predicate reference, and it separates two references that are
 * otherwise identical.
 *
 * <p>Both halves matter for M4. A reference whose polarity was never decided would default to
 * "the predicate must hold" if the field were allowed to be absent, and that default is exactly the
 * inversion the field exists to catch — a specification demanding {@code !p} would read as
 * demanding {@code p} and M4 would call it conformant. And unless polarity participates in
 * equality, the two references are the same edge of the comparison graph, so the difference could
 * be carried and still not be seen.
 */
class PredicateRefPolarityTest {

    private static final Provenance SITE = new Provenance("MacSpec.mop", 307);

    @Test
    @DisplayName("a null polarity is refused rather than defaulted to POSITIVE")
    void test_null_polarity_is_refused() {
        NullPointerException error = assertThrows(NullPointerException.class,
                () -> new PredicateRef("ENCRYPTED", List.of("output"), null, SITE));
        assertEquals(true, error.getMessage().contains("polarity"),
                "the message must name the missing field: " + error.getMessage());
    }

    @Test
    @DisplayName("polarity participates in identity: !p and p are two references, not one")
    void test_polarity_separates_two_otherwise_equal_references() {
        PredicateRef required = new PredicateRef("ENCRYPTED", List.of("output"),
                Polarity.POSITIVE, SITE);
        PredicateRef requiredAbsent = new PredicateRef("ENCRYPTED", List.of("output"),
                Polarity.NEGATED, SITE);

        assertNotEquals(required, requiredAbsent);
        assertEquals(required.name(), requiredAbsent.name(),
                "the name stays bare on both: encoding the negation into it would invent a "
                        + "predicate no rule declares");
    }
}
