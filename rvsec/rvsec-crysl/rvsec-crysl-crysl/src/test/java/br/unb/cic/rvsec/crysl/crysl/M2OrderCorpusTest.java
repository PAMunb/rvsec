package br.unb.cic.rvsec.crysl.crysl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.LiftFailure;
import br.unb.cic.rvsec.crysl.core.automata.Determinizer;
import br.unb.cic.rvsec.crysl.core.compare.AlphabetMap;
import br.unb.cic.rvsec.crysl.core.compare.Observability;
import br.unb.cic.rvsec.crysl.core.emit.MarkdownEmitter;
import br.unb.cic.rvsec.crysl.core.metric.M0Result;
import br.unb.cic.rvsec.crysl.core.metric.M0Vitality;
import br.unb.cic.rvsec.crysl.core.metric.M2Order;
import br.unb.cic.rvsec.crysl.core.metric.M2Result;
import br.unb.cic.rvsec.crysl.core.metric.MisuseAbsorption;
import br.unb.cic.rvsec.crysl.core.metric.SpecRulePairing;
import br.unb.cic.rvsec.crysl.core.model.Label;
import br.unb.cic.rvsec.crysl.core.model.OverlappingDispatch;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import br.unb.cic.rvsec.crysl.core.model.SourceStamp;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import br.unb.cic.rvsec.crysl.core.model.Unknown;
import br.unb.cic.rvsec.crysl.core.model.UnresolvedSignature;
import br.unb.cic.rvsec.crysl.core.model.Version;
import br.unb.cic.rvsec.crysl.core.model.Witness;
import br.unb.cic.rvsec.crysl.core.model.WitnessStatus;
import br.unb.cic.rvsec.crysl.mop.MopLift;
import br.unb.cic.rvsec.crysl.mop.MopLifter;
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
import java.util.Optional;
import java.util.Set;
import java.util.stream.Stream;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

/**
 * M2 over {@code jca_android} against the upstream {@code CrySL-Rules}, end to end.
 *
 * <p>Both lifters have to be on one classpath, so this lives here rather than in
 * {@code rvsec-crysl-core}, and it is oracle-dependent because the 47 rules that load are in the
 * sibling {@code rvsec-cognicrypt} repository that CI does not check out.
 *
 * <p><strong>Where the numbers disagree with the published ones, they are reported and not
 * reconciled</strong> (INV-CONF-14). Three of the verdicts of this group were published in
 * {@code docs/20260821_conformidade_mop_crysl.md} §5.2, and they were computed against the
 * <em>abandoned</em> {@code generated/api30} corpus, before design D-20 moved the inverse morphism
 * to lift time. Both changes move verdicts, in ways this suite measures rather than argues:
 *
 * <ul>
 *   <li>the oracle switch gives the upstream rules symbols {@code api30} did not generate -
 *       {@code SecureRandom}'s {@code nI: nextInt()} is the measured case, and the alphabet map,
 *       which is still anchored to {@code api30}, declares the {@code .mop}'s {@code next3} erased
 *       because {@code api30} named no such event;
 *   <li>D-20 makes the negated-twin idiom - an accepted and a rejected event over one call,
 *       separated by complementary {@code condition}s - an {@code Unknown{OverlappingDispatch}} at
 *       lift, so that call is not a letter of {@code SpecModel.order} at all. Nine of the 24
 *       specifications use the idiom and eleven refusals come out of it, and the verdicts they
 *       carry are marked refusal-borne here.
 * </ul>
 */
@Tag(OracleCorpus.TAG)
class M2OrderCorpusTest {

    private static final Path CORPUS = Paths.get("..", "..", "rvsec-mop", "src", "main",
            "resources", "jca_android").normalize();

    private static final Path ALPHABET_MAP = Paths.get("..", "..", "..", "rv-android", "data",
            "jca_android", "order_alphabet_map.csv").normalize();

    /**
     * The states N3 removes from an accepting set, declared per specification and never inferred.
     *
     * <p>Only {@code CipherSpec} declares one. Its {@code alias match2 = s3} exists to give
     * {@code encrypted[pre_ciphertext, pre_plaintext] after updates} an acceptance point
     * ({@code CipherSpec.mop}, the comment above the alias), and a program that stops at {@code s3}
     * has stopped in the middle of a cipher. The alias names do not survive the lift, and deriving
     * the set by pattern - "every alias but the first" - was measured to over-apply: it takes
     * {@code end} out of {@code SecureRandomSpec} and {@code taken} out of the two factory
     * specifications, each of which is a legitimate end. So the set is declared here, with its
     * reason, exactly as the &epsilon;-erasures are declared in the alphabet map.
     */
    private static final Map<String, Set<String>> PREDICATE_ONLY_STATES =
            Map.of("CipherSpec", Set.of("s3"));

