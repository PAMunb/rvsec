package br.unb.cic.rvsec.crysl.crysl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.LiftFailure;
import br.unb.cic.rvsec.crysl.core.metric.M4Predicates;
import br.unb.cic.rvsec.crysl.core.metric.PredicateGraph;
import br.unb.cic.rvsec.crysl.core.metric.PredicateSiteFacts;
import br.unb.cic.rvsec.crysl.core.metric.PredicateSubstrate;
import br.unb.cic.rvsec.crysl.core.metric.SpecRulePairing;
import br.unb.cic.rvsec.crysl.core.model.Polarity;
import br.unb.cic.rvsec.crysl.core.model.SourceStamp;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import br.unb.cic.rvsec.crysl.core.model.Version;
import br.unb.cic.rvsec.crysl.mop.MopLift;
import br.unb.cic.rvsec.crysl.mop.MopLifter;
import br.unb.cic.rvsec.crysl.mop.PredicateSite;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Stream;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

/**
 * M4 over the corpora that exist, rather than over pairs built for the occasion.
 *
 * <p>It lives in this module because it needs both lifters and this is the only module that has
 * both. The tests split on what they read: the ones over the {@code .mop} corpora alone run
 * anywhere, and the one that also reads the upstream rules is tagged, because the oracle is a
 * separate git repository the CI checkout does not have.
 *
 * <h2>Task 12.0: the aggregates below moved, and here is by how much</h2>
 *
 * <p>Until G12 this class kept its own pairing — a map from a rule's simple name to the rule — and
 * reached <b>23</b> pairs where {@link SpecRulePairing}, the component's rule of record, reaches
 * <b>22</b>. The extra pair was {@code IvChainJunction.mop}, which declares {@code Cipher} and, in
 * a non-injective map, claims {@code Cipher.crysl} alongside {@code CipherSpec}. Two metrics of one
 * report then disagreed about which specifications were compared, and no such report can be
 * published.
 *
 * <p>Measured before and after the change, on the same corpus and the same commit, so the shift is
 * visible rather than silent:
 *
 * <pre>
 *                 pairs  present  absent  inverted  rows  derived  derived fraction
 *   before (23)      23       50      53         0   123      103             0.837
 *   after  (22)      22       44      44         0   106       88             0.830
 *   gh109  (35)      35       68      40         0   131      108             0.824
 * </pre>
 *
 * <p>The nine that leave {@code absent} are the point: {@code Cipher.crysl}'s clauses were being
 * counted <em>twice</em>, once against {@code CipherSpec} and once against the junction, so the
 * old {@code 53} overstated what the corpus fails to implement. The derived fraction barely moves,
 * which is what one would expect from removing a duplicated pair rather than a class of judgement.
 *
 * <p><b>What the bridge from the lift carries, and what it does not.</b> {@link PredicateSite} is
 * the {@code -mop} module's record of a site and {@link PredicateSiteFacts} is the shape
 * {@code -core} compares; {@link #facts} maps one to the other. Two of the target's components have
 * no source in the current lift - the event a site sits in and whether it is in an event body or a
 * {@code @match} handler - so every site crosses as a body site with no event name. That costs the
 * derived {@code verdict} column its {@code :acceptance} half, which is why no test here asserts on
 * it; it costs the comparison nothing, because arity, polarity and argument position are all on the
 * reference itself.
 */
class M4PredicateCorpusTest {

    /** The corpora, read from the sibling {@code rvsec-mop} module's working tree (INV-CONF-12). */
    private static final Path RESOURCES =
            Paths.get("..", "..", "rvsec-mop", "src", "main", "resources").normalize();

    private final MopLifter mopLifter = new MopLifter();

    // ── 9.11 both substrates lift into the same graph ─────────────────────────────────────────

