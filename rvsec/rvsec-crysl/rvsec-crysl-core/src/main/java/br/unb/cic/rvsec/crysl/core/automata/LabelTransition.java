package br.unb.cic.rvsec.crysl.core.automata;

import br.unb.cic.rvsec.crysl.core.model.Label;
import java.util.Objects;

/**
 * One edge of a {@link LabelAutomaton}: a move on the name of an event rather than on a signature.
 *
 * @param from   source state
 * @param symbol the label consumed
 * @param to     target state
 */
public record LabelTransition(String from, Label symbol, String to) {

    public LabelTransition {
        Objects.requireNonNull(from, "LabelTransition.from is mandatory");
        Objects.requireNonNull(symbol, "LabelTransition.symbol is mandatory");
        Objects.requireNonNull(to, "LabelTransition.to is mandatory");
    }
}
