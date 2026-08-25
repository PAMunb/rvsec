package br.unb.cic.rvsec.crysl.crysl.cli;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.crysl.OracleCorpus;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.List;
import java.util.stream.Stream;
import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * The smoke run of {@code compare}: one specification against the upstream oracle, checked for the
 * three output formats <em>and their stamps</em>.
 *
 * <p>It is tagged {@code oracle-dependent} because two of its four inputs are outside this
 * checkout: the 49 CrySL rules are in the sibling {@code rvsec-cognicrypt} repository and
 * {@code android.jar} comes from {@code $ANDROID_HOME}. CI excludes the tag by name and says so;
 * locally the assumptions in {@link OracleCorpus} name the missing path rather than passing quietly.
 *
 * <p><b>What is asserted is not "a file appeared".</b> A file that appeared and carried no stamp
 * would be exactly the artefact this component exists to remove, so every assertion below is about
 * the header: both commits, both repositories, the pairing rule and the counting rule, in each of
 * the three renderings. The stamp is per corpus and not per run (D-17) — the {@code .mop} side and
 * the oracle are two git repositories — so a table that reported specification and rule side by
 * side under one commit would attribute an oracle-derived number to the repository that did not
 * produce it.
 *
 * <p>The two commits below are the states these corpora were measured at. They are asserted
 * verbatim in the output, which is what proves the arguments reached the header rather than being
 * parsed and dropped.
 */
@Tag(OracleCorpus.TAG)
class CompareSmokeIT {

    /** The specification corpus, in the sibling {@code rvsec-mop} module's working tree. */
    private static final Path CORPUS = Paths.get("..", "..", "rvsec-mop", "src", "main",
            "resources", "jca_android").normalize();

    /**
     * The alphabet map, in the sibling {@code rv-android} project (INV-CONF-12: read, never
     * written).
     */
    private static final Path ALPHABET_MAP = Paths.get("..", "..", "..", "rv-android", "data",
            "jca_android", "order_alphabet_map.csv").normalize();

    /** One specification: it pairs by declared type, M0 does not refuse it, and it has map rows. */
    private static final String SPECIFICATION = "MessageDigestSpec.mop";

    private static final String MOP_COMMIT = "6192b57a";
    private static final String ORACLE_COMMIT = "f2f4d3b";

    private final ByteArrayOutputStream out = new ByteArrayOutputStream();
    private final ByteArrayOutputStream err = new ByteArrayOutputStream();

