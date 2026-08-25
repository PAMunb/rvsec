package br.unb.cic.rvsec.crysl.core.metric;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.automata.Automaton;
import br.unb.cic.rvsec.crysl.core.automata.InverseMorphism;
import br.unb.cic.rvsec.crysl.core.automata.LabelAutomaton;
import br.unb.cic.rvsec.crysl.core.automata.LabelTransition;
import br.unb.cic.rvsec.crysl.core.automata.Transition;
import br.unb.cic.rvsec.crysl.core.compare.AlphabetMap;
import br.unb.cic.rvsec.crysl.core.compare.Normalizations;
import br.unb.cic.rvsec.crysl.core.compare.Observability;
import br.unb.cic.rvsec.crysl.core.compare.OrderSurgery;
import br.unb.cic.rvsec.crysl.core.emit.MarkdownEmitter;
import br.unb.cic.rvsec.crysl.core.model.Event;
import br.unb.cic.rvsec.crysl.core.model.Guard;
import br.unb.cic.rvsec.crysl.core.model.Label;
import br.unb.cic.rvsec.crysl.core.model.Normalization;
import br.unb.cic.rvsec.crysl.core.model.Provenance;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import br.unb.cic.rvsec.crysl.core.model.SourceStamp;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import br.unb.cic.rvsec.crysl.core.model.Unknown;
import br.unb.cic.rvsec.crysl.core.model.UnresolvedSignature;
import br.unb.cic.rvsec.crysl.core.model.Version;
import br.unb.cic.rvsec.crysl.core.model.Witness;
import br.unb.cic.rvsec.crysl.core.model.WitnessStatus;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * M2 over inputs whose answer is known before the code runs.
 *
 * <p>The suite states its own automata rather than reading the corpus, on purpose: the properties
 * that matter here - that an erasure comes from the map and not from the shape, that an undeclared
 * event refuses instead of choosing, that N1 does not run where the monitor is global - are
 * properties the corpus does not exhibit in isolation, and a test that can only be read by first
 * reading a {@code .mop} proves less than it costs. The corpus measurements live in
 * {@code M2OrderCorpusTest}, in the module that has both lifters.
 */
class M2OrderTest {

    private static final String TYPE = "br.unb.cic.Demo";
    private static final Provenance SITE = new Provenance("Demo.mop", 1);

    // ------------------------------------------------------------------ 10.3, 10.5

    @Test
    @DisplayName("10.3/10.5 · the erasure is the disposition column, and it carries its reason")
    void test_erasure_comes_from_the_map_and_quotes_its_reason(@TempDir Path dir)
            throws IOException {
        String reason = "the rejected-algorithm twin over the same get() call as e1";
        AlphabetMap map = map(dir,
                "Demo,e1,r1,event,Demo.crysl,10,mapped,",
                "Demo,e2,,,Demo.crysl,,order-unmapped,\"" + reason + "\"");

        M2Order.Comparison comparison = compare(map, twoEventSpecification(), ruleOverGet(),
                M2Order.Options.of(SITE, false));

        assertEquals(M2Result.Verdict.EQUIVALENT, comparison.result().verdict(),
                "erasing e2 leaves exactly the rule's language; without the erasure the two "
                        + "disagree about every word containing put()");

        Normalization erasure = comparison.result().normalizations().stream()
                .filter(n -> n.id().startsWith(Normalizations.DECLARED_ERASURE.id()))
                .findFirst()
                .orElseThrow(() -> new AssertionError("no declared erasure was reported: "
                        + comparison.result().normalizations()));
        assertEquals("N-EPS·Demo.e2", erasure.id(),
                "reported per erasure, so a verdict row names which event was erased");
        assertTrue(erasure.description().contains(reason),
                "the declared reason travels verbatim with the erasure instead of pointing at a "
                        + "CSV the reader has to open: " + erasure.description());
    }