    @Test
    @DisplayName("9.11: the frozen set and the current set lift into the same graph shape")
    void test_both_substrates_produce_one_comparable_graph() {
        List<PredicateSiteFacts> frozen = sitesOf("jca");
        List<PredicateSiteFacts> current = sitesOf("jca_android");

        assertEquals(85, frozen.size(),
                "counting rule: recognised predicate idioms of jca/*.mop, comments blanked. It is "
                        + "85 and not the 110 occurrences of 'ExecutionContext.instance()' the "
                        + "same files contain: 25 of those are setObjectAsInAcceptingState and "
                        + "unsetObjectAsInAcceptingState, which encode CrySL's 'an ENSURES fires "
                        + "only in an accepting state'. That is a guard on a predicate and not a "
                        + "predicate, and counting it here would add 25 references no rule "
                        + "declares to M4's denominator. 110 - 25 = 85, exactly");
        assertEquals(85, count(frozen, PredicateSubstrate.EXECUTION_CONTEXT),
                "the frozen set is entirely on substrate A, which is what makes reading it the "
                        + "only way to compare against the published measurements");
        assertEquals(0, count(frozen, PredicateSubstrate.PREDICATE_STORE));

        assertEquals(148, current.size(),
                "70 -> 101 -> 111 across gh109: task 1.3(b) writes the three generatedMessageDigest "
                        + "sites the transcription had omitted; group G2's fourteen producer "
                        + "specifications carry 14 writes and 10 reads of their own; and group G1b "
                        + "opens ten reads and no write -- the four guarded clauses of "
                        + "KeyPairGenerator at two initialize overloads each, and "
                        + "generatedManagerFactoryParameters at each of the two manager factories. "
                        + "The 0/70/21 signature this was written against is the shape and not the "
                        + "number: still no site on substrate A, and still every one of them on the "
                        + "store. Group G3 then takes it to 131 and group G4 to 146: fifteen "
                        + "sites over three specifications, all but four of them KeyAgreementSpec's "
                        + "eleven reads, because the two TLS rules state no REQUIRES and contribute "
                        + "only their own ENSURES. Group G8 then takes it to 148, one site from "
                        + "each of the two tasks of that wave that touch the graph: task 8.1 "
                        + "writes speccedKey in SecretKeySpecSpec's @match, the ENSURES the "
                        + "transcription had omitted on a reason measured false, and task 8.6 "
                        + "gives CipherSpec.i2 a SECOND probe of the one generatedKey clause, "
                        + "because the oracle puts two spellings on that string. Task 8.9 adds an "
                        + "event and no site, which is what a negated twin is: it accuses and "
                        + "writes nothing. It moves with every group that adds sites -- "
                        + "re-measure it at the start of one rather than one build cycle at a "
                        + "time");
        assertEquals(0, count(current, PredicateSubstrate.EXECUTION_CONTEXT),
                "so the substrate-A ceiling no longer binds this set: it is a property of the "
                        + "frozen set, not a defect of the current corpus");
        assertEquals(148, count(current, PredicateSubstrate.PREDICATE_STORE));

        PredicateGraph frozenGraph = PredicateGraph.of(frozen);
        PredicateGraph currentGraph = PredicateGraph.of(current);

        // The same question, asked of both graphs and answered from the same shape: the substrate
        // is a field of a site, never a different kind of graph. That is what makes the two sets
        // comparable, and what makes the differences below differences rather than artefacts.
        for (String predicate : List.of("GENERATED_KEY", "ENCRYPTED")) {
            assertTrue(frozenGraph.hasProducer(predicate),
                    predicate + " is written somewhere in the frozen set");
            assertTrue(currentGraph.hasProducer(predicate),
                    predicate + " is written somewhere in the current set");
        }
        assertTrue(frozenGraph.hasConsumer("GENERATED_KEY") && currentGraph.hasConsumer("GENERATED_KEY"),
                "the predicate both sets read is read in both");
        assertFalse(frozenGraph.hasConsumer("ENCRYPTED"),
                "and one measured difference the shared shape makes visible: the frozen set writes "
                        + "ENCRYPTED and never reads it, so the write changes no verdict there");
        assertTrue(currentGraph.hasConsumer("ENCRYPTED"),
                "the current set wired a consumer for it - MacSpec's validateAbsent - which is a "
                        + "change in the graph and not a change of substrate");
    }

