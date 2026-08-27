package br.unb.cic.rvsec.crysl.crysl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.ApiIndex;
import br.unb.cic.rvsec.crysl.core.LiftFailure;
import br.unb.cic.rvsec.crysl.core.compare.Pipeline;
import br.unb.cic.rvsec.crysl.core.metric.M0Result;
import br.unb.cic.rvsec.crysl.core.metric.M0Vitality;
import br.unb.cic.rvsec.crysl.core.metric.MisuseAbsorption;
import br.unb.cic.rvsec.crysl.core.metric.MonitorFacts;
import br.unb.cic.rvsec.crysl.core.metric.Silence;
import br.unb.cic.rvsec.crysl.core.metric.SilenceCause;
import br.unb.cic.rvsec.crysl.core.model.SourceStamp;
import br.unb.cic.rvsec.crysl.core.model.UnreachableAccusationSite;
import br.unb.cic.rvsec.crysl.core.model.Unknown;
import br.unb.cic.rvsec.crysl.core.model.UnresolvedSignature;
import br.unb.cic.rvsec.crysl.core.model.Version;
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
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Stream;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

/**
 * M0 over the two crypto corpora as they stand in the working tree.
 *
 * <p><strong>Where the numbers are anchored.</strong> The targets of this group were pinned at
 * {@code 5fbe8173}, which is an ancestor of the commit these tests run at: {@code 5bc5c893} rewrote
 * the {@code Arrays.asList(...)} value lists of 13 of the 24 {@code jca_android} specifications
 * while leaving every {@code ere}/{@code fsm} formula byte-identical. Everything M0 measures is
 * derived from the order, the handlers, the parameter binding or the presence of an
 * {@code addError}, and none of those moved — which is why the two pinned counts reproduce here.
 * A future disagreement is a finding about the corpus, and the counting rule is asserted beside
 * each number so the disagreement can be attributed rather than argued.
 *
 * <p>These tests live in the {@code -crysl} module because they need the MOP lifter and this is the
 * module that has both it and the model on its classpath. Only the two that read {@code android.jar}
 * carry {@link OracleCorpus#TAG}; the rest run in CI.
 */
class M0VitalityTest {

    private static final String ANDROID = "jca_android";
    private static final String JCA = "jca";

    /** The directory holding the corpora, in the sibling module's working tree. */
    private static final Path CORPORA =
            Paths.get("..", "..", "rvsec-mop", "src", "main", "resources").normalize();

    /**
     * One lift and the M0 inputs it hands down.
     *
     * <p>Nothing is assembled here any more: {@code MopLift.monitorFacts} is the production route,
     * and the only thing this test still supplies is the textual absorption scan, which is the
     * caller's by design because it does not go through the parser at all.
     */
    private record Read(MopLift lift, MonitorFacts facts) {
    }

    private static Read read(String corpus, Path path) throws LiftFailure {
        MopLift lift = new MopLifter().read(path, version(corpus));
        return new Read(lift, lift.monitorFacts(MisuseAbsorption.scan(path)));
    }

    private static Read read(String corpus, String name) throws LiftFailure {
        return read(corpus, CORPORA.resolve(corpus).resolve(name));
    }

    /**
     * The {@code .mop} files of one corpus, sorted, so that a run is diffable against the last.
     *
     * <p>The corpus is read and never written (INV-CONF-12).
     */
    private static List<Path> filesOf(String corpus) {
        try (Stream<Path> entries = Files.list(CORPORA.resolve(corpus))) {
            return entries.filter(p -> p.getFileName().toString().endsWith(".mop")).sorted()
                    .toList();
        } catch (IOException e) {
            throw new UncheckedIOException("cannot list corpus " + corpus, e);
        }
    }

    /**
     * How many {@code .mop} files the Android corpus holds right now.
     *
     * <p>Derived rather than pinned. This number moves whenever a file enters the directory and
     * carries no judgement of its own, so a literal here would only cost one build cycle per group
     * of new specifications to rediscover. Every pin below that names files, verdicts or witnesses
     * stays literal, because those move when a decision moves.
     */
    private static int corpusSize() {
        return filesOf(ANDROID).size();
    }

    /**
     * The stamp a lifted model carries in these tests.
     *
     * <p>The commit is a fixed literal rather than the working tree's HEAD: a test asserting
     * reproducible counts must itself be reproducible, and INV-CONF-01 only requires that a model
     * carry the stamp of the corpus it came from.
     */
    private static Version version(String corpus) {
        return new Version(corpus, new SourceStamp("rvsec", "working-tree", Instant.EPOCH));
    }