    // ---------------------------------------------------------------- 10.2-bis (closes G03 3.10)

    @Test
    @DisplayName("10.2-bis · how many of the 47 upstream rule automata are already deterministic")
    void test_determinization_census_over_the_upstream_oracle() throws IOException {
        List<SpecModel> rules = upstreamRules();
        assertEquals(47, rules.size(),
                "47 of the 49 upstream rules load; OAEPParameterSpec and SSLEngine are upstream "
                        + "defects recorded as findings (design D-08)");

        Determinizer.Census census = M2Order.census(rules);

        assertEquals(47, census.total());
        assertEquals(47, census.alreadyDeterministic(),
                "a new measurement over the upstream oracle, not the historical 30 of 30, which "
                        + "was taken over the abandoned api30 generation and is method history. "
                        + "Counting rule: " + Determinizer.COUNTING_RULE);
        assertTrue(M2Order.reportCountingRule(census).contains("47 of 47"));
        assertTrue(M2Order.reportCountingRule(census).contains("R-DET"),
                "the number never leaves without its rule (INV-CONF-02)");
    }

    // ---------------------------------------------------------------- 10.10

    @Test
    @DisplayName("10.10 · the recomputed KeyGeneratorSpec verdict, and how it differs")
    void test_key_generator_spec_verdict_recomputed() throws Exception {
        Corpus corpus = Corpus.read();
        M2Order.Comparison comparison = corpus.compare("KeyGeneratorSpec");

        assertEquals(M2Result.Verdict.MOP_MORE_RESTRICTIVE, comparison.result().verdict(),
                "this DIFFERS from the published 'M2-decl: EQUIVALENTES, sob N1' (docs/"
                        + "20260821_conformidade_mop_crysl.md §5.2), which was computed against "
                        + "the abandoned api30 rule");
        assertEquals(List.of("N-REN", "N1"), normalizationIds(comparison.result()),
                "and it is not the ere that moved it: the four init* the ere gained all map to "
                        + "the rule's i1..i5 and are absorbed by the letter identification, so no "
                        + "witness of either direction mentions an init at all");

        Witness ruleOnly = comparison.ruleOnly().orElseThrow(
                () -> new AssertionError("MOP_MORE_RESTRICTIVE with no rule-side witness"));
        assertEquals(WitnessStatus.ABSTRACT, ruleOnly.status());
        assertEquals(List.of("javax.crypto.KeyGenerator.getInstance(java.lang.String)",
                        "javax.crypto.KeyGenerator.generateKey()"),
                render(ruleOnly),
                "the sole distinguishing word, and every letter of it is a call the "
                        + "specification does monitor");

        assertTrue(comparison.refusalBorne(),
                "because getInstance(String) is claimed by g1 and by its negated twin g3 with "
                        + "complementary conditions, the lift refuses it and it is not a letter of "
                        + "SpecModel.order. The narrowing belongs to the refusal: "
                        + comparison.narrowing().orElse(""));
        assertTrue(comparison.narrowing().orElseThrow().contains("g1")
                        && comparison.narrowing().orElseThrow().contains("g3"),
                "and the statement names the two labels that claim the call");

        assertTrue(corpus.map.erases("KeyGeneratorSpec", "g3"),
                "the map declares g3 erased, with a reason and a rule line");
        assertFalse(normalizationIds(comparison.result()).stream()
                        .anyMatch(id -> id.startsWith("N-EPS·KeyGeneratorSpec.g3")),
                "and the erasure is nevertheless not reported as applied, because there is "
                        + "nothing left to erase: g1 and g3 claim the same call, the lift refused "
                        + "it, and the letter left the language before M2 saw it. The declared "
                        + "erasure of the negated twin is unreachable for every specification "
                        + "that uses the idiom, which is nine of the 24");

        M2Order.Comparison projected = corpus.compareWithoutRefusedLetters("KeyGeneratorSpec");
        assertEquals(M2Result.Verdict.EQUIVALENT, projected.result().verdict(),
                "over the alphabet the component could read, the two languages agree exactly. So "
                        + "the published EQUIVALENT survives modulo the refused letter, and the "
                        + "difference this run reports is an instrument narrowing rather than a "
                        + "divergence of the specification from its rule");
    }

