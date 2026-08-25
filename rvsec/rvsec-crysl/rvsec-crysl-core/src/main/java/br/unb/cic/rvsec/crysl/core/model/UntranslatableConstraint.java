package br.unb.cic.rvsec.crysl.core.model;

import java.util.Objects;

/**
 * A CrySL clause that runtime verification cannot express: it is about the static type of the
 * origin ({@code neverTypeOf}, {@code notHardCoded}) or it is a liveness obligation over
 * {@code ORDER} symbols ({@code callTo}), rather than about a runtime value.
 *
 * <p>{@code noCallTo} is deliberately not in this family: a prohibition is a safety property and
 * its violation is observable at the moment it happens.
 *
 * <p>These clauses are refused rather than commented, because a comment is not countable and does
 * not enter a metric.
 *
 * @param clause the clause as written
 * @param family the untranslatable family it belongs to, e.g. {@code neverTypeOf}
 * @param site   where it was written
 */
public record UntranslatableConstraint(String clause, String family, Provenance site)
        implements Unknown {

    public UntranslatableConstraint {
        Objects.requireNonNull(clause, "UntranslatableConstraint.clause is mandatory");
        Objects.requireNonNull(family, "UntranslatableConstraint.family is mandatory");
        Objects.requireNonNull(site, "UntranslatableConstraint.site is mandatory");
    }
}