    /** M0 over one corpus, keyed by specification, in file order. */
    private static Map<String, M0Result> examine(String corpus, Optional<ApiIndex> index)
            throws LiftFailure {
        Map<String, M0Result> results = new LinkedHashMap<>();
        for (Path path : filesOf(corpus)) {
            Read read = read(corpus, path);
            M0Result result = M0Vitality.examine(read.lift().model(), read.lift().labelOrder(),
                    read.facts(), index);
            results.put(result.specification(), result);
        }
        return results;
    }

    private static M0Result examineOne(String corpus, String file) throws LiftFailure {
        Read read = read(corpus, file);
        return M0Vitality.examine(read.lift().model(), read.lift().labelOrder(), read.facts(),
                Optional.empty());
    }

    // ---------------------------------------------------------------- 6.6

    @Test
    @DisplayName("6.6: exactly five jca_android specifications do not index, and the rule says why")
    void test_five_specifications_do_not_index() throws LiftFailure {
        Map<String, M0Result> results = examine(ANDROID, Optional.empty());

        assertEquals(corpusSize(), results.size(),
                "every file of the corpus is examined: " + results.keySet());

        List<String> notIndexing = results.values().stream()
                .filter(result -> !result.indexes())
                .map(M0Result::specification)
                .sorted()
                .toList();

        // Five became three, and the two movements have nothing to do with each other.
        // CipherInputStreamSpec, CipherOutputStreamSpec and KeyStoreSpec left the list under
        // gh105, which gave each of them a declared parameter to index on; this pin was never
        // re-measured then, so it has been carrying a stale list since. KeySpec joined it at
        // gh109 task 2.14 for the original reason: Key.crysl's one event is
        // `keyMaterial = getEncoded()`, the specification declares no parameter of its own, and
        // it compiles to one monitor for the whole program.
        assertEquals(List.of("HMACParameterSpecSpec", "KeySpec", "RandomStringPassword"),
                notIndexing,
                "the three specifications that compile to one monitor for the whole program");

        // The counting rule as data rather than as prose: the two ways a specification fails to
        // index are different facts about different files, and a test that only counted five would
        // pass just as well if the rule had quietly become something else that also gives five.
        Map<String, String> binding = new LinkedHashMap<>();
        for (Path path : filesOf(ANDROID)) {
            Read read = read(ANDROID, path);
            if (read.facts().declaredParameters() == 0) {
                binding.put(path.getFileName().toString().replace(".mop", ""), "no parameter");
            } else if (read.facts().eventsBindingParameters() == 0) {
                binding.put(path.getFileName().toString().replace(".mop", ""),
                        "0/" + read.facts().declaredEvents());
            }
        }
        // Only the 0/N half of the rule has members now. The three files that were here under
        // "no parameter" all declare one since gh105, so the half that applies to them stopped
        // applying; KeySpec is 0/1 because it declares a parameter its one event does not bind --
        // `Key+.getEncoded()` binds the receiver and the rule's own object is the returned array.
        assertEquals(Map.of(
                        "HMACParameterSpecSpec", "0/1",
                        "KeySpec", "0/1",
                        "RandomStringPassword", "0/2"),
                binding,
                "0/N binding, plus specifications declared with no parameter — the two halves of "
                        + "the rule, each with the file it applies to");

        assertTrue(results.get("KeyStoreSpec").countingRule().contains("0/N binding"),
                "INV-CONF-02: the rule is emitted with the number, not kept in a test");
    }

    @Test
    @DisplayName("6.2: every M0 result says the indexing answer is a proxy")
    void test_the_indexing_answer_is_published_as_a_proxy() throws LiftFailure {
        Map<String, M0Result> results = examine(ANDROID, Optional.empty());

        for (M0Result result : results.values()) {
            assertTrue(result.notes().contains(M0Vitality.INDEXING_PROXY_CAVEAT),
                    result.specification() + " published an indexing answer without the caveat");
        }
        assertTrue(M0Vitality.INDEXING_PROXY_CAVEAT.contains("not the same measurement"),
                "the proxy and the oracle agree on these five today; that agreement is a measured "
                        + "coincidence of one corpus at one commit and not a proof of equivalence");
    }

    // ---------------------------------------------------------------- 6.7

