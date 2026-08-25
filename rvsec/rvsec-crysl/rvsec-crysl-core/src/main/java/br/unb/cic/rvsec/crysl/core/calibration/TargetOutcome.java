package br.unb.cic.rvsec.crysl.core.calibration;

import java.util.List;
import java.util.Objects;

/**
 * What the gate found about one target: both values, both counting rules, and the items that
 * differ, named individually.
 *
 * <p>"4 versus 5" is unactionable. "These four, and the fifth is {@code KeyStoreSpec}" is a finding
 * someone can adjudicate in an afternoon — which is the entire difference between a gate that gets
 * disabled and a gate that gets used (task 12.3).
 *
 * @param target          the target, with the route's value and rule
 * @param measurement     the component's answer, with its own rule
 * @param verdict         what the comparison concluded
 * @param onlyInRoute     items the route named and the component did not
 * @param onlyInComponent items the component named and the route did not
 */
public record TargetOutcome(CalibrationTarget target, Measurement measurement, Verdict verdict,
                            List<String> onlyInRoute, List<String> onlyInComponent) {

    /** What one target's comparison concluded. */
    public enum Verdict {

        /** The component's value and items are the route's. */
        REPRODUCED,

        /**
         * They disagree. A finding to adjudicate by measuring both sides, never a signal to adjust
         * the component until it agrees (INV-CONF-14).
         */
        MISMATCH,

        /**
         * The target's value is not reproducible under <strong>any</strong> written rule, so it is
         * published as unreproducible with the component's value beside the component's rule
         * (task 12.10). Not a pass and not a mismatch: pretending it were either would be the lie.
         */
        UNREPRODUCIBLE,

        /**
         * The route is a rule the component implements, so this quantity is published as a labelled
         * self-consistency check and is not counted as calibration (D-18). It cannot fail the gate
         * because it cannot fail at all.
         */
        SELF_CONSISTENCY_CHECK
    }

    public TargetOutcome {
        Objects.requireNonNull(target, "TargetOutcome.target is mandatory");
        Objects.requireNonNull(measurement, "TargetOutcome.measurement is mandatory");
        Objects.requireNonNull(verdict, "TargetOutcome.verdict is mandatory");
        onlyInRoute = List.copyOf(onlyInRoute);
        onlyInComponent = List.copyOf(onlyInComponent);
    }

    /** Whether this outcome stops the publication of {@link CalibrationTarget#blocks()}. */
    public boolean suppresses() {
        return verdict == Verdict.MISMATCH;
    }

    /**
     * The finding in one block of text: both measurements, both counting rules, the named items.
     *
     * <p>This is what {@link CalibrationMismatch} carries and what the gate prints, so the two can
     * never drift into saying different things about the same disagreement.
     */
    public String describe() {
        StringBuilder text = new StringBuilder();
        text.append(target.id()).append(" [").append(verdict).append("] ")
                .append(target.subject()).append('\n');
        text.append("  route      : ").append(target.value())
                .append("   (").append(target.routeClass()).append(" — ").append(target.route())
                .append(" @ ").append(target.stamp().repository()).append('@')
                .append(target.stamp().commit()).append(")\n");
        text.append("  component  : ").append(measurement.value()).append('\n');
        text.append("  route rule : ").append(target.countingRule()).append('\n');
        text.append("  comp. rule : ").append(measurement.countingRule()).append('\n');
        if (!onlyInRoute.isEmpty()) {
            text.append("  only in the route     : ").append(String.join(", ", onlyInRoute))
                    .append('\n');
        }
        if (!onlyInComponent.isEmpty()) {
            text.append("  only in the component : ").append(String.join(", ", onlyInComponent))
                    .append('\n');
        }
        if (!target.note().isBlank()) {
            text.append("  note       : ").append(target.note()).append('\n');
        }
        return text.toString();
    }
}