    // ---------------------------------------------------------------- 10.11

    @Test
    @DisplayName("10.11 · the three byte-identical automata, re-emitted as results")
    void test_the_three_unchanged_automata_are_results_not_rederivations() throws Exception {
        Corpus corpus = Corpus.read();

        // The ere/fsm lines of these three are byte-identical between the pinned 5fbe8173 and the
        // current HEAD; 5bc5c893 rewrote value lists and left every formula alone. So what follows
        // is a result over an unchanged input, and what moved is the oracle and the lift.
        M2Order.Comparison messageDigest = corpus.compare("MessageDigestSpec");
        assertEquals(M2Result.Verdict.MOP_MORE_RESTRICTIVE, messageDigest.result().verdict(),
                "published: EQUIVALENTES sob N1. It is refusal-borne - g1 and its negated twin "
                        + "claim getInstance(String) - and equivalent once that letter leaves both "
                        + "sides");
        assertTrue(messageDigest.refusalBorne());
        assertEquals(M2Result.Verdict.EQUIVALENT,
                corpus.compareWithoutRefusedLetters("MessageDigestSpec").result().verdict());
        assertEquals(List.of("N-AGG", "N-REN", "N1"), normalizationIds(messageDigest.result()));

        M2Order.Comparison signature = corpus.compare("SignatureSpec");
        assertEquals(M2Result.Verdict.EQUIVALENT, signature.result().verdict(),
                "published: EQUIVALENTES sob N1, and it reproduces against the upstream oracle");
        assertEquals(List.of("N-AGG", "N-REN", "N1"), normalizationIds(signature.result()));
        assertTrue(signature.result().witness().isEmpty(),
                "two languages that agree have nothing to show");
        assertTrue(signature.result().refusals().isEmpty(),
                "and SignatureSpec carries no negated twin over a shared call, which is why it is "
                        + "the one of the three that reproduces unqualified");

        M2Order.Comparison secureRandom = corpus.compare("SecureRandomSpec");
        assertEquals(M2Result.Verdict.MOP_MORE_RESTRICTIVE, secureRandom.result().verdict(),
                "published: MOP MAIS PERMISSIVA sob N1+N2");
        for (M2Result result : List.of(messageDigest.result(), signature.result(),
                secureRandom.result())) {
            assertEquals(M2Result.LABEL, M2Result.LABEL, "every verdict is published as "
                    + M2Result.LABEL);
            result.witness().ifPresent(witness -> assertEquals(WitnessStatus.ABSTRACT,
                    witness.status(), "none of the three was executed"));
        }
    }

    // ---------------------------------------------------------------- 10.13

    @Test
    @DisplayName("10.13 · SecureRandomSpec: N2 is vacuous upstream and the map's api30 anchoring "
            + "is what moves the verdict")
    void test_secure_random_spec() throws Exception {
        Corpus corpus = Corpus.read();
        M2Order.Comparison comparison = corpus.compare("SecureRandomSpec");

        assertEquals(M2Result.Verdict.MOP_MORE_RESTRICTIVE, comparison.result().verdict(),
                "the published verdict is 'MOP more permissive, under N1 + N2' and it does not "
                        + "reproduce against the upstream oracle. Reported, not reconciled "
                        + "(INV-CONF-14)");
        assertTrue(normalizationIds(comparison.result()).contains("N1"));
        assertFalse(normalizationIds(comparison.result()).contains("N2"),
                "N2 has nothing to project: the protected next(int) it was about is an api30 "
                        + "artifact, and upstream SecureRandom.crysl orders nB, nI and nIR, all "
                        + "three public. Measured over android.jar, not asserted from a list");

        assertTrue(comparison.refusalBorne(),
                "g1/g2 and the negated twin g4 claim the same getInstance calls");
        M2Order.Comparison projected = corpus.compareWithoutRefusedLetters("SecureRandomSpec");
        assertEquals(M2Result.Verdict.MOP_MORE_RESTRICTIVE, projected.result().verdict(),
                "and unlike KeyGeneratorSpec a real difference survives the projection");
        assertEquals(List.of("java.security.SecureRandom.SecureRandom()",
                        "java.security.SecureRandom.nextInt()"),
                render(projected.ruleOnly().orElseThrow()),
                "the residual is exactly the api30 anchoring of the map: the row "
                        + "'SecureRandomSpec,next3,,,SecureRandom.cryptsl,,order-unmapped' says "
                        + "the rule names no such event, which was true of api30 and is false of "
                        + "the upstream rule, whose nI is nextInt(). The erasure is honoured "
                        + "because the map declares it (INV-CONF-10) and the consequence is "
                        + "reported rather than repaired (INV-CONF-12)");
        assertTrue(normalizationIds(comparison.result()).contains("N-EPS·SecureRandomSpec.next3"));
        assertEquals(WitnessStatus.ABSTRACT, projected.ruleOnly().orElseThrow().status());
    }

