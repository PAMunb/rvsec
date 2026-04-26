package br.unb.cic.rv.validator;

import org.apache.commons.math3.stat.inference.WilcoxonSignedRankTest;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Random;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.concurrent.TimeUnit;

/**
 * Layer-4 batch aggregator. Splits into a pure-data analyzer and a thin-IO
 * orchestration mode so the gate logic is fully unit-testable while the
 * actual {@code docker compose run} fan-out stays a thin shell over the
 * operator's environment.
 *
 * <h2>Pure-data analyzer ({@link #analyze})</h2>
 * Loads a {@code summary.csv} per variant ({@code ajc}, {@code dexlib2}),
 * pairs rows by {@code (apk, rep, tool)}, then runs the pre-registered
 * Wilcoxon signed-rank Two One-Sided Tests (TOST) per
 * {@code layer4-thresholds.yaml}:
 *
 * <ul>
 *   <li><b>Lower-bound test</b> — H0: {@code median(diff) <= -delta}.
 *       Reject (i.e. {@code p_lower < alpha}) means the dexlib2 pipeline
 *       is <b>non-inferior</b> to ajc on {@code cov_method}.</li>
 *   <li><b>Upper-bound test</b> — H0: {@code median(diff) >= +delta}.
 *       Reject (i.e. {@code p_upper < alpha}) means dexlib2 is also not
 *       <b>more than {@code delta}</b> better; combined with the lower
 *       test, this declares <b>equivalence</b>.</li>
 * </ul>
 *
 * The gate passes iff non-inferiority holds AND equivalence holds AND the
 * recovery-rate (paired-keys / max(per-variant-keys)) clears
 * {@code gates.recovery_rate_min}.
 *
 * <h2>Scope (honest)</h2>
 * The original Layer-4 spec covers {@code cov_method}, {@code per_spec_f1}
 * and {@code per_spec_kappa} TOST. <b>Only {@code cov_method} is
 * implemented in this commit.</b> Per-spec F1/κ TOST require a
 * Layer-3-batch-mode CSV (one row per {@code (apk, rep, tool, spec)}) that
 * the current {@link TraceComparator} does not yet emit (it returns a
 * single aggregate {@link Report} per invocation). Per-spec analysis is a
 * documented future enhancement triggered by Layer 3 gaining a
 * {@code --batch-mode} CSV output. The
 * {@code metrics.scopeNote} field of the report records this explicitly.
 *
 * <h2>Thin-IO orchestrator ({@link #orchestrate})</h2>
 * Drives {@code docker compose run} for every (variant, tool, rep) cell,
 * concatenating per-cell summaries into one {@code <variant>/summary.csv}
 * under {@code outputDir}. Returns operational metadata as an
 * {@link OrchestrationReport}, not a {@link Report} — orchestration is
 * not itself a gate; the resulting summaries are then fed back through
 * {@link #analyze}.
 *
 * <p>Manual smoke for orchestrate mode:
 * <pre>{@code
 *   java -jar validator-cli.jar layer4 --orchestrate \
 *        --apks /path/to/JCA-400 \
 *        --output build/layer4-batch \
 *        --docker-compose rv-android/docker/docker-compose.jca400-aperv.yml \
 *        --report build/reports/layer4-orchestrate.json
 * }</pre>
 *
 * <h2>Statistical convention used here</h2>
 * Apache Commons Math 3's {@code WilcoxonSignedRankTest.wilcoxonSignedRankTest(x, y, exact)}
 * returns a <b>two-sided</b> p-value. To obtain a one-sided p-value we
 * halve the two-sided value AND verify the median direction matches the
 * alternative hypothesis; otherwise the one-sided p-value is
 * {@code 1.0 - p_two_sided / 2}. See
 * {@link #oneSidedPValueGreaterThan} and
 * {@link #oneSidedPValueLessThan}.
 *
 * <h2>Reproducibility</h2>
 * The 90% confidence interval for {@code median(diff)} is computed by
 * bootstrap resampling (1000 iterations) using {@link Random} seeded with
 * {@link #BOOTSTRAP_SEED} (42), so the CI bounds are reproducible across
 * machines.
 */
public final class BatchValidator {

    public static final String LAYER_NAME = "layer4-batch-validator";

    /** Diagnostic cap on diff vector and unpaired key list emitted into the report. */
    private static final int MAX_DIAGNOSTIC = 50;