    @Test
    @DisplayName("compare emits JSON, CSV and Markdown, each carrying both stamps and its rule")
    void test_the_three_formats_appear_with_their_stamps(@TempDir Path root) throws IOException {
        Assumptions.assumeTrue(Files.isReadable(ALPHABET_MAP),
                "the alphabet map is M2's only source of ε-erasure and lives in the sibling "
                        + "rv-android project at " + ALPHABET_MAP.toAbsolutePath());

        Path mopDir = Files.createDirectories(root.resolve("corpus"));
        Files.copy(CORPUS.resolve(SPECIFICATION), mopDir.resolve(SPECIFICATION),
                StandardCopyOption.REPLACE_EXISTING);
        Path outputDir = root.resolve("out");

        ExitCode code = ConformanceCli.run(new String[] {
            "compare",
            "--mop-dir", mopDir.toString(),
            "--corpus", "jca_android",
            "--commit", MOP_COMMIT,
            "--rules-dir", OracleCorpus.cryslRules().toString(),
            "--oracle-commit", ORACLE_COMMIT,
            "--alphabet", ALPHABET_MAP.toString(),
            "--android-jar", OracleCorpus.androidJar().toString(),
            "--out", outputDir.toString(),
        }, new PrintStream(out, true, StandardCharsets.UTF_8),
                new PrintStream(err, true, StandardCharsets.UTF_8));

        String stdout = out.toString(StandardCharsets.UTF_8);
        assertEquals(ExitCode.OK, code, "stderr was: " + err.toString(StandardCharsets.UTF_8));
        assertTrue(stdout.contains("1 pairs, by declared type"),
                "MessageDigestSpec declares MessageDigest and pairs with MessageDigest.crysl; if "
                        + "it did not pair, every assertion below would be about an empty table");
        assertTrue(stdout.contains("2 did not lift"),
                "OAEPParameterSpec.crysl and SSLEngine.crysl are the two upstream residuals (D-08) "
                        + "and the run reports them and still exits 0: a LiftFailure is a result, "
                        + "not a failure of the run, and making it non-zero would turn every run "
                        + "of the real oracle red until somebody stopped reporting them. Got: "
                        + stdout);

        String json = read(outputDir, "conformance_report.json");
        assertStamped(json, "the JSON report");
        assertTrue(json.contains("INV-CONF-11"),
                "the pairing rule is in the JSON header, because a number published under the "
                        + "older by-name pairing has to be re-stamped before it can be reused");
        // The metric identifier is a method on MetricResult and not a record component, so it is
        // not serialized; what proves a metric ran is a field only that metric's result has.
        assertTrue(json.contains("accusationSiteReachable"),
                "M0's verdict is in the report, and M0 is what runs first; got: " + head(json));
        assertTrue(json.contains("ruleOnly") && json.contains("normalizations")
                        && json.contains("denominator"),
                "and M1, M2 and M3 ran behind it, which is what the Pipeline gate allows for a "
                        + "specification M0 did not refuse; got: " + head(json));

        String predicateGraph = read(outputDir, "predicate_graph.csv");
        assertStamped(predicateGraph, "predicate_graph.csv");
        assertTrue(predicateGraph.startsWith("file,event,site_kind"),
                "the CSV is emitted in the committed schema, column for column");
        assertTrue(predicateGraph.contains("mop_commit,mop_read_at"),
                "and the stamp columns are appended after it, which is the only extension a "
                        + "csv.DictReader survives");

        String constraints = read(outputDir, "constraint_table.csv");
        assertStamped(constraints, "constraint_table.csv");
        assertTrue(constraints.contains("R1"),
                "M3's denominator names the rule it was counted under (INV-CONF-02)");

        String order = read(outputDir, "m2_order.md");
        assertStamped(order, "m2_order.md");
        assertTrue(order.contains("M2-decl"),
                "every M2 verdict is labelled as a claim about the declared automata (INV-CONF-13)");
        assertTrue(order.contains("N3 (acceptance narrowing) was NOT applied"),
                "and the counting rule says which normalization this command cannot apply, "
                        + "because that changes what the verdict means");

        String predicates = read(outputDir, "m4_predicates.md");
        assertStamped(predicates, "m4_predicates.md");
        assertTrue(predicates.contains("INV-CONF-15"),
                "the M4 aggregate carries the judgement caveat beside it");

        assertTrue(read(outputDir, "m1_events.md").contains("R-M1"),
                "and M1's coverage figure names R-M1");

        assertEquals(List.of(SPECIFICATION), namesIn(mopDir),
                "nothing was written beside what was read (INV-CONF-12)");
    }

    /**
     * Both stamps, in one rendering.
     *
     * <p>Repository and commit for each side, because either alone is unattributable: the commit
     * without the repository does not say which of the two repositories moved, and the repository
     * without the commit does not say which state of it was measured.
     */
    private static void assertStamped(String rendering, String what) {
        assertTrue(rendering.contains("jca_android"), what + " names the .mop corpus");
        assertTrue(rendering.contains("rvsec") && rendering.contains(MOP_COMMIT),
                what + " names the .mop repository and the commit --commit asserted");
        assertTrue(rendering.contains("rvsec-cognicrypt") && rendering.contains(ORACLE_COMMIT),
                what + " names the oracle repository and the commit --oracle-commit asserted; the "
                        + "stamp is per corpus and the input is two repositories (D-17)");
        assertTrue(rendering.contains("counting_rule") || rendering.contains("counting rule")
                        || rendering.contains("countingRule"),
                what + " names the rule its counts were taken under (INV-CONF-02)");
    }

    private static List<String> namesIn(Path directory) throws IOException {
        try (Stream<Path> entries = Files.list(directory)) {
            return entries.map(path -> path.getFileName().toString()).sorted().toList();
        }
    }

    private static String read(Path outputDir, String fileName) throws IOException {
        Path file = outputDir.resolve(fileName);
        assertTrue(Files.isRegularFile(file), fileName + " was not emitted under " + outputDir);
        return Files.readString(file, StandardCharsets.UTF_8);
    }

    private static String head(String text) {
        return text.length() <= 400 ? text : text.substring(0, 400);
    }
}
