package br.unb.cic.rvsec.crysl.core.automata;

import br.unb.cic.rvsec.crysl.core.model.Signature;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.TreeSet;

/**
 * Hopcroft partition refinement, followed by a canonical renaming of the surviving states.
 *
 * <p>Minimization is what lets {@code a,(b|c)} and {@code (a,b)|(a,c)} compare equal. They are the
 * same language written two ways, and a comparison that worked over the shape of the formula would
 * report a divergence that does not exist - the specification and the rule are then accused of
 * disagreeing about an order they agree about.
 *
 * <p>The result is the unique minimal trimmed deterministic automaton of the language, with states
 * renamed {@code q0, q1, ...} by a breadth-first walk that visits letters in canonical order. The
 * renaming is what turns the uniqueness theorem into something a test can assert: two automata
 * accept the same language if and only if their minimal forms are equal as records.
 */
public final class Minimizer {

    /** The single state of the canonical automaton of the empty language. */
    private static final String EMPTY_LANGUAGE_STATE = "q0";

    private Minimizer() {
    }

    /**
     * The canonical minimal automaton of {@code L(automaton)}.
     *
     * <p>Determinization runs first, unconditionally: partition refinement is only correct over a
     * deterministic transition function, and the input is allowed to be non-deterministic.
     */
    public static Automaton minimize(Automaton automaton) {
        Automaton dfa = Determinizer.determinize(automaton);
        List<Signature> alphabet = Alphabet.sorted(dfa.alphabet());

        String sink = freshSinkName(dfa.states());
        Map<String, Map<Signature, String>> delta = totalTransitionFunction(dfa, alphabet, sink);

        Map<String, String> blockOf = refine(delta, alphabet, dfa.accepting());
        return canonicalize(blockOf, delta, alphabet, dfa.initial(), dfa.accepting());
    }

    /**
     * The transition function of {@code dfa} made total by routing every missing edge to a sink.
     *
     * <p>Partition refinement needs a total function: two states are distinguishable when one has
     * an edge the other lacks, and with a partial function that difference is invisible to the
     * refinement loop. The sink is removed again at the end, because it is dead by construction.
     */
    private static Map<String, Map<Signature, String>> totalTransitionFunction(
            Automaton dfa, List<Signature> alphabet, String sink) {
        Map<String, Map<Signature, String>> delta = new LinkedHashMap<>();
        for (String state : new TreeSet<>(dfa.states())) {
            Map<Signature, String> row = new LinkedHashMap<>();
            for (Transition transition : dfa.transitionsFrom(state)) {
                row.put(transition.symbol(), transition.to());
            }
            for (Signature symbol : alphabet) {
                row.putIfAbsent(symbol, sink);
            }
            delta.put(state, row);
        }
        Map<Signature, String> sinkRow = new LinkedHashMap<>();
        for (Signature symbol : alphabet) {
            sinkRow.put(symbol, sink);
        }
        delta.put(sink, sinkRow);
        return delta;
    }

    /** Hopcroft's algorithm; returns the block each state belongs to, named by its smallest member. */
    private static Map<String, String> refine(Map<String, Map<Signature, String>> delta,
                                              List<Signature> alphabet, Set<String> accepting) {
        Set<String> all = new TreeSet<>(delta.keySet());
        Set<String> finals = new TreeSet<>(all);
        finals.retainAll(accepting);
        Set<String> nonFinals = new TreeSet<>(all);
        nonFinals.removeAll(accepting);

        List<Set<String>> partition = new ArrayList<>();
        Deque<Splitter> worklist = new ArrayDeque<>();
        if (finals.isEmpty() || nonFinals.isEmpty()) {
            partition.add(all);
        } else {
            partition.add(finals);
            partition.add(nonFinals);
            Set<String> smaller = finals.size() <= nonFinals.size() ? finals : nonFinals;
            for (Signature symbol : alphabet) {
                worklist.addLast(new Splitter(smaller, symbol));
            }
        }

        Map<Signature, Map<String, Set<String>>> predecessors = predecessors(delta, alphabet);

        while (!worklist.isEmpty()) {
            Splitter splitter = worklist.removeFirst();
            Set<String> reaching = new TreeSet<>();
            Map<String, Set<String>> bySymbol = predecessors.get(splitter.symbol());
            for (String target : splitter.block()) {
                reaching.addAll(bySymbol.getOrDefault(target, Set.of()));
            }
            if (reaching.isEmpty()) {
                continue;
            }
            for (Set<String> block : List.copyOf(partition)) {
                Set<String> inside = new TreeSet<>(block);
                inside.retainAll(reaching);
                if (inside.isEmpty() || inside.size() == block.size()) {
                    continue;
                }
                Set<String> outside = new TreeSet<>(block);
                outside.removeAll(reaching);
                partition.remove(block);
                partition.add(inside);
                partition.add(outside);
                for (Signature symbol : alphabet) {
                    Splitter pending = new Splitter(block, symbol);
                    if (worklist.remove(pending)) {
                        worklist.addLast(new Splitter(inside, symbol));
                        worklist.addLast(new Splitter(outside, symbol));
                    } else {
                        worklist.addLast(new Splitter(
                                inside.size() <= outside.size() ? inside : outside, symbol));
                    }
                }
            }
        }

        Map<String, String> blockOf = new HashMap<>();
        for (Set<String> block : partition) {
            String name = new TreeSet<>(block).first();
            for (String state : block) {
                blockOf.put(state, name);
            }
        }
        return blockOf;
    }

