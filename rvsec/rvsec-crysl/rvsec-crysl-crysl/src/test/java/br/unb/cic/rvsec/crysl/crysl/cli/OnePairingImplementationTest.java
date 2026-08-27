package br.unb.cic.rvsec.crysl.crysl.cli;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.crysl.OracleCorpus;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.stream.Stream;
import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * Task 12.0: every metric of one report compares the same specifications, because they all pair
 * through {@code SpecRulePairing}.
 *
 * <h2>Why this test exists</h2>
 *
 * <p>Until G12 there were two pairing implementations. G07 built {@code SpecRulePairing} — by
 * declared type, injective, tie broken on signature coverage — and reached 22 pairs of the 24
 * {@code jca_android} specifications. G09's M4 census kept a private map from a rule's simple name
 * to the rule and reached 23, because {@code IvChainJunction.mop} declares {@code Cipher} and a
 * non-injective map lets it claim {@code Cipher.crysl} beside {@code CipherSpec}. Each was
 * defensible on its own; together they made M1 and M4 report over different pair sets, and a report
 * whose two metrics disagree about which specifications were compared cannot be published.
 *
 * <p>The check is deliberately made over the <em>emitted</em> report rather than over the objects
 * in memory. What matters is the artifact a reader receives: if the M3 table names a specification
 * the M4 table does not, the disagreement is in the published files whatever the code did.
 */
@Tag(OracleCorpus.TAG)
class OnePairingImplementationTest {

    private static final Path CORPUS = Paths.get("..", "..", "rvsec-mop", "src", "main",
            "resources", "jca_android").normalize();

    private static final Path ALPHABET_MAP = Paths.get("..", "..", "..", "rv-android", "data",
            "jca_android", "order_alphabet_map.csv").normalize();

    private static final String MOP_COMMIT = "6192b57a";
    private static final String ORACLE_COMMIT = "f2f4d3b";

    /**
     * The specifications of the set that pair with no rule of the lifted oracle, and the paired
     * ones M0 refuses.
     *
     * <p>Both lists are declared, because every membership is a judgement argued elsewhere
     * ({@code M1EventsCorpusTest} for the first, {@code M2OrderCorpusTest} for the second). What
     * derives is the arithmetic below, so that a group of new specifications entering the corpus
     * directory moves no literal in this class.
     */
    private static final Set<String> UNPAIRED =
            Set.of("IvChainJunction", "OAEPParameterSpecSpec", "RandomStringPassword");

    private static final Set<String> M0_REFUSED = Set.of("SecretKeySpec", "KeySpec");

    /** How many {@code .mop} files the set holds right now. Derived: it carries no judgement. */
    private static int corpusSize() {
        try (Stream<Path> entries = Files.list(CORPUS)) {
            return (int) entries.filter(p -> p.getFileName().toString().endsWith(".mop")).count();
        } catch (IOException e) {
            throw new java.io.UncheckedIOException("cannot list " + CORPUS, e);
        }
    }