    @Test
    @DisplayName("10.3 · automaton shape licenses nothing: the same automaton, no row, no erasure")
    void test_shape_is_not_a_source_of_erasure(@TempDir Path dir) throws IOException {
        AlphabetMap withRow = map(dir.resolve("with"),
                "Demo,e1,r1,event,Demo.crysl,10,mapped,",
                "Demo,e2,,,Demo.crysl,,order-unmapped,declared");
        AlphabetMap withoutRow = map(dir.resolve("without"),
                "Demo,e1,r1,event,Demo.crysl,10,mapped,",
                "Demo,e2,r2,event,Demo.crysl,12,mapped,");

        assertEquals(M2Result.Verdict.EQUIVALENT,
                compare(withRow, twoEventSpecification(), ruleOverGet(),
                        M2Order.Options.of(SITE, false)).result().verdict());
        assertEquals(M2Result.Verdict.MOP_MORE_PERMISSIVE,
                compare(withoutRow, twoEventSpecification(), ruleOverGet(),
                        M2Order.Options.of(SITE, false)).result().verdict(),
                "the automaton did not move between the two runs - only the map did. An erasure "
                        + "inferred from shape would give the same verdict twice and would be "
                        + "wrong once (INV-CONF-10)");
    }

    // ------------------------------------------------------------------ 10.4

    @Test
    @DisplayName("10.4 · an unmapped event with no disposition row yields Unknown, not an erasure")
    void test_an_undeclared_event_refuses(@TempDir Path dir) throws IOException {
        AlphabetMap map = map(dir, "Demo,e1,r1,event,Demo.crysl,10,mapped,");

        M2Order.Comparison comparison = compare(map, twoEventSpecification(), ruleOverGet(),
                M2Order.Options.of(SITE, false));

        List<Unknown> refusals = comparison.result().refusals();
        assertEquals(1, refusals.size(), "one event, e2, has no row: " + refusals);
        assertTrue(refusals.get(0) instanceof UnresolvedSignature, "typed, not a bare message");
        UnresolvedSignature refusal = (UnresolvedSignature) refusals.get(0);
        assertTrue(refusal.mode().startsWith(M2Order.UNDECLARED_EVENT_MODE));
        assertTrue(refusal.mode().contains("Demo.e2"), refusal.mode());

        assertEquals(M2Result.Verdict.MOP_MORE_PERMISSIVE, comparison.result().verdict(),
                "and the letter stays in the language: refusing to decide is not deciding to "
                        + "erase, so the specification still accepts the word the rule does not");
        assertTrue(comparison.result().normalizations().stream()
                        .noneMatch(n -> n.id().startsWith(Normalizations.DECLARED_ERASURE.id())),
                "no erasure was invented");
    }

    // ------------------------------------------------------------------ 10.2

    @Test
    @DisplayName("10.2 · determinization runs and is measured, and a genuine NFA compares right")
    void test_determinization_runs_on_a_genuinely_non_deterministic_rule(@TempDir Path dir)
            throws IOException {
        AlphabetMap map = map(dir, "Demo,e1,r1,event,Demo.crysl,10,mapped,");

        // The Glushkov shape of ORDER con, a?, a: from the initial state, `a` may be the optional
        // one or the mandatory one, so one state has two `a` edges. Compared without the subset
        // construction the search would follow one of them and answer about a smaller language.
        Automaton nfa = new Automaton(Set.of("q0", "q1", "q2"), "q0", Set.of("q2"),
                List.of(edge("q0", "get", "q1"), edge("q0", "get", "q2"),
                        edge("q1", "get", "q2")));
        SpecModel rule = rule(nfa);

        M2Order.Comparison deterministic = compare(map, oneEventSpecification("get", "get get"),
                rule, M2Order.Options.of(SITE, false));
        assertFalse(deterministic.result().ruleAutomatonWasDeterministic(),
                "the measurement is published, not assumed: this rule automaton is an NFA");
        assertEquals(M2Result.Verdict.MOP_MORE_RESTRICTIVE, deterministic.result().verdict(),
                "the rule accepts get and get get; the specification only get get");
    }

    // ------------------------------------------------------------------ 10.8, 10.9

