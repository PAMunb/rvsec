package br.unb.cic.rvsec.crysl.mop;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.LiftFailure;
import br.unb.cic.rvsec.crysl.core.model.Event;
import br.unb.cic.rvsec.crysl.core.model.Label;
import br.unb.cic.rvsec.crysl.core.model.OverlappingDispatch;
import br.unb.cic.rvsec.crysl.core.model.Polarity;
import br.unb.cic.rvsec.crysl.core.model.Provenance;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import br.unb.cic.rvsec.crysl.core.model.Unknown;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import javamop.util.MOPNameSpace;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * The lift over all 229 {@code .mop} files of the five corpora.
 *
 * <p>The three aggregate numbers are asserted as <strong>fields of a result object</strong> and not
 * only inside an assertion message, together with the counting rule each was taken under. A number
 * whose counting rule lives in a comment is a number nobody can reproduce, which is the failure
 * INV-CONF-02 exists to prevent; here the rule is a constant of {@link MopLift} and the test asserts
 * its text as well as the count.
 */
class MopLiftCorpusTest {

    /**
     * The census of one corpus. Every field is data on the result, including the two counting rules,
     * so that a caller reading a {@code Census} knows what was counted and how.
     *
     * @param corpus              the corpus name
     * @param files               {@code .mop} files found in the directory
     * @param ok                  files that lifted
     * @param fail                files that did not
     * @param events              sum over the corpus of {@link MopLift#declaredEventCount()}
     * @param parameters          sum over the corpus of {@link MopLift#declaredParameterCount()}
     * @param eventCountingRule   how {@code events} was counted
     * @param parameterCountingRule how {@code parameters} was counted
     * @param failures            file name to the failure message, for the ones that did not lift
     */
    record Census(String corpus, int files, int ok, int fail, int events, int parameters,
                  String eventCountingRule, String parameterCountingRule,
                  Map<String, String> failures) {
    }

    private static List<Census> censuses;
    private static Census total;
    private static List<MopLift> lifts;

    @BeforeAll
    static void liftEverything() {
        assertTrue(Files.isDirectory(Corpora.root()),
                "the corpora are read from the sibling rvsec-mop module at "
                        + Corpora.root().toAbsolutePath() + "; the working directory of the test "
                        + "must be the module base directory");

        // Sequential and single-threaded, deliberately: JavaMOPParser keeps its parser in a static
        // field and MOPNameSpace is a static map, so a parallel corpus walk shares both. MopLifter
        // offers no batch entry point precisely so that this loop has to be written by hand here.
        MopLifter lifter = new MopLifter();
        censuses = new ArrayList<>();
        lifts = new ArrayList<>();
        for (Corpora.Corpus corpus : Corpora.ALL) {
            List<Path> files = Corpora.filesOf(corpus.name());
            int ok = 0;
            int events = 0;
            int parameters = 0;
            Map<String, String> failures = new LinkedHashMap<>();
            for (Path file : files) {
                try {
                    MopLift lift = lifter.read(file, Corpora.version(corpus.name()));
                    lifts.add(lift);
                    events += lift.declaredEventCount();
                    parameters += lift.declaredParameterCount();
                    ok++;
                } catch (LiftFailure e) {
                    // A file that does not lift is a finding recorded in the census, not an
                    // incident that stops the walk: the count of what did not lift is one of the
                    // numbers this test publishes.
                    failures.put(file.getFileName().toString(), String.valueOf(e.getMessage()));
                }
            }
            censuses.add(new Census(corpus.name(), files.size(), ok, files.size() - ok,
                    events, parameters, MopLift.EVENT_COUNTING_RULE,
                    MopLift.PARAMETER_COUNTING_RULE, failures));
        }
        total = new Census("TOTAL",
                censuses.stream().mapToInt(Census::files).sum(),
                censuses.stream().mapToInt(Census::ok).sum(),
                censuses.stream().mapToInt(Census::fail).sum(),
                censuses.stream().mapToInt(Census::events).sum(),
                censuses.stream().mapToInt(Census::parameters).sum(),
                MopLift.EVENT_COUNTING_RULE, MopLift.PARAMETER_COUNTING_RULE, Map.of());
    }

