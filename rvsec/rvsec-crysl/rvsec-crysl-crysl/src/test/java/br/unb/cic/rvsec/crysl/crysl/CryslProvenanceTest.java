package br.unb.cic.rvsec.crysl.crysl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.LiftFailure;
import br.unb.cic.rvsec.crysl.core.automata.Transition;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import java.nio.file.Path;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

/**
 * D-19, checked on both halves: the EMF route supplies the names and positions the façade cannot,
 * and those names stay out of the alphabet the comparison runs over.
 */
@Tag(OracleCorpus.TAG)
class CryslProvenanceTest {

    @Test
    @DisplayName("the EMF route names the events and aggregates the facade hides")
    void test_event_and_aggregate_names_are_captured() {
        CryslProvenance provenance = CryslProvenance.read(rule("KeyGenerator.crysl"));

        assertTrue(provenance.valid(), "KeyGenerator.crysl parses clean; errors: " + provenance.errors());
        assertEquals(List.of("g1", "g2", "Get", "i1", "i2", "i3", "i4", "i5", "Init", "gk1", "GenKey"),
                provenance.eventNames().stream().map(CryslProvenance.EventName::name).toList(),
                "the declared names, in file order - TransitionEdge.getLabel() answers method "
                        + "signatures and can never produce this list");
        assertEquals(Set.of("Get", "Init", "GenKey"), provenance.eventNames().stream()
                        .filter(name -> name.kind() == CryslProvenance.EventKind.AGGREGATE)
                        .map(CryslProvenance.EventName::name)
                        .collect(java.util.stream.Collectors.toUnmodifiableSet()));
    }

    /**
     * The measured convention: a section's line is the line its <em>first element</em> sits on, not
     * the line of the {@code EVENTS} / {@code ORDER} keyword above it. In
     * {@code KeyGenerator.crysl} the keywords are on 10, 25 and 28 and the elements on 11, 26 and
     * 29. Asserting the convention rather than assuming it is the point: an off-by-one in a
     * provenance stamp is invisible in every report that carries it.
     */
    @Test
    @DisplayName("file:line comes from the node model, the only place it exists")
    void test_positions_are_read_from_the_node_model() {
        CryslProvenance provenance = CryslProvenance.read(rule("KeyGenerator.crysl"));

        assertEquals(11, provenance.lineOf(CryslProvenance.Section.EVENTS).orElseThrow(),
                "the EVENTS keyword is on line 10; g1, the first element, is on 11");
        assertEquals(26, provenance.lineOf(CryslProvenance.Section.ORDER).orElseThrow());
        assertEquals(29, provenance.lineOf(CryslProvenance.Section.CONSTRAINTS).orElseThrow());
        assertEquals(4, provenance.objectLines().get("keysize"));
        assertEquals(11, provenance.eventNames().get(0).line(), "g1 is declared on line 11");
        assertEquals(20, provenance.eventNames().stream()
                        .filter(name -> name.name().equals("Init")).findFirst().orElseThrow().line(),
                "the aggregate Init is declared on line 20");
    }

    @Test
    @DisplayName("a rule that does not parse still yields a provenance, carrying its diagnostics")
    void test_an_invalid_rule_still_produces_provenance() {
        CryslProvenance provenance = CryslProvenance.read(rule("SSLEngine.crysl"));

        assertFalse(provenance.valid());
        assertEquals(1, provenance.errors().size());
        assertEquals(12, provenance.errors().get(0).line());
        assertTrue(provenance.errors().get(0).message().contains("Couldn't resolve reference to Event 'cp1'"),
                provenance.errors().toString());
        assertTrue(provenance.eventNames().stream()
                        .anyMatch(name -> name.name().equals("ep1")),
                "the declared event is ep1, which is exactly what makes the ORDER's cp1 a typo and "
                        + "not a missing feature: " + provenance.eventNames());
    }

    /**
     * INV-CONF-03 at the seam where it is easiest to break. The rule's own names are available a
     * few lines away, and the temptation is to use one as a transition symbol; a symbol that is a
     * name is a symbol the MOP side cannot produce, and the comparison stops being a comparison.
     */
    @Test
    @DisplayName("INV-CONF-03: no rule-side name reaches the automaton's alphabet")
    void test_names_do_not_leak_into_the_alphabet() throws LiftFailure {
        Path file = rule("Cipher.crysl");
        SpecModel model = new CryslLifter().lift(file, OracleCorpus.version());
        Set<String> declaredNames = CryslProvenance.read(file).eventNames().stream()
                .map(CryslProvenance.EventName::name)
                .collect(java.util.stream.Collectors.toUnmodifiableSet());

        assertTrue(declaredNames.contains("Init"), "sanity: Cipher.crysl declares the aggregate Init");
        for (Transition transition : model.order().transitions()) {
            assertFalse(declaredNames.contains(transition.symbol().name()),
                    "the transition symbol " + transition.symbol() + " is a rule-side label, not a "
                            + "signature. The alphabet is Signature and only Signature.");
            assertTrue(transition.symbol().declaringType().contains("."),
                    "a signature always names a fully-qualified declaring type: " + transition.symbol());
        }
        assertEquals(8, model.order().transitions().stream()
                        .filter(transition -> transition.from().equals("0") && transition.to().equals("1"))
                        .count(),
                "the single edge labelled Init becomes eight transitions, one per init overload: "
                        + "they are eight different calls on device and merging them would compare "
                        + "something no program can execute");
    }

    private static Path rule(String fileName) {
        return OracleCorpus.cryslRules().resolve(fileName);
    }
}
