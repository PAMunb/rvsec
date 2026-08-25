package br.unb.cic.rvsec.crysl.core.compare;

import br.unb.cic.rvsec.crysl.core.automata.Automaton;
import br.unb.cic.rvsec.crysl.core.automata.Transition;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

/**
 * The four operations M2 performs on a declared order before it compares one with the other.
 *
 * <p>Each one implements exactly one named normalization and nothing else, so that a verdict can
 * say which of them ran. None of them is applied by default and none of them decides on its own
 * whether to run: the erasure set comes from the alphabet map's {@code disposition} column, the
 * creator restriction comes from M0.1, the accepting-set narrowing comes from what the caller
 * declares predicate-only, and the relabeling comes from {@link CanonicalAlphabet}. This class
 * performs; it does not choose.
 *
 * <p>Guards are dropped by every operation that rebuilds a transition. They are a side condition on
 * an event, deciding one is M3's subject rather than M2's, and {@code Automaton.accepts} never
 * consults them - so carrying a guard through a rebuild would preserve a field that no longer
 * describes the edge it sits on.
 */
public final class OrderSurgery {

    private OrderSurgery() {
    }

    /**
     * Erases letters to &epsilon;: the language of the result is the image of the original under
     * the projection that deletes every erased letter.
     *
     * <p>Implemented as the &epsilon;-NFA the erasure denotes, with the &epsilon;-moves eliminated
     * on the spot: a state is accepting when the erased letters carry it to an accepting one, and
     * an edge on a surviving letter leaves the whole erased-closure of its source. The result may
     * be non-deterministic, which is fine - the product search determinizes both sides.
     */
    public static Automaton erase(Automaton automaton, Set<Signature> erased) {
        if (erased.isEmpty()) {
            return automaton;
        }
        List<Transition> transitions = new ArrayList<>();
        Set<String> accepting = new LinkedHashSet<>();
        for (String state : automaton.states()) {
            Set<String> closure = closure(automaton, state, erased);
            for (String reachable : closure) {
                if (automaton.accepting().contains(reachable)) {
                    accepting.add(state);
                }
                for (Transition transition : automaton.transitionsFrom(reachable)) {
                    if (!erased.contains(transition.symbol())) {
                        transitions.add(new Transition(state, transition.symbol(),
                                Optional.empty(), transition.to()));
                    }
                }
            }
        }
        return new Automaton(automaton.states(), automaton.initial(), accepting,
                dedupe(transitions));
    }

    /**
     * Deletes the given letters: the language of the result is the original restricted to words
     * that do not contain them.
     *
     * <p>Not the same operation as {@link #erase} and not interchangeable with it. Erasure says the
     * call happens and the other side has no symbol for it, so it is invisible; restriction says
     * the call cannot happen at all. N2 is a restriction - a {@code protected} method is not a call
     * a client program makes and then hides, it is a call a client program cannot make - and
     * erasing instead would make the rule accept the rest of the word without it, which is a
     * different and larger language.
     */
    public static Automaton restrict(Automaton automaton, Set<Signature> removed) {
        if (removed.isEmpty()) {
            return automaton;
        }
        List<Transition> transitions = automaton.transitions().stream()
                .filter(transition -> !removed.contains(transition.symbol()))
                .toList();
        return new Automaton(automaton.states(), automaton.initial(), automaton.accepting(),
                transitions);
    }

    /**
     * Renames every letter to the canonical letter it was identified with.
     *
     * <p>Letters absent from the map keep their identity: {@link CanonicalAlphabet} gives a letter
     * with no counterpart on the other side a component of its own, so absence here means the
     * caller handed in an automaton the alphabet was not built from, and silently dropping the edge
     * would shorten the language without saying so.
     */
    public static Automaton relabel(Automaton automaton, Map<Signature, Signature> canonical) {
        List<Transition> transitions = new ArrayList<>(automaton.transitions().size());
        for (Transition transition : automaton.transitions()) {
            Signature symbol = canonical.getOrDefault(transition.symbol(), transition.symbol());
            transitions.add(new Transition(transition.from(), symbol, Optional.empty(),
                    transition.to()));
        }
        return new Automaton(automaton.states(), automaton.initial(), automaton.accepting(),
                dedupe(transitions));
    }