    @Test
    @DisplayName("10.9 · N1 runs only where M0.1 says the monitor indexes")
    void test_n1_is_not_a_general_rule(@TempDir Path dir) throws IOException {
        AlphabetMap map = map(dir, "Demo,e1,r1,event,Demo.crysl,10,mapped,");
        SpecModel specification = oneEventSpecification("get", "get get");
        SpecModel rule = rule(automaton("q0", "q1", edge("q0", "get", "q1")));

        M2Order.Comparison global = compare(map, specification, rule,
                M2Order.Options.of(SITE, false));
        assertEquals(M2Result.Verdict.INCOMPARABLE, global.result().verdict(),
                "a global monitor really does see get get, so the word is realisable and the two "
                        + "languages genuinely disagree in both directions");
        assertTrue(global.result().normalizations().stream()
                .noneMatch(n -> n.id().equals(Normalizations.N1_PARAMETRIC_SLICING.id())));

        M2Order.Comparison sliced = compare(map, specification, rule,
                M2Order.Options.of(SITE, true));
        assertEquals(M2Result.Verdict.MOP_MORE_RESTRICTIVE, sliced.result().verdict(),
                "one slice sees at most one creation, so get get leaves the language and what is "
                        + "left is strictly inside the rule's");
        assertTrue(sliced.result().normalizations().stream()
                        .anyMatch(n -> n.id().equals(Normalizations.N1_PARAMETRIC_SLICING.id())),
                "and the verdict says which normalization made it come out that way (10.7)");
    }

    @Test
    @DisplayName("10.8 · erasure and restriction are different operations and are not interchanged")
    void test_erase_is_not_restrict() {
        Automaton automaton = automaton("q0", "q2",
                edge("q0", "get", "q1"), edge("q1", "put", "q2"));
        Set<Signature> put = Set.of(sig("put"));

        assertTrue(OrderSurgery.erase(automaton, put).accepts(List.of(sig("get"))),
                "erasure says the call happened and the other side has no symbol for it, so the "
                        + "rest of the word stands");
        assertFalse(OrderSurgery.restrict(automaton, put).accepts(List.of(sig("get"))),
                "restriction says the call cannot happen at all, so the word leaves the language. "
                        + "N2 is a restriction: a protected method is not a call a program makes "
                        + "and hides");
    }

    // ------------------------------------------------------------------ 10.6, 10.12, 10.12-bis

    @Test
    @DisplayName("10.6/10.12-bis · every verdict is M2-decl, every claim is NONE, and the emitter "
            + "refuses anything else")
    void test_the_publication_path_carries_the_label_and_no_runtime_claim(@TempDir Path dir)
            throws IOException {
        AlphabetMap map = map(dir, "Demo,e1,r1,event,Demo.crysl,10,mapped,");
        M2Result result = compare(map, twoEventSpecification(), ruleOverGet(),
                M2Order.Options.of(SITE, false)).result();

        assertEquals(WitnessStatus.ABSTRACT, result.witness().orElseThrow().status(),
                "the product search finds words; it does not run programs");

        List<MarkdownEmitter.VerdictEntry> entries = M2Order.publish(List.of(result));
        assertEquals(MarkdownEmitter.Claim.NONE, entries.get(0).claim(),
                "there is no parameter with which a caller could ask for anything else");

        String markdown = new MarkdownEmitter().orderReport("M2", version(), version(),
                M2Order.COUNTING_RULE, entries);
        assertTrue(markdown.contains(M2Result.LABEL + ": "), "the label (INV-CONF-13)");
        assertTrue(markdown.contains(MarkdownEmitter.M2_DECL_QUALIFIER),
                "and the statement that a declared-automaton verdict says nothing about what the "
                        + "generated monitor accuses");

        IllegalArgumentException refused = assertThrows(IllegalArgumentException.class,
                () -> new MarkdownEmitter().orderReport("M2", version(), version(),
                        M2Order.COUNTING_RULE,
                        List.of(new MarkdownEmitter.VerdictEntry(result,
                                MarkdownEmitter.Claim.FALSE_POSITIVE))));
        assertTrue(refused.getMessage().contains("INV-CONF-08"),
                "the refusal is the invariant, not an obstacle to route around");
    }

    @Test
    @DisplayName("10.2-bis · the census reports a fraction and the rule that counted it")
    void test_the_census_carries_its_counting_rule() {
        SpecModel deterministic = rule(automaton("q0", "q1", edge("q0", "get", "q1")));
        SpecModel nondeterministic = rule(new Automaton(Set.of("q0", "q1", "q2"), "q0",
                Set.of("q2"), List.of(edge("q0", "get", "q1"), edge("q0", "get", "q2"))));

        var census = M2Order.census(List.of(deterministic, nondeterministic));

        assertEquals(2, census.total());
        assertEquals(1, census.alreadyDeterministic());
        assertTrue(M2Order.reportCountingRule(census).contains("1 of 2"));
        assertTrue(M2Order.reportCountingRule(census).contains("R-DET"),
                "the rule travels with the number (INV-CONF-02)");
    }

