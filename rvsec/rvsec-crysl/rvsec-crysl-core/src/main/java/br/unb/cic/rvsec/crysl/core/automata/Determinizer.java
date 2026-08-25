package br.unb.cic.rvsec.crysl.core.automata;

import br.unb.cic.rvsec.crysl.core.model.Guard;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Deque;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.TreeSet;

/**
 * Subset construction, plus the census that reports how often it was a no-op.
 *
 * <p>Determinization runs because it is required for correctness, not for speed. The Glushkov
 * construction of a rule of the form {@code ORDER con, a?, a} genuinely is non-deterministic: the
 * state after {@code con} carries two {@code a} edges, one into the optional occurrence and one
 * straight into the mandatory one. No rule of today's corpus has that shape, which is exactly why
 * the property is asserted on a synthetic rule rather than trusted to the corpus.
 *
 * <p>Guards are opaque to this construction. Two edges leaving one state on one signature are
 * non-determinism at the letter level whatever conditions they carry, so they merge; the merged
 * edge keeps a guard only when every edge that produced it carried the same one, and drops it
 * otherwise. Dropping is the honest outcome: a disjunction of guards is a guard this module has no
 * language to write, and inventing one would be a decision nobody reviewed. The guard is not part
 * of the language either way - {@link Automaton#accepts} does not read it.
 */
public final class Determinizer {

    /**
     * The rule behind every number {@link #census} publishes, printed beside it.
     *
     * <p>Stated because "already deterministic" has more than one defensible reading, and a count
     * without its rule is not a measurement.
     */
    public static final String COUNTING_RULE =
            "R-DET: an automaton counts as already deterministic when no state has two outgoing "
                    + "edges on the same signature. A partial transition function counts as "
                    + "deterministic - a missing edge is rejection, not choice. Guards are not "
                    + "consulted, because two edges on one letter are a choice whatever conditions "
                    + "they carry.";

    private Determinizer() {
    }

    /**
     * Whether the automaton already satisfies {@link #COUNTING_RULE}.
     */
    public static boolean isDeterministic(Automaton automaton) {
        for (String state : automaton.states()) {
            Set<Signature> seen = new HashSet<>();
            for (Transition transition : automaton.transitionsFrom(state)) {
                if (!seen.add(transition.symbol())) {
                    return false;
                }
            }
        }
        return true;
    }

    /**
     * The subset construction: an equivalent automaton with no state offering a choice.
     *
     * <p>Only reachable subsets are built, so the result is trimmed of unreachable states as a side
     * effect, and the transition function stays partial - the empty subset is never materialised as
     * a sink. {@link ProductSearch} adds the sink itself where it needs a total function, and
     * keeping it out here is what makes the result readable.
     */
    public static Automaton determinize(Automaton automaton) {
        List<Signature> alphabet = Alphabet.sorted(automaton.alphabet());

        Set<String> start = new TreeSet<>();
        start.add(automaton.initial());

        Set<String> states = new LinkedHashSet<>();
        Set<String> accepting = new LinkedHashSet<>();
        List<Transition> transitions = new ArrayList<>();

        Deque<Set<String>> pending = new ArrayDeque<>();
        Set<Set<String>> seen = new LinkedHashSet<>();
        pending.add(start);
        seen.add(start);
        states.add(name(start));

        while (!pending.isEmpty()) {
            Set<String> subset = pending.removeFirst();
            if (subset.stream().anyMatch(automaton.accepting()::contains)) {
                accepting.add(name(subset));
            }
            for (Signature symbol : alphabet) {
                Set<String> target = new TreeSet<>();
                Set<Optional<Guard>> guards = new LinkedHashSet<>();
                for (String state : subset) {
                    for (Transition transition : automaton.transitionsFrom(state)) {
                        if (transition.symbol().equals(symbol)) {
                            target.add(transition.to());
                            guards.add(transition.guard());
                        }
                    }
                }
                if (target.isEmpty()) {
                    continue;
                }
                if (seen.add(target)) {
                    states.add(name(target));
                    pending.addLast(target);
                }
                Optional<Guard> guard = guards.size() == 1
                        ? guards.iterator().next()
                        : Optional.empty();
                transitions.add(new Transition(name(subset), symbol, guard, name(target)));
            }
        }
        return new Automaton(states, name(start), accepting, transitions);
    }

    /**
     * How many of the given automata were already deterministic, with the rule that counted them.
     *
     * <p>This is the entry point the order metric calls to publish the measurement the spec asks
     * for over the upstream rule automata. It is deliberately a count this module computes and
     * never a value it asserts: the figure is a property of whatever corpus is handed in, and the
     * historical "all of them were" was measured over a corpus that has since been abandoned.
     */
    public static Census census(Collection<Automaton> automata) {
        int deterministic = 0;
        for (Automaton automaton : automata) {
            if (isDeterministic(automaton)) {
                deterministic++;
            }
        }
        return new Census(automata.size(), deterministic, COUNTING_RULE);
    }

    /**
     * The result of {@link #census}: two counts and the rule that produced them.
     *
     * @param total                the automata examined
     * @param alreadyDeterministic how many of them needed no subset construction
     * @param countingRule         the rule the count was made under
     */
    public record Census(int total, int alreadyDeterministic, String countingRule) {

        public Census {
            if (total < 0 || alreadyDeterministic < 0 || alreadyDeterministic > total) {
                throw new IllegalArgumentException(
                        "Census counts are inconsistent: " + alreadyDeterministic + " of " + total);
            }
            if (countingRule == null || countingRule.isBlank()) {
                throw new IllegalArgumentException(
                        "Census.countingRule is mandatory: a count without its rule is not a "
                                + "measurement");
            }
        }
    }

    /** The canonical name of a subset, so that two runs produce the same state names. */
    private static String name(Set<String> subset) {
        return "{" + String.join("|", new TreeSet<>(subset)) + "}";
    }
}
