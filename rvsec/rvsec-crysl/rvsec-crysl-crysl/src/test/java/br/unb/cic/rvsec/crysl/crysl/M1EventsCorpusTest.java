package br.unb.cic.rvsec.crysl.crysl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.LiftFailure;
import br.unb.cic.rvsec.crysl.core.metric.LabelAlignment;
import br.unb.cic.rvsec.crysl.core.metric.M1Events;
import br.unb.cic.rvsec.crysl.core.metric.M1Result;
import br.unb.cic.rvsec.crysl.core.metric.SpecRulePairing;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import br.unb.cic.rvsec.crysl.core.model.SourceStamp;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import br.unb.cic.rvsec.crysl.core.model.Version;
import br.unb.cic.rvsec.crysl.mop.MopLifter;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.stream.Stream;
import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

/**
 * M1 over the two corpora, end to end: {@code jca_android} against the upstream {@code CrySL-Rules}.
 *
 * <p>Both lifters have to be on one classpath for this, so it lives here rather than in
 * {@code rvsec-crysl-core}, and it is tagged oracle-dependent because the 49 rules are in the
 * sibling {@code rvsec-cognicrypt} repository that CI does not check out.
 *
 * <p>The pairing check does <strong>not</strong> re-derive its expectation from the component's own
 * rule. It reads the two declared skips out of
 * {@code rv-android/data/jca_android/order_alphabet_map.csv} — an artifact G-ORDER produced and this
 * component does not — and compares them with the specifications the pairing left over. A target
 * routed through the rule under test cannot fail and is not a check.
 */
@Tag(OracleCorpus.TAG)
class M1EventsCorpusTest {

    /** The specification corpus, read from the working tree of the sibling {@code rvsec-mop}. */
    private static final Path MOP_CORPUS = Paths.get("..", "..", "rvsec-mop", "src", "main",
            "resources", "jca_android").normalize();

    /**
     * The alphabet map, the independent route for the skip set.
     *
     * <p>It lives in the {@code rv-android} sibling project rather than in this reactor, which is
     * exactly what makes it independent: nothing in this component writes it, and its
     * {@code disposition} column was filled in by hand, per specification, with a written reason.
     */
    private static final Path ALPHABET_MAP = Paths.get("..", "..", "..", "rv-android", "data",
            "jca_android", "order_alphabet_map.csv").normalize();

    @Test
    @DisplayName("7.7 · MessageDigestSpec against MessageDigest.crysl: coverage and both lists")
    void test_message_digest_coverage_carries_both_differences() throws LiftFailure {
        SpecModel specification = specification("MessageDigestSpec.mop");
        SpecModel rule = rule("MessageDigest.crysl");

        M1Result result = M1Events.compare("MessageDigestSpec", specification,
                "MessageDigest", rule);

        assertEquals(9, result.declared(),
                "MessageDigest.crysl declares nine methods: three digest, two getInstance, four "
                        + "update; counting rule = distinct signatures over rule.getEvents()");
        assertEquals(8, result.covered());

        assertEquals(List.of("java.security.MessageDigest.getInstance(java.lang.String,AnyType)"),
                render(result.ruleOnly()),
                "the rule leaves the second argument of getInstance unbound and the specification "
                        + "writes the two overloads out instead, so the rule's open signature is "
                        + "covered by neither of them");
        assertEquals(List.of(
                        "java.security.MessageDigest.getInstance(java.lang.String,java.lang.String)",
                        "java.security.MessageDigest.getInstance(java.lang.String,"
                                + "java.security.Provider)"),
                render(result.mopOnly()),
                "and the same two overloads are calls the specification monitors under a name the "
                        + "rule never writes - the other half of the difference, which a coverage "
                        + "percentage on its own would hide entirely. Both sides now spell "
                        + "java.lang.String: the expander applies the implicit java.lang import, "
                        + "which is what the CrySL side has always done, and the difference this "
                        + "pair reports is therefore about the unbound second argument and nothing "
                        + "else. Neither declared (9) nor covered (8) moved when it was fixed");

        assertFalse(result.mopOnly().isEmpty(), "both lists are non-empty on this pair");
        assertFalse(result.ruleOnly().isEmpty(), "both lists are non-empty on this pair");
    }

