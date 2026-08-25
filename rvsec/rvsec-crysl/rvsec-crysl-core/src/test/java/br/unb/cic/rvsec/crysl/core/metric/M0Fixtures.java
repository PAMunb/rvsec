package br.unb.cic.rvsec.crysl.core.metric;

import br.unb.cic.rvsec.crysl.core.automata.Automaton;
import br.unb.cic.rvsec.crysl.core.automata.LabelAutomaton;
import br.unb.cic.rvsec.crysl.core.automata.LabelTransition;
import br.unb.cic.rvsec.crysl.core.model.Event;
import br.unb.cic.rvsec.crysl.core.model.Guard;
import br.unb.cic.rvsec.crysl.core.model.Label;
import br.unb.cic.rvsec.crysl.core.model.Provenance;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import br.unb.cic.rvsec.crysl.core.model.SourceStamp;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import br.unb.cic.rvsec.crysl.core.model.Version;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

/**
 * Hand-built inputs for the M0 tests that must not depend on a corpus.
 *
 * <p>The corpus tests live where the lifter is on the classpath and answer what {@code jca_android}
 * says today. These answer what the metric does, over automata small enough to reason about by
 * hand: an automaton with a live prefix, one without, a specification that cannot accuse, one that
 * can. A defect in the criterion shows up here as a one-line failure rather than as a corpus count
 * that moved for an unknown reason.
 */
final class M0Fixtures {

    static final String FILE = "Probe.mop";

    private M0Fixtures() {
    }

    static Provenance site() {
        return new Provenance(FILE, 1);
    }

    static Version version() {
        return new Version("fixture", new SourceStamp("rvsec", "test-fixture", Instant.EPOCH));
    }

    /** A signature per label, so that the model is well formed; M0 never reads this alphabet. */
    static Signature signature(String label) {
        return new Signature("p.Probe", label, List.of(), "void");
    }

    /** A model declaring the given labels in order, each resolving to one signature. */
    static SpecModel model(String... labels) {
        List<Event> events = new ArrayList<>();
        Map<Object, Provenance> provenance = new LinkedHashMap<>();
        for (int i = 0; i < labels.length; i++) {
            Event event = new Event(new Label(labels[i]), "call(* p.Probe." + labels[i] + "())",
                    Set.of(signature(labels[i])), Optional.<Guard>empty(), i);
            events.add(event);
            provenance.put(event, new Provenance(FILE, 10 + i));
        }
        Automaton unusedOrder = new Automaton(Set.of("q0"), "q0", Set.of("q0"), List.of());
        return new SpecModel(version(), "p.Probe", Set.of(), events, unusedOrder, List.of(),
                List.of(), List.of(), List.of(), Set.of(), provenance);
    }

    /**
     * The label automaton of a word: {@code q0 -a-> q1 -b-> q2}, with only the last state accepting.
     *
     * <p>{@code chain("a")} has no live prefix beyond the initial state; {@code chain("a", "b")}
     * has exactly one, which is the shape {@code ere : c1 (r1|r2)+ cl1} has and the shape
     * {@code ere : c} does not.
     */
    static LabelAutomaton chain(String... labels) {
        List<LabelTransition> transitions = new ArrayList<>();
        List<String> states = new ArrayList<>();
        states.add("q0");
        for (int i = 0; i < labels.length; i++) {
            states.add("q" + (i + 1));
            transitions.add(new LabelTransition("q" + i, new Label(labels[i]), "q" + (i + 1)));
        }
        return new LabelAutomaton(Set.copyOf(states), "q0", Set.of("q" + labels.length),
                transitions);
    }

    /** The automaton of {@code ere : a*}: one state, accepting, a self-loop per label. */
    static LabelAutomaton loop(String... labels) {
        List<LabelTransition> transitions = new ArrayList<>();
        for (String label : labels) {
            transitions.add(new LabelTransition("q0", new Label(label), "q0"));
        }
        return new LabelAutomaton(Set.of("q0"), "q0", Set.of("q0"), transitions);
    }

    /** Facts for a specification with the given handlers and no misuse absorption. */
    static MonitorFacts facts(int declaredParameters, int declaredEvents, int binding,
                              Map<String, HandlerState> handlers) {
        return new MonitorFacts(declaredParameters, declaredEvents, binding, handlers,
                new MisuseAbsorption(false, List.of(), MisuseAbsorption.RULE), site());
    }

    /** Facts for a specification whose named events carry an {@code addError} in their body. */
    static MonitorFacts absorbing(int declaredParameters, int declaredEvents, int binding,
                                  Map<String, HandlerState> handlers, String... events) {
        List<Label> labels = new ArrayList<>();
        for (String event : events) {
            labels.add(new Label(event));
        }
        return new MonitorFacts(declaredParameters, declaredEvents, binding, handlers,
                new MisuseAbsorption(true, labels, MisuseAbsorption.RULE), site());
    }
}
