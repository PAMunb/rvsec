package br.unb.cic.rvsec.crysl.core.automata;

import br.unb.cic.rvsec.crysl.core.model.Label;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;

/**
 * An automaton over event labels: the language an {@code ere} formula denotes, before the inverse
 * morphism turns it into a language over signatures.
 *
 * <p>This type is deliberately the only place labels appear in an automaton, and it is not a model
 * type. A {@code .mop} formula is written over the names its {@code event} declarations introduce,
 * so a lifter has no choice but to build the label language first; INV-CONF-03 governs what is then
 * <em>kept</em>, and what is kept is the signature automaton {@link InverseMorphism} produces from
 * this one. Nothing here is stored in a {@code SpecModel}.
 *
 * <p>It carries no operations of its own beyond following a word, because it never needs any: it is
 * consumed by {@link InverseMorphism} immediately and the four language operations all run on the
 * signature side.
 *
 * @param states      every state name
 * @param initial     the initial state, an element of {@code states}
 * @param accepting   the accepting states, a subset of {@code states}
 * @param transitions the edges
 */
public record LabelAutomaton(Set<String> states, String initial, Set<String> accepting,
                             List<LabelTransition> transitions) {

    public LabelAutomaton {
        Objects.requireNonNull(initial, "LabelAutomaton.initial is mandatory");
        states = Set.copyOf(states);
        accepting = Set.copyOf(accepting);
        transitions = List.copyOf(transitions);
        if (!states.contains(initial)) {
            throw new IllegalArgumentException(
                    "LabelAutomaton.initial is not among the states: " + initial);
        }
        if (!states.containsAll(accepting)) {
            throw new IllegalArgumentException(
                    "LabelAutomaton.accepting is not a subset of the states");
        }
        for (LabelTransition transition : transitions) {
            if (!states.contains(transition.from()) || !states.contains(transition.to())) {
                throw new IllegalArgumentException(
                        "LabelAutomaton transition leaves the state set: " + transition);
            }
        }
    }

    /**
     * The states reachable from {@code from} by reading {@code word}.
     *
     * <p>A set rather than a state, because the label automaton a lifter builds is allowed to be
     * non-deterministic and because the inverse morphism needs the whole set: every state the image
     * of a signature can lead to becomes a target of that signature's edge.
     */
    public Set<String> follow(Set<String> from, List<Label> word) {
        Set<String> current = new LinkedHashSet<>(from);
        for (Label symbol : word) {
            Set<String> next = new LinkedHashSet<>();
            for (LabelTransition transition : transitions) {
                if (current.contains(transition.from()) && transition.symbol().equals(symbol)) {
                    next.add(transition.to());
                }
            }
            current = next;
            if (current.isEmpty()) {
                return Set.of();
            }
        }
        return current;
    }
}
