package br.unb.cic.rvsec.crysl.core.model;

import java.util.Objects;

/**
 * One clause of a {@code CONSTRAINTS} section, or the specification-side idiom that implements one,
 * kept as the text it was written with plus where it was written.
 *
 * <p>Constraints are held in a {@code List} and never in a {@code Set}: two identical clauses at
 * different sites are two clauses, and a set collapses them into one, which silently moves every
 * denominator M3 publishes.
 *
 * @param text the clause as written, with comments already removed by the lifter
 * @param site where the clause was declared
 */
public record Constraint(String text, Provenance site) {

    public Constraint {
        Objects.requireNonNull(text, "Constraint.text is mandatory");
        Objects.requireNonNull(site, "Constraint.site is mandatory");
    }
}
