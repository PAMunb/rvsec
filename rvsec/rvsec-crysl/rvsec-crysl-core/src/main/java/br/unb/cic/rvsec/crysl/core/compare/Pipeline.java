package br.unb.cic.rvsec.crysl.core.compare;

import br.unb.cic.rvsec.crysl.core.metric.M0Result;
import br.unb.cic.rvsec.crysl.core.metric.MetricResult;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.function.Supplier;

/**
 * The one place M0's refusal is allowed to stop the comparison, and the only way M1-M4 are reached.
 *
 * <p>INV-CONF-09 has two halves and the second one is the one a pipeline usually loses: M0 runs
 * first, <em>and</em> a specification M0 refuses does not receive an M1, M2, M3 or M4 verdict. A
 * loop that computes the five metrics and then filters the output satisfies the first half and not
 * the second, because the four verdicts existed — they were computed, they can be printed, and
 * somebody eventually prints them. So the downstream metrics arrive here as a {@link Supplier} and
 * a refused specification never calls it: the verdicts are not filtered, they are not produced.
 *
 * <p>The class is small on purpose. It is a choke point, not a framework: everything about how the
 * four metrics are computed belongs to their own classes, and everything this one adds is the
 * decision not to compute them.
 */
public final class Pipeline {

    private Pipeline() {
    }

    /**
     * Runs M0 first and the rest only if M0 did not refuse.
     *
     * @param m0         the vitality result, already computed — M0 is what decides, so it cannot
     *                   itself be behind the gate
     * @param downstream the M1-M4 verdicts, computed only when the specification is not refused
     * @return the specification's whole result
     */
    public static Outcome run(M0Result m0, Supplier<List<MetricResult>> downstream) {
        Objects.requireNonNull(m0, "Pipeline.run needs the M0 result: M0 runs first (INV-CONF-09)");
        Objects.requireNonNull(downstream, "Pipeline.run needs the downstream metrics");
        if (m0.refused()) {
            return new Outcome(m0, List.of());
        }
        List<MetricResult> verdicts = new ArrayList<>(downstream.get());
        for (MetricResult verdict : verdicts) {
            if (verdict instanceof M0Result) {
                throw new IllegalArgumentException("the downstream supplier of "
                        + m0.specification() + " returned an M0Result; M0 is the gate and is passed "
                        + "in, not produced behind it");
            }
        }
        return new Outcome(m0, verdicts);
    }

    /**
     * Everything one specification's comparison produced.
     *
     * <p>{@code verdicts} is empty exactly when {@code m0.refused()} is true, and in that case the
     * typed refusal M0 emitted is the specification's whole result. {@link #results()} puts M0
     * first, because that is the order the report reads in and the order INV-CONF-09 describes.
     *
     * @param m0       the vitality result, always present
     * @param verdicts the M1-M4 verdicts, empty when M0 refused
     */
    public record Outcome(M0Result m0, List<MetricResult> verdicts) {

        public Outcome {
            Objects.requireNonNull(m0, "Outcome.m0 is mandatory");
            verdicts = List.copyOf(verdicts);
            if (m0.refused() && !verdicts.isEmpty()) {
                throw new IllegalArgumentException("M0 refused " + m0.specification()
                        + " and it carries " + verdicts.size() + " downstream verdicts; INV-CONF-09 "
                        + "says a refused specification receives none");
            }
        }

        /** The specification this outcome is about. */
        public String specification() {
            return m0.specification();
        }

        /** Whether M0 refused, in which case {@link #verdicts()} is empty. */
        public boolean refused() {
            return m0.refused();
        }

        /** M0 first, then whatever ran after it. */
        public List<MetricResult> results() {
            List<MetricResult> all = new ArrayList<>();
            all.add(m0);
            all.addAll(verdicts);
            return List.copyOf(all);
        }
    }
}
