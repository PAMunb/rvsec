package br.unb.cic.rvsec.crysl.core.automata;

import br.unb.cic.rvsec.crysl.core.model.Signature;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/**
 * The canonical order over the alphabet, and the alphabet a two-automaton comparison runs over.
 *
 * <p>The order exists so that every algorithm in this package is reproducible: subset construction,
 * Hopcroft refinement and the product breadth-first search all iterate over symbols, and without a
 * fixed order the shortest witness of a pair with several shortest witnesses would depend on hash
 * iteration order and change between runs. A witness that changes between runs cannot be published.
 */
final class Alphabet {

    /** Total order over signatures: declaring type, then name, then parameters, then return type. */
    static final Comparator<Signature> ORDER = Comparator
            .comparing(Signature::declaringType)
            .thenComparing(Signature::name)
            .thenComparing(s -> String.join(",", s.paramTypes()))
            .thenComparing(Signature::returnType);

    private Alphabet() {
    }

    /** The given symbols in canonical order, duplicates removed. */
    static List<Signature> sorted(Collection<Signature> symbols) {
        List<Signature> ordered = new ArrayList<>(new LinkedHashSet<>(symbols));
        ordered.sort(ORDER);
        return List.copyOf(ordered);
    }

    /**
     * The alphabet a comparison of {@code a} against {@code b} runs over: the union of the two.
     *
     * <p>The union rather than either side alone, because a letter one automaton never mentions is
     * still a letter the other one may accept, and completing only over the letters they share
     * would silently agree about words neither language was asked about.
     */
    static List<Signature> union(Automaton a, Automaton b) {
        Set<Signature> all = new LinkedHashSet<>(a.alphabet());
        all.addAll(b.alphabet());
        return sorted(all);
    }
}
