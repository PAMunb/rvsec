package br.unb.cic.rvsec.crysl.core.calibration;

import java.util.List;
import java.util.Objects;

/**
 * What the component answered for one target, under the rule the component counted by.
 *
 * <p>The counting rule travels with the value here for the same reason it travels with the target:
 * the interesting disagreements in this corpus are not "one side is wrong" but "the two sides
 * counted different things", and only two rules side by side make that visible. The nine
 * {@code validateAbsent} tokens against the five {@code validateAbsent} sites are the corpus's own
 * example — both numbers are right, under different rules, and a report that printed one without
 * its rule published an ambiguity.
 *
 * @param targetId     which target this answers
 * @param value        the component's value, in the canonical rendering the target also uses
 * @param items        the individual items behind it, named; empty when the quantity has none
 * @param countingRule the rule <strong>the component</strong> counted under, which is allowed to
 *                     differ from the target's and is then the first thing to read
 */
public record Measurement(String targetId, String value, List<String> items, String countingRule) {

    public Measurement {
        Objects.requireNonNull(targetId, "Measurement.targetId is mandatory");
        Objects.requireNonNull(value, "Measurement.value is mandatory");
        if (countingRule == null || countingRule.isBlank()) {
            throw new IllegalArgumentException("Measurement " + targetId + " has no counting rule. "
                    + "A count published without the rule that produced it is the failure "
                    + "INV-CONF-02 exists to prevent");
        }
        items = List.copyOf(items);
    }

    /** A measurement of a bare count, with no enumerable items behind it. */
    public static Measurement of(String targetId, String value, String countingRule) {
        return new Measurement(targetId, value, List.of(), countingRule);
    }
}