    @Test
    @DisplayName("9.2: polarity survives on both substrates, written two different ways")
    void test_polarity_is_read_on_both_substrates() {
        List<PredicateSiteFacts> frozen = sitesOf("jca");
        List<PredicateSiteFacts> current = sitesOf("jca_android");

        // 7, not the 6 measured at 5fbe8173, and no file of the frozen set changed: substrate A
        // writes the demand two ways and PredicateIdioms.negatedAt could only see one of them.
        // condition(!(ExecutionContext.instance().validate(...))) - PBEParameterSpecSpec.mop:47,
        // with grouping parentheses - lifted as POSITIVE, which is an M4 edge reported present
        // that is really inverted. The reader was corrected and the assertion follows the corpus.
        assertEquals(7, negated(frozen),
                "substrate A writes the demand as condition(!validate(...)), with or without "
                        + "grouping parentheses; counting rule = recognised sites whose "
                        + "PredicateRef.polarity is NEGATED");
        assertEquals(5, negated(current),
                "substrate B writes the same demand as validateAbsent(...)");
        assertTrue(frozen.stream().filter(site -> site.ref().polarity() == Polarity.NEGATED)
                        .allMatch(site -> site.substrate() == PredicateSubstrate.EXECUTION_CONTEXT),
                "and the two idioms are not interchangeable: each set writes its own");
        assertTrue(current.stream().filter(site -> site.ref().polarity() == Polarity.NEGATED)
                        .allMatch(site -> site.substrate() == PredicateSubstrate.PREDICATE_STORE));
    }

    @Test
    @DisplayName("the frozen set's RANDOMIZED chain is a producer and a consumer in different files")
    void test_the_frozen_bridge_is_located_by_the_graph() {
        PredicateGraph graph = PredicateGraph.of(sitesOf("jca"));

        List<String> producers = graph.producers("RANDOMIZED").stream()
                .map(PredicateSiteFacts::specification).distinct().sorted().toList();
        List<String> consumers = graph.consumers("RANDOMIZED").stream()
                .map(PredicateSiteFacts::specification).distinct().sorted().toList();

        assertTrue(producers.contains("RandomStringPassword.mop"),
                "the bridge writes the predicate over the char[] it produced");
        assertTrue(consumers.contains("PBEKeySpecSpec.mop"),
                "and its only consumer reads it over the password");
        assertNotEquals(producers, consumers,
                "producer and consumer are in different files, which is why a per-file graph "
                        + "would report the read as an orphan and the write as a dead end");
        assertTrue(graph.bridges().isEmpty(),
                "and the component reports no broken edge here today: both routes need something "
                        + "the current lift does not supply - a declared type per argument "
                        + "position, or an argument expression that builds a value at the site - "
                        + "and this corpus writes plain identifiers. Reporting a break without "
                        + "either would be an accusation, not a finding");
    }

    // ── M4 against the oracle ─────────────────────────────────────────────────────────────────