    @Test
    @DisplayName("all five corpora hold the file counts the change was measured against")
    void test_corpus_sizes() {
        for (int i = 0; i < Corpora.ALL.size(); i++) {
            Corpora.Corpus corpus = Corpora.ALL.get(i);
            assertEquals(corpus.expectedFiles(), censuses.get(i).files(),
                    "corpus " + corpus.name() + " changed size under the component");
        }
        assertEquals(229, total.files());
    }

    @Test
    @DisplayName("229 files, 229 ok, 0 fail")
    void test_all_229_files_lift() {
        for (Census census : censuses) {
            assertEquals(census.files(), census.ok(),
                    census.corpus() + " did not lift completely: " + census.failures());
            assertEquals(0, census.fail(), census.corpus() + ": " + census.failures());
        }
        assertEquals(229, total.ok());
        assertEquals(0, total.fail());
    }

    @Test
    @DisplayName("the aggregate is 927 events and 397 parameters, with the counting rules as data")
    void test_aggregate_events_and_parameters() {
        // These two numbers are the corpus drift tripwire, and Corpora reads the LIVE corpus, so a
        // specification repair is expected to move them. When it does, the repair re-measures and
        // re-pins here rather than the pin being loosened: 905 -> 907 was gh105 wiring one event
        // into KeyStoreSpec.mop and one into SSLContextSpec.mop, and 381 -> 383 was the same work
        // giving CipherInputStreamSpec.mop and CipherOutputStreamSpec.mop a parameter each, both
        // having declared none. A test that could not tell either from an accidental duplication
        // would not be worth running. 907 -> 908 is the gh109 R2 repair: KeyPairGeneratorSpec.mop
        // gained the `initError2` accuser for `initialize(int, SecureRandom)`, the twin of the
        // `initError` that already guarded `initialize(int)`. The parameter count does not move
        // with it, and that is the counting rule speaking rather than an oversight: parameters are
        // counted per specification, not per event, so only a spec that declares a new formal
        // parameter moves the second number. 383 was re-measured after 908 landed and held.
        //
        // 908 -> 927 and 383 -> 397 are gh109 group G2, the fourteen producer specifications the
        // set gained for rules of the pinned expert oracle it had never specified. The two moves
        // confirm the counting rule from both sides at once: nineteen events, because the group's
        // rules declare that many constructor and getter labels between them, and exactly fourteen
        // parameters, one per new specification, because each declares a single formal parameter
        // and no event of any of them adds one.
        //
        // Assert both counts, and note that the events assertion running first is why the parameter
        // drift went unseen: CI reported only the event failure for three runs while this line had
        // already been false for all three.
        assertEquals("spec.getEvents().size()", total.eventCountingRule());
        assertEquals("spec.getParameters().size()", total.parameterCountingRule());
        assertEquals(927, total.events(), "aggregate event count under " + total.eventCountingRule());
        assertEquals(397, total.parameters(),
                "aggregate parameter count under " + total.parameterCountingRule());
    }

    @Test
    @DisplayName("the model keeps the raw counts: one Event per declared event, one object per parameter")
    void test_model_matches_the_raw_census() {
        int modelEvents = lifts.stream().mapToInt(l -> l.model().events().size()).sum();
        int declaredEvents = lifts.stream().mapToInt(MopLift::declaredEventCount).sum();
        assertEquals(declaredEvents, modelEvents,
                "an Event is built for every declared event, so the two counts must agree");
        int modelObjects = lifts.stream().mapToInt(l -> l.model().objects().size()).sum();
        int declaredParameters = lifts.stream().mapToInt(MopLift::declaredParameterCount).sum();
        assertEquals(declaredParameters, modelObjects,
                "SpecModel.objects is a Set; a corpus with two identical parameter declarations in "
                        + "one specification would silently collapse them and this is where that "
                        + "would show");
    }

