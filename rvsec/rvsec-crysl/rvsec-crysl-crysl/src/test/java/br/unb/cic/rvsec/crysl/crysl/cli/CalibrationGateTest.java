package br.unb.cic.rvsec.crysl.crysl.cli;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.calibration.CalibrationReport;
import br.unb.cic.rvsec.crysl.core.calibration.CalibrationTarget;
import br.unb.cic.rvsec.crysl.core.calibration.CalibrationTargets;
import br.unb.cic.rvsec.crysl.core.calibration.MonitorIndexCensus;
import br.unb.cic.rvsec.crysl.core.calibration.PublishedMetric;
import br.unb.cic.rvsec.crysl.core.calibration.TargetOutcome;
import br.unb.cic.rvsec.crysl.crysl.OracleCorpus;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.Optional;
import java.util.stream.Stream;
import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

/**
 * The eight targets, each measured by the component and checked against the route that produced it.
 *
 * <h2>Why every test here is tagged, and how to run them</h2>
 *
 * <p>Six of the eight need the upstream oracle, which lives in {@code rvsec-cognicrypt} — a
 * different git repository the CI checkout does not have — so they carry {@link OracleCorpus#TAG}
 * and the CI workflow excludes them by name. That is the split G05 built, and the point of tagging
 * rather than skipping quietly is that the green CI prints is then honestly labelled.
 *
 * <p>{@link #test_target_8_route_from_the_regenerated_monitors} needs one more thing: a
 * {@code MultiSpec_1RuntimeMonitor.java} generated from the 24 {@code jca_android} specifications.
 * Nothing in this repository produces one, and generating it inside a test would put a
 * multi-minute toolchain run on the critical path of {@code mvn test}. The local setup, which
 * writes only to a scratch directory (INV-CONF-12):
 *
 * <pre>
 *   SCRATCH=/tmp/gh106-monitors
 *   mkdir -p $SCRATCH/specs $SCRATCH/out
 *   cp $RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android/*.mop $SCRATCH/specs/
 *   cd rv-android &amp;&amp; uv run rv-monitor-generator generate \
 *       --specs-dir $SCRATCH/specs --output $SCRATCH/out
 *   export RVSEC_GENERATED_MONITOR=$SCRATCH/out/MultiSpec_1RuntimeMonitor.java
 * </pre>
 *
 * <p>The specifications are copied into scratch first, and not generated in place, for a reason
 * that is easy to miss: {@code rv-monitor-generator} moves the {@code .rvm} files JavaMOP leaves
 * <em>beside the specs</em> into its output directory, so generating from the corpus directory
 * would write into the corpus. INV-CONF-12 forbids that, and a copy costs nothing.
 *
 * <h2>A disagreement here is a finding</h2>
 *
 * <p>If one of these ever goes red, the response is to measure both sides and adjudicate in
 * writing — never to adjust the component or relax an assertion until the numbers agree
 * (INV-CONF-14). The failure message already carries both values, both counting rules and the
 * named items, which is what makes that adjudication a morning's work rather than an archaeology
 * project.
 */
class CalibrationGateTest {

    /** The five {@code .mop} corpora, in the sibling module's working tree (INV-CONF-12). */
    private static final Path MOP_ROOT =
            Paths.get("..", "..", "rvsec-mop", "src", "main", "resources").normalize();

    /** The {@code rvsec} commit these runs read the {@code .mop} corpora at. */
    private static final String RUN_COMMIT = "6192b57a";

    /** The {@code rvsec-cognicrypt} commit these runs read the oracle at. */
    private static final String RUN_ORACLE_COMMIT = "f2f4d3b";

    /** Where the regenerated monitor is, when there is one. */
    private static final String MONITOR_ENV = "RVSEC_GENERATED_MONITOR";

    // ── 12.6: all eight, at their pinned per-repository stamps ────────────────────────────────

