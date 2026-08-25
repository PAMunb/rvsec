package br.unb.cic.rvsec.crysl.core.metric;

import br.unb.cic.rvsec.crysl.core.model.Unknown;
import java.util.List;

/**
 * What every metric returns for one specification.
 *
 * <p>The {@code countingRule} is a field rather than a comment because INV-CONF-02 reads it at
 * emission time: a table that reports a count without naming the rule that produced it must not be
 * emitted, and the only way to guarantee that mechanically is for the rule to travel with the
 * number. The same corpus yields different totals under different rules, so an aggregate without
 * its rule is not a measurement.
 *
 * <p>{@code refusals} travels with every result for the same reason: the {@code Unknown} count of a
 * metric is emitted in the same table as its coverage figure, so that "could not read" is never
 * silently added to "is not there".
 */
public sealed interface MetricResult permits M0Result, M1Result, M2Result, M3Result, M4Result {

    /** The metric identifier, {@code M0} through {@code M4}. */
    String metric();

    /** The specification this result is about. */
    String specification();

    /** The rule that produced every count in this result, stated in full. */
    String countingRule();

    /** The typed refusals this metric emitted for this specification. */
    List<Unknown> refusals();
}
