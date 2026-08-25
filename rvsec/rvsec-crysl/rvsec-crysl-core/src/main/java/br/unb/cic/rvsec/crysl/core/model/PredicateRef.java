package br.unb.cic.rvsec.crysl.core.model;

import java.util.List;
import java.util.Objects;

/**
 * One reference to a predicate, as it appears in an {@code ENSURES}, {@code REQUIRES} or
 * {@code NEGATES} section.
 *
 * <p>The section is the list the reference is held in on {@link SpecModel}; the {@link Polarity} is
 * a field, because the two are independent inside {@code REQUIRES}: {@code Mac.crysl:51} requires
 * {@code !encrypted[...]} next to positive requirements in the same block, and
 * {@code jca_android/MacSpec.mop:307} writes the same demand as {@code validateAbsent}. See
 * {@link Polarity} for why that cannot be folded back into the section.
 *
 * <p>Like {@link Constraint}, predicate references are held in a {@code List}: the same predicate
 * ensured at two sites is two edges of the M4 graph with different provenance.
 *
 * @param name      the predicate name, bare — never carrying a {@code !}
 * @param arguments the argument names as written; the arity is {@code arguments.size()} and the
 *                  argument position is the index, both of which M4 compares
 * @param polarity  whether the reference asks for the predicate or for its absence
 * @param site      where the reference was declared
 */
public record PredicateRef(String name, List<String> arguments, Polarity polarity, Provenance site) {

    public PredicateRef {
        Objects.requireNonNull(name, "PredicateRef.name is mandatory");
        Objects.requireNonNull(polarity, "PredicateRef.polarity is mandatory: a reference with an "
                + "unknown polarity is the defect this field exists to prevent, and defaulting it "
                + "to POSITIVE would silently restore it");
        Objects.requireNonNull(site, "PredicateRef.site is mandatory");
        arguments = List.copyOf(arguments);
    }
}
