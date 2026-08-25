package br.unb.cic.rvsec.crysl.core.automata;

import br.unb.cic.rvsec.crysl.core.model.Event;
import br.unb.cic.rvsec.crysl.core.model.Guard;
import br.unb.cic.rvsec.crysl.core.model.Label;
import br.unb.cic.rvsec.crysl.core.model.Provenance;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;

/**
 * A hand-built automaton in one line, so that every test in this package states an input whose
 * answer is known before the code runs.
 *
 * <p>The suite deliberately never reads the corpus. An algorithm proved on the corpus is proved
 * against whatever the corpus happens to contain today, and the two properties that matter most
 * here - that determinization is not decoration, and that two spellings of one language compare
 * equal - are properties no rule of the current corpus exhibits.
 */
final class Fixtures {

    static final Provenance SITE = new Provenance("Synthetic.mop", 1);

    private Fixtures() {
    }

    /** A distinct letter of the alphabet, named so that failures read like the test. */
    static Signature sig(String name) {
        return new Signature("br.unb.cic.Demo", name, List.of(), "void");
    }

    /** A word, written as the letter names in order. */
    static List<Signature> word(String... names) {
        return Arrays.stream(names).map(Fixtures::sig).toList();
    }

    /**
     * An automaton written as {@code "from symbol to"} edges; states are inferred from them.
     *
     * @param initial   the initial state
     * @param accepting the accepting states, comma separated, possibly empty
     * @param edges     each {@code "q0 a q1"}
     */
    static Automaton automaton(String initial, String accepting, String... edges) {
        Set<String> states = new LinkedHashSet<>();
        states.add(initial);
        Set<String> acceptingStates = names(accepting);
        states.addAll(acceptingStates);
        List<Transition> transitions = Arrays.stream(edges).map(edge -> {
            String[] parts = edge.trim().split("\\s+");
            states.add(parts[0]);
            states.add(parts[2]);
            return new Transition(parts[0], sig(parts[1]), Optional.empty(), parts[2]);
        }).toList();
        return new Automaton(states, initial, acceptingStates, transitions);
    }

    /** The same, over labels: the shape an {@code ere} formula denotes. */
    static LabelAutomaton labelAutomaton(String initial, String accepting, String... edges) {
        Set<String> states = new LinkedHashSet<>();
        states.add(initial);
        Set<String> acceptingStates = names(accepting);
        states.addAll(acceptingStates);
        List<LabelTransition> transitions = Arrays.stream(edges).map(edge -> {
            String[] parts = edge.trim().split("\\s+");
            states.add(parts[0]);
            states.add(parts[2]);
            return new LabelTransition(parts[0], new Label(parts[1]), parts[2]);
        }).toList();
        return new LabelAutomaton(states, initial, acceptingStates, transitions);
    }

    /** An event declared at {@code declIndex}, matching the named signatures, with no condition. */
    static Event event(String label, int declIndex, String... signatureNames) {
        return guardedEvent(label, declIndex, null, signatureNames);
    }

    /** The same, with a {@code condition} whose text is {@code guardText} when non-null. */
    static Event guardedEvent(String label, int declIndex, String guardText,
                              String... signatureNames) {
        Set<Signature> signatures = new LinkedHashSet<>();
        for (String name : signatureNames) {
            signatures.add(sig(name));
        }
        return new Event(new Label(label), label + "()", signatures,
                Optional.ofNullable(guardText).map(Guard::new), declIndex);
    }

    private static Set<String> names(String commaSeparated) {
        Set<String> names = new LinkedHashSet<>();
        for (String name : commaSeparated.split(",")) {
            if (!name.isBlank()) {
                names.add(name.trim());
            }
        }
        return names;
    }
}