    @Test
    @Tag(OracleCorpus.TAG)
    @DisplayName("12.6: all eight targets are reproduced, each with its counting rule as data")
    void test_the_eight_targets_are_reproduced() {
        CalibrationReport report = gate();

        assertEquals(8, report.outcomes().size(), "the change declares eight targets");
        assertEquals(8, report.calibrationTargets(),
                "and all eight route through something the component does not produce, so none of "
                        + "them is a self-consistency check in disguise (D-18)");
        for (TargetOutcome outcome : report.outcomes()) {
            assertEquals(TargetOutcome.Verdict.REPRODUCED, outcome.verdict(),
                    "a disagreement is a finding to adjudicate by measuring both sides, never a "
                            + "signal to adjust the component or this assertion (INV-CONF-14).\n"
                            + outcome.describe());
            assertFalse(outcome.measurement().countingRule().isBlank(),
                    outcome.target().id() + " was measured without the component stating the rule "
                            + "it counted under, which makes the agreement unadjudicable");
        }
        assertTrue(report.reproduced());
    }

    @Test
    @Tag(OracleCorpus.TAG)
    @DisplayName("12.6: each target's value, item by item, so an agreement is not a coincidence")
    void test_each_target_agrees_on_its_items_too() {
        CalibrationReport report = gate();

        assertEquals("215 files, 215 ok, 0 fail", valueOf(report, "T1-mop-lift"));
        assertEquals("93 of 118", valueOf(report, "T2-generic-multiparameter"));
        assertEquals(List.of("1:25", "2:39", "3:28", "4:18", "5:7", "6:1"),
                itemsOf(report, "T2-generic-multiparameter"),
                "the histogram and not only the total: a total can coincide over a different "
                        + "distribution");
        assertEquals("0 of 24", valueOf(report, "T3-android-multiparameter"));
        assertEquals("47 of 49", valueOf(report, "T4-rules-that-load"));
        assertEquals(List.of("OAEPParameterSpec.crysl", "SSLEngine.crysl"),
                itemsOf(report, "T4-rules-that-load"),
                "the two upstream residuals, named; they are findings about those files and are "
                        + "never repaired in place");
        assertEquals("80 of 119", valueOf(report, "T5-m3-denominator"));
        assertEquals("22 of 24", valueOf(report, "T6-pairing"));
        assertEquals(List.of("IvChainJunction", "RandomStringPassword"),
                itemsOf(report, "T6-pairing"));
        assertEquals("5 of 22", valueOf(report, "T7-partial-binding"));
        assertEquals("5 of 24", valueOf(report, "T8-without-map-of-monitor"));
        assertEquals(List.of("CipherInputStreamSpec", "CipherOutputStreamSpec",
                        "HMACParameterSpecSpec", "KeyStoreSpec", "RandomStringPassword"),
                itemsOf(report, "T8-without-map-of-monitor"));
    }

    @Test
    @Tag(OracleCorpus.TAG)
    @DisplayName("12.4: with no mismatch, every metric a target vouches for publishes")
    void test_every_metric_publishes_when_the_gate_is_clean() {
        CalibrationReport report = gate();

        for (PublishedMetric metric : List.of(PublishedMetric.MOP_LIFT, PublishedMetric.ORACLE_LIFT,
                PublishedMetric.PAIRING, PublishedMetric.M0, PublishedMetric.M3)) {
            assertTrue(report.publishes(metric), metric + " is suppressed by a clean gate");
        }
        assertTrue(report.publicationSummary().contains("publishes"));
        assertFalse(report.publicationSummary().contains("SUPPRESSED"));
    }

    // ── 12.5: the two stamps, side by side ────────────────────────────────────────────────────

    @Test
    @Tag(OracleCorpus.TAG)
    @DisplayName("12.5: the report shows the route's stamp beside the run's, per corpus")
    void test_the_report_prints_both_stamps_per_corpus() {
        String table = gate().stampTable();

        assertTrue(table.contains(CalibrationTargets.RVSEC_PINNED) && table.contains(RUN_COMMIT),
                "the rvsec side moved between the pinned targets and this run, and the table has "
                        + "to show both: " + table);
        assertTrue(table.contains("they differ"),
                "the rvsec corpora were read at a descendant of the commit the routes were taken "
                        + "at, and that is exactly the case one column would have hidden: " + table);
        assertTrue(table.contains(CalibrationTargets.ORACLE_PINNED),
                "while the oracle did not move at all — which is why the stamp is per corpus and "
                        + "never one scalar per run (D-17): " + table);
        assertTrue(table.contains("CrySL-Rules (rvsec-cognicrypt)"),
                "and each row names the repository the corpus came from: " + table);
    }