    /** Bootstrap iterations for the 90% CI on median(diff). */
    private static final int BOOTSTRAP_ITERATIONS = 1000;

    /** Seed for the bootstrap resampler — pinned for reproducibility. */
    private static final long BOOTSTRAP_SEED = 42L;

    /** Expected summary.csv header. */
    private static final String EXPECTED_HEADER =
            "apk,rep,timeout,tool,cov_act,cov_method,cov_rv_method,errors";

    private BatchValidator() {}

    // --- analyze (pure data) ------------------------------------------------

    /**
     * Pure-data analyzer. Reads {@code <ajcResultsDir>/summary.csv} and
     * {@code <dexlibResultsDir>/summary.csv}, pairs by
     * {@code (apk, rep, tool)}, runs Wilcoxon signed-rank TOST on the
     * paired diff vector for {@code cov_method}, and applies the
     * pre-registered gate.
     */
    public static Report analyze(Path ajcResultsDir, Path dexlibResultsDir,
                                 Path thresholdsYaml) throws IOException {
        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("thresholdsYaml", thresholdsYaml.toString());
        metrics.put("ajcResultsDir", ajcResultsDir.toString());
        metrics.put("dexlibResultsDir", dexlibResultsDir.toString());

        Thresholds th = parseThresholds(thresholdsYaml);
        metrics.put("alpha", th.alpha);

        Path ajcCsv = ajcResultsDir.resolve("summary.csv");
        Path dexCsv = dexlibResultsDir.resolve("summary.csv");
        if (!Files.isRegularFile(ajcCsv) || !Files.isRegularFile(dexCsv)) {
            metrics.put("ajcSummaryExists", Files.isRegularFile(ajcCsv));
            metrics.put("dexlibSummaryExists", Files.isRegularFile(dexCsv));
            return new Report(LAYER_NAME, false,
                    "summary.csv missing under one or both variant directories", metrics);
        }

        Map<String, SummaryRow> ajcRows = readSummary(ajcCsv);
        Map<String, SummaryRow> dexRows = readSummary(dexCsv);

        TreeSet<String> allKeys = new TreeSet<>();
        allKeys.addAll(ajcRows.keySet());
        allKeys.addAll(dexRows.keySet());

        TreeSet<String> pairedKeys = new TreeSet<>(ajcRows.keySet());
        pairedKeys.retainAll(dexRows.keySet());

        TreeSet<String> unpairedSet = new TreeSet<>(allKeys);
        unpairedSet.removeAll(pairedKeys);
        List<String> unpaired = new ArrayList<>();
        for (String k : unpairedSet) {
            if (unpaired.size() >= MAX_DIAGNOSTIC) break;
            String side = ajcRows.containsKey(k) ? " (missing in dexlib2)" : " (missing in ajc)";
            unpaired.add(k + side);
        }

        // Build paired diff vector for cov_method.
        double[] diffs = new double[pairedKeys.size()];
        int idx = 0;
        for (String k : pairedKeys) {
            double a = ajcRows.get(k).covMethod;
            double d = dexRows.get(k).covMethod;
            diffs[idx++] = d - a;
        }

        double recoveryRate = 0.0;
        int maxKeys = Math.max(ajcRows.size(), dexRows.size());
        if (maxKeys > 0) {
            recoveryRate = (double) pairedKeys.size() / (double) maxKeys;
        }
        boolean recoveryRatePassed = recoveryRate >= th.recoveryRateMin;

        // TOST on cov_method.
        double delta = th.deltaCovMethod;
        double pLower;
        double pUpper;
        double medianDiff;
        double ciLower;
        double ciUpper;
        boolean nonInferiorityPassed;
        boolean equivalencePassed;

        if (diffs.length == 0) {
            pLower = 1.0;
            pUpper = 1.0;
            medianDiff = 0.0;
            ciLower = 0.0;
            ciUpper = 0.0;
            nonInferiorityPassed = false;
            equivalencePassed = false;
        } else {
            // Lower-bound TOST: H1: median(diff) > -delta. Shift diffs by +delta;
            // alternative becomes "shifted median > 0" => greater-than zero one-sided test.
            double[] shiftedLower = shift(diffs, +delta);
            pLower = oneSidedPValueGreaterThan(shiftedLower);
            // Upper-bound TOST: H1: median(diff) < +delta. Shift diffs by -delta;
            // alternative becomes "shifted median < 0" => less-than zero one-sided test.
            double[] shiftedUpper = shift(diffs, -delta);
            pUpper = oneSidedPValueLessThan(shiftedUpper);

            medianDiff = median(diffs);
            double[] ci = bootstrapMedianCi90(diffs, BOOTSTRAP_ITERATIONS, BOOTSTRAP_SEED);
            ciLower = ci[0];
            ciUpper = ci[1];

            nonInferiorityPassed = pLower < th.alpha;
            equivalencePassed = (pLower < th.alpha) && (pUpper < th.alpha);
        }

        boolean passed = nonInferiorityPassed && equivalencePassed && recoveryRatePassed;

        // Truncated diff vector preview for the report.
        List<Double> diffPreview = new ArrayList<>();
        for (int i = 0; i < diffs.length && i < MAX_DIAGNOSTIC; i++) {
            diffPreview.add(round4(diffs[i]));
        }

        Map<String, Object> covMethod = new LinkedHashMap<>();
        covMethod.put("delta", round4(delta));
        covMethod.put("pairCount", diffs.length);
        covMethod.put("diffVector", diffPreview);
        covMethod.put("medianDiff", round4(medianDiff));
        covMethod.put("ci90Lower", round4(ciLower));
        covMethod.put("ci90Upper", round4(ciUpper));
        covMethod.put("pValueLower", round4(pLower));
        covMethod.put("pValueUpper", round4(pUpper));
        covMethod.put("nonInferiorityPassed", nonInferiorityPassed);
        covMethod.put("equivalencePassed", equivalencePassed);

        metrics.put("covMethod", covMethod);
        metrics.put("recoveryRate", round4(recoveryRate));
        metrics.put("recoveryRateMin", round4(th.recoveryRateMin));
        metrics.put("recoveryRatePassed", recoveryRatePassed);
        metrics.put("totalAjcKeys", ajcRows.size());
        metrics.put("totalDexlibKeys", dexRows.size());
        metrics.put("pairedKeys", pairedKeys.size());
        metrics.put("unpairedKeys", unpaired);
        metrics.put("scopeNote", "per-spec F1 and kappa TOST deferred — see Javadoc");

        String message = String.format(Locale.ROOT,
                "batch comparison: rec=%.2f, non_inf=%s, equiv=%s",
                recoveryRate,
                nonInferiorityPassed ? "pass" : "fail",
                equivalencePassed ? "pass" : "fail");
        return new Report(LAYER_NAME, passed, message, metrics);
    }