    @Test
    @DisplayName("events keep declaration order, and declIndex is the AST index")
    void test_events_keep_declaration_order() {
        for (MopLift lift : lifts) {
            List<Event> events = lift.model().events();
            for (int i = 0; i < events.size(); i++) {
                assertEquals(i, events.get(i).declIndex(),
                        lift.model().type() + ": declaration order is dispatch order (D-02)");
            }
        }
    }

    @Test
    @DisplayName("every event's provenance line really holds that event's declaration")
    void test_provenance_is_stamped_from_the_text() throws Exception {
        // Provenance is stamped by the parallel text scan, because the parser fabricates positions.
        // This is the check that the scan lands on the right line: read the line back out of the
        // file and require the event id to be on it. A scan that drifted by one event would pass
        // every count above and fail here.
        int checked = 0;
        for (MopLift lift : lifts) {
            for (Event event : lift.model().events()) {
                Provenance site = lift.model().provenance().get(event);
                assertNotNull(site, "every event carries provenance");
                Path file = fileOf(lift, site);
                List<String> lines = Files.readAllLines(file);
                String line = lines.get(site.line() - 1);
                assertTrue(line.contains(event.label().name()),
                        site + " does not hold the declaration of event '"
                                + event.label().name() + "': " + line);
                checked++;
            }
        }
        assertEquals(927, checked, "one provenance check per declared event");
    }

    @Test
    @DisplayName("every constraint and every predicate reference carries provenance that resolves")
    void test_constraints_and_predicates_are_stamped() throws Exception {
        int constraints = 0;
        int references = 0;
        for (MopLift lift : lifts) {
            for (var constraint : lift.model().constraints()) {
                assertEquals(constraint.site(), lift.model().provenance().get(constraint),
                        "a constraint's provenance is stamped on the model as well as on itself");
                String line = lineOf(lift, constraint.site());
                assertTrue(line.contains("condition"),
                        constraint.site() + " should hold the condition clause: " + line);
                constraints++;
            }
            for (var section : List.of(lift.model().ensures(), lift.model().requires(),
                    lift.model().negates())) {
                for (var reference : section) {
                    String line = lineOf(lift, reference.site());
                    assertTrue(line.contains(reference.name()),
                            reference.site() + " should name " + reference.name() + ": " + line);
                    references++;
                }
            }
        }
        assertTrue(constraints > 0 && references > 0,
                "the corpora do declare conditions and predicates; " + constraints + "/" + references);
    }

    private static String lineOf(MopLift lift, Provenance site) throws Exception {
        return Files.readAllLines(fileOf(lift, site)).get(site.line() - 1);
    }

    @Test
    @DisplayName("every order automaton leaves the lifter over real signatures the events name")
    void test_order_is_over_real_signatures() {
        // The strong form of INV-CONF-03, and deliberately stronger than "no symbol has a made-up
        // declaring type": every symbol has to be a signature some event of this same
        // specification declares, which no synthesised letter can satisfy by accident and which
        // therefore holds whatever a future lifter might invent to stand in for a label.
        for (MopLift lift : lifts) {
            Set<Signature> declared = new LinkedHashSet<>();
            lift.model().events().forEach(event -> declared.addAll(event.signatures()));
            for (Signature symbol : lift.model().order().alphabet()) {
                assertTrue(declared.contains(symbol),
                        lift.model().type() + ": " + symbol + " is a letter of the order automaton "
                                + "that no event declares; SpecModel.order is over real signatures "
                                + "(INV-CONF-03)");
            }
        }
    }