    @Test
    @DisplayName("6.7: RandomStringPassword is refused, and M1-M4 never run for it")
    void test_the_specification_with_no_accusation_site_is_refused() throws LiftFailure {
        M0Result result = examineOne(ANDROID, "RandomStringPassword.mop");

        assertFalse(result.accusationSiteReachable(),
                "ere : vo gb, an empty @match and no @fail: no trace can make it accuse");
        assertTrue(result.refused());

        Silence refusal = result.silences().stream().filter(Silence::refusal).findFirst()
                .orElseThrow();
        assertEquals(SilenceCause.LIVE_WITHOUT_ACCUSATION_SITE, refusal.cause());
        assertTrue(refusal.statement().contains("an empty handler is the only way to state an "
                        + "automaton with nothing to report"),
                "the file's own header explains why it is written this way, and the reason M0 "
                        + "emits quotes it: " + refusal.statement());
        assertTrue(refusal.statement().contains("property of the file and not of any corpus"),
                refusal.statement());

        AtomicInteger downstream = new AtomicInteger();
        Pipeline.Outcome outcome = Pipeline.run(result, () -> {
            downstream.incrementAndGet();
            return List.of();
        });
        assertEquals(0, downstream.get(), "INV-CONF-09: the four verdicts are not produced");
        assertEquals(List.of(result), outcome.results(),
                "the typed refusal is the specification's whole result");
    }

    @Test
    @DisplayName("M0.2 finds a second specification with no accusation site: SecretKeySpec")
    void test_secret_key_spec_also_has_no_accusation_site() throws LiftFailure {
        for (String corpus : List.of(JCA, ANDROID)) {
            M0Result result = examineOne(corpus, "SecretKeySpec.mop");

            assertTrue(result.indexes(),
                    corpus + "/SecretKeySpec.mop binds its parameter, so it does index — which is "
                            + "why the behavioural run never looked at it: that run examined the "
                            + "five specifications that do not index");
            assertFalse(result.accusationSiteReachable(), corpus + "/SecretKeySpec.mop declares a "
                    + "non-empty @match that writes a predicate, no @fail, and no addError "
                    + "anywhere. Its own event comment says it: 'nothing here translates a "
                    + "constraint and nothing here accuses'");
            assertTrue(result.refused(), "a propagation bridge cannot accuse, so four verdicts "
                    + "about how faithfully it accuses would be four verdicts about something it "
                    + "does not do");
        }

        List<String> refused = examine(ANDROID, Optional.empty()).values().stream()
                .filter(M0Result::refused)
                .map(M0Result::specification)
                .sorted()
                .toList();
        assertEquals(List.of("KeySpec", "RandomStringPassword", "SecretKeySpec"), refused,
                "three of the 38, not one. SecretKeySpec.mop is one of the pairs D-06 names, so "
                        + "refusing it removes a pair from what M1-M4 report on, and that "
                        + "consequence is named here rather than discovered downstream. KeySpec.mop "
                        + "joins it at gh109 task 2.14 and for the same reason, by design: Key.crysl "
                        + "states no CONSTRAINTS and no FORBIDDEN, its ORDER GetEnc* refuses no "
                        + "sequence, and the specification exists to write preparedKeyMaterial and "
                        + "nothing else. It has no accusation site because the rule asks for none, "
                        + "so M1-M4 do not report on it -- which is the cost of transcribing a rule "
                        + "that only produces, and it is named here rather than found downstream");

        // What that costs, measured rather than estimated, at this working tree:
        //
        //   pairing (INV-CONF-11)   22, unchanged — pairing asks whether a rule is the oracle of a
        //                           specification, vitality asks whether the specification can
        //                           accuse. Conflating them would corrupt the calibration target.
        //   M1 verdicts             22 -> 21. The dropped verdict is declared=2, covered=1,
        //                           ruleOnly=1 (SecretKey.crysl's getEncoded and destroy).
        //   M3 clause aggregates    unchanged, all of them. SecretKey.crysl has no CONSTRAINTS
        //                           section at all, so it contributes 0 clauses under R1: the
        //                           denominator stays 80/119, implemented 31, absent 36, refused 13.
        //                           Only the number of M3 verdicts moves, 22 -> 21.
        //   M4 over jca_android     paired 23 -> 22 (M4's own simple-name approximation, which
        //                           reaches 23 where the rule of record reaches 22), present
        //                           50 -> 49, absent 53 -> 52, inverted 0 -> 0, rows 123 -> 120,
        //                           derivedRows 103 -> 101, derived fraction 0.837 -> 0.842.
        //
        // The M1/M3/M4 corpus tests still pin the ungated numbers, because they measure those
        // metrics over the pairing and not over the gate; the gate is Pipeline's, and the two
        // readings are kept apart on purpose.
    }