    @Test
    @Tag(OracleCorpus.TAG)
    @DisplayName("M4 over jca_android against the upstream rules, with the derived fraction")
    void test_m4_over_the_current_corpus_against_the_oracle() throws IOException {
        Map<String, List<PredicateSiteFacts>> sitesBySpec = new LinkedHashMap<>();
        List<SpecRulePairing.Candidate> specifications = new ArrayList<>();
        for (Path file : filesOf("jca_android")) {
            MopLift lift = liftMop(file);
            String name = file.getFileName().toString();
            specifications.add(new SpecRulePairing.Candidate(name, lift.model()));
            sitesBySpec.put(name, facts(name, lift));
        }
        SpecRulePairing.Result pairing = SpecRulePairing.pair(specifications, upstreamRules());

        PredicateGraph corpus = PredicateGraph.of(sitesBySpec.values().stream()
                .flatMap(List::stream).toList());
        M4Predicates metric = new M4Predicates();

        int present = 0;
        int absent = 0;
        int inverted = 0;
        int derivedRows = 0;
        int rows = 0;
        for (SpecRulePairing.Pair pair : pairing.pairs()) {
            String name = pair.specification().name();
            M4Predicates.M4Analysis analysis = metric.compare(name,
                    pair.rule().name() + ".crysl", sitesBySpec.get(name),
                    pair.rule().model(), corpus, M4Predicates.Judgements.empty());
            present += analysis.result().present().size();
            absent += analysis.result().absent().size();
            inverted += analysis.result().inverted().size();
            derivedRows += analysis.result().derivedRows();
            rows += analysis.rows().size();
        }
        int paired = pairing.pairs().size();

        assertEquals(corpusSize() - UNPAIRED.size(), paired,
                "the pairing of record: SpecRulePairing, by declared type and INJECTIVE "
                        + "(INV-CONF-11 plus the injectivity the corpus forces). The four that "
                        + "pair with nothing are RandomStringPassword.mop, whose declared type is "
                        + "String; IvChainJunction.mop, which declares Cipher and loses "
                        + "Cipher.crysl to CipherSpec on signature coverage; and, since gh109, "
                        + "OAEPParameterSpecSpec.mop and SSLEngineSpec.mop, whose rules are the "
                        + "two the lift rejects");
        assertEquals(List.of("IvChainJunction.mop", "OAEPParameterSpecSpec.mop",
                        "RandomStringPassword.mop", "SSLEngineSpec.mop"),
                pairing.unpairedNames(),
                "and the losers are named rather than dropped in silence");
        assertEquals(107, present,
                "edges present over the pairs, with no declared alias. 105 -> 107 at group G8, "
                        + "the same two sites the census above counts: 8.1's speccedKey write "
                        + "reaches its three readers, and 8.6's second probe is a second edge over "
                        + "a clause that already had one");
        assertEquals(39, absent,
                "44 -> 40 at gh109 group G2: four clauses that no site implemented now have one. "
                        + "The group adds pairs as well as sites, so this number could have moved "
                        + "either way -- a new pair brings its rule's unimplemented clauses in "
                        + "with it -- and it fell, which is what a producer specification is for. "
                        + "40 -> 34 at group G1b, and this one could only fall: the group adds no "
                        + "pair at all, only sites, and the six clauses it implements are the four "
                        + "guarded REQUIRES of KeyPairGenerator and the "
                        + "generatedManagerFactoryParameters of each manager factory -- six clauses "
                        + "that had a rule and no site, read at ten sites because two of them are "
                        + "read at two overloads each. 38 -> 40 at group G4, and it ROSE, which is "
                        + "the other half of the same counting rule: the group adds two pairs -- "
                        + "KeyAgreementSpec and SSLParametersSpec, SSLEngineSpec pairing with "
                        + "nothing because its rule does not lift -- and KeyAgreementSpec "
                        + "implements every predicate clause its rule states, so what enters is "
                        + "the unimplemented clauses the two new rules bring with them. 40 -> 39 "
                        + "at group G8, and only one of that wave's two new sites moves it: task "
                        + "8.1 implements SecretKeySpec.crysl's speccedKey, a clause that had a "
                        + "rule and no site, while task 8.6's second probe reads a clause "
                        + "CipherSpec.i2 already implemented -- a second spelling of one string, "
                        + "not a second clause. The group adds no pair, so this number could only "
                        + "fall");
        assertEquals(0, inverted,
                "no site of the current corpus pairs with a clause and then disagrees with it on "
                        + "polarity or on argument order - including the one negated pair, "
                        + "MacSpec's validateAbsent against Mac.crysl's !encrypted, which agrees "
                        + "because both sides are read as NEGATED and not because both lifts lost "
                        + "the same signal");
        // 131 -> 135 at group G1b, and the arithmetic is the counting rule itself: ten sites
        // enter and six absences leave, because the six clauses those sites implement had a row
        // apiece as absences. Both halves move together and neither can be read off the other.
        // 135 -> 159 at group G3, and both halves of the counting rule move at once: twenty-four
        // sites enter over seven new pairs, and the absences rise with the pairing rather than
        // fall with the sites. 159 -> 175 at group G4: fourteen sites of paired specifications --
        // KeyAgreementSpec's eleven reads and two writes, SSLParametersSpec's one write, and none
        // of SSLEngineSpec's, whose specification pairs with no rule -- plus the two absences the
        // two new pairs bring in. 175 -> 176 at group G8, and the +1 is the two halves moving in
        // opposite directions over the same wave: two sites enter (8.1's speccedKey write, 8.6's
        // second probe) and one absence leaves (8.1's clause had a rule and no site), which is
        // 175 + 2 - 1. Task 8.9 moves neither half: a negated twin is an event, not a site.
        assertEquals(176, rows, "one row per site of a paired specification, plus one per absence");
        // 134 -> 145 at group G4, eleven of the sixteen new rows: the derived fraction falls
        // slightly, from 0.843 to 0.829, because five of the new rows are absences and an absence
        // is not a class this metric derives. 145 -> 146 at group G8, and the fraction RISES to
        // 0.830, which is the same rule read from the other side: the wave's two new rows are both
        // sites and one of the absences left, so the numerator gains what the denominator gains
        // and one non-derivable row is gone.
        assertEquals(146, derivedRows,
                "rows whose fidelity class this metric derived, under Judgements.empty(): no "
                        + "declared alias and no supplied class, so every derived row was derived "
                        + "by this metric and by nothing else");
        assertEquals(0.830, (double) derivedRows / rows, 0.001,
                "the derived fraction, which is the honest measure of how much of the manual "
                        + "table this component replaced; it rises when the comparison improves "
                        + "and not when the component is handed more judgement");
    }