    @Test
    @DisplayName("a refused overlap is carried on the lift, and its signature is not a letter")
    void test_overlap_refusals_are_carried_out_of_the_lift() {
        // h⁻¹ is taken at the lift now, so OverlappingDispatch arises here rather than in M2. The
        // lift does not fail over one: the file's other events, type, handlers and predicate sites
        // are all still lifted. What it does is carry the refusal, and the refused signature is
        // absent from the order alphabet - a narrowing that belongs to the refusal and not to the
        // specification, which is why a consumer has to read refusals() beside order().
        int refusing = 0;
        int refusals = 0;
        for (MopLift lift : lifts) {
            if (lift.morphism().refusals().isEmpty()) {
                continue;
            }
            refusing++;
            refusals += lift.morphism().refusals().size();
            for (Unknown refusal : lift.morphism().refusals()) {
                OverlappingDispatch overlap =
                        assertInstanceOf(OverlappingDispatch.class, refusal);
                assertTrue(overlap.labels().size() > 1,
                        "a refusal names every label that claims the call (INV-CONF-07)");
                assertFalse(lift.model().order().alphabet().contains(overlap.signature()),
                        lift.model().type() + ": " + overlap.signature() + " was refused, so it "
                                + "carries no image and cannot be a letter of the preimage");
            }
        }
        assertEquals(42, refusing, "files of the five corpora carrying at least one refusal");
        assertEquals(57, refusals, "OverlappingDispatch refusals over the five corpora");
    }

    @Test
    @DisplayName("D-02 end to end on jca_android/IvChainJunction.mop")
    void test_iv_chain_junction_overlap_lifts_to_one_letter_with_two_labels() throws Exception {
        // The witness the whole construction exists for. `use` is declared
        //   call(public void Cipher.init(int, Key, AlgorithmParameterSpec, ..))
        // and `useRandomSpec`
        //   call(public void Cipher.init(int, Key, AlgorithmParameterSpec, SecureRandom))
        // so one call matches both, neither declares a condition, and that single call drives the
        // monitor through two transitions. h maps the signature to the concatenation of the two
        // labels in declaration order (use is event 0, useRandomSpec is event 3), and the preimage
        // therefore accepts the one-call word - which a language over labels could not express and
        // a label-to-signatures substitution would have destroyed.
        MopLift lift = new MopLifter().read(Corpora.file("jca_android", "IvChainJunction.mop"),
                Corpora.version("jca_android"));

        Signature initWithSpecAndRandom = new Signature("javax.crypto.Cipher", "init",
                List.of("int", "java.security.Key", "java.security.spec.AlgorithmParameterSpec",
                        "java.security.SecureRandom"),
                "void");

        assertTrue(lift.morphism().refusals().isEmpty(),
                "no condition separates the two labels, so there is nothing to refuse");
        assertEquals(List.of(new Label("use"), new Label("useRandomSpec")),
                lift.morphism().images().get(initWithSpecAndRandom),
                "h maps the one call to both labels, in declaration order");
        assertTrue(lift.model().order().accepts(List.of(initWithSpecAndRandom)),
                "the single-call word is in h⁻¹(L): its image 'use useRandomSpec' is a word of the "
                        + "ere (use | useRandomKey | ... | finalRange)*");
        assertTrue(lift.model().order().alphabet().contains(initWithSpecAndRandom),
                "and the letter is the real signature, not a placeholder");
    }

    @Test
    @DisplayName("every model carries the corpus stamp it was lifted from")
    void test_every_model_is_stamped() {
        for (MopLift lift : lifts) {
            assertNotNull(lift.model().version(), "INV-CONF-01");
            assertTrue(Corpora.ALL.stream()
                            .anyMatch(c -> c.name().equals(lift.model().version().corpus())),
                    "the stamp names the corpus, not the run");
        }
    }