    @Test
    @DisplayName("7.7 · the aggregate expansion update ↦ {u1..u4} appears in the alignment")
    void test_the_update_aggregate_expands_to_the_rules_four_update_symbols() throws LiftFailure {
        LabelAlignment alignment = M1Events.align("MessageDigestSpec",
                specification("MessageDigestSpec.mop"), "MessageDigest", rule("MessageDigest.crysl"));

        LabelAlignment.Entry update = alignment.entries().stream()
                .filter(entry -> entry.mopLabel().name().equals("update"))
                .findFirst()
                .orElseThrow(() -> new AssertionError("MessageDigestSpec.mop no longer declares "
                        + "the aggregate event 'update'"));

        // The rule writes u1..u4 as four one-line EVENTS entries; the facade does not hand the
        // declared names over, so the assertion is on the four signatures those four names stand
        // for. MessageDigest.crysl:20-23 reads u1: update(preInputByte); u2: update(preInput);
        // u3: update(preInput, preOffset, preLen); u4: update(preInputByteBuffer); with the types
        // taken from OBJECTS, that is exactly the set below.
        assertEquals(List.of(
                        "java.security.MessageDigest.update(byte)",
                        "java.security.MessageDigest.update(byte[])",
                        "java.security.MessageDigest.update(byte[],int,int)",
                        "java.security.MessageDigest.update(java.nio.ByteBuffer)"),
                render(update.sharedSignatures()).stream().sorted().toList(),
                "one pointcut, call(void MessageDigest.update(..)), standing for the rule's u1 to "
                        + "u4 - the aggregate expansion, and it comes out of the signature-set "
                        + "intersection with no name comparison anywhere in the derivation");
        assertEquals(4, update.ruleSymbols().size());

        assertEquals(List.of("u1", "u2", "u3", "u4"),
                declaredLabelledNames("MessageDigest.crysl").stream()
                        .filter(name -> name.startsWith("u"))
                        .toList(),
                "and the rule does call those four entries u1 to u4, read off the EVENTS section "
                        + "through the EMF route rather than assumed");
    }

    @Test
    @DisplayName("7.4 · no name heuristic reproduces the alignment: g3 ↦ gI, setSeed1 ↦ s2")
    void test_the_alignment_is_not_reachable_by_name() throws LiftFailure {
        LabelAlignment alignment = M1Events.align("SecureRandomSpec",
                specification("SecureRandomSpec.mop"), "SecureRandom", rule("SecureRandom.crysl"));

        assertEquals(List.of("java.security.SecureRandom.getInstanceStrong()"),
                render(signaturesOf(alignment, "g3")),
                "the specification's g3 is getInstanceStrong(), which the rule calls gI; a name "
                        + "heuristic sends g3 to the rule's g1 or g2, both getInstance(...)");
        assertEquals(List.of("java.security.SecureRandom.setSeed(long)"),
                render(signaturesOf(alignment, "setSeed1")),
                "and setSeed1 is setSeed(long), which the rule calls s2; the name suggests s1, "
                        + "and s1 is setSeed(byte[]) - the heuristic does not miss, it picks the "
                        + "wrong overload");
    }