    @Test
    @DisplayName("10.13 · CipherSpec: incomparable, and the g1 i2 i2 f2 witness is still there")
    void test_cipher_spec() throws Exception {
        Corpus corpus = Corpus.read();
        M2Order.Comparison comparison = corpus.compare("CipherSpec");

        assertEquals(M2Result.Verdict.INCOMPARABLE, comparison.result().verdict());
        assertTrue(normalizationIds(comparison.result()).contains("N3"),
                "N3 because alias match2 = s3 is a predicate point rather than a legitimate end: "
                        + normalizationIds(comparison.result()));
        assertFalse(normalizationIds(comparison.result()).contains("N4"),
                "and N4 is NOT applied here, which corrects the published reading. §5.2 offers "
                        + "CipherSpec as the N4 case on the strength of doFinal(..) also matching "
                        + "doFinal(). At HEAD that overlap is separated by complementary "
                        + "conditions, so the lift refuses it instead of concatenating - it is the "
                        + "specification's one refusal - and the only call in the whole "
                        + "jca_android set that emits two letters is IvChainJunction's "
                        + "Cipher.init(int, Key, AlgorithmParameterSpec, SecureRandom)");

        assertTrue(comparison.mopOnly().isPresent() && comparison.ruleOnly().isPresent(),
                "BOTH directions are alive, which differs from the published reading that only "
                        + "rule \\ MOP sustained the verdict. The direction that died in gh105 "
                        + "task 6.6 was the f1/f2 one; another mop-only word took its place");
        // The word shrank from four letters to two, and not because of gh109: measured, the
        // `alias match3 = s2` that shortens it entered CipherSpec.mop at 62f65b3f (gh105 task
        // 11.5(e)), and gh109's one commit over that file touched comments and a CONSTRAINTS
        // helper - no alias, no event, no ere. An initialised-and-never-used Cipher is now the
        // shortest sequence the specification accepts and the expert ORDER rejects, which is what
        // the Python G-ORDER gate has asserted since that task (`cipher.witness == ("g1", "i1")`).
        // This pin never followed, and it is re-pinned here rather than left red: the number
        // belongs to gh105 and only the re-measurement belongs to gh109.
        //
        // What the D-10 note below says stays true of the word it describes - wrap after doFinal
        // in ENCRYPT_MODE is still automaton-valid and still impossible in Java. It is no longer
        // the SHORTEST such word, which is the only thing that moved.
        assertEquals(List.of("javax.crypto.Cipher.getInstance(java.lang.String,AnyType)",
                        "javax.crypto.Cipher.init(int,java.security.Key)"),
                render(comparison.mopOnly().orElseThrow()),
                "and the replacement is the case design D-10 exists for: wrap after a doFinal in "
                        + "ENCRYPT_MODE raises IllegalStateException before any monitor sees it, "
                        + "so this word is automaton-valid and impossible in Java - which is "
                        + "exactly why it stays ABSTRACT and carries no claim");

        // The same gh105 movement that shortened the mop-only word above moved this one, and
        // for the same reason: with `s2` accepting, the projected difference finds a shorter
        // separating word than `g1 i2 i2 f2` and `updateAAD` stands where the repeated `init`
        // did. The published reading is still about this direction being alive; which word
        // witnesses it is a shortest-word search and not a claim, and re-pinning it is a
        // re-measurement of gh105's change, not of gh109's.
        M2Order.Comparison projected = corpus.compareWithoutRefusedLetters("CipherSpec");
        assertEquals(List.of("javax.crypto.Cipher.getInstance(java.lang.String,AnyType)",
                        "javax.crypto.Cipher.init(int,java.security.Key)",
                        "javax.crypto.Cipher.updateAAD(byte[])",
                        "javax.crypto.Cipher.doFinal(byte[])"),
                render(projected.ruleOnly().orElseThrow()),
                "the rule \\ MOP direction is alive, letter for letter, once the refused "
                        + "getInstance(String) is taken out of the rule as well");
    }

