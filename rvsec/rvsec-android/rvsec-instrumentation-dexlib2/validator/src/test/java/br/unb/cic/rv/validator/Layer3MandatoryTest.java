package br.unb.cic.rv.validator;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * gh56 task 3.5: unit tests for the {@code layer3 --mandatory} gate
 * (INV-INS-73). The gate sits in
 * {@link ValidationCli.Layer3#applyMandatoryGateBatch} and
 * {@link ValidationCli.Layer3#applyMandatoryGateAnalyze}; this test exercises
 * the helpers directly without setting up a full picocli invocation, oracle
 * directory, or paired ajc/dexlib2 result trees.
 *
 * <p>Exit-code semantics:
 * <ul>
 *   <li>deviation detected + mandatory → {@code Report(passed=false)} → exit 1
 *       (NOT exit 2 — see D6 in {@code design.md} for the rationale).
 *   <li>no deviation + mandatory → passes through the original Report
 *       unchanged.
 *   <li>without mandatory → behaviour unchanged (the helpers are only
 *       invoked when the CLI flag is set; this test exercises the helpers
 *       directly so it skips the un-flagged path).
 * </ul>
 */
class Layer3MandatoryTest {

    private static final String LAYER = "layer3_batch";

    // ----- batch mode --------------------------------------------------------

    @Test
    void batchModeFlipsToFailedWhenAnyRowHasDeviation(@TempDir Path tmp) throws IOException {
        Path csv = tmp.resolve("per_spec.csv");
        // Header matches TraceComparator.writeCsv at L394. Two rows: the
        // first has dexFn=5 (5 oracle events missing from the dexlib2 trace
        // — the cryptoapp regression shape pre-fix); the second is clean.
        Files.write(csv, List.of(
                "apk,rep,tool,spec,ajcF1,dexF1,kappa,ajcTp,ajcFp,ajcFn,dexTp,dexFp,dexFn",
                "cryptoapp_1,0,ape,SecretKeySpecSpec,1.0,0.0,0.0,1,0,0,0,0,5",
                "cryptoapp_1,0,ape,MessageDigestSpec,1.0,1.0,1.0,2,0,0,2,0,0"
        ));

        Report original = new Report(LAYER, /*passed*/ true,
                "batch passed (diagnostic)", new LinkedHashMap<>());
        Report gated = ValidationCli.Layer3.applyMandatoryGateBatch(original, csv);

        assertFalse(gated.passed,
                "any row with dexFn > 0 must flip passed=false under --mandatory");
        assertEquals(1, gated.exitCode(),
                "Report.exitCode() must map passed=false to 1 (see D6)");
        assertEquals(true, gated.metrics.get("mandatoryGate"));
        assertEquals(1, gated.metrics.get("mandatoryDeviatingRows"));
        assertEquals(5, gated.metrics.get("mandatoryDexFnTotal"));
        assertEquals(0, gated.metrics.get("mandatoryDexFpTotal"));
        assertTrue(gated.message.startsWith("mandatory gate FAILED:"),
                "message must announce the mandatory gate failure for operators");
    }

    @Test
    void batchModeFlipsToFailedOnDexFalsePositiveToo(@TempDir Path tmp) throws IOException {
        Path csv = tmp.resolve("per_spec.csv");
        // dexFp > 0 — unexpected event in dexlib2 trace, also a deviation
        // worth blocking under --mandatory.
        Files.write(csv, List.of(
                "apk,rep,tool,spec,ajcF1,dexF1,kappa,ajcTp,ajcFp,ajcFn,dexTp,dexFp,dexFn",
                "cryptoapp_1,0,ape,KeyPairSpec,1.0,0.5,0.5,1,0,0,1,3,0"
        ));

        Report original = new Report(LAYER, true, "ok", new LinkedHashMap<>());
        Report gated = ValidationCli.Layer3.applyMandatoryGateBatch(original, csv);

        assertFalse(gated.passed);
        assertEquals(1, gated.metrics.get("mandatoryDeviatingRows"));
        assertEquals(3, gated.metrics.get("mandatoryDexFpTotal"));
    }

    @Test
    void batchModeStaysPassedWhenAllRowsClean(@TempDir Path tmp) throws IOException {
        Path csv = tmp.resolve("per_spec.csv");
        // All rows: dexFn=0, dexFp=0 — no deviation.
        Files.write(csv, List.of(
                "apk,rep,tool,spec,ajcF1,dexF1,kappa,ajcTp,ajcFp,ajcFn,dexTp,dexFp,dexFn",
                "cryptoapp_1,0,ape,SecretKeySpecSpec,1.0,1.0,1.0,1,0,0,1,0,0",
                "cryptoapp_1,0,ape,MessageDigestSpec,1.0,1.0,1.0,2,0,0,2,0,0"
        ));

        Report original = new Report(LAYER, true,
                "batch passed", new LinkedHashMap<>());
        Report gated = ValidationCli.Layer3.applyMandatoryGateBatch(original, csv);

        assertSame(original, gated,
                "no deviation → mandatory helper returns the original Report unchanged");
        assertEquals(0, gated.exitCode());
    }

    @Test
    void batchModeHandlesMissingCsvGracefully(@TempDir Path tmp) throws IOException {
        Path csv = tmp.resolve("nonexistent.csv");
        Report original = new Report(LAYER, true, "ok", new LinkedHashMap<>());
        Report gated = ValidationCli.Layer3.applyMandatoryGateBatch(original, csv);

        // Missing CSV → 0 deviating rows → passthrough. Defensive behaviour
        // for runs where the CSV emission failed for an orthogonal reason.
        assertSame(original, gated);
    }

    @Test
    void batchModeIgnoresMissingHeaderColumns(@TempDir Path tmp) throws IOException {
        Path csv = tmp.resolve("malformed.csv");
        // Header missing dexFn/dexFp columns — helper bails to passthrough
        // (does not throw). The validator already failed elsewhere if it
        // could not write proper CSV; we don't add a second failure mode.
        Files.write(csv, List.of(
                "apk,rep,tool,spec",
                "cryptoapp_1,0,ape,SecretKeySpecSpec"
        ));
        Report original = new Report(LAYER, true, "ok", new LinkedHashMap<>());
        Report gated = ValidationCli.Layer3.applyMandatoryGateBatch(original, csv);
        assertSame(original, gated);
    }

    // ----- analyze mode ------------------------------------------------------

    @Test
    void analyzeModeFlipsToFailedWhenAnyOracleHasPassedFalse() {
        Map<String, Object> perOracle = new LinkedHashMap<>();
        Map<String, Object> cryptoappOracle = new LinkedHashMap<>();
        cryptoappOracle.put("passed", false);
        cryptoappOracle.put("missing", List.of("KeyPairSpec", "SecretKeySpecSpec"));
        perOracle.put("cryptoapp", cryptoappOracle);

        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("perOracle", perOracle);

        // Default (non-mandatory) gate would report passed=true if F1/kappa
        // thresholds hold even with per-oracle deviations. Mandatory mode
        // tightens this.
        Report original = new Report("layer3", true,
                "F1/kappa thresholds met", metrics);
        Report gated = ValidationCli.Layer3.applyMandatoryGateAnalyze(original);

        assertFalse(gated.passed);
        assertEquals(1, gated.exitCode());
        assertEquals(1, gated.metrics.get("mandatoryFailingOracles"));
        assertEquals(true, gated.metrics.get("mandatoryGate"));
    }

    @Test
    void analyzeModePassesThroughAlreadyFailedReport() {
        // When the underlying TraceComparator already produced
        // Report(passed=false) (F1/kappa thresholds violated), the
        // mandatory helper is a no-op — the gate is already failing.
        Report failed = new Report("layer3", false,
                "F1 < 0.98", new LinkedHashMap<>());
        Report gated = ValidationCli.Layer3.applyMandatoryGateAnalyze(failed);
        assertSame(failed, gated);
    }

    @Test
    void analyzeModeStaysPassedWhenAllOraclesPass() {
        Map<String, Object> perOracle = new LinkedHashMap<>();
        Map<String, Object> ok = new LinkedHashMap<>();
        ok.put("passed", true);
        perOracle.put("cryptoapp", ok);
        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("perOracle", perOracle);
        Report original = new Report("layer3", true, "ok", metrics);
        Report gated = ValidationCli.Layer3.applyMandatoryGateAnalyze(original);
        assertSame(original, gated);
    }

    @Test
    void analyzeModeHandlesMissingPerOracleMetric() {
        // Defensive: if the upstream Report doesn't include perOracle (e.g.
        // an empty oracle dir produced an early-exit Report), the helper
        // bails to passthrough instead of NPE.
        Report original = new Report("layer3", true, "no oracles",
                new LinkedHashMap<>());
        Report gated = ValidationCli.Layer3.applyMandatoryGateAnalyze(original);
        assertSame(original, gated);
    }
}
