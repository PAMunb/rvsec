package br.unb.cic.rvsec.crysl.core.model;

import java.util.List;
import java.util.Objects;
import java.util.Optional;

/**
 * The word that distinguishes two languages in an M2 verdict, together with everything a reader
 * needs in order to know what it does and does not prove.
 *
 * <p>The {@code harness} is present if and only if the status is {@link WitnessStatus#CONCRETE}:
 * a concrete witness that cannot name what ran it is indistinguishable from an abstract one, and an
 * abstract witness carrying a harness claims an execution that never happened. Enforced here rather
 * than at emission so that no code path can build the inconsistent pair. INV-CONF-08.
 *
 * @param word           the witness, over the signature alphabet
 * @param status         abstract word or executed trace
 * @param normalizations the transformations applied to obtain it
 * @param harness        identifier of the harness and trace that executed it; present iff CONCRETE
 */
public record Witness(List<Signature> word, WitnessStatus status,
                      List<Normalization> normalizations, Optional<String> harness) {

    public Witness {
        Objects.requireNonNull(status, "Witness.status is mandatory");
        Objects.requireNonNull(harness, "Witness.harness is mandatory (use Optional.empty())");
        word = List.copyOf(word);
        normalizations = List.copyOf(normalizations);
        boolean concrete = status == WitnessStatus.CONCRETE;
        if (concrete != harness.isPresent()) {
            throw new IllegalArgumentException(
                    "Witness.harness must be present iff status == CONCRETE (INV-CONF-08); status="
                            + status + ", harness=" + harness);
        }
    }
}