    /**
     * Narrows the accepting set to the states the caller did not declare predicate-only (N3).
     *
     * <p>A {@code .mop} marks a state with an {@code alias match*} to give a predicate an
     * acceptance point, and such a state is not a legitimate end of the call sequence -
     * {@code CipherSpec}'s {@code alias match2 = s3} is where {@code encrypted[..] after updates}
     * fires, and a program that stops at {@code s3} has stopped in the middle of a cipher.
     */
    public static Automaton withoutAccepting(Automaton automaton, Set<String> predicateOnly) {
        Set<String> accepting = new LinkedHashSet<>(automaton.accepting());
        if (!accepting.removeAll(predicateOnly)) {
            return automaton;
        }
        return new Automaton(automaton.states(), automaton.initial(), accepting,
                automaton.transitions());
    }

    /**
     * Restricts the language to words carrying at most one creator letter (N1).
     *
     * <p>The product with a two-state counter: a word may pass through a creator once, and a second
     * creator has no edge. Sound only where the generated monitor indexes, which is why the caller
     * passes M0.1's answer rather than this class inspecting the automaton - a global monitor really
     * does see {@code g1 g1}, and the two cases are textually indistinguishable in the {@code .mop}.
     */
    public static Automaton atMostOneCreator(Automaton automaton, Set<Signature> creators) {
        if (creators.isEmpty()) {
            return automaton;
        }
        Set<String> states = new LinkedHashSet<>();
        Set<String> accepting = new LinkedHashSet<>();
        List<Transition> transitions = new ArrayList<>();
        for (String state : automaton.states()) {
            for (int seen = 0; seen <= 1; seen++) {
                String name = counted(state, seen);
                states.add(name);
                if (automaton.accepting().contains(state)) {
                    accepting.add(name);
                }
            }
        }
        for (String state : automaton.states()) {
            for (Transition transition : automaton.transitionsFrom(state)) {
                boolean creator = creators.contains(transition.symbol());
                for (int seen = 0; seen <= 1; seen++) {
                    if (creator && seen == 1) {
                        continue;
                    }
                    int next = creator ? 1 : seen;
                    transitions.add(new Transition(counted(state, seen), transition.symbol(),
                            Optional.empty(), counted(transition.to(), next)));
                }
            }
        }
        return new Automaton(states, counted(automaton.initial(), 0), accepting,
                dedupe(transitions));
    }

    /**
     * The letters that create the object the specification is keyed on: a constructor of the
     * declared type, or a call that returns it.
     *
     * <p>Decidable from the model alone, and it is the property N1 talks about - a monitor slice
     * begins when the object it is keyed on comes into existence. {@code KeyGenerator.getInstance}
     * returns a {@code KeyGenerator}, {@code new SecureRandom()} is a constructor, and
     * {@code KeyGenerator.init} is neither.
     */
    public static Set<Signature> creators(SpecModel model, Automaton automaton) {
        Set<Signature> creators = new LinkedHashSet<>();
        for (Signature signature : automaton.alphabet()) {
            boolean returnsIt = denote(signature.returnType(), model.type());
            boolean constructsIt = denote(signature.declaringType(), model.type())
                    && signature.name().equals(simpleName(model.type()));
            if (returnsIt || constructsIt) {
                creators.add(signature);
            }
        }
        return creators;
    }

    /**
     * Whether two type names denote the same type, tolerating one unqualified side.
     *
     * <p>A pointcut writes {@code KeyGenerator} where the model's declared type may be
     * {@code javax.crypto.KeyGenerator}, and the two are the same class. Two qualified names that
     * differ stay different, so this never merges types from different packages.
     */
    private static boolean denote(String left, String right) {
        if (left.equals(right)) {
            return true;
        }
        if (left.indexOf('.') >= 0 && right.indexOf('.') >= 0) {
            return false;
        }
        return simpleName(left).equals(simpleName(right));
    }

    private static String simpleName(String type) {
        int dot = type.lastIndexOf('.');
        return dot >= 0 ? type.substring(dot + 1) : type;
    }

    private static String counted(String state, int seen) {
        return state + "@" + seen;
    }

    private static Set<String> closure(Automaton automaton, String state, Set<Signature> erased) {
        Set<String> seen = new LinkedHashSet<>();
        Deque<String> pending = new ArrayDeque<>();
        seen.add(state);
        pending.add(state);
        while (!pending.isEmpty()) {
            String current = pending.removeFirst();
            for (Transition transition : automaton.transitionsFrom(current)) {
                if (erased.contains(transition.symbol()) && seen.add(transition.to())) {
                    pending.addLast(transition.to());
                }
            }
        }
        return seen;
    }

    private static List<Transition> dedupe(List<Transition> transitions) {
        return List.copyOf(new LinkedHashSet<>(transitions));
    }
}
