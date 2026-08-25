package br.unb.cic.rvsec.crysl.core.compare;

import br.unb.cic.rvsec.crysl.core.model.Label;
import br.unb.cic.rvsec.crysl.core.model.Normalization;
import java.util.List;

/**
 * The transformations an order comparison may be made modulo, each one named and each one reported
 * individually beside the verdict it produced.
 *
 * <p>Hiding which normalizations a comparison used makes two incomparable verdicts look alike. A
 * specification that is equivalent to its rule outright and one that is equivalent only after the
 * accepting set was narrowed and the pointcut overlap was resolved are saying different things, and
 * the second is saying something worth reading. So every rule below is an object with an identifier
 * and a written statement of what it did and on whose authority, the applied ones travel inside
 * {@link br.unb.cic.rvsec.crysl.core.metric.M2Result#normalizations()}, and the emitter prints the
 * identifiers in the verdict row and the statements underneath the table.
 *
 * <p>Two of these are not general rules and must not be applied by default.
 *
 * <ul>
 *   <li><strong>N1</strong> is a property of the <em>generated indexing tree</em>, not of JavaMOP.
 *       Five specifications of the set compile to one monitor for the whole program, and in those
 *       the word {@code g1 g1} is realisable, so slicing licenses nothing. M2 takes the predicate
 *       from M0.1 - does the generated monitor build a {@code MapOfMonitor} - and never re-derives
 *       it (task 10.9).
 *   <li><strong>N2</strong> depends on the platform: whether a symbol of the rule can be emitted by
 *       any program at all is a fact about the method's declared access, read from
 *       {@code android.jar}. With no platform supplied, N2 is not applied and the report says so
 *       rather than assuming the projection.
 * </ul>
 *
 * <p><strong>N4</strong> is listed here for reporting, but it is not applied here. Since design
 * D-02 and the D-20 reconciliation it is a <em>construction step</em>: the morphism {@code h} is
 * built at lift time and {@code SpecModel.order} is already the preimage {@code h⁻¹(L)}, so by the
 * time M2 sees the automaton the overlap has been accounted for. M2 reports N4 when the morphism
 * shows a call that emits more than one letter, because a comparison made over a non-disjoint
 * alphabet is a different claim from one made over a disjoint one.
 */
public final class Normalizations {

    /**
     * One {@code .mop} event standing for several rule events, or the reverse.
     *
     * <p>The {@code .mop} fuses by wildcard what the rule separates by overload
     * ({@code update(..)} against {@code u1..u4}) and the rule aggregates what the {@code .mop}
     * splits to bind arguments ({@code KeyGeneratorSpec.init} is the rule's {@code i1} and its
     * {@code i3}). Comparing over signatures dissolves most of it; where it survives, the letters
     * are identified and that identification is this rule.
     */
    public static final Normalization AGGREGATE = new Normalization("N-AGG",
            "1:N over aggregates - one letter of one side denotes several of the other, and the "
                    + "two were identified before the comparison. The identification is by "
                    + "signature under R-M1, never by name.");

    /**
     * A label and its rule symbol that carry different names.
     *
     * <p>{@code SecureRandomSpec.g3} is the rule's {@code gI} and {@code setSeed1} is the rule's
     * {@code s2}, not {@code s1}. No name heuristic gets either right, which is why the
     * association is a committed table and this rule only reports that the table was needed.
     */
    public static final Normalization CROSS_RENUMBERING = new Normalization("N-REN",
            "1:1 with cross-renumbering - the alphabet map declares a label whose rule symbol is "
                    + "spelled differently, and the association was taken from the map.");

    /** The family every declared &epsilon;-erasure is reported under; see {@link #erasure}. */
    public static final Normalization DECLARED_ERASURE = new Normalization("N-EPS",
            "declared epsilon-erasure - a .mop event with no ORDER symbol, erased on the authority "
                    + "of the disposition column of order_alphabet_map.csv and never inferred from "
                    + "automaton shape (INV-CONF-10).");

