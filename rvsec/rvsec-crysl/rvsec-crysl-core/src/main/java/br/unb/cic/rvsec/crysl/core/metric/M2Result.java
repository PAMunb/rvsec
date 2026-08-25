package br.unb.cic.rvsec.crysl.core.metric;

import br.unb.cic.rvsec.crysl.core.model.Normalization;
import br.unb.cic.rvsec.crysl.core.model.Unknown;
import br.unb.cic.rvsec.crysl.core.model.Witness;
import java.util.List;
import java.util.Objects;
import java.util.Optional;

/**
 * Order comparison between the specification's language and the rule's, decided by product search
 * in both directions over the inverse morphism.
 *
 * <p>Every verdict is published under the label {@link #LABEL}, which marks it as a statement about
 * <em>declarations</em>. It says nothing about what the generated monitor accuses: an order that is
 * equivalent at automaton level can still be accused at runtime, which was measured on
 * {@code KeyGeneratorSpec}. The normalizations are carried beside the verdict because "equivalent
 * under two erasures" and "equivalent" are different claims.
 *
 * <p>{@code ruleAutomatonWasDeterministic} records a measurement, not an assumption:
 * determinization always runs, because the Glushkov construction of {@code ORDER con, a?, a} is
 * genuinely non-deterministic, and how often it was a no-op over the current oracle is a number the
 * component publishes.
 *
 * @param specification the specification
 * @param rule          the rule it was paired with
 * @param verdict       the comparison outcome
 * @param witness       the shortest distinguishing witness, absent when the languages agree
 * @param normalizations the transformations both sides were compared modulo
 * @param ruleAutomatonWasDeterministic whether determinization of the rule automaton was a no-op
 * @param refusals      the typed refusals
 * @param countingRule  the rule behind the verdict
 */
public record M2Result(String specification, String rule, Verdict verdict,
                       Optional<Witness> witness, List<Normalization> normalizations,
                       boolean ruleAutomatonWasDeterministic, List<Unknown> refusals,
                       String countingRule) implements MetricResult {

    /** The label every M2 verdict is published under, marking it as a claim about declarations. */
    public static final String LABEL = "M2-decl";

    /** The four possible relations between the two languages. */
    public enum Verdict {
        EQUIVALENT,
        MOP_MORE_PERMISSIVE,
        MOP_MORE_RESTRICTIVE,
        INCOMPARABLE
    }

    public M2Result {
        Objects.requireNonNull(specification, "M2Result.specification is mandatory");
        Objects.requireNonNull(rule, "M2Result.rule is mandatory");
        Objects.requireNonNull(verdict, "M2Result.verdict is mandatory");
        Objects.requireNonNull(witness, "M2Result.witness is mandatory (use Optional.empty())");
        Objects.requireNonNull(countingRule, "M2Result.countingRule is mandatory (INV-CONF-02)");
        normalizations = List.copyOf(normalizations);
        refusals = List.copyOf(refusals);
    }

    @Override
    public String metric() {
        return "M2";
    }
}