    // --- orchestrate (thin IO) ----------------------------------------------

    /**
     * Operator-only IO: runs {@code docker compose run} for every
     * {@code (variant, tool, rep)} cell, concatenating per-cell summaries
     * into one {@code <variant>/summary.csv} under {@code outputDir}.
     * <p>This method is NOT unit-tested — its correctness is verified by
     * the manual smoke documented in the class javadoc. Tests would
     * require a docker-in-docker setup that we explicitly do not pay for
     * (CLAUDE.md).
     */
    public static OrchestrationReport orchestrate(Path apksDir, Path outputDir,
                                                  BatchOrchestrationOptions opts) throws IOException {
        if (opts == null) opts = new BatchOrchestrationOptions();
        Files.createDirectories(outputDir);

        int totalCells = opts.variants.size() * opts.tools.size() * opts.reps;
        Map<String, String> failures = new LinkedHashMap<>();
        int succeeded = 0;

        for (String variant : opts.variants) {
            Path variantDir = Files.createDirectories(outputDir.resolve(variant));
            Path summary = variantDir.resolve("summary.csv");
            Files.writeString(summary, EXPECTED_HEADER + "\n");

            for (String tool : opts.tools) {
                for (int rep = 1; rep <= opts.reps; rep++) {
                    String cellKey = variant + "/" + tool + "/rep" + rep;
                    try {
                        int exit = runDockerCompose(opts, variant, tool, rep, apksDir, variantDir);
                        if (exit != 0) {
                            failures.put(cellKey, "docker compose exited with " + exit);
                        } else {
                            succeeded++;
                        }
                    } catch (IOException | InterruptedException e) {
                        if (e instanceof InterruptedException) Thread.currentThread().interrupt();
                        failures.put(cellKey, e.getClass().getSimpleName() + ": " + e.getMessage());
                    }
                }
            }
        }

        return new OrchestrationReport(outputDir, totalCells, succeeded, failures);
    }

