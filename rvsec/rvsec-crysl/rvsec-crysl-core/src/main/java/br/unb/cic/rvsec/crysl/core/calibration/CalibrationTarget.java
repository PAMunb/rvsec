package br.unb.cic.rvsec.crysl.core.calibration;

import br.unb.cic.rvsec.crysl.core.model.SourceStamp;
import java.util.List;
import java.util.Objects;

/**
 * One number the component must reproduce, with everything a reader needs to re-take it.
 *
 * <h2>A target without its counting rule is not a target; it is a number</h2>
 *
 * <p>Phase 0 published four scalars — {@code 129}, {@code 12 of 23}, {@code 10/26} and
 * {@code 28 of 55} — that no reconstructible counting rule reproduces. They were not wrong so much
 * as unusable: without the rule, a disagreement cannot be adjudicated, because nobody can tell
 * whether the two sides counted the same thing. Every field below exists to stop that happening
 * again, and {@link #countingRule} is the one that does most of the work.
 *
 * <h2>The stamp is the route's own, not the run's</h2>
 *
 * <p>{@link #stamp} names the repository and commit <em>the route was taken at</em>, which is
 * routinely not the commit the gate runs at. The {@code .mop} corpora live in {@code rvsec}, which
 * moved four times during this change; the oracle lives in {@code rvsec-cognicrypt}, which has not
 * moved since May. A single commit per run would attribute an oracle-derived number to a repository
 * that did not produce it (D-17, INV-CONF-01), so the gate prints the two stamps side by side and
 * this record carries the route's half.
 *
 * @param id           short stable identifier, printed in every verdict line
 * @param subject      what the number is about, in one line
 * @param value        the route's value, in the canonical rendering both sides use
 * @param items        the individual items behind the value, named, so a disagreement can say
 *                     <em>which</em> ones differ rather than only how many; empty when the quantity
 *                     is a bare count with no enumerable items
 * @param countingRule the rule the route counted under, complete enough to be re-applied by hand
 * @param routeClass   whether this route can contradict the component (D-18)
 * @param route        where the route lives, as a path or an artifact name
 * @param corpus       the corpus the number is about, for the stamp table
 * @param stamp        the repository and commit <strong>the route</strong> was taken at
 * @param blocks       the metric whose publication a mismatch here stops, and only that one
 * @param note         what a reader has to know that the fields above do not say; may be empty
 */
public record CalibrationTarget(String id, String subject, String value, List<String> items,
                                String countingRule, RouteClass routeClass, String route,
                                String corpus, SourceStamp stamp, PublishedMetric blocks,
                                String note) {

    public CalibrationTarget {
        Objects.requireNonNull(id, "CalibrationTarget.id is mandatory");
        Objects.requireNonNull(subject, "CalibrationTarget.subject is mandatory");
        Objects.requireNonNull(value, "CalibrationTarget.value is mandatory");
        Objects.requireNonNull(routeClass, "CalibrationTarget.routeClass is mandatory (D-18)");
        Objects.requireNonNull(route, "CalibrationTarget.route is mandatory");
        Objects.requireNonNull(corpus, "CalibrationTarget.corpus is mandatory");
        Objects.requireNonNull(stamp, "CalibrationTarget.stamp is mandatory (D-17)");
        Objects.requireNonNull(blocks, "CalibrationTarget.blocks is mandatory (task 12.4)");
        Objects.requireNonNull(note, "CalibrationTarget.note is mandatory; use \"\" for none");
        if (countingRule == null || countingRule.isBlank()) {
            throw new IllegalArgumentException("CalibrationTarget " + id + " has no counting rule. "
                    + "A target without its counting rule is not a target, it is a number: a "
                    + "disagreement against it cannot be adjudicated, because nobody can tell "
                    + "whether the two sides counted the same thing");
        }
        items = List.copyOf(items);
    }

    /** The route's side of a comparison, in the shape the gate compares. */
    public Measurement asMeasurement() {
        return new Measurement(id, value, items, countingRule);
    }
}