    // ── 12.8-bis: target 8's route, from the regenerated monitors ─────────────────────────────

    @Test
    @Tag(OracleCorpus.TAG)
    @DisplayName("12.8-bis: the regenerated monitors give target 8's five, at this run's stamp")
    void test_target_8_route_from_the_regenerated_monitors() throws IOException {
        Path monitor = generatedMonitor();
        List<String> corpus = specificationNames();

        MonitorIndexCensus census = MonitorIndexCensus.read(Files.readString(monitor));
        List<String> without = MonitorIndexCensus.asFileNames(census.notIndexing(), corpus);
        CalibrationTarget target = CalibrationTargets.withoutMapOfMonitor();

        assertEquals(corpus.size(), census.declared().size(),
                "the generation covered every specification of the corpus; a monitor missing one "
                        + "would make the census smaller for a reason that has nothing to do with "
                        + "indexing");
        assertEquals(target.value(), without.size() + " of " + census.declared().size(),
                "the route re-taken at " + RUN_COMMIT + ", against the target pinned at "
                        + CalibrationTargets.RVSEC_PINNED + ". A difference here is a finding "
                        + "about the target, adjudicated in writing — the change's own note says "
                        + "not to assume a target carried across a corpus move");
        assertEquals(target.items(), without,
                "and the same five specifications, not merely the same count");
    }

    // ── fixtures ──────────────────────────────────────────────────────────────────────────────

    private static CalibrationReport gate() {
        CalibrateArgs args = new CalibrateArgs();
        args.mopRoot = MOP_ROOT.toString();
        args.rulesDir = OracleCorpus.cryslRules().toString();
        args.commit = RUN_COMMIT;
        args.oracleCommit = RUN_ORACLE_COMMIT;
        return CalibrateRun.run(args, MOP_ROOT, OracleCorpus.cryslRules(), null).report();
    }

    private static String valueOf(CalibrationReport report, String id) {
        return outcome(report, id).measurement().value();
    }

    private static List<String> itemsOf(CalibrationReport report, String id) {
        return outcome(report, id).measurement().items();
    }

    private static TargetOutcome outcome(CalibrationReport report, String id) {
        return report.outcomes().stream()
                .filter(candidate -> candidate.target().id().equals(id))
                .findFirst()
                .orElseThrow(() -> new AssertionError("no outcome for " + id));
    }

    /** The generated monitor, or a skip that says exactly how to produce one. */
    private static Path generatedMonitor() {
        String value = System.getenv(MONITOR_ENV);
        Optional<Path> located = value == null || value.isBlank()
                ? Optional.empty()
                : Optional.of(Paths.get(value)).filter(Files::isReadable);
        Assumptions.assumeTrue(located.isPresent(),
                "no regenerated monitor was supplied. Target 8's route is the generated "
                        + "MultiSpec_1RuntimeMonitor.java, which nothing in this repository "
                        + "produces: run rv-monitor-generator over a scratch copy of the 24 "
                        + "jca_android specifications and point " + MONITOR_ENV + " at the result. "
                        + "The class javadoc carries the four commands. " + MONITOR_ENV
                        + " is currently " + value);
        return located.get();
    }

    private static List<String> specificationNames() throws IOException {
        try (Stream<Path> entries = Files.list(MOP_ROOT.resolve("jca_android"))) {
            return entries.map(path -> path.getFileName().toString())
                    .filter(name -> name.endsWith(".mop"))
                    .map(name -> name.substring(0, name.length() - ".mop".length()))
                    .sorted()
                    .toList();
        }
    }
}
