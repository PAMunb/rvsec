package br.unb.cic.rvsec.crysl.core.metric;

import java.util.Objects;

/**
 * A producer and a consumer of the same predicate that are not talking about the same object.
 *
 * <p>This is the class of defect the {@code RandomStringPassword} bridge exhibits, and it is one
 * the component <em>contributes</em> rather than inherits: no manual table in this repository has a
 * column for it. The specification writes the predicate over one value and reads it over another
 * obtained from the first by a conversion - {@code String.valueOf(Object)} then
 * {@code String.toCharArray()} - and the write never reaches the read.
 *
 * <p>Two routes decide it, and which one applies depends on the substrate rather than on taste:
 *
 * <ul>
 *   <li>{@link Cause#INCOMPATIBLE_TYPES} - the declared type at a shared argument position differs
 *       between the two ends. A {@code byte[]} written and a {@code char[]} read are not the same
 *       key under any keying, and the conversion between them carries no bits of the original:
 *       {@code String.valueOf(byte[])} yields the identity string, measured as {@code "[B@726f3b58"};
 *   <li>{@link Cause#RECREATED_VALUE} - one end names a value that is constructed at the site. Under
 *       {@link PredicateSubstrate.Keying#IDENTITY} the reconstructed object is a different key and
 *       the predicate does not arrive at all; under {@link PredicateSubstrate.Keying#EQUALS} it
 *       arrives carrying whatever the conversion produced, which for a heap identity string is not
 *       a property of the value it names.
 * </ul>
 *
 * <p>Both ends of the finding are carried, never a summary. "The predicate does not propagate" is
 * unactionable; "this write, at this line, does not reach this read, at that line, because the
 * positions are typed {@code byte[]} and {@code char[]}" is a finding someone can adjudicate.
 *
 * @param predicate the predicate name, canonicalised
 * @param producer  the site that writes it
 * @param consumer  the site that reads it
 * @param cause     which of the two routes decided the edge is broken
 * @param detail    the route's evidence, stated in full
 */
public record PropagationBridge(String predicate, PredicateSiteFacts producer,
                                PredicateSiteFacts consumer, Cause cause, String detail) {

    public PropagationBridge {
        Objects.requireNonNull(predicate, "PropagationBridge.predicate is mandatory");
        Objects.requireNonNull(producer, "PropagationBridge.producer is mandatory");
        Objects.requireNonNull(consumer, "PropagationBridge.consumer is mandatory");
        Objects.requireNonNull(cause, "PropagationBridge.cause is mandatory");
        Objects.requireNonNull(detail, "PropagationBridge.detail is mandatory: an edge reported "
                + "broken without the evidence that decided it is an accusation, not a finding");
    }

    /** The two routes that decide a bridge from the graph. */
    public enum Cause {
        /** The declared types at a shared argument position differ. */
        INCOMPATIBLE_TYPES,
        /** One end names a value constructed at the site. */
        RECREATED_VALUE
    }

    /** The finding as one line, for a report or a failure message. */
    @Override
    public String toString() {
        return predicate + ": " + producer.ref().site() + " -> " + consumer.ref().site() + " ["
                + cause + "] " + detail;
    }
}