    // ---------------------------------------------------------------- 10.14, INV-CONF-09

    @Test
    @DisplayName("10.14 · over the paired corpus no event is undeclared, so no erasure is invented")
    void test_no_event_of_the_paired_corpus_lacks_a_disposition_row() throws Exception {
        Corpus corpus = Corpus.read();

        List<String> undeclared = new ArrayList<>();
        for (String specification : corpus.comparable()) {
            for (Unknown refusal : corpus.compare(specification).result().refusals()) {
                if (refusal instanceof UnresolvedSignature unresolved
                        && unresolved.mode().startsWith(M2Order.UNDECLARED_EVENT_MODE)) {
                    undeclared.add(unresolved.mode());
                }
            }
        }

        assertEquals(List.of(), undeclared,
                "task 7.1 of gh105 completed the map, and this is the check that it stayed "
                        + "complete. An event that lost its row would appear here as a refusal and "
                        + "never as an erasure (INV-CONF-10)");
    }

    @Test
    @DisplayName("INV-CONF-09 · the specification M0 refuses receives no M2 verdict")
    void test_the_refused_specification_gets_no_verdict() throws Exception {
        Corpus corpus = Corpus.read();

        assertEquals(corpusSize() - UNPAIRED.size(), corpus.pairs().size(),
                "all but the three unpaired pair by declared type");
        assertEquals(corpus.pairs().size() - M0_REFUSED.size(), corpus.comparable().size(),
                "and all but the two M0 refuses receive an M2 verdict: SecretKeySpec has a "
                        + "non-empty @match, no "
                        + "@fail and no addError, so it cannot accuse under any trace and M0 "
                        + "refuses it, and KeySpec is refused for the same reason at gh109 task "
                        + "2.14 - by design there, because Key.crysl asks for no accusation");
        assertFalse(corpus.comparable().contains("SecretKeySpec"));
        assertFalse(corpus.comparable().contains("KeySpec"));
    }

    // ---------------------------------------------------------------- 10.15

    @Test
    @DisplayName("10.15 · the overlap path: one Cipher.init emits use useRandomSpec in declaration "
            + "order, and a guarded overlap refuses")
    void test_the_overlap_path_end_to_end() throws Exception {
        Corpus corpus = Corpus.read();

        MopLift junction = corpus.lift("IvChainJunction");
        Signature init = new Signature("javax.crypto.Cipher", "init",
                List.of("int", "java.security.Key", "java.security.spec.AlgorithmParameterSpec",
                        "java.security.SecureRandom"), "void");
        assertEquals(List.of(new Label("use"), new Label("useRandomSpec")),
                junction.morphism().images().get(init),
                "declaration order is dispatch order: use is written with a trailing '..' at :131 "
                        + "and useRandomSpec exactly at :256, so one call really does emit two "
                        + "letters and h maps it to their concatenation (design D-02)");
        assertEquals(List.of(), junction.morphism().refusals(),
                "and neither event declares a condition, so nothing is refused here - the "
                        + "concatenation is decidable and this is the case that makes the "
                        + "non-disjointness argument a corpus witness rather than a claim");

        // The other half of the scenario: an overlap a guard separates, which this module has no
        // solver for and therefore refuses rather than choosing. The corpus's instance of it is
        // the negated-twin idiom, not the junction.
        List<Unknown> refusals = corpus.lift("KeyGeneratorSpec").morphism().refusals();
        assertEquals(1, refusals.size());
        OverlappingDispatch overlap = (OverlappingDispatch) refusals.get(0);
        assertEquals(List.of("g1", "g3"), overlap.labels(),
                "INV-CONF-07: a refusal that does not name which labels overlap does not say how "
                        + "many letters the call emits");
        assertEquals("getInstance", overlap.signature().name());
    }

    // ---------------------------------------------------------------- 10.12, 10.12-bis, 10.6, 10.7

