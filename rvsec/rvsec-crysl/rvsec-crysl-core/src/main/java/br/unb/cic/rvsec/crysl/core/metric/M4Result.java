package br.unb.cic.rvsec.crysl.core.metric;

import br.unb.cic.rvsec.crysl.core.model.PredicateRef;
import br.unb.cic.rvsec.crysl.core.model.Unknown;
import java.util.List;
import java.util.Objects;

/**
 * Comparison of the specification's {@code ENSURES}/{@code REQUIRES}/{@code NEGATES} graph against
 * the rule's, by arity, polarity and argument position.
 *
 * <p>{@code derivedRows} and {@code inheritedRows} are counted separately because the fidelity
 * classification is human judgement wherever it is inherited. A reader has to be able to compute
 * the derived fraction of any aggregate, otherwise a manual table has been replaced by an automatic
 * table that measures something else.
 *
 * @param specification  the specification
 * @param rule           the rule it was paired with
 * @param present        predicate references matched on both sides
 * @param absent         references the rule declares and the specification does not
 * @param inverted       references present on both sides with opposite polarity or argument order
 * @param derivedRows    rows whose fidelity class this metric derived
 * @param inheritedRows  rows whose fidelity class came from human judgement
 * @param refusals       the typed refusals
 * @param countingRule   the rule behind every count above
 */
public record M4Result(String specification, String rule, List<PredicateRef> present,
                       List<PredicateRef> absent, List<PredicateRef> inverted,
                       int derivedRows, int inheritedRows, List<Unknown> refusals,
                       String countingRule) implements MetricResult {

    public M4Result {
        Objects.requireNonNull(specification, "M4Result.specification is mandatory");
        Objects.requireNonNull(rule, "M4Result.rule is mandatory");
        Objects.requireNonNull(countingRule, "M4Result.countingRule is mandatory (INV-CONF-02)");
        present = List.copyOf(present);
        absent = List.copyOf(absent);
        inverted = List.copyOf(inverted);
        refusals = List.copyOf(refusals);
    }

    @Override
    public String metric() {
        return "M4";
    }
}
