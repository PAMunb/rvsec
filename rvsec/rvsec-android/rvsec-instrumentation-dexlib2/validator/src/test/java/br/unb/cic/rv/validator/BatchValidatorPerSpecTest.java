package br.unb.cic.rv.validator;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Unit tests for the 4-arg
 * {@link BatchValidator#analyze(Path, Path, Path, Path)} overload that
 * additionally consumes the per-(apk, rep, tool, spec) metrics CSV
 * produced by Layer 3 batch mode.
 *
 * <p>Each test builds a small synthetic cov_method {@code summary.csv}
 * pair (so the cov_method gate passes by default) plus an inline per-spec
 * CSV under {@code @TempDir}.
 */
class BatchValidatorPerSpecTest {

    private static final String SUMMARY_HEADER =
            "apk,rep,timeout,tool,cov_act,cov_method,cov_rv_method,errors";

    private static final String PER_SPEC_HEADER =
            "apk,rep,tool,spec,ajcF1,dexF1,kappa,ajcTp,ajcFp,ajcFn,dexTp,dexFp,dexFn";

    @Test
    void perSpecCsvWithinDeltaPasses(@TempDir Path tmp) throws Exception {
        // 30 paired (apk, rep, tool) triples × 2 specs = 60 rows.
        // F1 diffs alternate ±0.003 (well within delta=0.02).
        List<String> rows = new ArrayList<>();
        for (int i = 0; i < 30; i++) {
            String apk = "apk" + (i / 3);
            String rep = String.valueOf(i % 3 + 1);
            String tool = "aperv";
            double ajcF1 = 0.98 + (i % 5) * 0.001;
            double diff = (i % 2 == 0) ? +0.003 : -0.003;
            double dexF1 = ajcF1 + diff;
            for (String spec : new String[]{"SafeRandom", "SafeMessageDigest"}) {
                rows.add(specRow(apk, rep, tool, spec, ajcF1, dexF1, 0.99));
            }
        }
        Path perSpecCsv = writePerSpecCsv(tmp, rows);

        Path ajcDir = writeCovSummary(tmp, "ajc", 30, false, 0.0);
        Path dexDir = writeCovSummary(tmp, "dexlib2", 30, true, 0.0);
        Path yaml = writeFullThresholds(tmp);

        Report r = BatchValidator.analyze(ajcDir, dexDir, yaml, perSpecCsv);

        // Optional human-inspection dump.
        String dumpPath = System.getProperty("dumpLayer4PerSpecSample");
        if (dumpPath != null) r.write(Path.of(dumpPath));

        assertTrue(r.passed, () -> "expected gate pass; got: " + r.message
                + " metrics=" + r.metrics);
        assertEquals("per-spec F1 and kappa TOST included", r.metrics.get("scopeNote"));
        @SuppressWarnings("unchecked")
        Map<String, Object> perSpec = (Map<String, Object>) r.metrics.get("perSpec");
        assertEquals(2, perSpec.size());
        for (String spec : List.of("SafeRandom", "SafeMessageDigest")) {
            @SuppressWarnings("unchecked")
            Map<String, Object> sb = (Map<String, Object>) perSpec.get(spec);
            assertTrue((boolean) sb.get("specPassed"), spec + " must pass");
            @SuppressWarnings("unchecked")
            Map<String, Object> f1 = (Map<String, Object>) sb.get("f1");
            assertTrue((boolean) f1.get("nonInferiorityPassed"));
            assertTrue((boolean) f1.get("equivalencePassed"));
            @SuppressWarnings("unchecked")
            Map<String, Object> ka = (Map<String, Object>) sb.get("kappa");
            assertTrue((boolean) ka.get("passed"));
        }
        @SuppressWarnings("unchecked")
        Map<String, Object> sum = (Map<String, Object>) r.metrics.get("perSpecSummary");
        assertEquals(2, ((Number) sum.get("totalSpecs")).intValue());
        assertTrue((boolean) sum.get("perSpecGatePassed"));
    }

    @Test
    void oneSpecFailsNonInferiority(@TempDir Path tmp) throws Exception {
        // Spec A: 30 rows within delta. Spec B: 30 rows with dexlib uniformly
        // -0.05 (5pp worse) on F1 — non-inferiority must reject for spec B.
        List<String> rows = new ArrayList<>();
        for (int i = 0; i < 30; i++) {
            String apk = "apk" + (i / 3);
            String rep = String.valueOf(i % 3 + 1);
            String tool = "monkey";
            double ajcF1 = 0.98 + (i % 5) * 0.001;
            double dexF1A = ajcF1 + (i % 2 == 0 ? +0.003 : -0.003);
            double dexF1B = ajcF1 - 0.05;
            rows.add(specRow(apk, rep, tool, "SpecA", ajcF1, dexF1A, 0.99));
            rows.add(specRow(apk, rep, tool, "SpecB", ajcF1, dexF1B, 0.99));
        }
        Path perSpecCsv = writePerSpecCsv(tmp, rows);

        Path ajcDir = writeCovSummary(tmp, "ajc", 30, false, 0.0);
        Path dexDir = writeCovSummary(tmp, "dexlib2", 30, true, 0.0);
        Path yaml = writeFullThresholds(tmp);

        Report r = BatchValidator.analyze(ajcDir, dexDir, yaml, perSpecCsv);
        assertFalse(r.passed, () -> "expected gate fail; got: " + r.message);
        @SuppressWarnings("unchecked")
        Map<String, Object> sum = (Map<String, Object>) r.metrics.get("perSpecSummary");
        assertFalse((boolean) sum.get("f1NonInferiorityPassed"),
                "f1 non-inf gate must fail when one spec is uniformly worse");
        assertFalse((boolean) sum.get("perSpecGatePassed"));
    }

    @Test
    void kappaUniformlyLowFailsKappaGate(@TempDir Path tmp) throws Exception {
        // F1 within delta everywhere; kappas all 0.6 (well below 1 - 0.05 = 0.95).
        List<String> rows = new ArrayList<>();
        for (int i = 0; i < 30; i++) {
            String apk = "apk" + (i / 3);
            String rep = String.valueOf(i % 3 + 1);
            String tool = "fastbot";
            double ajcF1 = 0.98 + (i % 5) * 0.001;
            double dexF1 = ajcF1 + (i % 2 == 0 ? +0.003 : -0.003);
            for (String spec : new String[]{"SpecA", "SpecB"}) {
                rows.add(specRow(apk, rep, tool, spec, ajcF1, dexF1, 0.60));
            }
        }
        Path perSpecCsv = writePerSpecCsv(tmp, rows);

        Path ajcDir = writeCovSummary(tmp, "ajc", 30, false, 0.0);
        Path dexDir = writeCovSummary(tmp, "dexlib2", 30, true, 0.0);
        Path yaml = writeFullThresholds(tmp);

        Report r = BatchValidator.analyze(ajcDir, dexDir, yaml, perSpecCsv);
        assertFalse(r.passed);
        @SuppressWarnings("unchecked")
        Map<String, Object> sum = (Map<String, Object>) r.metrics.get("perSpecSummary");
        assertFalse((boolean) sum.get("kappaPassed"),
                "kappa gate must fail when kappas are uniformly low");
        // F1 should still pass non-inf and equivalence:
        assertTrue((boolean) sum.get("f1NonInferiorityPassed"));
        assertTrue((boolean) sum.get("f1EquivalencePassed"));
    }

    @Test
    void equivalenceFractionThresholdAllowsOneFailingSpec(@TempDir Path tmp) throws Exception {
        // 5 specs total. Specs A-D: equivalent on F1. Spec E: NOT equivalent
        // but non-inferior (dexlib +0.04 = 4pp better, outside ±2pp band so
        // upper-bound TOST fails → equivalence rejects, but lower-bound TOST
        // still rejects so non-inferiority passes).
        List<String> rows = new ArrayList<>();
        String[] equivSpecs = {"SpecA", "SpecB", "SpecC", "SpecD"};
        for (int i = 0; i < 30; i++) {
            String apk = "apk" + (i / 3);
            String rep = String.valueOf(i % 3 + 1);
            String tool = "aperv";
            double ajcF1 = 0.95 + (i % 5) * 0.001;
            double dexF1Equiv = ajcF1 + (i % 2 == 0 ? +0.003 : -0.003);
            double dexF1Nonequiv = ajcF1 + 0.04; // uniformly +4pp > delta=0.02
            for (String spec : equivSpecs) {
                rows.add(specRow(apk, rep, tool, spec, ajcF1, dexF1Equiv, 0.99));
            }
            rows.add(specRow(apk, rep, tool, "SpecE", ajcF1, dexF1Nonequiv, 0.99));
        }
        Path perSpecCsv = writePerSpecCsv(tmp, rows);

        Path ajcDir = writeCovSummary(tmp, "ajc", 30, false, 0.0);
        Path dexDir = writeCovSummary(tmp, "dexlib2", 30, true, 0.0);
        Path yaml = writeFullThresholds(tmp);

        Report r = BatchValidator.analyze(ajcDir, dexDir, yaml, perSpecCsv);
        @SuppressWarnings("unchecked")
        Map<String, Object> sum = (Map<String, Object>) r.metrics.get("perSpecSummary");
        assertEquals(5, ((Number) sum.get("totalSpecs")).intValue());
        assertEquals(5, ((Number) sum.get("f1NonInferiorityPassedCount")).intValue());
        assertEquals(4, ((Number) sum.get("f1EquivalencePassedCount")).intValue());
        // 4/5 = 0.80 EXACTLY meets the inclusive >= 0.80 threshold.
        assertTrue((boolean) sum.get("f1EquivalencePassed"),
                "4/5 == 0.80 must pass an inclusive equivalence_specs_min_pct=0.80 gate");
        assertTrue((boolean) sum.get("kappaPassed"));
        assertTrue((boolean) sum.get("perSpecGatePassed"));
        assertTrue(r.passed, () -> "expected report pass; got: " + r.message);
    }

    @Test
    void missingPerSpecCsvFallsBackToLegacy(@TempDir Path tmp) throws Exception {
        // 4-arg call with perSpecMetricsCsv=null must behave identically to
        // the legacy 3-arg call.
        Path ajcDir = writeCovSummary(tmp, "ajc", 30, false, 0.0);
        Path dexDir = writeCovSummary(tmp, "dexlib2", 30, true, 0.0);
        Path yaml = writeFullThresholds(tmp);

        Report r4 = BatchValidator.analyze(ajcDir, dexDir, yaml, null);
        Report r3 = BatchValidator.analyze(ajcDir, dexDir, yaml);

        assertEquals(r3.passed, r4.passed);
        assertNull(r4.metrics.get("perSpec"),
                "perSpec block must be absent when CSV is null");
        assertNull(r4.metrics.get("perSpecSummary"));
        assertEquals("cov_method TOST only (per-spec CSV not provided)",
                r4.metrics.get("scopeNote"));
        assertEquals(r3.metrics.get("scopeNote"), r4.metrics.get("scopeNote"));
    }

    // --- fixture builders ---------------------------------------------------

    private static String specRow(String apk, String rep, String tool, String spec,
                                  double ajcF1, double dexF1, double kappa) {
        // Synthetic TP/FP/FN counts matching the F1 values are not needed for
        // the per-spec analysis (we only consume columns 4-6); zeros suffice.
        return String.format(Locale.ROOT,
                "%s,%s,%s,%s,%.4f,%.4f,%.4f,0,0,0,0,0,0",
                apk, rep, tool, spec, ajcF1, dexF1, kappa);
    }

    private static Path writePerSpecCsv(Path root, List<String> rows) throws Exception {
        Path csv = root.resolve("per-spec.csv");
        StringBuilder sb = new StringBuilder();
        sb.append(PER_SPEC_HEADER).append('\n');
        for (String r : rows) sb.append(r).append('\n');
        Files.writeString(csv, sb.toString());
        return csv;
    }

    /**
     * Writes a per-variant summary.csv with N paired (apk, rep, tool) rows
     * where the dex side equals the ajc side plus {@code dexOffset}.
     * Setting {@code dexOffset = 0.0} keeps cov_method diffs at ±0.003 so
     * the cov_method gate passes by default (matching the existing
     * cov_method test fixtures).
     */
    private static Path writeCovSummary(Path root, String variant, int n,
                                         boolean dexSide, double dexOffset) throws Exception {
        Path dir = Files.createDirectories(root.resolve(variant));
        StringBuilder sb = new StringBuilder();
        sb.append(SUMMARY_HEADER).append('\n');
        for (int i = 0; i < n; i++) {
            String apk = "apk" + (i / 3);
            String rep = "rep" + (i % 3 + 1);
            String tool = "aperv";
            double ajcCov = 0.50 + i * 0.001;
            double dexCov = ajcCov + (i % 2 == 0 ? +0.003 : -0.003) + dexOffset;
            double cov = dexSide ? dexCov : ajcCov;
            sb.append(apk).append(',')
                    .append(rep).append(',')
                    .append("300").append(',')
                    .append(tool).append(',')
                    .append(String.format(Locale.ROOT, "%.4f", cov * 0.9)).append(',')
                    .append(String.format(Locale.ROOT, "%.4f", cov)).append(',')
                    .append(String.format(Locale.ROOT, "%.4f", cov * 0.95)).append(',')
                    .append("0").append('\n');
        }
        Files.writeString(dir.resolve("summary.csv"), sb.toString());
        return dir;
    }

    /**
     * Inline subset of {@code layer4-thresholds.yaml} including the per-spec
     * F1 / kappa bounds and the equivalence_specs_min_pct + non_inferiority
     * gates the 4-arg analyze path consumes.
     */
    private static Path writeFullThresholds(Path root) throws Exception {
        String yaml = ""
                + "name: layer4-thresholds\n"
                + "statistical_test:\n"
                + "  paired: true\n"
                + "  test: wilcoxon_signed_rank_tost\n"
                + "  alpha: 0.05\n"
                + "equivalence_bounds:\n"
                + "  cov_method:\n"
                + "    delta: 0.02\n"
                + "    units: proportion\n"
                + "  per_spec_f1:\n"
                + "    delta: 0.02\n"
                + "    units: f1_score\n"
                + "  per_spec_kappa:\n"
                + "    delta: 0.05\n"
                + "    units: cohen_kappa\n"
                + "gates:\n"
                + "  recovery_rate_min: 0.90\n"
                + "  non_inferiority: required\n"
                + "  equivalence_specs_min_pct: 0.80\n";
        Path out = root.resolve("thresholds.yaml");
        Files.writeString(out, yaml);
        return out;
    }
}
