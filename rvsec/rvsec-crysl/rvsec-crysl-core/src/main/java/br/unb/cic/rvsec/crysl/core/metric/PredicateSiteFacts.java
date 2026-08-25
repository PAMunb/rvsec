package br.unb.cic.rvsec.crysl.core.metric;

import br.unb.cic.rvsec.crysl.core.model.PredicateRef;
import java.util.List;
import java.util.Locale;
import java.util.Objects;
import java.util.Optional;

/**
 * One predicate site of one specification, in the vocabulary {@code -core} can hold.
 *
 * <p>The lift produces richer objects than this - the {@code -mop} module knows which JavaMOP
 * construct a site was written in - but the model module knows neither parser, so the facts M4
 * needs cross the boundary as this record. The caller fills it; nothing here reads a {@code .mop}
 * file.
 *
 * <p>{@code argumentTypes} is the one component whose producer is not this metric. Position types
 * are what makes the type half of a propagation bridge decidable (see {@link PropagationBridge}),
 * and they come from the event that hosts the site, which is the lift's subject and not M4's. When
 * the caller supplies none, the type route is simply not taken and the counting rule says so; M4
 * does not guess a type from an argument name.
 *
 * @param specification the file the site is in, as {@code predicate_graph.csv} names it, e.g.
 *                      {@code CipherSpec.mop}
 * @param section       which of the model's three predicate sections the site belongs to
 * @param substrate     which substrate wrote it
 * @param event         the event or handler the site sits in, as the {@code event} column carries
 *                      it, e.g. {@code i2} or {@code match1}; blank when the caller has none
 * @param siteKind      whether the site is in an event body or in a {@code @match} handler
 * @param verdict       the {@code PredicateVerdict} constant the call is compared against, when it
 *                      is compared on the same statement
 * @param argumentTypes the declared type at each argument position, in position order; empty when
 *                      the caller supplies none, and never inferred here
 * @param ref           the reference itself, with its name, arity, polarity and {@code file:line}
 */
public record PredicateSiteFacts(String specification, Section section,
                                 PredicateSubstrate substrate, String event, SiteKind siteKind,
                                 Optional<String> verdict, List<String> argumentTypes,
                                 PredicateRef ref) {

    public PredicateSiteFacts {
        Objects.requireNonNull(specification, "PredicateSiteFacts.specification is mandatory");
        Objects.requireNonNull(section, "PredicateSiteFacts.section is mandatory");
        Objects.requireNonNull(substrate, "PredicateSiteFacts.substrate is mandatory: a predicate "
                + "count that does not say which substrate produced it is not comparable across "
                + "the frozen and the current corpus");
        Objects.requireNonNull(siteKind, "PredicateSiteFacts.siteKind is mandatory");
        Objects.requireNonNull(verdict, "PredicateSiteFacts.verdict is mandatory (Optional.empty())");
        Objects.requireNonNull(ref, "PredicateSiteFacts.ref is mandatory");
        event = event == null ? "" : event;
        argumentTypes = List.copyOf(argumentTypes);
    }

    /** Which of the model's three predicate sections the site belongs to. */
    public enum Section {
        /** The specification writes the predicate. */
        ENSURES,
        /** The specification reads the predicate as a precondition. */
        REQUIRES,
        /** The specification withdraws the predicate. */
        NEGATES
    }

    /**
     * Where in the specification the site is written.
     *
     * <p>It decides one derived column outright: an event body is a letter of the order automaton,
     * a {@code @match} handler is not, so {@code automaton_membership} is {@code member} for the
     * first and {@code n/a} for the second.
     */
    public enum SiteKind {
        /** Inside an event's action or {@code condition(...)}. */
        BODY("body", "member"),
        /** Inside a {@code @match} handler, which fires at the acceptance point. */
        MATCH("@match", "n/a");

        private final String csv;
        private final String automatonMembership;

        SiteKind(String csv, String automatonMembership) {
            this.csv = csv;
            this.automatonMembership = automatonMembership;
        }

        /** The value the {@code site_kind} column carries. */
        public String csv() {
            return csv;
        }

        /** The value the {@code automaton_membership} column carries for a site of this kind. */
        public String automatonMembership() {
            return automatonMembership;
        }
    }

    /** The predicate name as the specification writes it, e.g. {@code GENERATED_KEY}. */
    public String predicate() {
        return ref.name();
    }

    /** The value the {@code polarity} column carries: {@code positive} or {@code negated}. */
    public String polarityCsv() {
        return ref.polarity().name().toLowerCase(Locale.ROOT);
    }

    /** The value the {@code arity} column carries. */
    public int arity() {
        return ref.arguments().size();
    }
}
