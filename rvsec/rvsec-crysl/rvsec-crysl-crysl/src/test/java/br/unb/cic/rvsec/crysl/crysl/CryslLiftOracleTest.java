package br.unb.cic.rvsec.crysl.crysl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.LiftFailure;
import br.unb.cic.rvsec.crysl.core.model.Event;
import br.unb.cic.rvsec.crysl.core.model.Polarity;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import br.unb.cic.rvsec.crysl.core.model.SourceStamp;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import br.unb.cic.rvsec.crysl.core.model.Version;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.stream.Stream;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

/**
 * The lift, measured against the oracle it exists to read: the 49 upstream {@code .crysl} files of
 * {@code rvsec-cognicrypt}, as they stand on disk.
 *
 * <p>The number these tests defend is {@code ok = 47, fail = 2}. It is not a target that the
 * implementation may be tuned towards — if it ever stops reproducing, the disagreement is the
 * finding and the counting rule below is what a reader should check first. <strong>The counting
 * rule:</strong> one attempt per file whose name ends in {@code .crysl} directly under the oracle
 * directory, each with its own reader; a file counts as {@code ok} when {@code lift} returns a
 * model and as {@code fail} when it throws {@link LiftFailure}. No file is skipped, excluded or
 * pre-processed.
 */
@Tag(OracleCorpus.TAG)
class CryslLiftOracleTest {

    private static final int EXPECTED_FILES = 49;
    private static final int EXPECTED_OK = 47;
    private static final int EXPECTED_FAIL = 2;

    /**
     * Forty is enough. The failure this test hunts is a shared reader, and a shared reader gave
     * three distinct totals over forty random orders ({@code {29:3, 30:15, 31:22}}) — it would be
     * caught by a handful. The seed is fixed so that a failure is reproducible: a flaky
     * order-invariance test that cannot be replayed is worse than none.
     */
    private static final int SHUFFLES = 40;
    private static final long SEED = 20260824L;

    private static List<Path> rules;
    private static CryslLifter lifter;

    @BeforeAll
    static void locateOracle() throws IOException {
        Path directory = OracleCorpus.cryslRules();
        try (Stream<Path> entries = Files.list(directory)) {
            rules = entries.filter(path -> path.getFileName().toString().endsWith(".crysl"))
                    .sorted(Comparator.comparing(path -> path.getFileName().toString()))
                    .toList();
        }
        lifter = new CryslLifter();
    }

    @Test
    @DisplayName("the oracle directory holds exactly the 49 rules the numbers were measured over")
    void test_oracle_corpus_size() {
        assertEquals(EXPECTED_FILES, rules.size(),
                "the corpus moved. Every count in this class was measured over 49 files; a "
                        + "different size makes them incomparable rather than wrong. Found: "
                        + rules.stream().map(path -> path.getFileName().toString()).toList());
    }

    @Test
    @DisplayName("47 of 49 lift, un-normalized, with a fresh reader per rule")
    void test_upstream_corpus_lifts_47_of_49() throws IOException {
        CryslLifter.CorpusLift lift = lifter.liftCorpus(OracleCorpus.cryslRules(), OracleCorpus.version());

        assertEquals(EXPECTED_OK, lift.ok(), "expected 47 rules to lift; failures were "
                + lift.failures().stream().map(failure -> failure.file().getFileName().toString()).toList());
        assertEquals(EXPECTED_FAIL, lift.failed());
        assertEquals(EXPECTED_FILES, lift.ok() + lift.failed());
    }

    /**
     * The second number of the oracle, and the one every later metric is denominated in.
     *
     * <p><strong>Counting rule:</strong> one line per {@code CrySLMethod} of {@code rule.getEvents()}
     * over the 47 rules that lift — one model {@code Event} each, carrying one {@code Signature}.
     * Aggregates are not counted: they are names for sets of these methods, not methods. 215 is what
     * the pre-change probe measured over this corpus, with and without {@code android.jar} on the
     * parser's virtual classpath (D-09), and the two runs were byte-identical.
     */
    @Test
    @DisplayName("the 47 rules that lift carry 215 signature lines")
    void test_the_oracle_carries_215_signature_lines() throws IOException {
        CryslLifter.CorpusLift lift = lifter.liftCorpus(OracleCorpus.cryslRules(), OracleCorpus.version());

        int lines = lift.models().stream().mapToInt(model -> model.events().size()).sum();
        assertEquals(215, lines,
                "one line per CrySLMethod of the 47 rules that lift, aggregates excluded");
    }