    @Test
    @Tag(OracleCorpus.TAG)
    @DisplayName("the two predicate vocabularies do not align mechanically, and that is measured")
    void test_the_two_vocabularies_do_not_fully_align() throws IOException {
        Map<String, MopLift> lifts = new LinkedHashMap<>();
        List<SpecRulePairing.Candidate> specifications = new ArrayList<>();
        for (Path file : filesOf("jca_android")) {
            MopLift lift = liftMop(file);
            lifts.put(file.getFileName().toString(), lift);
            specifications.add(
                    new SpecRulePairing.Candidate(file.getFileName().toString(), lift.model()));
        }
        List<String> unmatched = new ArrayList<>();
        for (SpecRulePairing.Pair pair : SpecRulePairing.pair(specifications, upstreamRules())
                .pairs()) {
            MopLift lift = lifts.get(pair.specification().name());
            SpecModel rule = pair.rule().model();
            List<String> ruleNames = Stream.of(rule.ensures(), rule.requires(), rule.negates())
                    .flatMap(List::stream)
                    .map(ref -> PredicateGraph.canonical(ref.name()))
                    .distinct().toList();
            for (PredicateSite site : lift.predicateSites()) {
                String canonical = PredicateGraph.canonical(site.ref().name());
                if (!ruleNames.contains(canonical)) {
                    unmatched.add(site.ref().name());
                }
            }
        }

        assertFalse(unmatched.isEmpty(),
                "lowercasing with the underscores removed aligns most of the two vocabularies and "
                        + "not all of it: MACED against macced, GENERATED_PUBLIC_KEY against "
                        + "generatedPubkey, GENERATE_SSL_CONTEXT against generatedSSLContext are "
                        + "pairings a person made. They cross as declared aliases and the rows "
                        + "they produce stay inherited, which is exactly why the derived fraction "
                        + "is below 1 and does not rise by being handed the alias map");
        assertTrue(unmatched.contains("MACED"),
                "the canonical rule cannot reach 'macced' from 'MACED', and it does not pretend to");
    }

    // ── bridge from the lift ──────────────────────────────────────────────────────────────────

    /**
     * Map the {@code -mop} module's sites onto the shape {@code -core} compares.
     *
     * <p>{@code argumentTypes} is left empty rather than guessed. A type inferred from an argument
     * name would be a fabrication with the authority of a measurement, and the propagation-bridge
     * check would then report findings nobody could trace to a declaration.
     */
    private static List<PredicateSiteFacts> facts(String specification, MopLift lift) {
        List<PredicateSiteFacts> facts = new ArrayList<>(lift.predicateSites().size());
        for (PredicateSite site : lift.predicateSites()) {
            facts.add(new PredicateSiteFacts(specification, section(site.kind()),
                    substrate(site.substrate()), "", PredicateSiteFacts.SiteKind.BODY,
                    site.verdict(), List.of(), site.ref()));
        }
        return facts;
    }