    private static int runDockerCompose(BatchOrchestrationOptions opts,
                                        String variant, String tool, int rep,
                                        Path apksDir, Path variantDir)
            throws IOException, InterruptedException {
        List<String> cmd = new ArrayList<>();
        cmd.add("docker");
        cmd.add("compose");
        if (opts.dockerComposeFile != null) {
            cmd.add("-f");
            cmd.add(opts.dockerComposeFile.toString());
        }
        cmd.add("run");
        cmd.add("--rm");
        cmd.add("-e");
        cmd.add("RVSEC_VARIANT=" + variant);
        cmd.add("-e");
        cmd.add("RVSEC_TOOL=" + tool);
        cmd.add("-e");
        cmd.add("RVSEC_REP=" + rep);
        cmd.add("-e");
        cmd.add("RVSEC_TIMEOUT=" + opts.timeoutSeconds);
        cmd.add("-e");
        cmd.add("RVSEC_APKS=" + apksDir);
        cmd.add("-e");
        cmd.add("RVSEC_OUTPUT=" + variantDir);
        cmd.add("rvsec-batch");

        ProcessBuilder pb = new ProcessBuilder(cmd);
        pb.redirectErrorStream(true);
        Process p = pb.start();
        try (var in = p.getInputStream()) {
            in.transferTo(java.io.OutputStream.nullOutputStream());
        }
        if (!p.waitFor(opts.timeoutSeconds * 4L, TimeUnit.SECONDS)) {
            p.destroyForcibly();
            return -1;
        }
        return p.exitValue();
    }

    // --- thresholds parser --------------------------------------------------

    /**
     * Hand-rolled YAML parser scoped to the {@code layer4-thresholds.yaml}
     * schema actually committed under {@code validator/oracles/}. We only
     * consume {@code statistical_test.alpha},
     * {@code equivalence_bounds.cov_method.delta} and
     * {@code gates.recovery_rate_min}; everything else is informational
     * for the human reviewer and ignored here. Mirrors the parser pattern
     * established by {@link TraceComparator#parseOracle}.
     */
    static Thresholds parseThresholds(Path yaml) throws IOException {
        Thresholds out = new Thresholds();
        if (!Files.isRegularFile(yaml)) {
            throw new IOException("thresholds yaml not found: " + yaml);
        }
        List<String> lines = Files.readAllLines(yaml);

        // Section tracking: top-level key whose body is a block-style map.
        String section = null;
        // Sub-section under equivalence_bounds: e.g. "cov_method".
        String covSubsection = null;
        int sectionIndent = -1;

        for (String raw : lines) {
            String stripped = stripComment(raw);
            String trimmed = stripped.stripTrailing();
            if (trimmed.isBlank()) continue;
            int indent = leadingSpaces(stripped);
            String content = stripped.substring(indent);

            if (indent == 0) {
                // Top-level key.
                int colon = content.indexOf(':');
                if (colon < 0) continue;
                section = content.substring(0, colon).trim();
                sectionIndent = 0;
                covSubsection = null;
                continue;
            }

            // Inside a section.
            if (section == null) continue;
            String[] kv = splitKv(content);

            switch (section) {
                case "statistical_test" -> {
                    if (kv != null && "alpha".equals(kv[0])) {
                        out.alpha = parseDouble(kv[1], out.alpha);
                    }
                }
                case "equivalence_bounds" -> {
                    // Two indent levels: bound name (e.g. "cov_method:") then "delta: 0.02".
                    if (indent == sectionIndent + 2) {
                        // Bound name line, e.g. "  cov_method:".
                        if (kv != null) {
                            covSubsection = kv[0];
                        }
                    } else if (indent > sectionIndent + 2 && covSubsection != null) {
                        if (kv != null && "delta".equals(kv[0]) && "cov_method".equals(covSubsection)) {
                            out.deltaCovMethod = parseDouble(kv[1], out.deltaCovMethod);
                        }
                    }
                }
                case "gates" -> {
                    if (kv != null && "recovery_rate_min".equals(kv[0])) {
                        out.recoveryRateMin = parseDouble(kv[1], out.recoveryRateMin);
                    }
                }
                default -> {
                    // ignore
                }
            }
        }
        return out;
    }

