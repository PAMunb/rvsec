package br.unb.cic.rvsec.crysl.core.metric;

import br.unb.cic.rvsec.crysl.core.model.Signature;
import br.unb.cic.rvsec.crysl.core.model.Unknown;
import java.util.List;
import java.util.Objects;

/**
 * Event coverage of the specification against the paired rule, over concrete signatures.
 *
 * <p>Both differences are fields, not a derived convenience: a coverage percentage emitted without
 * the two lists beside it says which fraction was covered but not what was left out on either side,
 * and the two sides mean different things - a MOP-only signature is a monitor watching something
 * the rule does not name, a rule-only signature is an obligation nobody monitors.
 *
 * @param specification the specification
 * @param rule          the rule it was paired with, by declared type (INV-CONF-11)
 * @param covered       signatures monitored by the specification and named by the rule
 * @param declared      signatures named by the rule
 * @param mopOnly       monitored by the specification, not named by the rule
 * @param ruleOnly      named by the rule, not monitored by the specification
 * @param refusals      the typed refusals
 * @param countingRule  the rule behind {@code covered} and {@code declared}
 */
public record M1Result(String specification, String rule, int covered, int declared,
                       List<Signature> mopOnly, List<Signature> ruleOnly,
                       List<Unknown> refusals, String countingRule) implements MetricResult {

    public M1Result {
        Objects.requireNonNull(specification, "M1Result.specification is mandatory");
        Objects.requireNonNull(rule, "M1Result.rule is mandatory");
        Objects.requireNonNull(countingRule, "M1Result.countingRule is mandatory (INV-CONF-02)");
        mopOnly = List.copyOf(mopOnly);
        ruleOnly = List.copyOf(ruleOnly);
        refusals = List.copyOf(refusals);
    }

    @Override
    public String metric() {
        return "M1";
    }
}
