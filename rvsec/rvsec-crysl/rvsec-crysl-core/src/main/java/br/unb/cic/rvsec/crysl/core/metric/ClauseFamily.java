package br.unb.cic.rvsec.crysl.core.metric;

/**
 * What kind of thing one {@code CONSTRAINTS} clause is, and the route M3 takes for that kind.
 *
 * <p>The families are declared rather than discovered because the abandoned {@code api30}
 * generation had erased three of them — {@code instanceOf}, the {@code alg}/{@code mode}/{@code
 * pad} string parts, and {@code notHardCoded} — and they all occur in the upstream oracle that
 * replaced it (design D-06). Without a route written down per family, a later reader has two ways
 * to be wrong about them: invent a speculative recogniser for a family nobody measured, or count
 * the family's clauses absent because the reader was never taught to look. Each constant below
 * says which it is.
 *
 * <p>Measured over the 49 upstream rules under {@link CountingRule#R1}: {@code neverTypeOf} 7
 * occurrences in 5 rules, {@code notHardCoded} 4 in 4, {@code callTo} 1 in 1, {@code noCallTo} 4
 * in 2, {@code instanceOf} 4 (all in {@code Cipher.crysl}), the transformation string parts 26
 * (also all in {@code Cipher.crysl}).
 */
public enum ClauseFamily {

    /**
     * {@code neverTypeOf[x, java.lang.String]} — a property of the <em>static type of the value's
     * origin</em>. At the call boundary a runtime monitor observes, the value is already a {@code
     * char[]}; there is nothing left to look at. Routed to {@link
     * br.unb.cic.rvsec.crysl.core.model.UntranslatableConstraint}, never to absent, because
     * "unobservable by construction" and "the author forgot" are different findings.
     */
    NEVER_TYPE_OF("neverTypeOf", "Unknown{UntranslatableConstraint}: static type of the origin"),

    /**
     * {@code notHardCoded[x]} — literal constancy is a property of the source code, not of a
     * value. Same route as {@link #NEVER_TYPE_OF}, same reason.
     */
    NOT_HARD_CODED("notHardCoded", "Unknown{UntranslatableConstraint}: property of the source code"),

    /**
     * {@code callTo[Ev]} — an <em>obligation</em> that some call happen. It is liveness, and
     * JavaMOP has no end-of-trace instant at which the absence of a call becomes decidable, so it
     * shares the root of the {@code IncompleteOperationError} loss.
     *
     * <p>The asymmetry with {@link #NO_CALL_TO} is deliberate and it inverted an earlier
     * diagnosis: a prohibition is <em>safety</em> and its violation is observable at the moment it
     * happens, so {@code noCallTo} is not untranslatable. Only the obligation is.
     */
    CALL_TO("callTo", "Unknown{UntranslatableConstraint}: liveness without an end-of-trace"),

    /**
     * {@code noCallTo[Ev]} — translatable in principle (the forbidden call is observable), but its
     * arguments are {@code ORDER} symbols rather than value expressions, so recognising an
     * implementation means reasoning about the coupling between {@code CONSTRAINTS} and the
     * automaton. This reader does not follow that coupling; the honest output is {@link
     * br.unb.cic.rvsec.crysl.core.model.UnrecognizedConstraint}, which lands in the ceiling of the
     * instrument and not in the count of what the specification failed to write.
     */
    NO_CALL_TO("noCallTo", "Unknown{UnrecognizedConstraint}: CONSTRAINTS/ORDER coupling not followed"),

    /**
     * {@code instanceOf[x, T]} — 4 occurrences, all in {@code Cipher.crysl}. The route is a runtime
     * {@code instanceof}, whether written in the specification or in an external helper, and at
     * runtime the check is <em>exact</em>: this is one of the few places where the dynamic monitor
     * is stronger than the static analyser it was translated from. Absence is therefore a real
     * absence and is counted as one.
     */
    INSTANCE_OF("instanceOf", "idiom D or an inline instanceof; exact at runtime"),

    /**
     * {@code alg(t)}/{@code mode(t)}/{@code pad(t)} — 26 occurrences, all in {@code Cipher.crysl}.
     * The route is idiom D: the transformation-splitting helper class in {@code rvsec-core}, which
     * is where the split and the per-part allow-lists live.
     */
    TRANSFORMATION_PART("alg/mode/pad", "idiom D: the external transformation helper"),

    /**
     * {@code x in {…}} — the allow-list. The route is idiom A, an {@code Arrays.asList(…)} in the
     * specification, or idiom C when the list is declared inside a helper method of the
     * specification.
     */
    VALUE_LIST("in {…}", "idiom A (allow-list), or C when it lives in a helper of the spec"),

    /**
     * An arithmetic comparison, including {@code length[x]}. The route is idiom B, the comparison
     * written directly in a {@code condition(…)} or in an event body over {@code args()}-bound
     * variables, or idiom C when it is delegated to a helper of the specification.
     */
    ARITHMETIC("comparison", "idiom B (inline arithmetic), or C via a helper of the spec"),

    /**
     * A clause of none of the above shapes. Routed to {@link
     * br.unb.cic.rvsec.crysl.core.model.UnrecognizedConstraint}: the reader does not know what it
     * is looking at, which is a statement about the reader.
     */
    OTHER("unclassified", "Unknown{UnrecognizedConstraint}: shape not recognised");

    private final String label;
    private final String route;

    ClauseFamily(String label, String route) {
        this.label = label;
        this.route = route;
    }

    /** The family's name as a CrySL author would recognise it. */
    public String label() {
        return label;
    }

    /** The route M3 takes for this family, stated so that it is not re-derived per clause. */
    public String route() {
        return route;
    }

    /**
     * Classifies one clause by the text the CrySL façade renders it as.
     *
     * <p>The order of the tests is load-bearing, because clauses combine. {@code Cipher.crysl}
     * writes {@code mode(transformation) in {…} && encmode == 1 => callTo[IV]}: it mentions the
     * transformation parts <em>and</em> {@code callTo}, and it is the {@code callTo} that decides,
     * because the obligation is what the specification would have to observe and cannot. The three
     * untranslatable families are therefore tested first, then the two order-coupled and
     * type-shaped ones, and only then the value and arithmetic shapes.
     *
     * <p>{@code "noCallTo("} does not contain {@code "callTo("} — the façade capitalises the
     * {@code C} — so the {@code callTo} test does not need to exclude it, and a test asserts that
     * this stays true.
     *
     * @param clauseText the clause as the façade rendered it
     * @return its family, never {@code null}
     */
    public static ClauseFamily of(String clauseText) {
        String text = clauseText == null ? "" : clauseText;
        if (text.contains("neverTypeOf(")) {
            return NEVER_TYPE_OF;
        }
        if (text.contains("notHardCoded(")) {
            return NOT_HARD_CODED;
        }
        if (text.contains("callTo(")) {
            return CALL_TO;
        }
        if (text.contains("noCallTo(")) {
            return NO_CALL_TO;
        }
        if (text.contains("instanceOf(")) {
            return INSTANCE_OF;
        }
        if (text.contains(".split(")) {
            return TRANSFORMATION_PART;
        }
        if (text.contains("VC:")) {
            return VALUE_LIST;
        }
        if (text.contains("length(") || text.matches("(?s).*[<>!=]=.*") || text.matches("(?s).*[<>].*")) {
            return ARITHMETIC;
        }
        return OTHER;
    }
}
