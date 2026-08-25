package br.unb.cic.rvsec.crysl.core.metric;

import br.unb.cic.rvsec.crysl.core.model.Provenance;
import br.unb.cic.rvsec.crysl.core.model.Unknown;
import java.util.Objects;
import java.util.Optional;

/**
 * What M3 concluded about one {@code CONSTRAINTS} clause.
 *
 * <p>One row per clause of the rule, so the aggregate is always re-derivable from the rows and a
 * reader who distrusts the total can check it line by line. The three dispositions are mutually
 * exclusive by construction: an {@code idiom} means the specification implements the clause, a
 * {@code refusal} means the reader could not decide, and neither means the clause is absent. That
 * exclusivity is the whole reason this record exists — a census that collapsed "could not read" into
 * "is not there" would report the reader's limits as the specification's defects.
 *
 * @param clause            the clause as the CrySL façade rendered it
 * @param family            the shape it has, and therefore the route M3 took
 * @param idiom             the idiom that implements it, empty when nothing was found
 * @param aliasTableService the {@code ConscryptAliasTable} service the check goes through, empty
 *                          when it goes through none — see below
 * @param evidence          the specification text that was matched, so the reader can judge it
 * @param site              where in the specification that text is
 * @param refusal           the typed refusal, when the reader declined to decide
 * @param ruleSite          where in the rule the clause is
 */
public record ClauseVerdict(String clause, ClauseFamily family,
                            Optional<M3Result.Idiom> idiom,
                            Optional<String> aliasTableService,
                            Optional<String> evidence,
                            Optional<Provenance> site,
                            Optional<Unknown> refusal,
                            Provenance ruleSite) {

    public ClauseVerdict {
        Objects.requireNonNull(clause, "ClauseVerdict.clause is mandatory");
        Objects.requireNonNull(family, "ClauseVerdict.family is mandatory");
        Objects.requireNonNull(idiom, "ClauseVerdict.idiom is mandatory (use Optional.empty())");
        Objects.requireNonNull(aliasTableService, "ClauseVerdict.aliasTableService is mandatory");
        Objects.requireNonNull(evidence, "ClauseVerdict.evidence is mandatory");
        Objects.requireNonNull(site, "ClauseVerdict.site is mandatory");
        Objects.requireNonNull(refusal, "ClauseVerdict.refusal is mandatory");
        Objects.requireNonNull(ruleSite, "ClauseVerdict.ruleSite is mandatory");
        if (idiom.isPresent() && refusal.isPresent()) {
            throw new IllegalArgumentException("a clause is implemented or refused, never both: "
                    + clause);
        }
    }

    /** Whether the specification implements this clause through a recognised idiom. */
    public boolean implemented() {
        return idiom.isPresent();
    }

    /** Whether the reader declined to decide — this is the ceiling of the instrument. */
    public boolean refused() {
        return refusal.isPresent();
    }

    /** Whether the clause is genuinely not implemented, as opposed to not readable. */
    public boolean absent() {
        return idiom.isEmpty() && refusal.isEmpty();
    }

    /**
     * Whether the check the specification performs is widened by the alias table.
     *
     * <p>This is not decoration. An allow-list transcribed character for character from the rule is
     * <em>more permissive</em> than the rule when it is consulted through {@code
     * ConscryptAliasTable.matches(…)}, because the table maps platform spellings onto the list's
     * entries and the rule maps nothing. A literal extractor comparing the two lists would answer
     * "conformant"; the correct verdict is "more permissive". The dependency is recorded here, per
     * clause, and the weight of it is read from the table itself — it is distributed very unevenly
     * across services, down to services with a dependency and no rows at all.
     */
    public boolean widenedByAliasTable() {
        return aliasTableService.isPresent();
    }
}
