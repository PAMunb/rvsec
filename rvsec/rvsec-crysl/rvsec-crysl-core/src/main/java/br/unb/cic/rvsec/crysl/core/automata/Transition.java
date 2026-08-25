package br.unb.cic.rvsec.crysl.core.automata;

import br.unb.cic.rvsec.crysl.core.model.Guard;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import java.util.Objects;
import java.util.Optional;

/**
 * One edge of an {@link Automaton}: a move from one state to another on a signature, optionally
 * conditioned by a guard.
 *
 * <p>The symbol is a {@link Signature} and never a label, which is what lets the MOP-side and the
 * CrySL-side automata be compared at all (INV-CONF-03).
 *
 * @param from   source state
 * @param symbol the letter consumed
 * @param guard  the side condition of the move, when the source declares one
 * @param to     target state
 */
public record Transition(String from, Signature symbol, Optional<Guard> guard, String to) {

    public Transition {
        Objects.requireNonNull(from, "Transition.from is mandatory");
        Objects.requireNonNull(symbol, "Transition.symbol is mandatory");
        Objects.requireNonNull(guard, "Transition.guard is mandatory (use Optional.empty())");
        Objects.requireNonNull(to, "Transition.to is mandatory");
    }
}
