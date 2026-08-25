package br.unb.cic.rvsec.crysl.core.model;

import java.util.Objects;

/**
 * The specification declares no place from which it could ever accuse, so M0 refuses it and M1-M4
 * emit no verdict for it (INV-CONF-09).
 *
 * <p>This is not {@link UnresolvedSignature}, and the distance between the two is the reason this
 * tag exists. {@code UnresolvedSignature} says the platform does not carry a class the pointcut
 * names: the specification would accuse, and the target is absent. This tag says the opposite about
 * the same silence — the target is there, the monitor is live, its automaton changes state, and
 * there is no {@code @fail} with a body and no {@code addError} in any event body the formula
 * admits. No trace can make it report. Emitting one under the other's name would put a wrong reason
 * in a countable column, which is the failure the typed taxonomy exists to prevent.
 *
 * <p>Two specifications of the corpora are exactly this, in both {@code jca} and
 * {@code jca_android}: {@code RandomStringPassword.mop}, which declares an empty {@code @match} and
 * no {@code @fail}, and {@code SecretKeySpec.mop}, whose {@code @match} is not empty — it writes a
 * predicate — and which still has nowhere to report from. The second is why the tag names the
 * criterion rather than the witness: "an empty {@code @match} and no {@code @fail}" is one instance
 * of "the accusation site is not reachable", not a definition of it.
 *
 * @param specification the specification refused, named by its {@code .mop} file without the
 *                      extension, because a refusal attributed to a declared type the reader cannot
 *                      find the file for is not actionable
 * @param evidence      what the file does declare — the state of {@code @fail}, the {@code @match}
 *                      keys it writes — so the refusal can be checked against the file rather than
 *                      believed
 * @param site          where the specification itself is declared
 */
public record UnreachableAccusationSite(String specification, String evidence, Provenance site)
        implements Unknown {

    public UnreachableAccusationSite {
        Objects.requireNonNull(specification,
                "UnreachableAccusationSite.specification is mandatory");
        Objects.requireNonNull(site, "UnreachableAccusationSite.site is mandatory");
        if (evidence == null || evidence.isBlank()) {
            throw new IllegalArgumentException("UnreachableAccusationSite.evidence is mandatory: a "
                    + "refusal that names no evidence cannot be checked against the file");
        }
    }
}