    @Test
    @DisplayName("7.5/7.8 · the declared-type pairing leaves over exactly the map's declared skips")
    void test_pairing_leaves_over_the_two_specifications_the_alphabet_map_skips()
            throws LiftFailure, IOException {
        SpecRulePairing.Result pairing = pairTheCorpus();

        assertEquals(corpusSize(), pairing.pairs().size() + pairing.unpaired().size(),
                "every specification of the set is accounted for, paired or not");
        assertEquals(pairedSize(), pairing.pairs().size(),
                "all but the four unpaired pair by declared type; counting rule = "
                        + SpecRulePairing.PAIRING_RULE);
        assertEquals(pairedSize(), pairing.pairedRules(),
                "and as many distinct rules are claimed, because the pairing is injective - "
                        + "denominator every later aggregate is stated over");

        // Until gh109 the two sets were the same two names, and the assertion was equality.
        // They came apart when the coverage specifications landed, and group G4 widened the gap
        // with the second of the two lift failures: SSLEngineSpec.mop owns rows in the alphabet
        // map for the same reason OAEPParameterSpecSpec.mop does, and is unpaired here for the
        // same reason too. OAEPParameterSpecSpec.mop
        // owns rows in the alphabet map, because the map is derived by a reader that parses
        // OAEPParameterSpec.crysl without complaint, and is still unpaired here, because the
        // lift does not - the rule is one of the two lift failures (OAEPParameterSpec:8,
        // SSLEngine:12), so no rule of the *lifted* oracle declares its type. A specification
        // whose oracle does not parse is not a specification the map declared a skip for, and
        // collapsing the two would file a parser defect under a mapping decision. So the
        // containment is what holds: every map skip is unpaired, and what is unpaired beyond
        // them is named with its reason below.
        assertTrue(Set.copyOf(pairing.unpairedNames()).containsAll(alphabetMapSkips()),
                "every specification the alphabet map declares a skip for is one the pairing "
                        + "leaves over, read from an artifact this component does not produce");
        assertEquals(UNPAIRED, Set.copyOf(pairing.unpairedNames()),
                "and nothing else is left over");

        assertEquals(SpecRulePairing.Reason.NO_RULE_DECLARES_THE_TYPE,
                reasonFor(pairing, "OAEPParameterSpecSpec"),
                "not because the oracle states no rule about javax.crypto.spec.OAEPParameterSpec "
                        + "- it states one - but because that rule does not lift, so it is absent "
                        + "from the corpus the pairing reads. The consequence is that M1-M4 report "
                        + "nothing about this specification, and it is named here rather than "
                        + "discovered as a hole in a denominator");

        assertEquals(SpecRulePairing.Reason.NO_RULE_DECLARES_THE_TYPE,
                reasonFor(pairing, "SSLEngineSpec"),
                "the twin of the row above, and the other half of the same parser defect: the "
                        + "oracle states SSLEngine.crysl about javax.net.ssl.SSLEngine, and the "
                        + "rule does not lift because :12 binds EnableProtocol to an event cp1 "
                        + "the rule never declares. gh109 task 4.1 transcribes the evident intent "
                        + "and records the defect as an oracle-wart row; what cannot be "
                        + "transcribed away is the lift failure, so M1-M4 report nothing about "
                        + "this specification and it is named here rather than discovered as a "
                        + "hole in a denominator");

        assertEquals(SpecRulePairing.Reason.NO_RULE_DECLARES_THE_TYPE,
                reasonFor(pairing, "RandomStringPassword"),
                "RandomStringPassword is about java.lang.String and no rule of the oracle is");
        assertEquals(SpecRulePairing.Reason.RULE_CLAIMED_BY_ANOTHER_SPECIFICATION,
                reasonFor(pairing, "IvChainJunction"),
                "IvChainJunction declares Cipher c exactly as CipherSpec does, so the declared "
                        + "type alone reaches Cipher.crysl for both; the rule is the oracle of the "
                        + "one that covers more of it, and the junction translates no rule");
    }

    @Test
    @DisplayName("7.6 · SecretKeySpec.mop pairs with SecretKey.crysl, which the file name cannot")
    void test_the_pair_file_name_matching_gets_backwards() throws LiftFailure, IOException {
        SpecRulePairing.Result pairing = pairTheCorpus();

        assertEquals("SecretKey", ruleOf(pairing, "SecretKeySpec"),
                "SecretKeySpec.mop declares SecretKeySpec(SecretKey secretKey); by file name it "
                        + "would take SecretKeySpec.crysl, which is a different rule");
        assertEquals("SecretKeySpec", ruleOf(pairing, "SecretKeySpecSpec"),
                "and SecretKeySpecSpec.mop is the one SecretKeySpec.crysl is the oracle of");
    }

