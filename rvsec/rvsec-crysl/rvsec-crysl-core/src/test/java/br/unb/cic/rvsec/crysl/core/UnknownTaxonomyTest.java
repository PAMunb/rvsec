package br.unb.cic.rvsec.crysl.core;

import static org.junit.jupiter.api.Assertions.assertEquals;

import br.unb.cic.rvsec.crysl.core.model.MultiSlicedOrder;
import br.unb.cic.rvsec.crysl.core.model.OverlappingDispatch;
import br.unb.cic.rvsec.crysl.core.model.UnreachableAccusationSite;
import br.unb.cic.rvsec.crysl.core.model.UnrecognizedConstraint;
import br.unb.cic.rvsec.crysl.core.model.UnresolvedSignature;
import br.unb.cic.rvsec.crysl.core.model.UntranslatableConstraint;
import br.unb.cic.rvsec.crysl.core.model.Unknown;
import java.util.Arrays;
import java.util.Set;
import java.util.stream.Collectors;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * INV-CONF-06: the refusal taxonomy is closed to exactly six tags.
 *
 * <p>The assertion runs over {@code getPermittedSubclasses()} rather than over a hand-written list,
 * so a further tag added to the {@code permits} clause breaks this test instead of slipping in with
 * the commit that added it. That is exactly what happened to the sixth,
 * {@code UnreachableAccusationSite}: it was five, this test went red, and the count was raised
 * deliberately alongside the amendment of the invariant. The assertion stays <em>exact</em> rather
 * than becoming a lower bound, because a bound that only grows is a door left open.
 */
class UnknownTaxonomyTest {

    @Test
    @DisplayName("INV-CONF-06: Unknown permits exactly the six declared tags")
    void test_inv_conf_06_exactly_six_tags() {
        Class<?>[] permitted = Unknown.class.getPermittedSubclasses();

        assertEquals(6, permitted.length,
                "the Unknown taxonomy is closed to six tags; adding one is a contract change");

        Set<String> names = Arrays.stream(permitted)
                .map(Class::getSimpleName)
                .collect(Collectors.toSet());
        assertEquals(Set.of("UnrecognizedConstraint", "OverlappingDispatch", "MultiSlicedOrder",
                "UnresolvedSignature", "UntranslatableConstraint", "UnreachableAccusationSite"),
                names);
    }

    @Test
    @DisplayName("INV-CONF-06: the six tags are the six records, sealed and final")
    void test_inv_conf_06_tags_are_final_records() {
        for (Class<?> tag : new Class<?>[] {UnrecognizedConstraint.class, OverlappingDispatch.class,
                MultiSlicedOrder.class, UnresolvedSignature.class, UntranslatableConstraint.class,
                UnreachableAccusationSite.class}) {
            assertEquals(true, tag.isRecord(), tag.getSimpleName() + " must be a record");
            // A non-final permitted subtype would reopen the hierarchy one level down.
            assertEquals(0, tag.getPermittedSubclasses() == null ? 0 : tag.getPermittedSubclasses().length,
                    tag.getSimpleName() + " must not permit further subtypes");
        }
    }
}