    @Test
    @DisplayName("12.0: M1, M2, M3 and M4 of one report name the same specifications")
    void test_every_metric_pairs_through_one_implementation(@TempDir Path root) throws IOException {
        Assumptions.assumeTrue(Files.isReadable(ALPHABET_MAP),
                "the alphabet map lives in the sibling rv-android project at "
                        + ALPHABET_MAP.toAbsolutePath());
        Path out = root.resolve("out");

        CompareArgs args = new CompareArgs();
        args.mopDir = CORPUS.toString();
        args.rulesDir = OracleCorpus.cryslRules().toString();
        args.alphabetMap = ALPHABET_MAP.toString();
        args.androidJar = OracleCorpus.androidJar().toString();
        args.corpus = "jca_android";
        args.commit = MOP_COMMIT;
        args.oracleCommit = ORACLE_COMMIT;
        args.outputDir = out.toString();

        CompareRun.Summary summary = CompareRun.run(args, CORPUS, OracleCorpus.cryslRules(),
                ALPHABET_MAP, OracleCorpus.androidJar());

        assertEquals(corpusSize() - UNPAIRED.size(), summary.pairs(),
                "the pairing of record, by declared type and injective (INV-CONF-11 plus the "
                        + "injectivity the corpus forces); the simple-name approximation that "
                        + "reached 23 no longer exists anywhere");
        assertEquals(summary.pairs() - M0_REFUSED.size(), summary.compared(),
                "M0 refuses SecretKeySpec and KeySpec, so the pairs yield that many fewer sets of "
                        + "M1-M4 verdicts. Pairing and vitality are different questions and "
                        + "conflating them would corrupt the pairing target");

        Set<String> m1 = firstColumnOfMarkdown(out.resolve(CompareRun.M1_MARKDOWN));
        Set<String> m2 = firstColumnOfMarkdown(out.resolve(CompareRun.M2_MARKDOWN));
        Set<String> m3 = firstColumnOfCsv(out.resolve("constraint_table.csv"));
        Set<String> m4 = firstColumnOfCsv(out.resolve("predicate_graph.csv"));

        assertFalse(m1.isEmpty(), "M1 published no specification at all");
        assertEquals(m1, m2, "M1 and M2 disagree about which specifications were compared");
        assertTrue(m1.containsAll(m4),
                "M4 names a specification no other metric compared, which is exactly the "
                        + "IvChainJunction case task 12.0 removed: " + minus(m4, m1));
        assertTrue(m1.containsAll(m3),
                "M3 names a specification no other metric compared: " + minus(m3, m1));

        // M3 and M4 are row tables, so a specification with nothing to say produces no row and
        // disappears from the file. That is not a pairing disagreement and must not be asserted as
        // one: measured here, the ones missing from the M3 table are exactly those whose paired
        // rule states no CONSTRAINTS clause at all - HMACParameterSpec.crysl and KeyPair.crysl are
        // 0 under R1 - so M3's denominator for them is 0 and there is no row to write. Naming them
        // is what keeps the assertion a measurement rather than a tolerance.
        //
        // Two became nine at gh109 group G2, and the seven that joined are the ones whose whole
        // content is a predicate: ECParameterSpec, KeyStoreBuilderParameters,
        // CertPathTrustManagerParameters, PKIXParameters, PKIXBuilderParameters, TrustAnchor and
        // X509EncodedKeySpec state REQUIRES and ENSURES and no CONSTRAINTS at all. They are absent
        // from M3 and present in M4, which is where a rule with nothing to constrain and something
        // to produce belongs.
        assertEquals(Set.of("CertPathTrustManagerParametersSpec", "ECParameterSpecSpec",
                        "HMACParameterSpecSpec", "KeyPairSpec", "KeyStoreBuilderParametersSpec",
                        "PKIXBuilderParametersSpec", "PKIXParametersSpec", "TrustAnchorSpec",
                        "X509EncodedKeySpecSpec"), minus(m1, m3),
                "the only specifications M1 compares and the M3 table omits are those whose "
                        + "upstream rule has an empty CONSTRAINTS section, so M3 has no clause to "
                        + "write a row about");
        assertFalse(m1.contains("IvChainJunction"),
                "the junction pairs with nothing: its ere accepts every sequence of its own "
                        + "events, so comparing it against Cipher.crysl's ORDER would report an "
                        + "ordering defect against a file that states no ordering");
        assertFalse(m1.contains("RandomStringPassword"),
                "and String has no rule");
    }

    /** The first column of every data row of an emitted CSV, header and comments excluded. */
    private static Set<String> firstColumnOfCsv(Path file) throws IOException {
        Set<String> names = new LinkedHashSet<>();
        List<String> lines = Files.readAllLines(file, StandardCharsets.UTF_8);
        boolean past = false;
        for (String line : lines) {
            if (line.isBlank() || line.startsWith("#")) {
                continue;
            }
            if (!past) {
                past = true;
                continue;
            }
            names.add(line.split(",", -1)[0].trim());
        }
        return names;
    }

    /**
     * The first cell of every table row of an emitted Markdown report.
     *
     * <p>The separator row and the header row are skipped by shape rather than by position: a
     * report gains sections over time and a positional reader would silently start counting the
     * wrong table.
     */
    private static Set<String> firstColumnOfMarkdown(Path file) throws IOException {
        Set<String> corpus = specificationNames();
        Set<String> names = new LinkedHashSet<>();
        try (Stream<String> lines = Files.lines(file, StandardCharsets.UTF_8)) {
            lines.filter(line -> line.startsWith("|")).forEach(line -> {
                String first = line.split("\\|", -1)[1].trim().replace("`", "");
                if (corpus.contains(first)) {
                    names.add(first);
                }
            });
        }
        return names;
    }

    private static Set<String> specificationNames() throws IOException {
        try (Stream<Path> entries = Files.list(CORPUS)) {
            return entries.map(path -> path.getFileName().toString())
                    .filter(name -> name.endsWith(".mop"))
                    .map(name -> name.substring(0, name.length() - ".mop".length()))
                    .collect(LinkedHashSet::new, Set::add, Set::addAll);
        }
    }

    private static Set<String> minus(Set<String> from, Set<String> against) {
        Set<String> difference = new LinkedHashSet<>(from);
        difference.removeAll(against);
        return difference;
    }
}