    private static PredicateSiteFacts.Section section(PredicateSite.Kind kind) {
        return switch (kind) {
            case ENSURES -> PredicateSiteFacts.Section.ENSURES;
            case REQUIRES -> PredicateSiteFacts.Section.REQUIRES;
            case NEGATES -> PredicateSiteFacts.Section.NEGATES;
        };
    }

    private static PredicateSubstrate substrate(PredicateSite.Substrate substrate) {
        return switch (substrate) {
            case EXECUTION_CONTEXT -> PredicateSubstrate.EXECUTION_CONTEXT;
            case PREDICATE_STORE -> PredicateSubstrate.PREDICATE_STORE;
        };
    }

    // ── corpus access ─────────────────────────────────────────────────────────────────────────

    private List<PredicateSiteFacts> sitesOf(String corpus) {
        List<PredicateSiteFacts> sites = new ArrayList<>();
        for (Path file : filesOf(corpus)) {
            sites.addAll(facts(file.getFileName().toString(), liftMop(file)));
        }
        return sites;
    }

    private MopLift liftMop(Path file) {
        try {
            return mopLifter.read(file, new Version(file.getParent().getFileName().toString(),
                    new SourceStamp("rvsec", "working-tree", Instant.EPOCH)));
        } catch (LiftFailure e) {
            throw new IllegalStateException("the corpus must lift: " + file, e);
        }
    }

    /**
     * The specifications of the set that pair with no rule of the lifted oracle.
     *
     * <p>Declared, because each name is a judgement — and the four are named with their reasons
     * in the assertion right below the count. Only the arithmetic derives from the list, which is
     * what keeps a group of new specifications from moving a literal that says nothing about
     * predicates.
     */
    private static final Set<String> UNPAIRED = Set.of("IvChainJunction", "OAEPParameterSpecSpec",
            "RandomStringPassword", "SSLEngineSpec");

    /** How many {@code .mop} files the Android set holds right now. Derived: no judgement in it. */
    private static int corpusSize() {
        return filesOf("jca_android").size();
    }

    private static List<Path> filesOf(String corpus) {
        try (Stream<Path> entries = Files.list(RESOURCES.resolve(corpus))) {
            return entries.filter(path -> path.getFileName().toString().endsWith(".mop"))
                    .sorted().toList();
        } catch (IOException e) {
            throw new UncheckedIOException("cannot list corpus " + corpus, e);
        }
    }

    /**
     * The upstream rules as pairing candidates.
     *
     * <p>They are handed to {@link SpecRulePairing} rather than indexed by simple name here, and
     * that is the whole of task 12.0: this class used to keep its own by-simple-name map, which
     * reached 23 pairs where the component's rule of record reaches 22, because
     * {@code IvChainJunction.mop} declares {@code Cipher} and a non-injective map lets it claim
     * {@code Cipher.crysl} beside {@code CipherSpec}. A report whose M1 and M4 disagree about which
     * specifications were compared cannot be published, so both now pair through one
     * implementation.
     */
    private static List<SpecRulePairing.Candidate> upstreamRules() throws IOException {
        CryslLifter lifter = new CryslLifter();
        CryslLifter.CorpusLift lift =
                lifter.liftCorpus(OracleCorpus.cryslRules(), OracleCorpus.version());
        List<SpecRulePairing.Candidate> candidates = new ArrayList<>(lift.models().size());
        for (SpecModel rule : lift.models()) {
            candidates.add(new SpecRulePairing.Candidate(simpleName(rule.type()), rule));
        }
        return candidates;
    }

    private static String simpleName(String type) {
        int dot = type.lastIndexOf('.');
        return dot < 0 ? type : type.substring(dot + 1);
    }

    private static long count(List<PredicateSiteFacts> sites, PredicateSubstrate substrate) {
        return sites.stream().filter(site -> site.substrate() == substrate).count();
    }

    private static long negated(List<PredicateSiteFacts> sites) {
        return sites.stream().filter(site -> site.ref().polarity() == Polarity.NEGATED).count();
    }
}