    // ---------------------------------------------------------------- 6.8

    @Test
    @Tag(OracleCorpus.TAG)
    @DisplayName("6.8: HMACParameterSpecSpec is live and its target class is absent")
    void test_an_absent_target_class_is_not_a_dead_monitor() throws LiftFailure, IOException {
        ApiIndex index = ApiIndex.index(OracleCorpus.androidJar());
        Read read = read(ANDROID, "HMACParameterSpecSpec.mop");
        M0Result result = M0Vitality.examine(read.lift().model(), read.lift().labelOrder(),
                read.facts(), Optional.of(index));

        List<UnresolvedSignature> unresolved = new ArrayList<>();
        for (Unknown refusal : result.refusals()) {
            assertTrue(refusal instanceof UnresolvedSignature,
                    "M0.3 emits UnresolvedSignature and nothing else: " + refusal);
            unresolved.add((UnresolvedSignature) refusal);
        }
        assertEquals(1, unresolved.size(), unresolved.toString());
        assertEquals("javax.xml.crypto.dsig.spec.HMACParameterSpec",
                unresolved.get(0).declaringClass());
        assertEquals(M0Vitality.MODE_ABSENT_CLASS, unresolved.get(0).mode());

        Silence silence = result.silences().stream()
                .filter(s -> s.cause() == SilenceCause.LIVE_TARGET_ABSENT)
                .findFirst().orElseThrow(() -> new AssertionError(result.silences().toString()));
        assertEquals(SilenceCause.Disposition.TYPED_UNKNOWN, silence.cause().disposition());
        assertTrue(silence.statement().contains("the monitor is live"),
                "the monitor accuses on the JSE, where the class exists; what is absent is the "
                        + "class, on the platform. Saying the monitor is dead would be a different "
                        + "finding about a different subject: " + silence.statement());
        assertTrue(silence.statement().contains("not a dead monitor"), silence.statement());
        assertFalse(result.refused(),
                "an absent target class does not stop M1-M4: the order, the events and the "
                        + "constraints are still worth comparing against the rule (design D-04)");
    }

    // ---------------------------------------------------------------- 6.9

    @Test
    @DisplayName("6.9: the two stream specifications are blind, not dead, and are not refused")
    void test_the_stream_specifications_are_a_divergence_and_not_a_refusal() throws LiftFailure {
        for (String specification : List.of("CipherInputStreamSpec", "CipherOutputStreamSpec")) {
            M0Result result = examineOne(ANDROID, specification + ".mop");

            assertFalse(result.refused(), specification + " was refused. Its ere is "
                    + "c1 (r1|r2)+ cl1; the word c1 r1 is a live prefix of an accepted word, and "
                    + "JavaMOP has no end-of-trace event, so the silence on the -unclosed traces "
                    + "is the IncompleteOperationError blind spot of the formalism");
            assertTrue(result.accusationSiteReachable(),
                    specification + " declares a @fail with a body: the negative control c1 cl1 "
                            + "does accuse, in both corpora");

            assertEquals(1, result.divergences().size(),
                    specification + " silences: " + result.silences());
            assertEquals(SilenceCause.LIVE_BLIND_TO_END_OF_TRACE,
                    result.divergences().get(0).cause());
            assertEquals(SilenceCause.Disposition.DIVERGENCE_RECORD,
                    result.divergences().get(0).cause().disposition(),
                    "it belongs in divergence_record.csv, not in a refusal: it is a property of "
                            + "JavaMOP and not a defect of the file");
        }
    }

    // ---------------------------------------------------------------- 6.10

