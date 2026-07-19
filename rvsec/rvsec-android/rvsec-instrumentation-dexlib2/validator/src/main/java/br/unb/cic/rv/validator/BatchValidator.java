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
 * <h2>Scope</h2>
 * The Layer-4 spec covers {@code cov_method}, {@code per_spec_f1} and
 * {@code per_spec_kappa} TOST. The 3-arg overload {@link #analyze(Path, Path,
 * Path)} computes only {@code cov_method} (legacy behavior, preserved for
 * backward compatibility). The 4-arg overload {@link #analyze(Path, Path,
 * Path, Path)} additionally consumes the per-spec metrics CSV produced by
 * {@link TraceComparator#batchAnalyze} and applies per-spec F1 and κ TOST
 * with their own gates. The {@code metrics.scopeNote} field of the report
 * records which scope was used.
 *
 * <h3>Kappa one-sample test convention (methodological note)</h3>
 * Cohen's κ is itself a two-rater agreement metric — Layer 3 already
 * computes it across the ajc and dexlib2 pipelines for each
 * {@code (apk, rep, tool, spec)} cell. Treating κ as a paired difference
 * across pipelines would double-count the agreement. We therefore use a
 * one-sample location test: shift the κ values by {@code -(1 - delta)} and
 * apply the lower-bound TOST against zero (H1: shifted median > 0, i.e.
 * median κ > 1 - delta). This is the conservative interpretation
 * documented in the pre-registered methodology.
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
     * Pure-data analyzer (legacy 3-arg overload). Equivalent to
     * {@link #analyze(Path, Path, Path, Path)} with
     * {@code perSpecMetricsCsv = null}: only the {@code cov_method} TOST
     * block is computed and gated.
     */
    public static Report analyze(Path ajcResultsDir, Path dexlibResultsDir,
                                 Path thresholdsYaml) throws IOException {
        return analyze(ajcResultsDir, dexlibResultsDir, thresholdsYaml, null);
    }

    /**
     * Pure-data analyzer. Reads {@code <ajcResultsDir>/summary.csv} and
     * {@code <dexlibResultsDir>/summary.csv}, pairs by
     * {@code (apk, rep, tool)}, runs Wilcoxon signed-rank TOST on the
     * paired diff vector for {@code cov_method}, and applies the
     * pre-registered gate. When {@code perSpecMetricsCsv} is non-null and
     * readable, the analyzer additionally consumes the Layer-3-batch CSV
     * (schema documented at {@link TraceComparator#batchAnalyze}) and
     * applies per-spec F1 TOST and per-spec κ one-sample lower-bound TOST,
     * gated by {@code equivalence_bounds.per_spec_f1.delta},
     * {@code equivalence_bounds.per_spec_kappa.delta},
     * {@code gates.equivalence_specs_min_pct} and
     * {@code gates.non_inferiority}.
     */
    public static Report analyze(Path ajcResultsDir, Path dexlibResultsDir,
                                 Path thresholdsYaml, Path perSpecMetricsCsv) throws IOException {
        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("thresholdsYaml", thresholdsYaml.toString());
        metrics.put("ajcResultsDir", ajcResultsDir.toString());
        metrics.put("dexlibResultsDir", dexlibResultsDir.toString());
        metrics.put("perSpecMetricsCsv",
                perSpecMetricsCsv == null ? null : perSpecMetricsCsv.toString());

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
        TostBlock cov = tostBlock(diffs, delta, th.alpha);

        // Truncated diff vector preview for the report.
        List<Double> diffPreview = new ArrayList<>();
        for (int i = 0; i < diffs.length && i < MAX_DIAGNOSTIC; i++) {
            diffPreview.add(round4(diffs[i]));
        }

        Map<String, Object> covMethod = new LinkedHashMap<>();
        covMethod.put("delta", round4(delta));
        covMethod.put("pairCount", diffs.length);
        covMethod.put("diffVector", diffPreview);
        covMethod.put("medianDiff", round4(cov.median));
        covMethod.put("ci90Lower", round4(cov.ci90Lower));
        covMethod.put("ci90Upper", round4(cov.ci90Upper));
        covMethod.put("pValueLower", round4(cov.pValueLower));
        covMethod.put("pValueUpper", round4(cov.pValueUpper));
        covMethod.put("nonInferiorityPassed", cov.nonInferiorityPassed);
        covMethod.put("equivalencePassed", cov.equivalencePassed);

        metrics.put("covMethod", covMethod);
        metrics.put("recoveryRate", round4(recoveryRate));
        metrics.put("recoveryRateMin", round4(th.recoveryRateMin));
        metrics.put("recoveryRatePassed", recoveryRatePassed);
        metrics.put("totalAjcKeys", ajcRows.size());
        metrics.put("totalDexlibKeys", dexRows.size());
        metrics.put("pairedKeys", pairedKeys.size());
        metrics.put("unpairedKeys", unpaired);

        // Per-spec analysis (optional second scope).
        boolean perSpecRequested = perSpecMetricsCsv != null
                && Files.isReadable(perSpecMetricsCsv);
        PerSpecOutcome perSpecOutcome = null;
        if (perSpecRequested) {
            perSpecOutcome = analyzePerSpec(perSpecMetricsCsv, th);
            metrics.put("perSpec", perSpecOutcome.perSpec);
            metrics.put("perSpecSummary", perSpecOutcome.summary);
            metrics.put("scopeNote", "per-spec F1 and kappa TOST included");
        } else {
            metrics.put("scopeNote", "cov_method TOST only (per-spec CSV not provided)");
        }

        boolean passed = cov.nonInferiorityPassed
                && cov.equivalencePassed
                && recoveryRatePassed
                && (perSpecOutcome == null || perSpecOutcome.gatePassed);

        String message = String.format(Locale.ROOT,
                "batch comparison: rec=%.2f, non_inf=%s, equiv=%s%s",
                recoveryRate,
                cov.nonInferiorityPassed ? "pass" : "fail",
                cov.equivalencePassed ? "pass" : "fail",
                perSpecOutcome == null ? ""
                        : (", per_spec=" + (perSpecOutcome.gatePassed ? "pass" : "fail")));
        return new Report(LAYER_NAME, passed, message, metrics);
    }

    // --- TOST helper (shared by cov_method and per-spec F1) -----------------

    /**
     * Runs the paired Wilcoxon signed-rank TOST on a diff vector against
     * an equivalence bound {@code delta}. Returns the lower/upper p-values,
     * the median, the 90% bootstrap CI, and the non-inferiority /
     * equivalence flags decided against {@code alpha}.
     *
     * <p>Empty input returns an empty block ({@code p=1.0}, both flags
     * false). The kappa one-sample test reuses this with the diff vector
     * pre-shifted by {@code -(1 - delta)} (see {@link #kappaTostBlock}).
     */
    static TostBlock tostBlock(double[] diffs, double delta, double alpha) {
        if (diffs.length == 0) {
            return new TostBlock(0.0, 0.0, 0.0, 1.0, 1.0, false, false);
        }
        // Lower-bound TOST: H1: median(diff) > -delta. Shift diffs by +delta;
        // alternative becomes "shifted median > 0" => greater-than zero one-sided test.
        double[] shiftedLower = shift(diffs, +delta);
        double pLower = oneSidedPValueGreaterThan(shiftedLower);
        // Upper-bound TOST: H1: median(diff) < +delta. Shift diffs by -delta;
        // alternative becomes "shifted median < 0" => less-than zero one-sided test.
        double[] shiftedUpper = shift(diffs, -delta);
        double pUpper = oneSidedPValueLessThan(shiftedUpper);

        double med = median(diffs);
        double[] ci = bootstrapMedianCi90(diffs, BOOTSTRAP_ITERATIONS, BOOTSTRAP_SEED);

        boolean nonInf = pLower < alpha;
        boolean equiv = (pLower < alpha) && (pUpper < alpha);
        return new TostBlock(med, ci[0], ci[1], pLower, pUpper, nonInf, equiv);
    }

    /**
     * Kappa one-sample lower-bound TOST: shift κ values by {@code -(1 - delta)}
     * so values close to 1 become positive, then test
     * {@code H1: median(shifted) > 0} (equivalent to {@code median(κ) > 1 - delta}).
     * Returns a {@link KappaTostBlock} with the same p-value / CI shape as
     * {@link #tostBlock} but only the lower-bound side is used (κ is bounded
     * above by 1 by construction, so the upper-bound TOST is trivial).
     */
    static KappaTostBlock kappaTostBlock(double[] kappas, double delta, double alpha) {
        if (kappas.length == 0) {
            return new KappaTostBlock(0.0, 0.0, 0.0, 1.0, false);
        }
        double shiftPoint = 1.0 - delta;
        // Shift kappas by -(1 - delta): values >= (1 - delta) become >= 0.
        double[] shifted = shift(kappas, -shiftPoint);
        double pLower = oneSidedPValueGreaterThan(shifted);
        double med = median(kappas);
        double[] ci = bootstrapMedianCi90(kappas, BOOTSTRAP_ITERATIONS, BOOTSTRAP_SEED);
        boolean passed = pLower < alpha;
        return new KappaTostBlock(med, ci[0], ci[1], pLower, passed);
    }

    // --- per-spec analyzer --------------------------------------------------

    /**
     * Per-spec second scope: reads the Layer-3-batch per-spec CSV, groups rows
     * by spec, and runs two TOST families per spec — F1 (paired dexlib2−ajc
     * diff) and κ (one-sample lower bound) — then rolls them up into one gate.
     *
     * <h3>Asymmetric aggregate gate (deliberate)</h3>
     * The three sub-gates are NOT held to the same bar:
     * <ul>
     *   <li><b>F1 non-inferiority — required for ALL specs.</b> A dexlib2
     *       pipeline that regresses recall/precision on even ONE spec is a
     *       correctness defect (it would silently miss or invent violations
     *       for that spec), so {@code f1NonInfPassedCount == totalSpecs} is
     *       mandatory — a single failure fails the gate.</li>
     *   <li><b>F1 equivalence and κ — required for ≥{@code equivalence_specs_min_pct}
     *       (default 80%) of specs.</b> Equivalence (two-sided TOST) is the
     *       STRICTER, more data-hungry bar: a spec with few paired
     *       observations can fail to PROVE equivalence yet still be
     *       non-inferior. Demanding 100% equivalence would make the gate
     *       hostage to low-sample specs, so we accept the documented 80%
     *       majority while still forbidding any non-inferiority regression.</li>
     * </ul>
     * In short: non-inferiority is the safety floor (all specs, no exceptions);
     * equivalence/κ is the tighter statistical claim where a per-spec-count
     * quorum is sufficient.
     */
    private static PerSpecOutcome analyzePerSpec(Path csv, Thresholds th) throws IOException {
        Map<String, List<SpecRow>> bySpec = readPerSpecCsv(csv);

        Map<String, Object> perSpecOut = new LinkedHashMap<>();
        int f1NonInfPassedCount = 0;
        int f1EquivPassedCount = 0;
        int kappaPassedCount = 0;
        int totalSpecs = bySpec.size();

        for (Map.Entry<String, List<SpecRow>> e : bySpec.entrySet()) {
            String spec = e.getKey();
            List<SpecRow> rows = e.getValue();
            int n = rows.size();

            double[] f1Diffs = new double[n];
            double[] kappas = new double[n];
            for (int i = 0; i < n; i++) {
                f1Diffs[i] = rows.get(i).dexF1 - rows.get(i).ajcF1;
                kappas[i] = rows.get(i).kappa;
            }

            TostBlock f1Tost = tostBlock(f1Diffs, th.deltaPerSpecF1, th.alpha);
            KappaTostBlock kappaTost = kappaTostBlock(kappas, th.deltaPerSpecKappa, th.alpha);

            if (f1Tost.nonInferiorityPassed) f1NonInfPassedCount++;
            if (f1Tost.equivalencePassed) f1EquivPassedCount++;
            if (kappaTost.passed) kappaPassedCount++;

            boolean specPassed = f1Tost.nonInferiorityPassed
                    && f1Tost.equivalencePassed
                    && kappaTost.passed;

            Map<String, Object> f1Block = new LinkedHashMap<>();
            f1Block.put("delta", round4(th.deltaPerSpecF1));
            f1Block.put("pairCount", n);
            f1Block.put("medianDiff", round4(f1Tost.median));
            f1Block.put("ci90Lower", round4(f1Tost.ci90Lower));
            f1Block.put("ci90Upper", round4(f1Tost.ci90Upper));
            f1Block.put("pValueLower", round4(f1Tost.pValueLower));
            f1Block.put("pValueUpper", round4(f1Tost.pValueUpper));
            f1Block.put("nonInferiorityPassed", f1Tost.nonInferiorityPassed);
            f1Block.put("equivalencePassed", f1Tost.equivalencePassed);

            Map<String, Object> kappaBlock = new LinkedHashMap<>();
            kappaBlock.put("delta", round4(th.deltaPerSpecKappa));
            kappaBlock.put("shiftPoint", round4(1.0 - th.deltaPerSpecKappa));
            kappaBlock.put("rowCount", n);
            kappaBlock.put("median", round4(kappaTost.median));
            kappaBlock.put("ci90Lower", round4(kappaTost.ci90Lower));
            kappaBlock.put("ci90Upper", round4(kappaTost.ci90Upper));
            kappaBlock.put("pValueLower", round4(kappaTost.pValueLower));
            kappaBlock.put("passed", kappaTost.passed);

            Map<String, Object> specBlock = new LinkedHashMap<>();
            specBlock.put("rowCount", n);
            specBlock.put("f1", f1Block);
            specBlock.put("kappa", kappaBlock);
            specBlock.put("specPassed", specPassed);
            perSpecOut.put(spec, specBlock);
        }

        // Aggregate gate evaluation — see the method javadoc for WHY the bars
        // differ. Non-inferiority requires a 1.0 ratio (every spec); equivalence
        // and kappa require only equivalence_specs_min_pct. That fraction is an
        // inclusive lower bound (>=) so the documented 0.80 threshold is met by
        // exactly 4-of-5 specs (4/5 == 0.80).
        double f1NonInfRatioRequired = 1.0; // gates.non_inferiority == required
        double f1EquivRatioRequired = th.equivalenceSpecsMinPct;
        double kappaRatioRequired = th.equivalenceSpecsMinPct;
        boolean f1NonInfGate;
        boolean f1EquivGate;
        boolean kappaGate;
        if (totalSpecs == 0) {
            f1NonInfGate = false;
            f1EquivGate = false;
            kappaGate = false;
        } else {
            f1NonInfGate = (f1NonInfPassedCount == totalSpecs);
            f1EquivGate = ((double) f1EquivPassedCount / (double) totalSpecs) >= f1EquivRatioRequired;
            kappaGate = ((double) kappaPassedCount / (double) totalSpecs) >= kappaRatioRequired;
        }
        boolean perSpecGatePassed = f1NonInfGate && f1EquivGate && kappaGate;

        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("totalSpecs", totalSpecs);
        summary.put("f1NonInferiorityPassedCount", f1NonInfPassedCount);
        summary.put("f1NonInferiorityRequiredFraction", round4(f1NonInfRatioRequired));
        summary.put("f1EquivalencePassedCount", f1EquivPassedCount);
        summary.put("f1EquivalenceRequiredFraction", round4(f1EquivRatioRequired));
        summary.put("kappaPassedCount", kappaPassedCount);
        summary.put("kappaRequiredFraction", round4(kappaRatioRequired));
        summary.put("f1NonInferiorityPassed", f1NonInfGate);
        summary.put("f1EquivalencePassed", f1EquivGate);
        summary.put("kappaPassed", kappaGate);
        summary.put("perSpecGatePassed", perSpecGatePassed);

        return new PerSpecOutcome(perSpecOut, summary, perSpecGatePassed);
    }

    /**
     * Reads the per-spec metrics CSV produced by
     * {@link TraceComparator#batchAnalyze}. Header is
     * {@code apk,rep,tool,spec,ajcF1,dexF1,kappa,ajcTp,ajcFp,ajcFn,dexTp,dexFp,dexFn};
     * we use positional indices and silently skip malformed rows.
     */
    static Map<String, List<SpecRow>> readPerSpecCsv(Path csv) throws IOException {
        Map<String, List<SpecRow>> out = new TreeMap<>();
        try (BufferedReader r = new BufferedReader(
                new InputStreamReader(Files.newInputStream(csv), StandardCharsets.UTF_8))) {
            String header = r.readLine();
            if (header == null
                    || !header.startsWith("apk,rep,tool,spec,ajcF1,dexF1,kappa")) {
                throw new IOException("unexpected per-spec CSV header in " + csv + ": " + header);
            }
            String line;
            while ((line = r.readLine()) != null) {
                if (line.isBlank()) continue;
                String[] parts = line.split(",", -1);
                if (parts.length < 7) continue;
                String apk = parts[0].trim();
                String rep = parts[1].trim();
                String tool = parts[2].trim();
                String spec = parts[3].trim();
                double ajcF1 = parseDouble(parts[4], 0.0);
                double dexF1 = parseDouble(parts[5], 0.0);
                double kappa = parseDouble(parts[6], 0.0);
                out.computeIfAbsent(spec, k -> new ArrayList<>())
                        .add(new SpecRow(apk, rep, tool, spec, ajcF1, dexF1, kappa));
            }
        }
        return out;
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
     * schema actually committed under {@code validator/oracles/}. Consumes:
     * {@code statistical_test.alpha},
     * {@code equivalence_bounds.cov_method.delta},
     * {@code equivalence_bounds.per_spec_f1.delta},
     * {@code equivalence_bounds.per_spec_kappa.delta},
     * {@code gates.recovery_rate_min},
     * {@code gates.equivalence_specs_min_pct},
     * {@code gates.non_inferiority}; everything else is informational and
     * ignored. Mirrors the parser pattern established by
     * {@link TraceComparator#parseOracle}.
     */
    static Thresholds parseThresholds(Path yaml) throws IOException {
        Thresholds out = new Thresholds();
        if (!Files.isRegularFile(yaml)) {
            throw new IOException("thresholds yaml not found: " + yaml);
        }
        List<String> lines = Files.readAllLines(yaml);

        // Section tracking: top-level key whose body is a block-style map.
        String section = null;
        // Sub-section under equivalence_bounds: e.g. "cov_method", "per_spec_f1".
        String boundSubsection = null;
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
                boundSubsection = null;
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
                            boundSubsection = kv[0];
                        }
                    } else if (indent > sectionIndent + 2 && boundSubsection != null) {
                        if (kv != null && "delta".equals(kv[0])) {
                            switch (boundSubsection) {
                                case "cov_method" ->
                                        out.deltaCovMethod = parseDouble(kv[1], out.deltaCovMethod);
                                case "per_spec_f1" ->
                                        out.deltaPerSpecF1 = parseDouble(kv[1], out.deltaPerSpecF1);
                                case "per_spec_kappa" ->
                                        out.deltaPerSpecKappa = parseDouble(kv[1], out.deltaPerSpecKappa);
                                default -> { /* ignore unknown bound */ }
                            }
                        }
                    }
                }
                case "gates" -> {
                    if (kv == null) break;
                    switch (kv[0]) {
                        case "recovery_rate_min" ->
                                out.recoveryRateMin = parseDouble(kv[1], out.recoveryRateMin);
                        case "equivalence_specs_min_pct" ->
                                out.equivalenceSpecsMinPct =
                                        parseDouble(kv[1], out.equivalenceSpecsMinPct);
                        case "non_inferiority" -> {
                            String v = kv[1] == null ? "" : kv[1].trim();
                            if (v.length() >= 2 && (v.charAt(0) == '"' || v.charAt(0) == '\'')) {
                                v = v.substring(1, v.length() - 1);
                            }
                            out.nonInferiorityRequired = "required".equalsIgnoreCase(v);
                        }
                        default -> { /* ignore */ }
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

    /** Pre-registered thresholds parsed from {@code layer4-thresholds.yaml} (defaults shown). */
    static final class Thresholds {
        /** Significance level for every one-sided TOST decision. */
        double alpha = 0.05;
        /** Equivalence bound (percentage points) for the cov_method TOST. */
        double deltaCovMethod = 0.02;
        /** Equivalence bound for the per-spec F1 TOST. */
        double deltaPerSpecF1 = 0.02;
        /** Equivalence bound for the per-spec κ one-sample test (shift = 1 − this). */
        double deltaPerSpecKappa = 0.05;
        /** Minimum paired/max-keys recovery rate the pairing must clear. */
        double recoveryRateMin = 0.90;
        /** Fraction of specs that must pass equivalence/κ (majority quorum). */
        double equivalenceSpecsMinPct = 0.80;
        /** Whether F1 non-inferiority is required for all specs (gates.non_inferiority). */
        boolean nonInferiorityRequired = true;
    }

    /** TOST output for a paired diff vector. */
    static final class TostBlock {
        /** Median of the raw paired diff vector. */
        final double median;
        /** Lower bound of the 90% bootstrap CI on the median. */
        final double ci90Lower;
        /** Upper bound of the 90% bootstrap CI on the median. */
        final double ci90Upper;
        /** One-sided p-value for the lower-bound (non-inferiority) test. */
        final double pValueLower;
        /** One-sided p-value for the upper-bound (not-too-much-better) test. */
        final double pValueUpper;
        /** True when {@code pValueLower < alpha} (dexlib2 not worse than ajc). */
        final boolean nonInferiorityPassed;
        /** True when both p-values clear alpha (two-sided equivalence). */
        final boolean equivalencePassed;
        TostBlock(double median, double ci90Lower, double ci90Upper,
                  double pValueLower, double pValueUpper,
                  boolean nonInferiorityPassed, boolean equivalencePassed) {
            this.median = median;
            this.ci90Lower = ci90Lower;
            this.ci90Upper = ci90Upper;
            this.pValueLower = pValueLower;
            this.pValueUpper = pValueUpper;
            this.nonInferiorityPassed = nonInferiorityPassed;
            this.equivalencePassed = equivalencePassed;
        }
    }

    /** One-sample lower-bound TOST output for a κ vector. */
    static final class KappaTostBlock {
        /** Median of the raw κ vector (unshifted). */
        final double median;
        /** Lower bound of the 90% bootstrap CI on the κ median. */
        final double ci90Lower;
        /** Upper bound of the 90% bootstrap CI on the κ median. */
        final double ci90Upper;
        /** One-sided p-value for {@code median(κ) > 1 − delta}. */
        final double pValueLower;
        /** True when {@code pValueLower < alpha} (κ agreement is high enough). */
        final boolean passed;
        KappaTostBlock(double median, double ci90Lower, double ci90Upper,
                       double pValueLower, boolean passed) {
            this.median = median;
            this.ci90Lower = ci90Lower;
            this.ci90Upper = ci90Upper;
            this.pValueLower = pValueLower;
            this.passed = passed;
        }
    }

    /** One row of the per-spec metrics CSV, restricted to fields used here. */
    static final class SpecRow {
        /** APK filename this row was measured on. */
        final String apk;
        /** Repetition index of the run. */
        final String rep;
        /** Testing tool that drove the run. */
        final String tool;
        /** Monitored-operation spec name this row scores. */
        final String spec;
        /** F1 of the ajc pipeline for this (apk, rep, tool, spec) cell. */
        final double ajcF1;
        /** F1 of the dexlib2 pipeline for the same cell. */
        final double dexF1;
        /** Cohen's κ agreement between the two pipelines for the cell. */
        final double kappa;
        SpecRow(String apk, String rep, String tool, String spec,
                double ajcF1, double dexF1, double kappa) {
            this.apk = apk;
            this.rep = rep;
            this.tool = tool;
            this.spec = spec;
            this.ajcF1 = ajcF1;
            this.dexF1 = dexF1;
            this.kappa = kappa;
        }
    }

    /** Bundled output of the per-spec analyzer (per-spec details + summary + gate). */
    static final class PerSpecOutcome {
        /** spec → {F1 block, κ block, specPassed} detail map for the report. */
        final Map<String, Object> perSpec;
        /** Roll-up counts and sub-gate booleans across all specs. */
        final Map<String, Object> summary;
        /** Combined per-spec gate result (non-inferiority ∧ equivalence ∧ κ). */
        final boolean gatePassed;
        PerSpecOutcome(Map<String, Object> perSpec, Map<String, Object> summary, boolean gatePassed) {
            this.perSpec = perSpec;
            this.summary = summary;
            this.gatePassed = gatePassed;
        }
    }

    /** One row of {@code summary.csv}, restricted to fields used by the analyzer. */
    static final class SummaryRow {
        /** APK filename for this run. */
        final String apk;
        /** Repetition index of the run. */
        final String rep;
        /** Testing tool that drove the run. */
        final String tool;
        /** Method coverage (the metric the cov_method TOST is run on). */
        final double covMethod;
        /** Monitored-operation method coverage (carried but not gated here). */
        final double covRvMethod;
        SummaryRow(String apk, String rep, String tool, double covMethod, double covRvMethod) {
            this.apk = apk;
            this.rep = rep;
            this.tool = tool;
            this.covMethod = covMethod;
            this.covRvMethod = covRvMethod;
        }
    }

    /** Tunables for {@link #orchestrate}; defaults shown. */
    public static final class BatchOrchestrationOptions {
        /** Instrumentation variants to run; each gets its own {@code <variant>/summary.csv}. */
        public List<String> variants = List.of("ajc", "dexlib2");
        /** Testing tools to fan out over. */
        public List<String> tools = List.of("aperv", "monkey", "fastbot");
        /** Repetitions per (variant, tool) cell. */
        public int reps = 3;
        /** Per-cell run timeout in seconds (the process wait is 4× this). */
        public int timeoutSeconds = 300;
        /** Optional {@code docker-compose.yml}; null uses the default compose resolution. */
        public Path dockerComposeFile;
    }

    /** Operational outcome of an {@link #orchestrate} run (not a gate — see class javadoc). */
    public static final class OrchestrationReport {
        /** Root directory the per-variant summaries were written under. */
        public final Path outputDir;
        /** Total (variant × tool × rep) cells attempted. */
        public final int totalCells;
        /** Cells whose docker compose run exited cleanly. */
        public final int succeededCells;
        /** {@code variant/tool/repN} → failure reason for every failed cell. */
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