    @Test
    @DisplayName("10.6/10.7/10.12-bis · the corpus report carries the label, the normalizations, "
            + "the witness status and no runtime claim")
    void test_the_corpus_report() throws Exception {
        Corpus corpus = Corpus.read();
        List<M2Result> results = new ArrayList<>();
        for (String specification : corpus.comparable()) {
            results.add(corpus.compare(specification).result());
        }
        assertEquals(corpus.comparable().size(), results.size());

        for (M2Result result : results) {
            result.witness().ifPresent(witness -> assertEquals(WitnessStatus.ABSTRACT,
                    witness.status(), result.specification() + ": none of these was executed"));
        }

        List<MarkdownEmitter.VerdictEntry> entries = M2Order.publish(results);
        assertTrue(entries.stream().allMatch(e -> e.claim() == MarkdownEmitter.Claim.NONE));

        String markdown = new MarkdownEmitter().orderReport("M2 · jca_android against upstream",
                corpus.mopVersion(), OracleCorpus.version(),
                M2Order.reportCountingRule(M2Order.census(upstreamRules())), entries);

        assertTrue(markdown.contains(MarkdownEmitter.M2_DECL_QUALIFIER), "INV-CONF-13");
        assertTrue(markdown.contains("47 of 47"), "the census travels into the report (10.2-bis)");
        assertTrue(markdown.contains("N-EPS·SecureRandomSpec.next3"),
                "each declared erasure is named in the row that used it (10.7)");
        assertTrue(markdown.contains("the rule names no such event"),
                "and the map's own reason is quoted verbatim underneath (10.5)");
        assertTrue(markdown.contains("rvsec-cognicrypt"), "the oracle is named (INV-CONF-11)");
        assertFalse(markdown.contains("FALSE_POSITIVE"), "no runtime claim anywhere (INV-CONF-08)");
    }

    @Test
    @DisplayName("N2 · the projection is a measurement over android.jar, and upstream it is empty")
    void test_n2_is_measured_and_not_a_list() throws Exception {
        Observability platform = Observability.of(OracleCorpus.androidJar());
        assertTrue(platform.populated(), "the instrument read something");

        Signature next = new Signature("java.security.SecureRandom", "next", List.of("int"), "int");
        Signature nextInt = new Signature("java.security.SecureRandom", "nextInt", List.of(), "int");
        assertFalse(platform.observable(next),
                "next(int) is protected on the platform, so no client program emits it. This is "
                        + "the symbol N2 was written for, and it is decided from the access flags "
                        + "rather than from a list of names");
        assertTrue(platform.observable(nextInt), "nextInt() is public");

        Corpus corpus = Corpus.read();
        List<String> withUnobservableSymbols = new ArrayList<>();
        for (SpecRulePairing.Pair pair : corpus.pairs()) {
            if (!platform.unobservable(pair.rule().model().order().alphabet()).isEmpty()) {
                withUnobservableSymbols.add(pair.rule().name());
            }
        }
        assertEquals(List.of(), withUnobservableSymbols,
                "and no upstream rule of the 22 orders a symbol a program cannot emit, so N2 is "
                        + "vacuous against this oracle. It was not vacuous against api30, whose "
                        + "generated SecureRandom rule ordered next(int) - which is why the "
                        + "published SecureRandomSpec verdict carries an N2 this run does not");
    }

    // ---------------------------------------------------------------- corpus plumbing