    @Test
    @DisplayName("the M1 corpus table names the oracle, the counting rule and the pairing rule")
    void test_the_corpus_table_carries_its_header() throws LiftFailure, IOException {
        SpecRulePairing.Result pairing = pairTheCorpus();
        List<M1Result> results = new ArrayList<>();
        for (SpecRulePairing.Pair pair : pairing.pairs()) {
            results.add(M1Events.compare(pair.specification().name(), pair.specification().model(),
                    pair.rule().name(), pair.rule().model()));
        }
        String markdown = M1Events.table(results, mopVersion(), OracleCorpus.version(),
                pairing.pairingRule()).markdown(List.of());

        assertEquals(pairedSize(), results.size());
        assertTrue(markdown.contains("rvsec-cognicrypt"), "the oracle repository (INV-CONF-11)");
        assertTrue(markdown.contains("INV-CONF-11"), "the pairing rule (INV-CONF-11)");
        assertTrue(markdown.contains("R-M1"), "the counting rule (INV-CONF-02)");
    }

    private static SpecRulePairing.Result pairTheCorpus() throws LiftFailure, IOException {
        List<SpecRulePairing.Candidate> specifications = new ArrayList<>();
        MopLifter lifter = new MopLifter();
        for (Path file : mopFiles()) {
            String name = file.getFileName().toString().replace(".mop", "");
            specifications.add(new SpecRulePairing.Candidate(name,
                    lifter.lift(file, mopVersion())));
        }
        assertEquals(corpusSize(), specifications.size(),
                "every .mop file of the jca_android set is a pairing candidate");

        List<SpecRulePairing.Candidate> rules = new ArrayList<>();
        CryslLifter.CorpusLift lift = new CryslLifter()
                .liftCorpus(OracleCorpus.cryslRules(), OracleCorpus.version());
        for (SpecModel model : lift.models()) {
            rules.add(new SpecRulePairing.Candidate(simpleName(model.type()), model));
        }
        assertEquals(47, rules.size(),
                "47 of the 49 upstream rules load; OAEPParameterSpec and SSLEngine are upstream "
                        + "defects recorded as findings (design D-08)");
        return SpecRulePairing.pair(specifications, rules);
    }

    /**
     * The specifications the alphabet map declares as G-ORDER skips.
     *
     * <p>The map states a skip as the <em>absence</em> of data rows, on purpose and with the reason
     * written in its header: {@code read_map} groups by specification and {@code build_automata}
     * skips on {@code if not rows}, so any row at all — even one with an empty {@code disposition} —
     * would take the file out of the skip. So the skips are the specifications of the set that own
     * no row of the {@code disposition} column, which is what this method computes.
     */
    private static Set<String> alphabetMapSkips() throws IOException {
        Assumptions.assumeTrue(Files.isReadable(ALPHABET_MAP),
                "the alphabet map is the independent route for the skip set and lives in the "
                        + "sibling rv-android project at " + ALPHABET_MAP.toAbsolutePath());
        Set<String> withRows = new LinkedHashSet<>();
        List<String> lines = Files.readAllLines(ALPHABET_MAP, StandardCharsets.UTF_8);
        boolean header = true;
        for (String line : lines) {
            if (line.startsWith("#") || line.isBlank()) {
                continue;
            }
            if (header) {
                assertTrue(line.contains("disposition"),
                        "the map's first data line is its header and it names a disposition column");
                header = false;
                continue;
            }
            withRows.add(line.substring(0, line.indexOf(',')));
        }
        Set<String> skips = new LinkedHashSet<>();
        for (Path file : mopFiles()) {
            String name = file.getFileName().toString().replace(".mop", "");
            if (!withRows.contains(name)) {
                skips.add(name);
            }
        }
        // Stated as the complement rather than as a literal, which makes it an assertion about
        // the map instead of about the corpus size: the row-owners and the skips partition the
        // set exactly when the map owns rows for no file outside it.
        assertEquals(corpusSize() - skips.size(), withRows.size(),
                "the map's row-owners are all files of the set: " + withRows);
        return skips;
    }

