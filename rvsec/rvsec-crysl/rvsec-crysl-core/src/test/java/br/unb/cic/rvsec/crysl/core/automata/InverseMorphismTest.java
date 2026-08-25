package br.unb.cic.rvsec.crysl.core.automata;

import static br.unb.cic.rvsec.crysl.core.automata.Fixtures.SITE;
import static br.unb.cic.rvsec.crysl.core.automata.Fixtures.event;
import static br.unb.cic.rvsec.crysl.core.automata.Fixtures.guardedEvent;
import static br.unb.cic.rvsec.crysl.core.automata.Fixtures.labelAutomaton;
import static br.unb.cic.rvsec.crysl.core.automata.Fixtures.sig;
import static br.unb.cic.rvsec.crysl.core.automata.Fixtures.word;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.model.Label;
import br.unb.cic.rvsec.crysl.core.model.OverlappingDispatch;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

/**
 * The morphism and its preimage, on the overlap shape the corpus actually contains.
 *
 * <p>The pair is written after {@code IvChainJunction}, where {@code use} and {@code useRandomSpec}
 * both match one {@code Cipher.init(int, Key, AlgorithmParameterSpec, SecureRandom)} call and
 * neither declares a condition: one call emits two letters, and the whole reason the comparison
 * object is the preimage rather than a language over labels is that this shape exists.
 */
@Tag("automata")
class InverseMorphismTest {

    private static final Label USE = new Label("use");
    private static final Label USE_RANDOM_SPEC = new Label("useRandomSpec");

    /** The label language {@code use useRandomSpec}: exactly the two-letter word, in that order. */
    private static LabelAutomaton useThenUseRandomSpec() {
        return labelAutomaton("l0", "l2",
                "l0 use l1",
                "l1 useRandomSpec l2");
    }

    @Test
    @DisplayName("a two-label overlap maps the signature to the concatenation, in declaration order")
    void test_overlap_yields_the_concatenation_in_declaration_order() {
        InverseMorphism morphism = InverseMorphism.of(
                List.of(event("use", 0, "init4"), event("useRandomSpec", 1, "init4")), SITE);

        assertTrue(morphism.refusals().isEmpty(), "no condition separates them, so nothing to refuse");
        assertEquals(List.of(USE, USE_RANDOM_SPEC), morphism.images().get(sig("init4")));

        Automaton preimage = morphism.preimage(useThenUseRandomSpec());
        assertTrue(preimage.accepts(word("init4")),
                "one call emits both letters, so the single-call word is in the preimage");
        assertFalse(preimage.accepts(word()));
        assertFalse(preimage.accepts(word("init4", "init4")));
    }

    @Test
    @DisplayName("reversing the declaration order changes the language")
    void test_declaration_order_is_dispatch_order() {
        InverseMorphism reversed = InverseMorphism.of(
                List.of(event("use", 1, "init4"), event("useRandomSpec", 0, "init4")), SITE);

        assertEquals(List.of(USE_RANDOM_SPEC, USE), reversed.images().get(sig("init4")));
        assertFalse(reversed.preimage(useThenUseRandomSpec()).accepts(word("init4")),
                "the image is now useRandomSpec use, which the label language does not accept");
    }

    @Test
    @DisplayName("an overlap separated by a guard is refused, never resolved by choosing")
    void test_guarded_overlap_refuses_with_the_labels_named() {
        InverseMorphism morphism = InverseMorphism.of(
                List.of(event("use", 0, "init4"),
                        guardedEvent("useRandomSpec", 1, "spec instanceof IvParameterSpec", "init4")),
                SITE);

        assertEquals(1, morphism.refusals().size());
        OverlappingDispatch refusal =
                assertInstanceOf(OverlappingDispatch.class, morphism.refusals().get(0));
        assertEquals(List.of("use", "useRandomSpec"), refusal.labels(),
                "the refusal names the labels in declaration order (INV-CONF-07)");
        assertEquals(sig("init4"), refusal.signature());
        assertEquals(SITE, refusal.site());
        assertFalse(morphism.images().containsKey(sig("init4")),
                "the refused signature has no image: the morphism does not guess one");

        assertThrows(IllegalStateException.class,
                () -> morphism.preimage(useThenUseRandomSpec()),
                "a preimage over an unresolved overlap would be a confident answer built on a gap");
    }

    @Test
    @DisplayName("a guard on an event that overlaps nothing is not a refusal")
    void test_a_lone_guarded_event_still_has_an_image() {
        InverseMorphism morphism = InverseMorphism.of(
                List.of(guardedEvent("g1", 0, "keysize == 2048", "genKey")), SITE);

        assertTrue(morphism.refusals().isEmpty(),
                "there is nothing to disambiguate, so the condition changes no letter count");
        assertEquals(List.of(new Label("g1")), morphism.images().get(sig("genKey")));
    }

    @Test
    @DisplayName("one label matching several signatures gives each of them the same image")
    void test_a_label_with_several_signatures() {
        InverseMorphism morphism = InverseMorphism.of(
                List.of(event("g1", 0, "genA", "genB"), event("f1", 1, "fin")), SITE);

        Automaton preimage = morphism.preimage(labelAutomaton("l0", "l2",
                "l0 g1 l1", "l1 f1 l2"));
        assertTrue(preimage.accepts(word("genA", "fin")));
        assertTrue(preimage.accepts(word("genB", "fin")));
        assertFalse(preimage.accepts(word("fin", "genA")));
    }

    @Test
    @DisplayName("the preimage is stable across runs")
    void test_the_preimage_record_is_reproducible() {
        List<br.unb.cic.rvsec.crysl.core.model.Event> events =
                List.of(event("g1", 0, "genA", "genB"), event("f1", 1, "fin"));
        LabelAutomaton language = labelAutomaton("l0", "l2", "l0 g1 l1", "l1 f1 l2");

        assertEquals(InverseMorphism.of(events, SITE).preimage(language),
                InverseMorphism.of(events, SITE).preimage(language),
                "state and letter order are fixed, because an unstable edge order would make two "
                        + "equal languages compare unequal as records");
    }
}
