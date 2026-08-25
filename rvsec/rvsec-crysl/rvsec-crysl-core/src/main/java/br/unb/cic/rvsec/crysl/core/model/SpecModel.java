package br.unb.cic.rvsec.crysl.core.model;

import br.unb.cic.rvsec.crysl.core.automata.Automaton;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

/**
 * The canonical model both sides are lifted to: one {@code .mop} specification or one
 * {@code .crysl} rule, expressed so that the five metrics can compare them without knowing which
 * parser produced which.
 *
 * <p>Three shape decisions are load-bearing and are enforced by the type, not by convention:
 *
 * <ul>
 *   <li>{@code events} is a {@code List} ordered by declaration index, because declaration order is
 *       dispatch order (INV-CONF-03);
 *   <li>{@code order} is an automaton over {@link Signature} and never over {@link Label}, because
 *       labels are a MOP-side naming convention that the CrySL side does not share - no field of
 *       this module may have a type assignable to {@code Map<Label, ?>}, which
 *       {@code ModelShapeArchTest} checks;
 *   <li>{@code constraints}, {@code ensures}, {@code requires} and {@code negates} are {@code List}s
 *       and never {@code Set}s, because identical clauses at different sites are different clauses.
 * </ul>
 *
 * <p>The {@code version} is mandatory at construction. INV-CONF-01 makes an unstamped model a fatal
 * condition at emission; rejecting {@code null} here means no code path can even build one, so the
 * emitter never has to trust a caller.
 *
 * @param version     the corpus and commit this model was lifted from
 * @param type        the fully-qualified type the specification or rule is about
 * @param objects     the declared objects
 * @param events      the events, ordered by {@link Event#declIndex()}
 * @param order       the order automaton, over signatures
 * @param constraints the {@code CONSTRAINTS} clauses
 * @param ensures     the predicates the artifact ensures
 * @param requires    the predicates it requires
 * @param negates     the predicates it negates
 * @param forbidden   the signatures declared forbidden
 * @param provenance  {@code file:line} per item of the model, keyed by the item itself
 */
public record SpecModel(Version version, String type, Set<ObjectDecl> objects,
                        List<Event> events, Automaton order, List<Constraint> constraints,
                        List<PredicateRef> ensures, List<PredicateRef> requires,
                        List<PredicateRef> negates, Set<Signature> forbidden,
                        Map<Object, Provenance> provenance) {

    public SpecModel {
        Objects.requireNonNull(version, "SpecModel.version is mandatory (INV-CONF-01)");
        Objects.requireNonNull(type, "SpecModel.type is mandatory");
        Objects.requireNonNull(order, "SpecModel.order is mandatory");
        objects = Set.copyOf(objects);
        events = List.copyOf(events);
        constraints = List.copyOf(constraints);
        ensures = List.copyOf(ensures);
        requires = List.copyOf(requires);
        negates = List.copyOf(negates);
        forbidden = Set.copyOf(forbidden);
        provenance = Map.copyOf(provenance);
    }
}