    /**
     * The specifications of the set that pair with no rule of the <em>lifted</em> oracle.
     *
     * <p>Declared rather than derived, and short on purpose: each of the four names is a
     * judgement, and the reason for it is asserted beside the name in
     * {@link #test_pairing_leaves_over_the_two_specifications_the_alphabet_map_skips()}. What
     * derives from the list is only arithmetic — the pairing denominator is the corpus minus these
     * four — and deriving it is what keeps a group of new specifications from moving half a dozen
     * literals that say nothing about the oracle.
     *
     * <p>Three until gh109 group G4 added {@code SSLEngineSpec}, whose rule is the second of the
     * two the lift rejects. A name enters this list only with a measured reason, and that one is a
     * parser failure over the pinned oracle, not a mapping decision.
     */
    private static final Set<String> UNPAIRED = Set.of("IvChainJunction", "OAEPParameterSpecSpec",
            "RandomStringPassword", "SSLEngineSpec");

    /** How many {@code .mop} files the set holds right now. Derived: it carries no judgement. */
    private static int corpusSize() {
        return mopFiles().size();
    }

    /** The denominator every M1 aggregate is stated over: the corpus minus {@link #UNPAIRED}. */
    private static int pairedSize() {
        return corpusSize() - UNPAIRED.size();
    }

    private static List<Path> mopFiles() {
        Assumptions.assumeTrue(Files.isDirectory(MOP_CORPUS),
                "the .mop corpus is read from the sibling rvsec-mop module at "
                        + MOP_CORPUS.toAbsolutePath());
        try (Stream<Path> entries = Files.list(MOP_CORPUS)) {
            return entries.filter(path -> path.getFileName().toString().endsWith(".mop"))
                    .sorted()
                    .toList();
        } catch (IOException e) {
            throw new UncheckedIOException("cannot list " + MOP_CORPUS, e);
        }
    }

    private static SpecRulePairing.Reason reasonFor(SpecRulePairing.Result pairing, String name) {
        return pairing.unpaired().stream()
                .filter(miss -> miss.specification().name().equals(name))
                .findFirst()
                .orElseThrow(() -> new AssertionError(name + " is paired, not left over"))
                .reason();
    }

    private static String ruleOf(SpecRulePairing.Result pairing, String name) {
        return pairing.pairs().stream()
                .filter(pair -> pair.specification().name().equals(name))
                .findFirst()
                .orElseThrow(() -> new AssertionError(name + " did not pair"))
                .rule().name();
    }

    private static List<Signature> signaturesOf(LabelAlignment alignment, String label) {
        return alignment.entries().stream()
                .filter(entry -> entry.mopLabel().name().equals(label))
                .findFirst()
                .orElseThrow(() -> new AssertionError("no entry for " + label))
                .sharedSignatures();
    }

    /** The {@code LABELED} names of a rule's {@code EVENTS}, in file order, via the EMF route. */
    private static List<String> declaredLabelledNames(String rule) {
        return CryslProvenance.read(OracleCorpus.cryslRules().resolve(rule)).eventNames().stream()
                .filter(name -> name.kind() == CryslProvenance.EventKind.LABELED)
                .map(CryslProvenance.EventName::name)
                .toList();
    }

    private static List<String> render(List<Signature> signatures) {
        return signatures.stream()
                .map(s -> s.declaringType() + "." + s.name()
                        + "(" + String.join(",", s.paramTypes()) + ")")
                .toList();
    }

    private static SpecModel specification(String file) throws LiftFailure {
        return new MopLifter().lift(MOP_CORPUS.resolve(file), mopVersion());
    }

    private static SpecModel rule(String file) throws LiftFailure {
        return new CryslLifter().lift(OracleCorpus.cryslRules().resolve(file),
                OracleCorpus.version());
    }

    private static String simpleName(String type) {
        int dot = type.lastIndexOf('.');
        return dot >= 0 ? type.substring(dot + 1) : type;
    }

    private static Version mopVersion() {
        return new Version("jca_android", new SourceStamp("rvsec", "working-tree", Instant.EPOCH));
    }
}