    /** One read of both corpora, so that a test that needs several verdicts pays for one lift. */
    private record Corpus(Map<String, MopLift> lifts, SpecRulePairing.Result pairing,
                          AlphabetMap map, Map<String, M0Result> vitality,
                          Observability platform) {

        static Corpus read() throws LiftFailure, IOException {
            MopLifter lifter = new MopLifter();
            Map<String, MopLift> lifts = new LinkedHashMap<>();
            Map<String, M0Result> vitality = new LinkedHashMap<>();
            List<SpecRulePairing.Candidate> specifications = new ArrayList<>();
            for (Path file : mopFiles()) {
                String name = file.getFileName().toString().replace(".mop", "");
                MopLift lift = lifter.read(file, mopVersionOf());
                lifts.put(name, lift);
                vitality.put(name, M0Vitality.examine(lift.model(), lift.labelOrder(),
                        lift.monitorFacts(MisuseAbsorption.scan(file)), Optional.empty()));
                specifications.add(new SpecRulePairing.Candidate(name, lift.model()));
            }
            List<SpecRulePairing.Candidate> rules = new ArrayList<>();
            for (SpecModel model : upstreamRules()) {
                rules.add(new SpecRulePairing.Candidate(simpleName(model.type()), model));
            }
            return new Corpus(lifts, SpecRulePairing.pair(specifications, rules),
                    AlphabetMap.read(ALPHABET_MAP),
                    vitality, Observability.of(OracleCorpus.androidJar()));
        }

        List<SpecRulePairing.Pair> pairs() {
            return pairing.pairs();
        }

        /** The paired specifications M0 did not refuse - the ones M1-M4 report on (INV-CONF-09). */
        List<String> comparable() {
            return pairs().stream()
                    .map(pair -> pair.specification().name())
                    .filter(name -> !vitality.get(name).refused())
                    .toList();
        }

        MopLift lift(String specification) {
            return lifts.get(specification);
        }

        Version mopVersion() {
            return mopVersionOf();
        }

        M2Order.Comparison compare(String specification) {
            SpecRulePairing.Pair pair = pairOf(specification);
            return compareAgainst(specification, pair.rule().name(), pair.rule().model());
        }

        /**
         * The second number of a refusal-borne verdict: the same comparison with every letter a
         * refusal covers removed from the rule as well.
         */
        M2Order.Comparison compareWithoutRefusedLetters(String specification) {
            SpecRulePairing.Pair pair = pairOf(specification);
            return compareAgainst(specification, pair.rule().name(),
                    M2Order.withoutRefusedLetters(pair.rule().model(),
                            lifts.get(specification).morphism()));
        }

        private M2Order.Comparison compareAgainst(String specification, String rule,
                                                  SpecModel ruleModel) {
            MopLift lift = lifts.get(specification);
            M2Order.Options options = new M2Order.Options(lift.site(),
                    vitality.get(specification).indexes(),
                    PREDICATE_ONLY_STATES.getOrDefault(specification, Set.of()), platform);
            return M2Order.compare(specification, lift.model(), lift.morphism(), rule, ruleModel,
                    map, options);
        }

        private SpecRulePairing.Pair pairOf(String specification) {
            return pairs().stream()
                    .filter(pair -> pair.specification().name().equals(specification))
                    .findFirst()
                    .orElseThrow(() -> new AssertionError(specification + " is not paired"));
        }
    }

    private static List<SpecModel> upstreamRules() throws IOException {
        return new CryslLifter().liftCorpus(OracleCorpus.cryslRules(), OracleCorpus.version())
                .models();
    }

    /**
     * The specifications of the set that pair with no rule of the lifted oracle.
     *
     * <p>Declared, because each name is a judgement — the reasons are asserted one by one in
     * {@code M1EventsCorpusTest}. Only the arithmetic derives from it, so that a group of new
     * specifications moves no literal here.
     */
    private static final Set<String> UNPAIRED =
            Set.of("IvChainJunction", "OAEPParameterSpecSpec", "RandomStringPassword");

    /**
     * The paired specifications M0 refuses, which therefore receive no M2 verdict (INV-CONF-09).
     *
     * <p>Declared for the same reason: both memberships were argued and are asserted below with
     * their cause.
     */
    private static final Set<String> M0_REFUSED = Set.of("SecretKeySpec", "KeySpec");

    /** How many {@code .mop} files the set holds right now. Derived: it carries no judgement. */
    private static int corpusSize() {
        return mopFiles().size();
    }

    private static List<Path> mopFiles() {
        try (Stream<Path> entries = Files.list(CORPUS)) {
            return entries.filter(p -> p.getFileName().toString().endsWith(".mop")).sorted()
                    .toList();
        } catch (IOException e) {
            throw new UncheckedIOException("cannot list " + CORPUS, e);
        }
    }

    private static List<String> normalizationIds(M2Result result) {
        return result.normalizations().stream()
                .map(normalization -> normalization.id())
                .toList();
    }

    private static List<String> render(Witness witness) {
        return witness.word().stream()
                .map(signature -> signature.declaringType() + "." + signature.name() + "("
                        + String.join(",", signature.paramTypes()) + ")")
                .toList();
    }

    private static Version mopVersionOf() {
        return new Version("jca_android", new SourceStamp("rvsec", "working-tree", Instant.EPOCH));
    }

    private static String simpleName(String type) {
        int dot = type.lastIndexOf('.');
        return dot >= 0 ? type.substring(dot + 1) : type;
    }
}