    // ------------------------------------------------------------------ fixtures

    /** {@code e1: get()} mapped, {@code e2: put()} whatever the map says; {@code ere: e1 e2*}. */
    private static SpecModel twoEventSpecification() {
        List<Event> events = List.of(
                new Event(new Label("e1"), "call(void Demo.get())", Set.of(sig("get")),
                        Optional.empty(), 0),
                new Event(new Label("e2"), "call(void Demo.put())", Set.of(sig("put")),
                        Optional.empty(), 1));
        LabelAutomaton order = new LabelAutomaton(Set.of("s0", "s1"), "s0", Set.of("s1"),
                List.of(new LabelTransition("s0", new Label("e1"), "s1"),
                        new LabelTransition("s1", new Label("e2"), "s1")));
        return specification(events, order);
    }

    /** One event over {@code name}, with the label word given as the {@code ere} spelled out. */
    private static SpecModel oneEventSpecification(String name, String word) {
        // The signature returns the monitored type, which is what makes it a creator letter and
        // therefore what N1 is about. The rule's letter for it is the plain one: the identification
        // does not compare return types, exactly as R-M1 does not.
        List<Event> events = List.of(new Event(new Label("e1"), "call(Demo Demo." + name + "())",
                Set.of(new Signature(TYPE, name, List.of(), TYPE)), Optional.empty(), 0));
        List<LabelTransition> transitions = new ArrayList<>();
        String[] letters = word.split(" ");
        for (int i = 0; i < letters.length; i++) {
            transitions.add(new LabelTransition("s" + i, new Label("e1"), "s" + (i + 1)));
        }
        Set<String> states = new LinkedHashSet<>();
        for (int i = 0; i <= letters.length; i++) {
            states.add("s" + i);
        }
        return specification(events, new LabelAutomaton(states, "s0",
                Set.of("s" + letters.length), transitions));
    }

    private static SpecModel specification(List<Event> events, LabelAutomaton order) {
        InverseMorphism morphism = InverseMorphism.of(events, SITE);
        Map<Object, Provenance> provenance = new LinkedHashMap<>();
        events.forEach(event -> provenance.put(event, SITE));
        return new SpecModel(version(), TYPE, Set.of(), events, morphism.preimage(order),
                List.of(), List.of(), List.of(), List.of(), Set.of(), provenance);
    }

    /** The rule {@code ORDER get, put*}: what {@code twoEventSpecification} erases down to. */
    private static SpecModel ruleOverGet() {
        return rule(automaton("q0", "q1", edge("q0", "get", "q1")));
    }

    private static SpecModel rule(Automaton order) {
        return new SpecModel(version(), TYPE, Set.of(), List.of(), order, List.of(), List.of(),
                List.of(), List.of(), Set.of(), Map.of());
    }

    private static M2Order.Comparison compare(AlphabetMap map, SpecModel specification,
                                              SpecModel rule, M2Order.Options options) {
        InverseMorphism morphism = InverseMorphism.of(specification.events(), SITE);
        return M2Order.compare("Demo", specification, morphism, "Demo", rule, map, options);
    }

    private static AlphabetMap map(Path dir, String... rows) throws IOException {
        Files.createDirectories(dir);
        Path csv = dir.resolve("order_alphabet_map.csv");
        Files.writeString(csv, "# synthetic\n" + AlphabetMap.HEADER + "\n"
                + String.join("\n", rows) + "\n", StandardCharsets.UTF_8);
        return AlphabetMap.read(csv);
    }

    private static Signature sig(String name) {
        return new Signature(TYPE, name, List.of(), "void");
    }

    private static Transition edge(String from, String name, String to) {
        return new Transition(from, sig(name), Optional.empty(), to);
    }

    private static Automaton automaton(String initial, String accepting, Transition... edges) {
        Set<String> states = new LinkedHashSet<>();
        states.add(initial);
        states.add(accepting);
        for (Transition edge : edges) {
            states.add(edge.from());
            states.add(edge.to());
        }
        return new Automaton(states, initial, Set.of(accepting), List.of(edges));
    }

    private static Version version() {
        return new Version("synthetic", new SourceStamp("rvsec", "test-fixture", Instant.EPOCH));
    }
}
