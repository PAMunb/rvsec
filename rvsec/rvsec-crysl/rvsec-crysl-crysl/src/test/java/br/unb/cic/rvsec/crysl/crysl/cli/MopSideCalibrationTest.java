package br.unb.cic.rvsec.crysl.crysl.cli;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.calibration.CalibrationGate;
import br.unb.cic.rvsec.crysl.core.calibration.CalibrationReport;
import br.unb.cic.rvsec.crysl.core.calibration.CalibrationTarget;
import br.unb.cic.rvsec.crysl.core.calibration.CalibrationTargets;
import br.unb.cic.rvsec.crysl.core.calibration.Measurement;
import br.unb.cic.rvsec.crysl.core.calibration.TargetOutcome;
import br.unb.cic.rvsec.crysl.core.model.SourceStamp;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * The half of the calibration gate that needs nothing outside this repository.
 *
 * <p>Five of the eight targets — 1, 2, 3, 7 and 8 — are about the {@code .mop} corpora alone, and
 * the corpora are in this checkout. So they run in CI, untagged, and a corpus move breaks the build
 * on the machine that made it rather than on the one machine that happens to have the oracle beside
 * it. Targets 4, 5 and 6 need {@code rvsec-cognicrypt} and live in {@code CalibrationGateTest} with
 * the {@code oracle-dependent} tag.
 *
 * <p>Target 8 is here for a reason worth stating: its <em>route</em> needs a generation pass, but
 * its <em>target</em> is a value that pass produced and this file pins. Comparing the component's
 * AST proxy against that pinned value costs nothing and catches the case the proxy drifts. Whether
 * the route itself still holds today is the separate check in {@code CalibrationGateTest}, and it
 * was re-taken at this run's commit rather than assumed.
 */
class MopSideCalibrationTest {

    private static final Path MOP_ROOT =
            Paths.get("..", "..", "rvsec-mop", "src", "main", "resources").normalize();

    private static final String RUN_COMMIT = "6192b57a";

    /** The five targets that need no oracle. */
    private static final List<String> MOP_SIDE = List.of("T1-mop-lift",
            "T2-generic-multiparameter", "T3-android-multiparameter", "T7-partial-binding",
            "T8-without-map-of-monitor");

    @Test
    @DisplayName("12.6 in CI: the five .mop-side targets are reproduced, items included")
    void test_the_mop_side_targets_are_reproduced() {
        CalibrateRun.MopSide mop = CalibrateRun.liftMopCorpora(RUN_COMMIT, MOP_ROOT);
        Map<String, Measurement> measurements = CalibrateRun.mopMeasurements(mop);
        List<CalibrationTarget> targets = CalibrationTargets.eight().stream()
                .filter(target -> MOP_SIDE.contains(target.id()))
                .toList();

        CalibrationReport report = CalibrationGate.check(targets, measurements,
                Map.of("rvsec", new SourceStamp("rvsec", RUN_COMMIT, Instant.EPOCH)), List.of());

        assertEquals(5, report.outcomes().size());
        for (TargetOutcome outcome : report.outcomes()) {
            assertEquals(TargetOutcome.Verdict.REPRODUCED, outcome.verdict(),
                    "a disagreement is a finding to adjudicate by measuring both sides, never a "
                            + "signal to adjust the component or this assertion (INV-CONF-14).\n"
                            + outcome.describe());
        }
        assertTrue(report.reproduced());
    }

    @Test
    @DisplayName("the .mop measurements each state the rule the component counted under")
    void test_every_measurement_carries_its_counting_rule() {
        Map<String, Measurement> measurements =
                CalibrateRun.mopMeasurements(CalibrateRun.liftMopCorpora(RUN_COMMIT, MOP_ROOT));

        assertEquals(5, measurements.size());
        measurements.forEach((id, measurement) -> assertTrue(
                measurement.countingRule().length() > 40,
                id + " was measured without a legible counting rule, which makes the number "
                        + "unadjudicable against anything (INV-CONF-02)"));
    }
}
