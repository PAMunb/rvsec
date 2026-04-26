package br.unb.cic.rv.validator;

import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Skeletons for the five layered validators whose full implementation
 * depends on Phase 5 infrastructure (Docker batch, emulator via
 * rv-platform, captured logcat traces). Each entry point has a stable
 * signature + returns a {@link Report} so the cli / Python wrapper can
 * wire them now; the bodies fail-fast with a documented pending status.
 *
 * <p>When Phase 5 infra is in place, each method's body is replaced with
 * the full layer logic. The signatures + report shape stay stable so
 * callers never rebreak.
 */
public final class LayerSkeletons {

    private LayerSkeletons() {}

    // Layer 1 (BaksmaliDiffer) is implemented in BaksmaliDiffer.diff;
    // see ValidationCli.Layer1 for the wired CLI path.

    // Layer 2 (BootValidator) is implemented in BootValidator.analyze / .capture;
    // see ValidationCli.Layer2 for the wired CLI path.

    // Layer 3 (TraceComparator) is implemented in TraceComparator.compare;
    // see ValidationCli.Layer3 for the wired CLI path.

    /**
     * Layer 4 — {@code BatchValidator}: orchestrates JCA-400 × 3 tools × 3
     * reps via Docker; aggregates; runs Wilcoxon signed-rank TOST per
     * INV-INS-21 with pre-registered Δ bounds.
     */
    public static Report layer4BatchValidator(Path thresholdsYaml, Path batchResultsDir) {
        return pending("layer-4-batch-validator",
                "needs Docker batch results (945 tasks, ~36h wallclock) + pre-registered "
                        + "thresholds YAML (INV-INS-21: Δ=2pp cov_method, Δ=0.02 F1, Δ=0.05 κ, "
                        + "α=0.05). Contract: recovery_rate ≥ 90% AND paired Wilcoxon "
                        + "TOST non-inferiority rejects for every spec.");
    }

    // Layer 5 (CoverageValidator) is implemented in CoverageValidator.compare;
    // see ValidationCli.Layer5 for the wired CLI path.

    private static Report pending(String layer, String message) {
        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("status", "pending");
        metrics.put("phase", "phase-5-infra");
        return new Report(layer, false, message, metrics);
    }
}
