package br.unb.cic.rvsec.crysl.core.automata;

import br.unb.cic.rvsec.crysl.core.model.Normalization;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import br.unb.cic.rvsec.crysl.core.model.Witness;
import br.unb.cic.rvsec.crysl.core.model.WitnessStatus;
import java.util.List;
import java.util.Objects;
import java.util.Optional;

/**
 * The one place a {@link Witness} is built, and the reason there is only one.
 *
 * <p>INV-CONF-08 requires every published witness to carry its status and the normalizations that
 * produced it. Two of the three ways to get that wrong are closed by the {@code Witness} record
 * itself, which rejects a null status and a harness inconsistent with it. The third - a word
 * travelling out of the comparison with nobody having said what it was compared modulo - is closed
 * here: the search returns words, this class is the only thing that turns a word into a witness,
 * and both of its methods demand the normalization list.
 *
 * <p>The list may be empty. "Compared modulo nothing" is a real and stronger claim than "compared
 * modulo two erasures", and stating it explicitly is the point; what is refused is not stating it.
 */
public final class Witnesses {

    private Witnesses() {
    }

    /**
     * A word over the alphabet, produced by search and never executed.
     *
     * <p>This is the status a product-search witness always has. A word accepted by an automaton is
     * not an executable trace - {@code javax.crypto.Cipher} carries a mode state machine that
     * neither the specification nor the rule models - so no caller may attach a false-positive or
     * false-negative claim to what this returns.
     */
    public static Witness abstractWitness(List<Signature> word,
                                          List<Normalization> normalizations) {
        Objects.requireNonNull(word, "a witness needs its word");
        Objects.requireNonNull(normalizations,
                "a witness must carry the normalizations applied to reach it (INV-CONF-08); pass "
                        + "an empty list to state that none were");
        return new Witness(word, WitnessStatus.ABSTRACT, normalizations, Optional.empty());
    }

    /**
     * A trace that was executed, naming the harness that executed it.
     *
     * <p>The harness is mandatory and is what separates this from the abstract case: a concrete
     * witness that cannot name what ran it is indistinguishable from one that was never run.
     */
    public static Witness concreteWitness(List<Signature> word,
                                          List<Normalization> normalizations, String harness) {
        Objects.requireNonNull(word, "a witness needs its word");
        Objects.requireNonNull(normalizations,
                "a witness must carry the normalizations applied to reach it (INV-CONF-08); pass "
                        + "an empty list to state that none were");
        Objects.requireNonNull(harness,
                "a CONCRETE witness must name the harness that executed it (INV-CONF-08)");
        return new Witness(word, WitnessStatus.CONCRETE, normalizations, Optional.of(harness));
    }
}
