package br.unb.cic.rvsec.crysl.core.automata;

import br.unb.cic.rvsec.crysl.core.model.Signature;
import java.util.ArrayDeque;
import java.util.Collections;
import java.util.Deque;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;

/**
 * A symbolic finite automaton over signatures: the shape both an {@code ere} formula and a CrySL
 * {@code ORDER} are lifted to.
 *
 * <p>The record carries the representation and the queries a reader of the representation needs -
 * its alphabet, the edges out of a state, which states the initial one reaches, and whether a word
 * is accepted. Determinization, minimization, the product construction and the inverse morphism are
 * the four language operations, and they live in their own classes; keeping them out of the record
 * is what allows the model module to stay free of the comparison logic.
 *
 * <p>The alphabet is <em>derived</em> from the transitions rather than declared as a component. A
 * symbol nothing reads is not part of any language, and the one case where the distinction is
 * visible - a symbol reachable from no state - is representable anyway, as an edge leaving a state
 * the initial one cannot reach.
 *
 * <p>The automaton may be non-deterministic: the Glushkov construction of a rule of the form
 * {@code ORDER con, a?, a} genuinely is, which is why M2 determinizes before comparing instead of
 * assuming the corpus happens to be deterministic.
 *
 * @param states      every state name
 * @param initial     the initial state, an element of {@code states}
 * @param accepting   the accepting states, a subset of {@code states}
 * @param transitions the edges
 */
public record Automaton(Set<String> states, String initial, Set<String> accepting,
                        List<Transition> transitions) {

    public Automaton {
        Objects.requireNonNull(initial, "Automaton.initial is mandatory");
        states = Set.copyOf(states);
        accepting = Set.copyOf(accepting);
        transitions = List.copyOf(transitions);
        if (!states.contains(initial)) {
            throw new IllegalArgumentException("Automaton.initial is not among the states: " + initial);
        }
        if (!states.containsAll(accepting)) {
            throw new IllegalArgumentException("Automaton.accepting is not a subset of the states");
        }
        for (Transition transition : transitions) {
            if (!states.contains(transition.from()) || !states.contains(transition.to())) {
                throw new IllegalArgumentException(
                        "Automaton transition leaves the state set: " + transition);
            }
        }
    }

    /** The letters that appear on some edge, in canonical order. */
    public Set<Signature> alphabet() {
        Set<Signature> symbols = new LinkedHashSet<>();
        for (Transition transition : transitions) {
            symbols.add(transition.symbol());
        }
        return Collections.unmodifiableSet(symbols);
    }

    /** The edges leaving {@code state}. */
    public List<Transition> transitionsFrom(String state) {
        return transitions.stream().filter(t -> t.from().equals(state)).toList();
    }

    /** The states {@link #initial} reaches, itself included. */
    public Set<String> reachableStates() {
        Set<String> seen = new LinkedHashSet<>();
        Deque<String> pending = new ArrayDeque<>();
        seen.add(initial);
        pending.add(initial);
        while (!pending.isEmpty()) {
            String current = pending.removeFirst();
            for (Transition transition : transitionsFrom(current)) {
                if (seen.add(transition.to())) {
                    pending.addLast(transition.to());
                }
            }
        }
        return Collections.unmodifiableSet(seen);
    }

    /**
     * Whether the word is in the language, by simulating the automaton over the set of states it
     * may be in - so this answers correctly whether or not the automaton is deterministic.
     *
     * <p>Guards are not consulted: they are a side condition on the event, and deciding one is M3's
     * subject rather than M2's. See {@link Determinizer} for what that costs when edges merge.
     */
    public boolean accepts(List<Signature> word) {
        Set<String> current = new LinkedHashSet<>();
        current.add(initial);
        for (Signature symbol : word) {
            Set<String> next = new LinkedHashSet<>();
            for (String state : current) {
                for (Transition transition : transitionsFrom(state)) {
                    if (transition.symbol().equals(symbol)) {
                        next.add(transition.to());
                    }
                }
            }
            if (next.isEmpty()) {
                return false;
            }
            current = next;
        }
        return current.stream().anyMatch(accepting::contains);
    }
}
