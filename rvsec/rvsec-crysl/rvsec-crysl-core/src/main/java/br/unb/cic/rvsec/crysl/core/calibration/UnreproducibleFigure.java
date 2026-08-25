package br.unb.cic.rvsec.crysl.core.calibration;

import java.util.Objects;

/**
 * A published figure no written rule reproduces, recorded as such beside the component's own value
 * and rule (task 12.10).
 *
 * <p>Phase 0 produced four of these — {@code 129}, {@code 12 of 23}, {@code 10/26} and
 * {@code 28 of 55} — and the response that worked was neither to chase the missing rule nor to
 * quietly drop the figure, but to write down that it does not reproduce, say what was tried, and
 * publish the component's answer with the rule it was taken under. A figure recorded this way stays
 * legible as history; a figure deleted becomes a number someone re-derives next year from the same
 * unknown rule.
 *
 * @param figure          the published figure, as published
 * @param statedIn        where it is stated
 * @param whatWasTried    the rules that were applied and what each answered
 * @param componentValue  what the component answers instead
 * @param componentRule   the rule the component answered under
 */
public record UnreproducibleFigure(String figure, String statedIn, String whatWasTried,
                                   String componentValue, String componentRule) {

    public UnreproducibleFigure {
        Objects.requireNonNull(figure, "UnreproducibleFigure.figure is mandatory");
        Objects.requireNonNull(statedIn, "UnreproducibleFigure.statedIn is mandatory");
        Objects.requireNonNull(whatWasTried, "UnreproducibleFigure.whatWasTried is mandatory");
        Objects.requireNonNull(componentValue, "UnreproducibleFigure.componentValue is mandatory");
        Objects.requireNonNull(componentRule, "UnreproducibleFigure.componentRule is mandatory");
    }

    /** The record in one block, in the shape the gate prints it. */
    public String describe() {
        return figure + " (" + statedIn + ") does not reproduce.\n"
                + "  what was tried  : " + whatWasTried + '\n'
                + "  component value : " + componentValue + '\n'
                + "  component rule  : " + componentRule + '\n';
    }
}