    private static double parseDouble(String s, double fallback) {
        if (s == null) return fallback;
        String v = s.trim();
        // Strip trailing comments (already done by stripComment) and any quotes.
        if (v.length() >= 2 && (v.charAt(0) == '"' || v.charAt(0) == '\'')) {
            v = v.substring(1, v.length() - 1);
        }
        if (v.isEmpty()) return fallback;
        try {
            return Double.parseDouble(v);
        } catch (NumberFormatException e) {
            return fallback;
        }
    }

    // --- summary.csv reader -------------------------------------------------

    /**
     * Reads a {@code summary.csv} file and returns a map keyed by
     * {@code "apk|rep|tool"} (a stable, sortable key separator that does
     * not appear in any of the three columns). Header row is verified to
     * begin with {@link #EXPECTED_HEADER}; extra columns are tolerated.
     */
    static Map<String, SummaryRow> readSummary(Path csv) throws IOException {
        Map<String, SummaryRow> out = new TreeMap<>();
        try (BufferedReader r = new BufferedReader(
                new InputStreamReader(Files.newInputStream(csv), StandardCharsets.UTF_8))) {
            String header = r.readLine();
            if (header == null || !header.startsWith("apk,rep,timeout,tool,cov_act,cov_method")) {
                throw new IOException("unexpected summary.csv header in " + csv + ": " + header);
            }
            String line;
            while ((line = r.readLine()) != null) {
                if (line.isBlank()) continue;
                String[] parts = line.split(",", -1);
                if (parts.length < 7) continue;
                String apk = parts[0].trim();
                String rep = parts[1].trim();
                String tool = parts[3].trim();
                double covMethod = parseDouble(parts[5], 0.0);
                double covRvMethod = parseDouble(parts[6], 0.0);
                String key = apk + "|" + rep + "|" + tool;
                out.put(key, new SummaryRow(apk, rep, tool, covMethod, covRvMethod));
            }
        }
        return out;
    }

    // --- statistics ---------------------------------------------------------

    /**
     * Returns the one-sided p-value for {@code H1: median(x) > 0}. Uses
     * Apache Commons Math 3's two-sided Wilcoxon signed-rank test then
     * halves it (when the observed median agrees with the alternative) or
     * computes {@code 1 - p_two_sided / 2} otherwise. This is the
     * standard convention for converting a two-sided rank test to one
     * sided when an exact one-sided API is unavailable.
     */
    static double oneSidedPValueGreaterThan(double[] x) {
        return oneSidedPValue(x, true);
    }

    /** Symmetric of {@link #oneSidedPValueGreaterThan} for {@code H1: median(x) < 0}. */
    static double oneSidedPValueLessThan(double[] x) {
        return oneSidedPValue(x, false);
    }

    private static double oneSidedPValue(double[] x, boolean alternativeGreater) {
        if (x.length == 0) return 1.0;
        // Wilcoxon signed-rank test against zero: pass paired (x, zero) and ask for two-sided.
        // Apache Commons Math 3's WilcoxonSignedRankTest works on paired samples; supply
        // the diff vs. a zero vector.
        double[] zero = new double[x.length];
        WilcoxonSignedRankTest test = new WilcoxonSignedRankTest();
        // Fast-fail edge case: all values equal -> the test is degenerate.
        boolean allZero = true;
        for (double v : x) {
            if (v != 0.0) { allZero = false; break; }
        }
        if (allZero) {
            // All diffs are zero: no evidence either way; p=1.0 means "do not reject H0".
            return 1.0;
        }
        double pTwoSided;
        try {
            // Asymptotic normal approximation; exact mode would require no ties / small n,
            // and our pair counts are always > 25 in practice. False = asymptotic.
            pTwoSided = test.wilcoxonSignedRankTest(x, zero, false);
        } catch (Exception e) {
            // Defensive: any internal exception => non-informative p-value.
            return 1.0;
        }
        double median = median(x);
        boolean medianAgreesWithAlternative = alternativeGreater ? (median > 0.0) : (median < 0.0);
        if (medianAgreesWithAlternative) {
            return pTwoSided / 2.0;
        } else {
            return 1.0 - pTwoSided / 2.0;
        }
    }