    @Test
    @DisplayName("6.10: the AST checker catches what parser, generator and javac all pass")
    void test_the_ast_checker_catches_what_the_pipeline_passes() throws LiftFailure {
        M0Result gcm = examineOne(JCA, "GCMParameterSpecSpec.mop");
        assertTrue(gcm.astViolations().stream()
                        .anyMatch(v -> v.contains("duplicate event identifier 'c1'")),
                "two event declarations share the identifier c1: " + gcm.astViolations());
        assertTrue(gcm.astViolations().stream()
                        .anyMatch(v -> v.contains("the formula names 'c2'")),
                "ere : c1 | c2, and no event declares c2: " + gcm.astViolations());

        M0Result secretKeySpec = examineOne(JCA, "SecretKeySpecSpec.mop");
        assertTrue(secretKeySpec.astViolations().stream()
                        .anyMatch(v -> v.contains("event 'c3' is declared and absent")),
                secretKeySpec.astViolations().toString());
        assertTrue(secretKeySpec.astViolations().stream()
                        .anyMatch(v -> v.contains("event 'c4' is declared and absent")),
                "four events are declared and the ere admits two; the file also carries an "
                        + "unbalanced parenthesis in c1's condition and parses anyway: "
                        + secretKeySpec.astViolations());

        for (M0Result result : List.of(gcm, secretKeySpec)) {
            assertTrue(result.notes().contains(M0Vitality.AST_CHECKER_CAVEAT),
                    result.specification() + " reported violations without the note that says "
                            + "where they were found: " + result.notes());
        }
        assertTrue(M0Vitality.AST_CHECKER_CAVEAT.contains("compile with zero errors"),
                "both files parse, generate a monitor and compile with zero errors, so neither "
                        + "'it parsed' nor 'it compiled' is an oracle of sanity");
    }

    // ---------------------------------------------------------------- 6.11

    @Test
    @DisplayName("6.11: 18 of 24 jca_android and 15 of 23 jca absorb misuse, under the stated rule")
    void test_the_absorbs_misuse_census() throws LiftFailure {
        Map<String, M0Result> android = examine(ANDROID, Optional.empty());
        Map<String, M0Result> jca = examine(JCA, Optional.empty());

        List<String> androidAbsorbing = android.values().stream()
                .filter(result -> result.absorption().absorbs())
                .map(M0Result::specification)
                .sorted()
                .toList();
        List<String> jcaAbsorbing = jca.values().stream()
                .filter(result -> result.absorption().absorbs())
                .map(M0Result::specification)
                .sorted()
                .toList();

        assertEquals(corpusSize(), android.size());
        assertEquals(23, jca.size());
        // 18 -> 32 at gh109 group G2: every one of the fourteen producer specifications
        // absorbs its own misuse, which is what a transcribed value clause is -- the accusation
        // is raised on the branch the clause rejects, inside the event, and no other
        // specification of the set is asked to notice. 32 -> 39 at group G3: all seven medium
        // specifications absorb too, which is not a given -- `CertificateFactorySpec` absorbs on
        // its type and encoding clauses, and the two digest streams on a read length and on a
        // FORBIDDEN call -- so the census says the group kept the shape rather than that it kept
        // the count.
        assertEquals(39, androidAbsorbing.size(), "jca_android absorbing: " + androidAbsorbing);
        assertEquals(15, jcaAbsorbing.size(), "jca absorbing: " + jcaAbsorbing);

        // The lists, not only the totals: the independent probe
        // (docs/handoff/20260824_arnes_adjudicacao/scripts/absorve.py) prints these same names, and
        // two routes agreeing on a count while disagreeing on which files it is made of would be a
        // coincidence read as a confirmation.
        assertEquals(List.of("AlgorithmParameterGeneratorSpec", "AlgorithmParametersSpec",
                        "CertPathTrustManagerParametersSpec", "CertificateFactorySpec",
                        "CipherInputStreamSpec",
                        "CipherOutputStreamSpec", "CipherSpec", "DHGenParameterSpecSpec",
                        "DHParameterSpecSpec", "DSAParameterSpecSpec",
                        "DigestInputStreamSpec", "DigestOutputStreamSpec",
                        "ECGenParameterSpecSpec",
                        "GCMParameterSpecSpec", "IvChainJunction", "IvParameterSpec",
                        "KeyFactorySpec", "KeyGeneratorSpec", "KeyManagerFactorySpec",
                        "KeyPairGeneratorSpec",
                        "KeyPairSpec", "KeyStoreSpec", "MGF1ParameterSpecSpec", "MacSpec",
                        "MessageDigestSpec", "OAEPParameterSpecSpec", "PBEKeySpecSpec",
                        "PBEParameterSpecSpec", "PKIXBuilderParametersSpec", "PKIXParametersSpec",
                        "RSAKeyGenParameterSpecSpec", "SSLContextSpec", "SecretKeyFactorySpec",
                        "SecretKeySpecSpec",
                        "SecureRandomSpec", "SignatureSpec", "TrustAnchorSpec",
                        "TrustManagerFactorySpec", "X509EncodedKeySpecSpec"),
                androidAbsorbing);
        assertEquals(List.of("CipherSpec", "IvParameterSpec", "KeyGeneratorSpec",
                        "KeyManagerFactorySpec", "KeyPairGeneratorSpec", "KeyStoreSpec", "MacSpec",
                        "MessageDigestSpec", "PBEKeySpecSpec", "PBEParameterSpecSpec",
                        "SSLContextSpec", "SecretKeySpecSpec", "SecureRandomSpec", "SignatureSpec",
                        "TrustManagerFactorySpec"),
                jcaAbsorbing);

        assertEquals(MisuseAbsorption.RULE, android.get("CipherSpec").absorption().rule(),
                "INV-CONF-02: the rule is emitted beside the number");
        assertTrue(android.get("CipherSpec").countingRule().contains(MisuseAbsorption.RULE),
                "and it is in the result's own counting rule too");
    }

