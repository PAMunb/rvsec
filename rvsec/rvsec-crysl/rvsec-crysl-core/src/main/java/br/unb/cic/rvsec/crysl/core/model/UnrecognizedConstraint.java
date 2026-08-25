package br.unb.cic.rvsec.crysl.core.model;

import java.util.Objects;

/**
 * M3 met a {@code condition} or {@code action} whose idiom the reader does not follow.
 *
 * <p>Emitted instead of counting the clause absent: a minimal-scope extractor would otherwise
 * report eleven implemented clauses of the current corpus as missing, turning a limitation of the
 * instrument into an accusation against the specification.
 *
 * @param rawText the clause as written
 * @param site    where it was written
 */
public record UnrecognizedConstraint(String rawText, Provenance site) implements Unknown {

    public UnrecognizedConstraint {
        Objects.requireNonNull(rawText, "UnrecognizedConstraint.rawText is mandatory");
        Objects.requireNonNull(site, "UnrecognizedConstraint.site is mandatory");
    }
}