    static double median(double[] x) {
        if (x.length == 0) return 0.0;
        double[] copy = x.clone();
        Arrays.sort(copy);
        int n = copy.length;
        if ((n & 1) == 1) return copy[n / 2];
        return (copy[n / 2 - 1] + copy[n / 2]) / 2.0;
    }

    /**
     * Returns {@code [ci90Lower, ci90Upper]} for {@code median(x)} via
     * percentile bootstrap with the supplied seed.
     */
    static double[] bootstrapMedianCi90(double[] x, int iters, long seed) {
        if (x.length == 0) return new double[]{0.0, 0.0};
        Random rng = new Random(seed);
        double[] medians = new double[iters];
        double[] sample = new double[x.length];
        for (int it = 0; it < iters; it++) {
            for (int i = 0; i < x.length; i++) {
                sample[i] = x[rng.nextInt(x.length)];
            }
            medians[it] = median(sample);
        }
        Arrays.sort(medians);
        int loIdx = (int) Math.floor(0.05 * (iters - 1));
        int hiIdx = (int) Math.ceil(0.95 * (iters - 1));
        return new double[]{medians[loIdx], medians[hiIdx]};
    }

    private static double[] shift(double[] x, double delta) {
        double[] out = new double[x.length];
        for (int i = 0; i < x.length; i++) out[i] = x[i] + delta;
        return out;
    }

    // --- utility ------------------------------------------------------------

    private static String stripComment(String line) {
        boolean inSingle = false;
        boolean inDouble = false;
        for (int i = 0; i < line.length(); i++) {
            char c = line.charAt(i);
            if (c == '\'' && !inDouble) inSingle = !inSingle;
            else if (c == '"' && !inSingle) inDouble = !inDouble;
            else if (c == '#' && !inSingle && !inDouble) return line.substring(0, i);
        }
        return line;
    }

    private static String[] splitKv(String s) {
        int idx = s.indexOf(':');
        if (idx < 0) return null;
        String k = s.substring(0, idx).trim();
        String v = s.substring(idx + 1).trim();
        if (k.isEmpty()) return null;
        return new String[]{k, v};
    }

    private static int leadingSpaces(String s) {
        int i = 0;
        while (i < s.length() && s.charAt(i) == ' ') i++;
        return i;
    }

    private static double round4(double x) {
        if (Double.isNaN(x) || Double.isInfinite(x)) return x;
        return Math.round(x * 10000.0) / 10000.0;
    }

    // --- value types --------------------------------------------------------

    /** Pre-registered thresholds parsed from {@code layer4-thresholds.yaml}. */
    static final class Thresholds {
        double alpha = 0.05;
        double deltaCovMethod = 0.02;
        double recoveryRateMin = 0.90;
    }

    /** One row of {@code summary.csv}, restricted to fields used by the analyzer. */
    static final class SummaryRow {
        final String apk;
        final String rep;
        final String tool;
        final double covMethod;
        final double covRvMethod;
        SummaryRow(String apk, String rep, String tool, double covMethod, double covRvMethod) {
            this.apk = apk;
            this.rep = rep;
            this.tool = tool;
            this.covMethod = covMethod;
            this.covRvMethod = covRvMethod;
        }
    }

    public static final class BatchOrchestrationOptions {
        public List<String> variants = List.of("ajc", "dexlib2");
        public List<String> tools = List.of("aperv", "monkey", "fastbot");
        public int reps = 3;
        public int timeoutSeconds = 300;
        public Path dockerComposeFile;
    }

    public static final class OrchestrationReport {
        public final Path outputDir;
        public final int totalCells;
        public final int succeededCells;
        public final Map<String, String> failures;

        public OrchestrationReport(Path outputDir, int totalCells, int succeededCells,
                                   Map<String, String> failures) {
            this.outputDir = outputDir;
            this.totalCells = totalCells;
            this.succeededCells = succeededCells;
            this.failures = failures == null ? Collections.emptyMap()
                    : Collections.unmodifiableMap(new LinkedHashMap<>(failures));
        }

        /** Project to a JSON-friendly map for {@link Report}-shaped serialization. */
        public Map<String, Object> toMetrics() {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("outputDir", outputDir.toString());
            m.put("totalCells", totalCells);
            m.put("succeededCells", succeededCells);
            m.put("failures", failures);
            return m;
        }
    }
}