    /** For each letter, which states move into which target: the reverse of {@code delta}. */
    private static Map<Signature, Map<String, Set<String>>> predecessors(
            Map<String, Map<Signature, String>> delta, List<Signature> alphabet) {
        Map<Signature, Map<String, Set<String>>> reverse = new LinkedHashMap<>();
        for (Signature symbol : alphabet) {
            reverse.put(symbol, new LinkedHashMap<>());
        }
        for (Map.Entry<String, Map<Signature, String>> row : delta.entrySet()) {
            for (Map.Entry<Signature, String> edge : row.getValue().entrySet()) {
                reverse.get(edge.getKey())
                        .computeIfAbsent(edge.getValue(), key -> new TreeSet<>())
                        .add(row.getKey());
            }
        }
        return reverse;
    }

    /**
     * The quotient automaton, trimmed of every state that cannot reach an accepting one and renamed
     * by a breadth-first walk in canonical letter order.
     *
     * <p>Trimming is what removes the sink again, and the walk is what makes the naming independent
     * of the names the input happened to carry.
     */
    private static Automaton canonicalize(Map<String, String> blockOf,
                                          Map<String, Map<Signature, String>> delta,
                                          List<Signature> alphabet, String initial,
                                          Set<String> accepting) {
        String initialBlock = blockOf.get(initial);
        Set<String> acceptingBlocks = new TreeSet<>();
        for (String state : accepting) {
            acceptingBlocks.add(blockOf.get(state));
        }
        Map<String, Map<Signature, String>> quotient = new LinkedHashMap<>();
        for (Map.Entry<String, Map<Signature, String>> row : delta.entrySet()) {
            Map<Signature, String> blockRow =
                    quotient.computeIfAbsent(blockOf.get(row.getKey()), key -> new LinkedHashMap<>());
            for (Map.Entry<Signature, String> edge : row.getValue().entrySet()) {
                blockRow.put(edge.getKey(), blockOf.get(edge.getValue()));
            }
        }

        Set<String> productive = productiveBlocks(quotient, acceptingBlocks);
        if (!productive.contains(initialBlock)) {
            return emptyLanguage();
        }

        Map<String, String> renamed = new LinkedHashMap<>();
        List<Transition> transitions = new ArrayList<>();
        Deque<String> pending = new ArrayDeque<>();
        renamed.put(initialBlock, "q" + renamed.size());
        pending.add(initialBlock);
        while (!pending.isEmpty()) {
            String block = pending.removeFirst();
            for (Signature symbol : alphabet) {
                String target = quotient.get(block).get(symbol);
                if (!productive.contains(target)) {
                    continue;
                }
                if (!renamed.containsKey(target)) {
                    renamed.put(target, "q" + renamed.size());
                    pending.addLast(target);
                }
                transitions.add(new Transition(renamed.get(block), symbol, Optional.empty(),
                        renamed.get(target)));
            }
        }
        Set<String> finalAccepting = new LinkedHashSet<>();
        for (String block : acceptingBlocks) {
            if (renamed.containsKey(block)) {
                finalAccepting.add(renamed.get(block));
            }
        }
        return new Automaton(new LinkedHashSet<>(renamed.values()), renamed.get(initialBlock),
                finalAccepting, transitions);
    }

    /** The blocks from which an accepting block is reachable. */
    private static Set<String> productiveBlocks(Map<String, Map<Signature, String>> quotient,
                                                Set<String> acceptingBlocks) {
        Set<String> productive = new LinkedHashSet<>(acceptingBlocks);
        boolean grew = true;
        while (grew) {
            grew = false;
            for (Map.Entry<String, Map<Signature, String>> row : quotient.entrySet()) {
                if (productive.contains(row.getKey())) {
                    continue;
                }
                if (row.getValue().values().stream().anyMatch(productive::contains)) {
                    productive.add(row.getKey());
                    grew = true;
                }
            }
        }
        return productive;
    }

    /**
     * The canonical automaton of the empty language: one state, accepting nothing.
     *
     * <p>Every empty language collapses to this same record whatever alphabet it was written over,
     * which is what keeps the equality test meaningful at the degenerate end.
     */
    private static Automaton emptyLanguage() {
        return new Automaton(Set.of(EMPTY_LANGUAGE_STATE), EMPTY_LANGUAGE_STATE, Set.of(), List.of());
    }

    /** A state name no state of the automaton uses, so the sink cannot be mistaken for a real one. */
    private static String freshSinkName(Set<String> states) {
        String candidate = "sink";
        int suffix = 0;
        while (states.contains(candidate)) {
            candidate = "sink" + suffix++;
        }
        return candidate;
    }

    /** One entry of Hopcroft's worklist: a block to split against, and the letter to split on. */
    private record Splitter(Set<String> block, Signature symbol) {
    }
}