    /** At most one creator event per monitor; valid per specification, from M0.1. */
    public static final Normalization N1_PARAMETRIC_SLICING = new Normalization("N1",
            "parametric slicing - the generated monitor indexes (M0.1: it builds a MapOfMonitor), "
                    + "so one monitor instance sees at most one creation of the object it is keyed "
                    + "on, and the specification's language was restricted to words with at most "
                    + "one creator letter. Not a general rule: where the monitor is global the "
                    + "word g1 g1 is realisable and this restriction is unsound, so it is applied "
                    + "only where M0.1 says the specification indexes.");

    /** Projection of a rule symbol no program can emit. */
    public static final Normalization N2_NON_OBSERVABLE = new Normalization("N2",
            "projection of a non-observable symbol - the rule orders a call the platform does not "
                    + "expose to a client (SecureRandom.next(int) is protected), so no program can "
                    + "emit it and the rule's language was projected onto the observable alphabet. "
                    + "Decided from the declared access in android.jar, not from a list.");

    /** Not every {@code alias match*} state is a legitimate end of the protocol. */
    public static final Normalization N3_ACCEPTANCE = new Normalization("N3",
            "acceptance is not every alias match* - a .mop marks a state with an alias to give a "
                    + "predicate an acceptance point (CipherSpec's alias match2 = s3 is where "
                    + "encrypted[..] after updates fires), and such a state is not a legitimate end "
                    + "of the call sequence. The states the caller declares predicate-only were "
                    + "removed from the accepting set before comparing.");

    /** Overlapping pointcuts; a construction step since D-02, reported and not applied. */
    public static final Normalization N4_OVERLAPPING_POINTCUTS = new Normalization("N4",
            "overlapping pointcuts - the event alphabet is not disjoint and one observed call "
                    + "emits several letters, in declaration order. Since design D-02 this is a "
                    + "construction step and not a post-hoc normalization: SpecModel.order is "
                    + "already the preimage h-inverse(L) under the morphism the lift built. It is "
                    + "reported because a comparison over a non-disjoint alphabet is a different "
                    + "claim from one over a disjoint one.");

    /** The catalogue, in the order a report lists it. */
    public static final List<Normalization> CATALOGUE = List.of(
            AGGREGATE, CROSS_RENUMBERING, DECLARED_ERASURE, N1_PARAMETRIC_SLICING,
            N2_NON_OBSERVABLE, N3_ACCEPTANCE, N4_OVERLAPPING_POINTCUTS);

    private Normalizations() {
    }

    /**
     * One declared &epsilon;-erasure, reported individually and carrying its reason verbatim.
     *
     * <p>Per erasure rather than one {@code N-EPS} entry per verdict, for two reasons that are the
     * same reason twice. A reader who sees {@code N-EPS} in a verdict row learns that something was
     * erased and has to open a CSV to learn what and why; a reader who sees
     * {@code N-EPS·KeyGeneratorSpec.g3} learns which event, and the statement underneath the table
     * carries the map's own words for why. And the emitter keys the statement block by identifier,
     * so a single shared {@code N-EPS} identifier would print one specification's reason and
     * silently drop every other one.
     *
     * @param specification the specification whose event was erased
     * @param label         the erased event
     * @param reason        the {@code reason} column, quoted verbatim (task 10.5)
     */
    public static Normalization erasure(String specification, Label label, String reason) {
        String quoted = reason == null || reason.isBlank()
                ? "(the map declares the erasure and leaves the reason column empty)"
                : "\"" + reason + "\"";
        return new Normalization(DECLARED_ERASURE.id() + "·" + specification + "."
                + label.name(),
                "declared epsilon-erasure of " + specification + "." + label.name()
                        + ", on the authority of order_alphabet_map.csv, disposition = "
                        + AlphabetMap.Disposition.ORDER_UNMAPPED.csv()
                        + ". Declared reason, verbatim: " + quoted);
    }
}
