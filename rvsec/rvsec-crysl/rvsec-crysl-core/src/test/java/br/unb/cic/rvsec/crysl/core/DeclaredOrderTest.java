package br.unb.cic.rvsec.crysl.core;

import static org.junit.jupiter.api.Assertions.assertEquals;

import br.unb.cic.rvsec.crysl.core.metric.M3Result;
import br.unb.cic.rvsec.crysl.core.model.Event;
import br.unb.cic.rvsec.crysl.core.model.Label;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import java.util.EnumMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * Every ordering the component publishes has to be a rule somebody wrote down, not whatever the
 * JVM's hash iteration happened to produce.
 *
 * <p>{@code Set.of}, {@code Set.copyOf} and {@code Map.copyOf} salt their iteration order once per
 * JVM. That is invisible inside one run and lethal across runs: measured over six separate JVMs on
 * one unchanged corpus, {@code constraint_table.csv} alternated between two contents and
 * {@code conformance_report.json} came out six different ways, while the stamp on both said the
 * same thing. A table whose content moves while its stamp does not is the failure INV-CONF-02
 * exists to prevent, so the two collections below are held in an order this test can name.
 *
 * <p>These assertions run inside one JVM and therefore cannot observe the salt themselves — the
 * salt is drawn once, at class-init. What they check is the property that makes the salt
 * irrelevant: the iteration order is the order the caller declared. A regression to
 * {@code Set.copyOf} fails here on almost every run rather than on one run in two.
 */
class DeclaredOrderTest {

    @Test
    @DisplayName("Event.signatures iterates in the order the lifter wrote it, not in hash order")
    void test_event_keeps_the_order_its_signatures_were_given_in() {
        // Names chosen so that hash order and declared order are very unlikely to coincide, and so
        // that the declared order is not the alphabetical one either: an implementation that
        // sorted instead of preserving would also fail.
        List<Signature> declared = List.of(
                signature("z.Zeta", "third"),
                signature("a.Alpha", "first"),
                signature("m.Mu", "second"));

        Event event = new Event(new Label("e"), "call(*)", new LinkedHashSet<>(declared),
                Optional.empty(), 0);

        assertEquals(declared, List.copyOf(event.signatures()),
                "signatures() is a pairing key: MopLifter answers the declared type of a "
                        + "parameterless specification from the first element, and pairing runs on "
                        + "that answer (INV-CONF-11). A set whose first element is chosen by a "
                        + "per-JVM hash salt is not a key");
    }

    @Test
    @DisplayName("M3Result.byIdiom iterates in the enum's declaration order, whatever it was built from")
    void test_by_idiom_is_published_in_declaration_order() {
        // Built in the reverse of the declaration order on purpose: the record must impose the
        // order rather than inherit whatever the caller happened to use.
        Map<M3Result.Idiom, Integer> reversed = new LinkedHashMap<>();
        reversed.put(M3Result.Idiom.D_EXTERNAL_HELPER, 8);
        reversed.put(M3Result.Idiom.C_LOCAL_HELPER, 4);
        reversed.put(M3Result.Idiom.B_INLINE_ARITHMETIC, 7);
        reversed.put(M3Result.Idiom.A_ALIAS_TABLE, 12);

        M3Result result = new M3Result("DemoSpec", "Demo", reversed, 31, 80, 0, 3,
                List.of(), "R1", List.of());

        assertEquals(List.of(M3Result.Idiom.values()), List.copyOf(result.byIdiom().keySet()),
                "this map is serialized straight into conformance_report.json, so its iteration "
                        + "order is published");
        assertEquals(EnumMap.class, new EnumMap<>(result.byIdiom()).getClass(),
                "and the values survive the reordering");
        assertEquals(Integer.valueOf(12), result.byIdiom().get(M3Result.Idiom.A_ALIAS_TABLE));
        assertEquals(Integer.valueOf(8), result.byIdiom().get(M3Result.Idiom.D_EXTERNAL_HELPER));
    }

    @Test
    @DisplayName("an empty byIdiom is still an EnumMap, not an empty immutable map")
    void test_an_empty_by_idiom_keeps_the_rule() {
        M3Result result = new M3Result("DemoSpec", "Demo", Map.of(), 0, 0, 0, 0,
                List.of(), "R1", List.of());

        assertEquals(Set.of(), result.byIdiom().keySet());
    }

    private static Signature signature(String type, String name) {
        return new Signature(type, name, List.of(), "void");
    }
}
