package br.unb.cic.rvsec.crysl.core.calibration;

import java.util.List;
import java.util.Objects;

/**
 * A target the component does not reproduce (INV-CONF-14).
 *
 * <p>It carries the whole {@link CalibrationReport}, not only the disagreements, because the two
 * facts a reader needs arrive together: <em>this</em> failed, and <em>those</em> still publish. A
 * gate that threw away the passing side would make a single mismatch look like a broken run, and
 * the next person would run the component without the gate.
 *
 * <p>The component is never adjusted to clear this exception. The response is to measure both sides
 * and adjudicate in writing; if the target proves unreproducible under any written rule, it is
 * recorded as unreproducible with the component's value beside its own rule (task 12.10). Tuning
 * the instrument until it agrees produces a green that is evidence of nothing, which is strictly
 * worse than having no gate at all.
 */
public class CalibrationMismatch extends RuntimeException {

    private static final long serialVersionUID = 1L;

    private final transient CalibrationReport report;

    /**
     * @param report the full report, mismatches and passes alike
     */
    public CalibrationMismatch(CalibrationReport report) {
        super(message(report));
        this.report = Objects.requireNonNull(report, "CalibrationMismatch.report is mandatory");
    }

    /** The full report: every target's outcome and what still publishes. */
    public CalibrationReport report() {
        return report;
    }

    /** The disagreements, each with both measurements, both rules and the named items. */
    public List<TargetOutcome> mismatches() {
        return report.mismatches();
    }

    private static String message(CalibrationReport report) {
        StringBuilder text = new StringBuilder();
        text.append(report.mismatches().size()).append(" of ")
                .append(report.calibrationTargets())
                .append(" calibration targets were not reproduced. A disagreement is a finding to "
                        + "adjudicate by measuring both sides, never a signal to adjust the "
                        + "component until it agrees (INV-CONF-14).\n\n");
        report.mismatches().forEach(outcome -> text.append(outcome.describe()).append('\n'));
        text.append(report.publicationSummary());
        return text.toString();
    }
}
