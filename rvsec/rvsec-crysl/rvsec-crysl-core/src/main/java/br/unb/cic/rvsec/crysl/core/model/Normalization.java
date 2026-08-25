package br.unb.cic.rvsec.crysl.core.model;

import java.util.Objects;

/**
 * One transformation applied to an automaton or to a word before a comparison was made, e.g. the
 * erasure of an event the alphabet map declares unmapped.
 *
 * <p>Normalizations are published beside every verdict and every witness because a comparison is
 * only meaningful under the transformations it was made modulo: "equivalent" under two erasures and
 * "equivalent" outright are different claims.
 *
 * @param id          short identifier used in verdict text, e.g. {@code N1}
 * @param description what the transformation did and on whose authority
 */
public record Normalization(String id, String description) {

    public Normalization {
        Objects.requireNonNull(id, "Normalization.id is mandatory");
        Objects.requireNonNull(description, "Normalization.description is mandatory");
    }
}