    @Test
    @DisplayName("INV-CONF-12: the lift writes nothing under a corpus directory")
    void test_inv_conf_12_corpora_are_read_only() throws Exception {
        // Snapshot every entry of every corpus directory - name, size and last-modified - lift a
        // whole corpus again, and require the snapshot to be identical. Listing file names alone
        // would not do: the corpus directories legitimately hold artifacts this component did not
        // write (jca and generic_new each carry a MultiSpec_1MonitorAspect.aj, jca_android carries
        // codes.csv), so the check has to be "nothing changed" and not "only .mop files are here".
        Map<String, String> before = snapshotCorpora();
        MopLifter lifter = new MopLifter();
        for (Path file : Corpora.filesOf("jca_android")) {
            lifter.read(file, Corpora.version("jca_android"));
        }
        assertEquals(before, snapshotCorpora(),
                "a corpus directory changed while the component was reading it (INV-CONF-12)");
    }

    private static Map<String, String> snapshotCorpora() throws Exception {
        Map<String, String> snapshot = new LinkedHashMap<>();
        for (Corpora.Corpus corpus : Corpora.ALL) {
            try (var entries = Files.list(Corpora.directory(corpus.name()))) {
                for (Path entry : entries.sorted().toList()) {
                    snapshot.put(corpus.name() + "/" + entry.getFileName(),
                            Files.size(entry) + "@" + Files.getLastModifiedTime(entry));
                }
            }
        }
        return snapshot;
    }

    @Test
    @DisplayName("INV-CONF-05: MOPNameSpace.init() runs for each file, and the corpus proves it")
    void test_inv_conf_05_init_per_file() throws LiftFailure {
        // MOPNameSpace has no call counter, so the spy is behavioural. init() resets the "used"
        // flag, and while that flag is set every addUserVariable throws. So: set the flag, lift one
        // file, and require the namespace to be writable again. If the init() call at the top of
        // MopLifter.read is deleted, the flag survives the lift and this assertion fails on the
        // first file - which is exactly the regression the invariant is about.
        //
        // What it proves is "init() ran during this file's lift", once per file, for every file of
        // the corpus below. It does not count invocations; nothing observable does.
        MopLifter lifter = new MopLifter();
        List<Path> files = Corpora.filesOf("jca");
        assertEquals(23, files.size());
        for (Path file : files) {
            poisonNameSpace();
            assertTrue(nameSpaceIsPoisoned(),
                    "the spy needs the namespace poisoned before the lift, or it proves nothing");
            lifter.read(file, Corpora.version("jca"));
            assertFalse(nameSpaceIsPoisoned(),
                    "MOPNameSpace was still marked used after lifting " + file.getFileName()
                            + ", so init() did not run for that file (INV-CONF-05)");
        }
    }


    /**
     * No lifted signature carries AspectJ's subtype marker in any of its type positions.
     *
     * <p>{@code Collection+} is the name {@code Collection} plus the matching rule "and any subtype
     * of it". The rule is not part of the name, and a name that keeps it misses every lookup it is
     * ever put to — the file's imports, the {@code java.lang} probe, and finally the
     * {@code android.jar} index, where the miss was published as
     * {@code Unknown{UnresolvedSignature, mode: CLASSE-AUSENTE}}: the expander's own defect
     * reported as an absence in the Android platform. Measured over {@code generic_new}, dropping
     * the marker took M0.3's census from 82 refusals across 23 specifications to 73 across 19, and
     * corrected the declared type — the pairing key — of seven files.
     *
     * <p>Asserted over the corpora rather than over a fixture because the marker reaches a
     * signature by three separate routes (the pointcut's owner, its parameters and its return
     * type) and a fixture would only pin the one it was written for.
     */
    @Test
    @DisplayName("no lifted signature keeps the '+' of a subtype pattern in any type position")
    void test_the_subtype_marker_never_reaches_a_signature() {
        List<String> offenders = new ArrayList<>();
        for (MopLift lift : lifts) {
            for (Event event : lift.model().events()) {
                for (Signature signature : event.signatures()) {
                    List<String> types = new ArrayList<>(signature.paramTypes());
                    types.add(signature.declaringType());
                    types.add(signature.returnType());
                    for (String type : types) {
                        if (type.endsWith("+")) {
                            offenders.add(lift.model().version().corpus() + "/"
                                    + event.label().name() + ": " + type);
                        }
                    }
                }
            }
        }
        assertEquals(List.of(), offenders,
                "a type name ending in '+' resolves against nothing and is published as a platform "
                        + "absence; the marker is a matching rule and PointcutExpander.resolve "
                        + "drops it");
    }

