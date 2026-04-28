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
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Unit tests for {@link BatchValidator#analyze(Path, Path, Path)}. Each
 * test builds two synthetic {@code summary.csv} files plus a stripped-down
 * thresholds YAML under {@code @TempDir}, then asserts on the
 * {@link Report} fields. The orchestrate (docker compose) path is not
 * unit-tested — its correctness is verified by the manual smoke documented
 * in {@link BatchValidator}.
 */
class BatchValidatorTest {

    private static final String CSV_HEADER =
            "apk,rep,timeout,tool,cov_act,cov_method,cov_rv_method,errors";

    @Test
    void pairedDataWithinDeltaPassesGate(@TempDir Path tmp) throws Exception {
        // 30 pairs, all diffs in [-0.005, +0.005] (well within delta=0.02).
        List<Pair> pairs = new ArrayList<>();
        double[] diffs = new double[30];
        for (int i = 0; i < 30; i++) {
            // Alternating tiny positive / negative diffs around zero so the
            // signed-rank test confidently rejects both equivalence H0s.
            double base = 0.50 + i * 0.001;
            double diff = (i % 2 == 0 ? +0.003 : -0.003);
            pairs.add(new Pair("apk" + (i / 3), "rep" + (i % 3 + 1), "aperv", base, base + diff));
            diffs[i] = diff;
        }
        Path ajcDir = writeVariantSummary(tmp, "ajc", pairs, true);
        Path dexDir = writeVariantSummary(tmp, "dexlib2", pairs, false);
        Path yaml = writeThresholds(tmp, 0.05, 0.02, 0.90);

        Report r = BatchValidator.analyze(ajcDir, dexDir, yaml);
        assertTrue(r.passed, () -> "expected gate pass; got: " + r.message
                + " metrics=" + r.metrics);
        assertEquals(30, ((Number) r.metrics.get("pairedKeys")).intValue());
        Map<?, ?> cov = (Map<?, ?>) r.metrics.get("covMethod");
        assertTrue((boolean) cov.get("nonInferiorityPassed"),
                "non-inf must pass for tightly bounded diffs");
        assertTrue((boolean) cov.get("equivalencePassed"),
                "equivalence must pass for tightly bounded diffs");
        assertTrue((boolean) r.metrics.get("recoveryRatePassed"));

        // Optional dump for human inspection of report shape.
        String dumpPath = System.getProperty("dumpLayer4Sample");
        if (dumpPath != null) r.write(Path.of(dumpPath));
    }

    @Test
    void dexlibUniformlyWorseFailsNonInferiority(@TempDir Path tmp) throws Exception {
        // 30 pairs, dexlib uniformly -0.03 (3pp worse) -> non-inf rejects.
        List<Pair> pairs = new ArrayList<>();
        for (int i = 0; i < 30; i++) {
            double a = 0.60 + i * 0.001;
            pairs.add(new Pair("apk" + (i / 3), "rep" + (i % 3 + 1), "monkey", a, a - 0.03));
        }
        Path ajcDir = writeVariantSummary(tmp, "ajc", pairs, true);
        Path dexDir = writeVariantSummary(tmp, "dexlib2", pairs, false);
        Path yaml = writeThresholds(tmp, 0.05, 0.02, 0.90);

        Report r = BatchValidator.analyze(ajcDir, dexDir, yaml);
        assertFalse(r.passed, () -> "expected gate fail; got: " + r.message);
        Map<?, ?> cov = (Map<?, ?>) r.metrics.get("covMethod");
        assertFalse((boolean) cov.get("nonInferiorityPassed"),
                "non-inf must fail when dexlib is uniformly worse");
    }

    @Test
    void dexlibUniformlyBetterPassesNonInferiority(@TempDir Path tmp) throws Exception {
        // 30 pairs, dexlib uniformly +0.01 (1pp better, within delta=0.02).
        List<Pair> pairs = new ArrayList<>();
        for (int i = 0; i < 30; i++) {
            double a = 0.55 + i * 0.001;
            pairs.add(new Pair("apk" + (i / 3), "rep" + (i % 3 + 1), "fastbot", a, a + 0.01));
        }
        Path ajcDir = writeVariantSummary(tmp, "ajc", pairs, true);
        Path dexDir = writeVariantSummary(tmp, "dexlib2", pairs, false);
        Path yaml = writeThresholds(tmp, 0.05, 0.02, 0.90);

        Report r = BatchValidator.analyze(ajcDir, dexDir, yaml);
        assertTrue(r.passed, () -> "expected gate pass; got: " + r.message);
        Map<?, ?> cov = (Map<?, ?>) r.metrics.get("covMethod");
        assertTrue((boolean) cov.get("nonInferiorityPassed"),
                "non-inf must pass when dexlib is uniformly better within delta");
    }

    @Test
    void lowRecoveryFailsRegardlessOfTost(@TempDir Path tmp) throws Exception {
        // ajc has 30 keys, dexlib has 5 paired keys + 0 extra.
        // recovery = 5 / max(30, 5) = 0.166 < 0.90 -> gate fails even though
        // those 5 paired diffs are tiny.
        List<Pair> ajcOnly = new ArrayList<>();
        List<Pair> paired = new ArrayList<>();
        for (int i = 0; i < 30; i++) {
            double a = 0.55 + i * 0.001;
            if (i < 5) {
                paired.add(new Pair("apk" + i, "rep1", "aperv", a, a + 0.001));
            } else {
                ajcOnly.add(new Pair("apk" + i, "rep1", "aperv", a, 0.0)); // dex value unused
            }
        }
        // ajc: paired + ajcOnly. dex: paired only.
        List<Pair> ajcAll = new ArrayList<>();
        ajcAll.addAll(paired);
        ajcAll.addAll(ajcOnly);
        Path ajcDir = writeVariantSummary(tmp, "ajc", ajcAll, true);
        Path dexDir = writeVariantSummary(tmp, "dexlib2", paired, false);
        Path yaml = writeThresholds(tmp, 0.05, 0.02, 0.90);

        Report r = BatchValidator.analyze(ajcDir, dexDir, yaml);
        assertFalse(r.passed, () -> "expected gate fail due to low recovery; got: " + r.message);
        assertFalse((boolean) r.metrics.get("recoveryRatePassed"));
        assertEquals(5, ((Number) r.metrics.get("pairedKeys")).intValue());
        assertEquals(30, ((Number) r.metrics.get("totalAjcKeys")).intValue());
        assertEquals(5, ((Number) r.metrics.get("totalDexlibKeys")).intValue());
    }

    @Test
    void unpairedKeysListedAndCappedAt50(@TempDir Path tmp) throws Exception {
        // 60 keys exclusively in ajc, 0 in dexlib -> 60 unpaired, capped at 50 in the report.
        List<Pair> ajcOnly = new ArrayList<>();
        for (int i = 0; i < 60; i++) {
            ajcOnly.add(new Pair("orphan" + i, "rep1", "aperv", 0.5, 0.0));
        }
        Path ajcDir = writeVariantSummary(tmp, "ajc", ajcOnly, true);
        // Empty dex variant: just the header.
        Path dexDir = Files.createDirectories(tmp.resolve("dexlib2"));
        Files.writeString(dexDir.resolve("summary.csv"), CSV_HEADER + "\n");
        Path yaml = writeThresholds(tmp, 0.05, 0.02, 0.90);

        Report r = BatchValidator.analyze(ajcDir, dexDir, yaml);
        assertFalse(r.passed);
        List<?> unpaired = (List<?>) r.metrics.get("unpairedKeys");
        assertEquals(50, unpaired.size(), "unpaired list must be capped at 50");
        assertEquals(0, ((Number) r.metrics.get("pairedKeys")).intValue());
    }

    // --- fixture builders ---------------------------------------------------

    /** Pair carrying both ajc and dexlib cov_method values for a single (apk, rep, tool). */
    private record Pair(String apk, String rep, String tool, double ajcCov, double dexCov) {}

    /**
     * Write a variant's summary.csv. {@code writeAjcSide} selects which
     * column of each {@link Pair} ends up in the {@code cov_method} field.
     */
    private static Path writeVariantSummary(Path root, String variant, List<Pair> pairs,
                                            boolean writeAjcSide) throws Exception {
        Path dir = Files.createDirectories(root.resolve(variant));
        StringBuilder sb = new StringBuilder();
        sb.append(CSV_HEADER).append('\n');
        for (Pair p : pairs) {
            double cov = writeAjcSide ? p.ajcCov() : p.dexCov();
            sb.append(p.apk()).append(',')
              .append(p.rep()).append(',')
              .append("300").append(',')
              .append(p.tool()).append(',')
              .append(String.format(Locale.ROOT, "%.4f", cov * 0.9)).append(',')   // cov_act (irrelevant)
              .append(String.format(Locale.ROOT, "%.4f", cov)).append(',')          // cov_method
              .append(String.format(Locale.ROOT, "%.4f", cov * 0.95)).append(',')   // cov_rv_method
              .append("0").append('\n');
        }
        Files.writeString(dir.resolve("summary.csv"), sb.toString());
        return dir;
    }

    private static Path writeThresholds(Path root, double alpha, double deltaCovMethod,
                                        double recoveryMin) throws Exception {
        String yaml = ""
                + "name: layer4-thresholds\n"
                + "statistical_test:\n"
                + "  paired: true\n"
                + "  test: wilcoxon_signed_rank_tost\n"
                + "  alpha: " + alpha + "\n"
                + "equivalence_bounds:\n"
                + "  cov_method:\n"
                + "    delta: " + deltaCovMethod + "\n"
                + "    units: proportion\n"
                + "gates:\n"
                + "  recovery_rate_min: " + recoveryMin + "\n";
        Path out = root.resolve("thresholds.yaml");
        Files.writeString(out, yaml);
        return out;
    }
}