    // ---------------------------------------------------------------- M0.3 over the whole corpus

    @Test
    @Tag(OracleCorpus.TAG)
    @DisplayName("M0.3: exactly one class of jca_android is absent, and no bare name is left")
    void test_the_absent_target_classes_of_jca_android() throws LiftFailure, IOException {
        ApiIndex index = ApiIndex.index(OracleCorpus.androidJar());
        Map<String, M0Result> results = examine(ANDROID, Optional.of(index));

        Map<String, String> absentByClass = new LinkedHashMap<>();
        for (M0Result result : results.values()) {
            for (Unknown refusal : result.refusals()) {
                // refusals() carries both tags M0 emits. M0.3's are about signatures; M0.2's, the
                // UnreachableAccusationSite, is about the file having nowhere to report from, and
                // is asserted on its own below.
                if (refusal instanceof UnresolvedSignature unresolved) {
                    absentByClass.put(unresolved.declaringClass(), result.specification());
                }
            }
        }

        // Two buckets, because they are two findings about two different things. A fully-qualified
        // name the index does not have is a statement about the Android platform. A bare name is a
        // statement about this component: the pointcut expander did not resolve it, so the lookup
        // was never a platform question at all. Merging them would let a lift defect be published
        // as a platform absence, which is the shape of error M0 exists to prevent.
        Map<String, String> qualified = new LinkedHashMap<>();
        Map<String, String> unqualified = new LinkedHashMap<>();
        absentByClass.forEach((name, specification) -> {
            if (name.contains(".")) {
                qualified.put(name, specification);
            } else {
                unqualified.put(name, specification);
            }
        });

        assertEquals(Map.of("javax.xml.crypto.dsig.spec.HMACParameterSpec", "HMACParameterSpecSpec"),
                qualified,
                "measured against " + index.source() + ". Android carries no javax.xml.crypto at "
                        + "any level, and every other fully-qualified pointcut of the set names a "
                        + "class API 30 has. A second name here is either a new pointcut or a "
                        + "different API level, and the two must be told apart before it is "
                        + "believed");

        // This bucket held {String: RandomStringPassword} until mop.PointcutExpander was taught the
        // implicit java.lang import. The file writes call(public static String
        // String.valueOf(Object)) and imports no java.lang, so it lifted to declaringType "String",
        // missed the index, and was published as an unresolved signature — a defect of this
        // component wearing the costume of an absent Android class. With the import applied it
        // resolves to java.lang.String.valueOf(java.lang.Object), which API 30 does declare, so the
        // corpus now publishes one unresolved class instead of two and the remaining one is
        // genuinely the platform's.
        assertEquals(Map.of(), unqualified,
                "a bare type name means the expander did not qualify it, and a lookup on an "
                        + "unqualified name was never a platform question at all. The bucket is "
                        + "kept, and kept empty, because it is what makes the defect visible if it "
                        + "returns");

        Map<String, String> unreachable = new LinkedHashMap<>();
        for (M0Result result : results.values()) {
            for (Unknown refusal : result.refusals()) {
                if (refusal instanceof UnreachableAccusationSite site) {
                    unreachable.put(site.specification(), site.evidence());
                }
            }
        }
        assertEquals(List.of("KeySpec", "RandomStringPassword", "SecretKeySpec"),
                List.copyOf(new java.util.TreeSet<>(unreachable.keySet())),
                "INV-CONF-09: the three refusals of the set are emitted as typed Unknowns and not "
                        + "only as Silence rows, so they are counted in the same vocabulary as "
                        + "every other refusal of the report");
    }
}