    /**
     * The negated references of the oracle, which the model could not represent until polarity
     * became a field of {@code PredicateRef} (risk-register RISK-017).
     *
     * <p><strong>Counting rule:</strong> entries of {@code SpecModel.requires()} whose
     * {@code polarity()} is {@code NEGATED}, over the 47 rules that lift. Three, in two rules:
     * {@code Cipher.crysl:137} {@code !macced[_, plainText]} and {@code Mac.crysl:51} and
     * {@code :52} {@code !encrypted[...]}. They stay in {@code requires} — {@code REQUIRES !p}
     * demands the predicate be absent, whereas {@code NEGATES p} says the event withdraws it — so
     * the {@code negates} lists must not have grown to absorb them.
     */
    @Test
    @DisplayName("RISK-017: the oracle's 3 negated REQUIRES survive the lift, and stay in REQUIRES")
    void test_the_oracle_carries_three_negated_requirements() throws IOException {
        CryslLifter.CorpusLift lift = lifter.liftCorpus(OracleCorpus.cryslRules(), OracleCorpus.version());

        Map<String, Long> negatedByRule = new LinkedHashMap<>();
        int negatedInOtherSections = 0;
        for (SpecModel model : lift.models()) {
            long negated = model.requires().stream()
                    .filter(ref -> ref.polarity() == Polarity.NEGATED)
                    .count();
            if (negated > 0) {
                negatedByRule.put(model.type(), negated);
            }
            negatedInOtherSections += (int) Stream.concat(model.ensures().stream(),
                            model.negates().stream())
                    .filter(ref -> ref.polarity() == Polarity.NEGATED)
                    .count();
        }

        assertEquals(3L, negatedByRule.values().stream().mapToLong(Long::longValue).sum(),
                "three negated REQUIRES entries, in two rules; found " + negatedByRule);
        assertEquals(2, negatedByRule.size(), "the two rules are Cipher and Mac; found "
                + negatedByRule.keySet());
        assertEquals(0, negatedInOtherSections,
                "ENSURES and NEGATES entries are positive references: the facade reports "
                        + "isNegated() == true for every NEGATES entry, but that flag is the block "
                        + "it was read from and not a fact of the reference, and copying it would "
                        + "make every NEGATES pair read as inverted against a .mop remove(...)");
    }

    @Test
    @DisplayName("the two failures are OAEPParameterSpec:8 and SSLEngine:12, recorded not repaired")
    void test_the_two_upstream_failures_are_named_findings() throws IOException {
        CryslLifter.CorpusLift lift = lifter.liftCorpus(OracleCorpus.cryslRules(), OracleCorpus.version());

        Map<String, LiftFailure> byName = new LinkedHashMap<>();
        for (LiftFailure failure : lift.failures()) {
            byName.put(failure.file().getFileName().toString(), failure);
        }
        assertEquals(Set.of("OAEPParameterSpec.crysl", "SSLEngine.crysl"), byName.keySet());

        // OAEPParameterSpec declares an object named `alg`, which the grammar reserves. The facade's
        // own message says only "Skipping rule since it contains errors", which is why the
        // diagnostics are read from the EMF route and carried on the failure (D-19).
        assertDiagnostic(byName.get("OAEPParameterSpec.crysl"), 8,
                "mismatched input 'alg' expecting RULE_ID");
        // SSLEngine's ORDER references an event `cp1`; the file declares `ep1`.
        assertDiagnostic(byName.get("SSLEngine.crysl"), 12,
                "Couldn't resolve reference to Event 'cp1'");

        for (LiftFailure failure : lift.failures()) {
            assertTrue(failure.getCause() != null,
                    "a lift failure must carry the parser's own exception, not just a message");
        }
    }

    @Test
    @DisplayName("INV-CONF-12: reading the oracle does not write to it")
    void test_inv_conf_12_the_oracle_is_read_only() throws IOException {
        Path directory = OracleCorpus.cryslRules();
        Map<String, Long> before = fingerprint(directory);

        lifter.liftCorpus(directory, OracleCorpus.version());

        assertEquals(before, fingerprint(directory),
                "the lift changed the oracle directory. The two rules that do not parse are "
                        + "findings about upstream files and are never repaired in place.");
    }

    /**
     * INV-CONF-04. This is the only test that would notice a reintroduced shared reader, because a
     * shared reader still produces a plausible number — just not the same one twice.
     */
    @Test
    @DisplayName("INV-CONF-04: 47 under every one of 40 shuffled read orders")
    void test_inv_conf_04_order_invariance() {
        Random random = new Random(SEED);
        Version version = OracleCorpus.version();
        List<Integer> totals = new ArrayList<>();

        for (int round = 0; round < SHUFFLES; round++) {
            List<Path> order = new ArrayList<>(rules);
            Collections.shuffle(order, random);

            int ok = 0;
            for (Path rule : order) {
                try {
                    lifter.lift(rule, version);
                    ok++;
                } catch (LiftFailure expected) {
                    // Two of the 49 always fail; which two is what the next assertion pins down.
                }
            }
            totals.add(ok);
        }

        assertEquals(Set.of(EXPECTED_OK), Set.copyOf(totals),
                "the number of rules that lift depends on the order they are read in, which means a "
                        + "reader is being shared. Under a shared reader OBJECTS scope leaks in both "
                        + "directions - SecretKey.crysl read before Key.crysl breaks Key.crysl - and "
                        + "40 random orders gave {29:3, 30:15, 31:22}. Totals observed: " + totals);
    }

