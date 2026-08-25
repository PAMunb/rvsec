package br.unb.cic.rvsec.crysl.core.calibration;

import br.unb.cic.rvsec.crysl.core.model.SourceStamp;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

/**
 * Checks what the component measured against what an independent route measured, and reports.
 *
 * <h2>It reports; it does not reconcile</h2>
 *
 * <p>{@link #check} never throws and never rewrites either side. It compares, names what differs
 * and hands back a {@link CalibrationReport} in which every target carries both values and both
 * counting rules. {@link #verify} is {@link #check} plus a signal: it raises
 * {@link CalibrationMismatch} when a calibration target was not reproduced, with the whole report
 * attached so a caller sees at once what failed and what still publishes.
 *
 * <p>The prohibition this class exists to enforce is INV-CONF-14, and it is a prohibition on the
 * <em>author</em>, not on the code: the cheapest way to pass a calibration gate is to relax a
 * counting rule or widen a recogniser until the instrument agrees, and the result is a green that
 * is evidence of nothing. Nothing here can stop that being done. What it can do is make a
 * disagreement expensive to hide — both rules printed, the differing items named — so that tuning
 * leaves a trace where silence would not.
 *
 * <h2>A target whose route is the component's own rule is refused as a target</h2>
 *
 * <p>{@link RouteClass#SAME_ALGORITHM_RESTATEMENT} is not compared and not counted. Its outcome is
 * {@link TargetOutcome.Verdict#SELF_CONSISTENCY_CHECK}, labelled so a reader does not count it as
 * external validation (D-18). Two of the eight targets were written that way once, and a gate built
 * on them could not fail.
 */
public final class CalibrationGate {

    /**
     * How two values are compared, printed with every report.
     *
     * <p>Both sides render a value into one canonical string and, when the quantity has enumerable
     * items, the items are compared as sets. The item comparison is what turns "4 versus 5" into
     * "the fifth is {@code KeyStoreSpec}", and it is checked even when the two values agree: two
     * counts can coincide over different items, and that is a disagreement worth catching rather
     * than a pass.
     */
    public static final String COMPARISON_RULE =
            "a target is reproduced when the component's canonical value string equals the route's "
                    + "and, where the target enumerates items, the two item sets are equal. Items "
                    + "are compared as sets even when the counts agree, because two counts can "
                    + "coincide over different items and that is a disagreement, not a pass";

    private CalibrationGate() {
    }

    /**
     * Compares every target against the component's measurement of it.
     *
     * @param targets        the targets, each with its route, its rule and its own stamp
     * @param measurements   the component's answers, keyed by target id
     * @param runStamps      repository to the stamp this run read that repository at
     * @param unreproducible figures no written rule reproduces (task 12.10)
     * @return the report; never null, never thrown, never reconciled
     */
    public static CalibrationReport check(List<CalibrationTarget> targets,
                                          Map<String, Measurement> measurements,
                                          Map<String, SourceStamp> runStamps,
                                          List<UnreproducibleFigure> unreproducible) {
        Objects.requireNonNull(targets, "targets is mandatory");
        Objects.requireNonNull(measurements, "measurements is mandatory");
        Objects.requireNonNull(runStamps, "runStamps is mandatory (D-17)");

        List<TargetOutcome> outcomes = new ArrayList<>(targets.size());
        for (CalibrationTarget target : targets) {
            outcomes.add(compare(target, measurements.get(target.id())));
        }
        return new CalibrationReport(outcomes, runStamps,
                unreproducible == null ? List.of() : unreproducible);
    }

    /**
     * {@link #check}, and then a signal when a calibration target was not reproduced.
     *
     * @throws CalibrationMismatch when any target of a calibrating route disagrees; the report is
     *                             attached, so the metrics that still publish are visible from the
     *                             exception itself
     */
    public static CalibrationReport verify(List<CalibrationTarget> targets,
                                           Map<String, Measurement> measurements,
                                           Map<String, SourceStamp> runStamps,
                                           List<UnreproducibleFigure> unreproducible) {
        CalibrationReport report = check(targets, measurements, runStamps, unreproducible);
        if (!report.reproduced()) {
            throw new CalibrationMismatch(report);
        }
        return report;
    }

    private static TargetOutcome compare(CalibrationTarget target, Measurement measurement) {
        if (!target.routeClass().calibrates()) {
            // D-18: the route is the component's own rule, so the comparison cannot come out
            // wrong. It is published, labelled, and not counted as calibration.
            Measurement answered = measurement == null ? target.asMeasurement() : measurement;
            return new TargetOutcome(target, answered,
                    TargetOutcome.Verdict.SELF_CONSISTENCY_CHECK, List.of(), List.of());
        }
        if (measurement == null) {
            // Nothing was measured for this target. That is a mismatch and not a pass: a target the
            // run never answered is exactly the silence the gate exists to break.
            Measurement absent = Measurement.of(target.id(), "(not measured by this run)",
                    "no measurement was supplied for this target");
            return new TargetOutcome(target, absent, TargetOutcome.Verdict.MISMATCH,
                    target.items(), List.of());
        }

        List<String> onlyInRoute = missing(target.items(), measurement.items());
        List<String> onlyInComponent = missing(measurement.items(), target.items());
        boolean sameValue = target.value().equals(measurement.value());
        boolean sameItems = onlyInRoute.isEmpty() && onlyInComponent.isEmpty();
        TargetOutcome.Verdict verdict = sameValue && sameItems
                ? TargetOutcome.Verdict.REPRODUCED
                : TargetOutcome.Verdict.MISMATCH;
        return new TargetOutcome(target, measurement, verdict, onlyInRoute, onlyInComponent);
    }

    private static List<String> missing(List<String> from, List<String> against) {
        Set<String> other = new LinkedHashSet<>(against);
        return from.stream().filter(item -> !other.contains(item)).distinct().toList();
    }
}