    /**
     * The negated predicate references of the five corpora, which the shared model could not
     * represent until polarity became a field of {@code PredicateRef} (risk-register RISK-017).
     *
     * <p><strong>Counting rule:</strong> one per recognised predicate idiom whose lifted
     * {@code PredicateRef.polarity()} is {@code NEGATED}, over every file that lifts, grouped by
     * corpus. Two idioms produce it and both are the CrySL {@code !p[x]} of a {@code REQUIRES}
     * clause: substrate B's {@code validateAbsent(...)}, and substrate A's
     * {@code condition(!...validate(...))}, which is the same demand written from the violating
     * branch. Comments do not count — {@link SourceText} blanks them before the scan, which is why
     * the raw {@code grep} for {@code validateAbsent} over {@code jca_android} answers 9 and this
     * answers 5.
     */
    @Test
    @DisplayName("RISK-017: the corpora's negated references survive the lift, per corpus")
    void test_negated_references_per_corpus() {
        Map<String, Long> negated = new LinkedHashMap<>();
        for (Corpora.Corpus corpus : Corpora.ALL) {
            negated.put(corpus.name(), 0L);
        }
        for (MopLift lift : lifts) {
            long count = lift.predicateSites().stream()
                    .filter(site -> site.ref().polarity() == Polarity.NEGATED)
                    .count();
            negated.merge(lift.model().version().corpus(), count, Long::sum);
        }

        // Measured at 6192b57a. jca and jca_android_bug_predicate are on substrate A and write
        // the demand as condition(!...validate(...)); jca_android is on substrate B and writes it
        // as validateAbsent(...). The two generic sets declare no predicate at all.
        //
        // jca and jca_android_bug_predicate each answer ONE MORE than the 6 and 25 measured at
        // 5fbe8173, and nothing in either corpus changed: PredicateIdioms.negatedAt could not see
        // a negation written with grouping parentheses, so the single
        // condition(!(ExecutionContext.instance().validate(...))) that each of those two sets
        // writes - PBEParameterSpecSpec.mop:47, the same line in both - lifted as POSITIVE. The
        // triple below is the corrected reality and the earlier one was an undercount by the
        // reader; the assertion is raised to meet the corpus, never the reverse (INV-CONF-14).
        assertEquals(Map.of("jca", 7L, "jca_android", 5L, "jca_android_bug_predicate", 26L,
                "generic", 0L, "generic_new", 0L), negated);
    }

    /** Marks the namespace used, which is the state {@code init()} clears. */
    private static void poisonNameSpace() {
        MOPNameSpace.getMOPVar("rvsecConformanceProbe");
    }

    /** Whether the namespace is still in the "used" state, observed through its own contract. */
    private static boolean nameSpaceIsPoisoned() {
        try {
            MOPNameSpace.addUserVariable("rvsecConformanceProbeVariable");
            return false;
        } catch (Exception e) {
            return true;
        }
    }

    private static Path fileOf(MopLift lift, Provenance site) {
        for (Corpora.Corpus corpus : Corpora.ALL) {
            Path candidate = Corpora.file(corpus.name(), site.file());
            if (corpus.name().equals(lift.model().version().corpus()) && Files.exists(candidate)) {
                return candidate;
            }
        }
        throw new IllegalStateException("cannot locate " + site);
    }
}