    @Test
    @DisplayName("the same rule lifts to the same signatures whatever was read before it")
    void test_a_rule_is_independent_of_its_predecessors() throws LiftFailure {
        Path key = rule("Key.crysl");
        Path secretKey = rule("SecretKey.crysl");
        Version version = OracleCorpus.version();

        Set<Signature> alone = signaturesOf(lifter.lift(key, version));
        lifter.lift(secretKey, version);
        Set<Signature> afterSecretKey = signaturesOf(lifter.lift(key, version));

        assertEquals(alone, afterSecretKey,
                "SecretKey.crysl read before Key.crysl is the measured witness of the scope leak: "
                        + "under a shared reader the second read of Key.crysl fails outright.");
    }

    /**
     * INV-CONF-01, from the lifter's side. The corpus identity is a parameter, so a model can be
     * attributed only to the corpus the caller says it came from.
     */
    @Test
    @DisplayName("INV-CONF-01: the corpus identity the caller supplies is the one the model carries")
    void test_inv_conf_01_corpus_identity_is_stamped_from_the_parameter() throws LiftFailure {
        Version upstream = OracleCorpus.version();
        Version other = new Version("some-other-corpus",
                new SourceStamp("elsewhere", "deadbeef", Instant.EPOCH));

        SpecModel fromUpstream = lifter.lift(rule("KeyGenerator.crysl"), upstream);
        SpecModel fromOther = lifter.lift(rule("KeyGenerator.crysl"), other);

        assertSame(upstream, fromUpstream.version());
        assertSame(other, fromOther.version());
        assertEquals("CrySL-Rules", fromUpstream.version().corpus());
        assertEquals("rvsec-cognicrypt", fromUpstream.version().source().repository());
        assertFalse(fromUpstream.version().equals(fromOther.version()),
                "two lifts of one file under two corpus identities must not be indistinguishable");
    }

    @Test
    @DisplayName("a model reaches the alphabet the comparison runs on")
    void test_key_generator_lifts_to_signatures_and_an_order_over_them() throws LiftFailure {
        SpecModel model = lifter.lift(rule("KeyGenerator.crysl"), OracleCorpus.version());

        assertEquals("javax.crypto.KeyGenerator", model.type());
        assertEquals(8, model.events().size(),
                "KeyGenerator.crysl declares g1, g2, i1..i5 and gk1 - eight methods; the aggregates "
                        + "Get, Init and GenKey are names, not events of the alphabet");
        assertTrue(signaturesOf(model).contains(new Signature("javax.crypto.KeyGenerator",
                        "generateKey", List.of(), "javax.crypto.SecretKey")),
                "lifted signatures: " + signaturesOf(model));
        assertTrue(model.order().transitions().stream()
                        .allMatch(transition -> transition.symbol() != null),
                "INV-CONF-03: the order automaton runs over signatures");
        assertEquals("javax.crypto.KeyGenerator", model.order().transitions().get(0)
                .symbol().declaringType());
        assertEquals(2, model.constraints().size());
        assertEquals(List.of("generatedKey"),
                model.ensures().stream().map(reference -> reference.name()).toList());
        assertEquals(List.of("randomized"),
                model.requires().stream().map(reference -> reference.name()).toList());
    }

    @Test
    @DisplayName("a directory that is not a corpus is an I/O failure, not an empty result")
    void test_a_missing_corpus_directory_is_not_silently_empty() {
        assertThrows(IOException.class,
                () -> lifter.liftCorpus(Path.of("no", "such", "corpus"), OracleCorpus.version()));
    }

    private static void assertDiagnostic(LiftFailure failure, int line, String fragment) {
        assertTrue(failure.errors().stream()
                        .anyMatch(error -> error.line() == line && error.message().contains(fragment)),
                "expected a diagnostic at line " + line + " containing \"" + fragment
                        + "\"; got " + failure.errors());
    }

    private static Set<Signature> signaturesOf(SpecModel model) {
        return model.events().stream()
                .map(Event::signatures)
                .flatMap(Set::stream)
                .collect(java.util.stream.Collectors.toUnmodifiableSet());
    }

    private static Path rule(String fileName) {
        return rules.stream()
                .filter(path -> path.getFileName().toString().equals(fileName))
                .findFirst()
                .orElseThrow(() -> new IllegalStateException(fileName + " is not in the oracle"));
    }

    /** Name and last-modified time of every file in the directory, as a cheap tamper check. */
    private static Map<String, Long> fingerprint(Path directory) throws IOException {
        Map<String, Long> stamps = new LinkedHashMap<>();
        try (Stream<Path> entries = Files.list(directory)) {
            for (Path entry : entries.sorted().toList()) {
                stamps.put(entry.getFileName().toString(), Files.getLastModifiedTime(entry).toMillis());
            }
        }
        return stamps;
    }
}
