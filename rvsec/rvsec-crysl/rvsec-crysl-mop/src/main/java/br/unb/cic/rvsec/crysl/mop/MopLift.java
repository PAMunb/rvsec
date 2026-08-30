package br.unb.cic.rvsec.crysl.mop;

import br.unb.cic.rvsec.crysl.core.automata.InverseMorphism;
import br.unb.cic.rvsec.crysl.core.automata.LabelAutomaton;
import br.unb.cic.rvsec.crysl.core.metric.HandlerState;
import br.unb.cic.rvsec.crysl.core.metric.MisuseAbsorption;
import br.unb.cic.rvsec.crysl.core.metric.MonitorFacts;
import br.unb.cic.rvsec.crysl.core.model.Provenance;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * Everything one {@code .mop} file yields: the canonical {@link SpecModel} the metrics compare, plus
 * the MOP-side facts the model has no field for.
 *
 * <p>{@code SpecModel} is the shape both languages are lifted to, so it deliberately carries nothing
 * that only JavaMOP has. Five such facts are needed downstream and live here instead:
 *
 * <ul>
 *   <li>{@code labelOrder} and {@code morphism} — the two halves of {@code SpecModel.order}, which
 *       is the preimage {@code h⁻¹(labelOrder)} under {@code morphism} (design D-02, D-20). Both
 *       are kept because the preimage cannot be run backwards. It is a language over signatures and
 *       says nothing about which label a call emitted, so {@code mop.lower} cannot recover the
 *       {@code ere} from it, and a report cannot say which labels a refusal was about. Neither is
 *       an artefact of the lift left lying around: delete either and the lowerer has to re-parse
 *       the file, and the {@code Unknown} refusals lose the only object that holds them.
 *       {@code morphism.refusals()} is where {@code Unknown{OverlappingDispatch}} arrives, because
 *       the morphism is built here and not in M2; see {@link MopLifter} for what
 *       {@code SpecModel.order} then contains for a specification that has one;
 *   <li>{@code handlers} — M0 decides whether a specification can accuse at all, and that is a
 *       question about {@code @match} and {@code @fail}, which CrySL has no counterpart for;
 *   <li>{@code predicateSites} — the substrate each predicate reference was written on, and the
 *       {@code PredicateVerdict} it was compared against, neither of which the shared model has a
 *       field for (see {@link PredicateSite}); the polarity of a reference is on the reference
 *       itself, because CrySL carries it too and M4 compares the two;
 *   <li>{@code acceptingStateMarks} — substrate A's explicit encoding of CrySL's "ENSURES fires
 *       only in an accepting state", which is a guard and not a predicate.
 * </ul>
 *
 * <p>The three parser counts are carried as data rather than recomputed by each caller, and each
 * comes with the counting rule it was taken under, because a count published without its rule is
 * the failure INV-CONF-02 exists to prevent. They are the raw parser counts, and the aggregate over
 * the five corpora is 974 events and 407 parameters across 239 files.
 *
 * <p>{@code eventsBindingParameters} is the third of them and it is here because M0.1 cannot be
 * answered without it and cannot recover it from the text: {@code getMOPParametersOnSpec()} is the
 * intersection JavaMOP itself computes between an event's parameters and the specification's, and
 * with that intersection empty for every event the generated monitor has nothing to key a slice on
 * and compiles to one monitor for the whole program. It reaches M0 through
 * {@link #monitorFacts(MisuseAbsorption)}, which is the only route: the alternative is a second
 * parse of the same file, and a metric that parses its subject twice can report two different
 * answers about it.
 *
 * @param model                  the canonical model
 * @param labelOrder             the language the {@code ere}/{@code fsm} denotes, over labels
 * @param morphism               {@code h}, from signatures to label words, and its refusals
 * @param site                   where the specification itself is declared
 * @param handlers               handler key (lowercased) to what the parser found; a key missing
 *                               from the map means the handler is absent
 * @param predicateSites         every recognised predicate idiom, in file order
 * @param acceptingStateMarks    every substrate-A accepting-state mark, in file order
 * @param declaredEventCount     {@code spec.getEvents().size()}
 * @param declaredParameterCount {@code spec.getParameters().size()}
 * @param eventsBindingParameters how many of the declared events bind at least one declared
 *                               specification parameter, i.e. have a non-empty
 *                               {@code getMOPParametersOnSpec()}
 */
public record MopLift(SpecModel model, LabelAutomaton labelOrder, InverseMorphism morphism,
                      Provenance site, Map<String, HandlerBlock> handlers,
                      List<PredicateSite> predicateSites,
                      List<PredicateIdioms.AcceptingStateMark> acceptingStateMarks,
                      int declaredEventCount, int declaredParameterCount,
                      int eventsBindingParameters) {

    /** The counting rule behind {@link #declaredEventCount()}. */
    public static final String EVENT_COUNTING_RULE = "spec.getEvents().size()";

    /** The counting rule behind {@link #declaredParameterCount()}. */
    public static final String PARAMETER_COUNTING_RULE = "spec.getParameters().size()";

    /** The counting rule behind {@link #eventsBindingParameters()}. */
    public static final String EVENT_BINDING_COUNTING_RULE =
            "events whose getMOPParametersOnSpec() is non-empty, i.e. that bind at least one "
                    + "parameter the specification declares";

    public MopLift {
        Objects.requireNonNull(model, "MopLift.model is mandatory");
        Objects.requireNonNull(labelOrder, "MopLift.labelOrder is mandatory: it is what the "
                + "lowerer reconstructs the formula from, and the preimage cannot be run backwards");
        Objects.requireNonNull(morphism, "MopLift.morphism is mandatory: it carries the "
                + "OverlappingDispatch refusals, which arise at the lift and nowhere else");
        Objects.requireNonNull(site, "MopLift.site is mandatory");
        handlers = Map.copyOf(handlers);
        predicateSites = List.copyOf(predicateSites);
        acceptingStateMarks = List.copyOf(acceptingStateMarks);
        if (eventsBindingParameters < 0 || eventsBindingParameters > declaredEventCount) {
            throw new IllegalArgumentException("MopLift.eventsBindingParameters ("
                    + eventsBindingParameters + ") is not in 0.." + declaredEventCount
                    + "; it is a subset of the declared events, and a value outside that range "
                    + "means the binding was counted against the wrong specification");
        }
    }

    /**
     * The facts M0 consumes, assembled from this lift.
     *
     * <p>{@code MonitorFacts} lives in the model module and M0 may not depend on the lifter
     * (design D-16), so the lift hands the facts down rather than the metric reaching up. Everything
     * here comes from the parse this object already paid for; only {@code absorption} does not,
     * because that scan is textual by design — the {@code ere}/{@code fsm} line is a lexical
     * boundary and not an AST node — and it is therefore the caller's to run from the path it
     * already holds, with {@link MisuseAbsorption#scan(java.nio.file.Path)}.
     *
     * @param absorption whether misuse is reported from inside an event body, and where
     * @return the M0 inputs for this specification
     */
    public MonitorFacts monitorFacts(MisuseAbsorption absorption) {
        Map<String, HandlerState> states = new LinkedHashMap<>();
        for (Map.Entry<String, HandlerBlock> entry : handlers.entrySet()) {
            states.put(entry.getKey(), stateOf(entry.getValue().status()));
        }
        return new MonitorFacts(declaredParameterCount, declaredEventCount, eventsBindingParameters,
                states, absorption, site);
    }

    private static HandlerState stateOf(HandlerBlock.Status status) {
        return switch (status) {
            case ABSENT -> HandlerState.ABSENT;
            case EMPTY -> HandlerState.EMPTY;
            case NON_EMPTY -> HandlerState.NON_EMPTY;
            case UNPARSED -> HandlerState.UNPARSED;
        };
    }

    /**
     * The handler under {@code key}, or an {@link HandlerBlock.Status#ABSENT} block stamped with the
     * specification's own site when no handler with that key is declared.
     *
     * <p>Callers pass the key lowercased, because that is how {@code getHandlers()} reports it —
     * trap (e): the grammar does {@code handlers.put(id.toLowerCase(), handler)}, so {@code @match1}
     * is the key {@code "match1"} and a lookup of {@code "@match1"} silently finds nothing.
     */
    public HandlerBlock handler(String key) {
        HandlerBlock found = handlers.get(key.toLowerCase());
        if (found != null) {
            return found;
        }
        return new HandlerBlock(key.toLowerCase(), HandlerBlock.Status.ABSENT, 0, site);
    }
}
