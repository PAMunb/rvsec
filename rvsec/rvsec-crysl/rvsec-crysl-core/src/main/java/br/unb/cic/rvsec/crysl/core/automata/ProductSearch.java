package br.unb.cic.rvsec.crysl.core.automata;

import br.unb.cic.rvsec.crysl.core.metric.M2Result;
import br.unb.cic.rvsec.crysl.core.model.Normalization;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import br.unb.cic.rvsec.crysl.core.model.Witness;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

/**
 * Emptiness of {@code L(A) INTERSECT complement(L(B))} in both directions, returning the shortest
 * word that separates the two languages or reporting that none exists.
 *
 * <p>Shortest is a requirement rather than a convenience. The witness is the part of the verdict a
 * reader actually reads, and a witness twelve calls long says nothing a reader can check by hand.
 * Breadth-first search over the product gives the shortest word for free, and visiting letters in
 * canonical order makes the choice among equally short witnesses reproducible across runs.
 *
 * <p>Both sides are determinized and completed over the <em>union</em> of the two alphabets before
 * the search. Completing over either alphabet alone would make the two languages agree about every
 * word built from a letter the other side never mentions.
 */
public final class ProductSearch {

    private ProductSearch() {
    }

    /**
     * The shortest word accepted by {@code accepted} and rejected by {@code rejected}, or empty
     * when {@code L(accepted)} is contained in {@code L(rejected)}.
     */
    public static Optional<List<Signature>> shortestAcceptedOnlyBy(Automaton accepted,
                                                                  Automaton rejected) {
        List<Signature> alphabet = Alphabet.union(accepted, rejected);
        Dfa left = Dfa.of(accepted, alphabet);
        Dfa right = Dfa.of(rejected, alphabet);

        Deque<Search> pending = new ArrayDeque<>();
        Set<String> seen = new LinkedHashSet<>();
        pending.add(new Search(left.initial(), right.initial(), List.of()));
        seen.add(left.initial() + "#" + right.initial());

        while (!pending.isEmpty()) {
            Search current = pending.removeFirst();
            if (left.accepting().contains(current.left())
                    && !right.accepting().contains(current.right())) {
                return Optional.of(current.word());
            }
            for (Signature symbol : alphabet) {
                String nextLeft = left.step(current.left(), symbol);
                String nextRight = right.step(current.right(), symbol);
                if (!seen.add(nextLeft + "#" + nextRight)) {
                    continue;
                }
                List<Signature> word = new ArrayList<>(current.word());
                word.add(symbol);
                pending.addLast(new Search(nextLeft, nextRight, List.copyOf(word)));
            }
        }
        return Optional.empty();
    }

    /**
     * The comparison in both directions, which is what an order verdict is made of.
     *
     * <p>The two arguments are named for the sides they carry because the verdict is not symmetric:
     * a word the specification accepts and the rule does not is the specification being more
     * permissive, and swapping the arguments inverts the published claim.
     */
    public static OrderComparison compare(Automaton mop, Automaton crysl) {
        return new OrderComparison(shortestAcceptedOnlyBy(mop, crysl),
                shortestAcceptedOnlyBy(crysl, mop));
    }

    /**
     * The outcome of a two-direction comparison, and the only way to get a witness out of this
     * package.
     *
     * <p>The separating words are held privately and are handed out only as a {@link Witness}, and
     * every method that hands one out demands the normalizations the comparison was made under.
     * That is INV-CONF-08 made structural rather than remembered: there is no accessor that returns
     * a word, so no caller can publish one while forgetting to say what it was compared modulo.
     */
    public static final class OrderComparison {

        private final Optional<List<Signature>> mopOnly;
        private final Optional<List<Signature>> cryslOnly;

        private OrderComparison(Optional<List<Signature>> mopOnly,
                                Optional<List<Signature>> cryslOnly) {
            this.mopOnly = mopOnly;
            this.cryslOnly = cryslOnly;
        }

        /** Whether the specification accepts something the rule does not. */
        public boolean mopIsMorePermissive() {
            return mopOnly.isPresent();
        }

        /** Whether the rule accepts something the specification does not. */
        public boolean mopIsMoreRestrictive() {
            return cryslOnly.isPresent();
        }

        /** The relation between the two languages. */
        public M2Result.Verdict verdict() {
            if (mopOnly.isEmpty() && cryslOnly.isEmpty()) {
                return M2Result.Verdict.EQUIVALENT;
            }
            if (mopOnly.isPresent() && cryslOnly.isEmpty()) {
                return M2Result.Verdict.MOP_MORE_PERMISSIVE;
            }
            if (mopOnly.isEmpty()) {
                return M2Result.Verdict.MOP_MORE_RESTRICTIVE;
            }
            return M2Result.Verdict.INCOMPARABLE;
        }

        /** The shortest word the specification accepts and the rule rejects, as a witness. */
        public Optional<Witness> mopOnlyWitness(List<Normalization> normalizations) {
            return mopOnly.map(word -> Witnesses.abstractWitness(word, normalizations));
        }

        /** The shortest word the rule accepts and the specification rejects, as a witness. */
        public Optional<Witness> cryslOnlyWitness(List<Normalization> normalizations) {
            return cryslOnly.map(word -> Witnesses.abstractWitness(word, normalizations));
        }

        /**
         * The single witness that accompanies the verdict: the shorter of the two directions, the
         * specification's side breaking a tie.
         *
         * <p>Absent exactly when the verdict is {@code EQUIVALENT} - two languages that agree have
         * nothing to show.
         */
        public Optional<Witness> shortestWitness(List<Normalization> normalizations) {
            if (mopOnly.isEmpty()) {
                return cryslOnlyWitness(normalizations);
            }
            if (cryslOnly.isEmpty()) {
                return mopOnlyWitness(normalizations);
            }
            return cryslOnly.get().size() < mopOnly.get().size()
                    ? cryslOnlyWitness(normalizations)
                    : mopOnlyWitness(normalizations);
        }
    }

    /** One node of the breadth-first search: a state on each side and the word that reached it. */
    private record Search(String left, String right, List<Signature> word) {
    }

    /**
     * A deterministic automaton with a total transition function over a fixed alphabet: the shape
     * the product search needs, where a missing edge has to be a real move into a rejecting state
     * rather than the absence of a move.
     */
    private record Dfa(String initial, Set<String> accepting,
                       Map<String, Map<Signature, String>> delta, String sink) {

        static Dfa of(Automaton automaton, List<Signature> alphabet) {
            Automaton deterministic = Determinizer.determinize(automaton);
            String sink = "!sink";
            Map<String, Map<Signature, String>> delta = new LinkedHashMap<>();
            for (String state : deterministic.states()) {
                Map<Signature, String> row = new LinkedHashMap<>();
                for (Transition transition : deterministic.transitionsFrom(state)) {
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
            return new Dfa(deterministic.initial(), deterministic.accepting(), delta, sink);
        }

        String step(String state, Signature symbol) {
            return delta.getOrDefault(state, Map.of()).getOrDefault(symbol, sink);
        }
    }
}
