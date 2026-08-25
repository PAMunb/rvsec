package br.unb.cic.rvsec.crysl.core.model;

/**
 * Whether a {@link PredicateRef} names its predicate or the absence of it.
 *
 * <p>Polarity is <em>not</em> the section. The section says what the specification does with the
 * predicate — writes it ({@code ENSURES}), reads it as a precondition ({@code REQUIRES}), withdraws
 * it ({@code NEGATES}) — and polarity says which of the two things the reference itself asks for.
 * The two are independent in exactly one place, and the corpora write it on both sides:
 *
 * <ul>
 *   <li>{@code Mac.crysl:51} requires {@code !encrypted[output1, _]}: a {@code REQUIRES} entry that
 *       demands the predicate be <em>absent</em>. That is not a {@code NEGATES} entry — the rule
 *       has none — and filing it as one would claim a clause the rule does not have;
 *   <li>{@code jca_android/MacSpec.mop:307} writes
 *       {@code validateAbsent(Property.ENCRYPTED, output)}, which is the same demand.
 * </ul>
 *
 * <p>Four semantics over three lists, which is why polarity is a field rather than the list a
 * reference is held in. M4 compares {@code ENSURES}/{@code REQUIRES}/{@code NEGATES} by arity,
 * polarity and argument position, and reports an <em>inverted</em> edge when the polarities differ:
 * without this field the two models would agree on a specification demanding the opposite of the
 * rule, and no downstream stage could recover a {@code !} the lift discarded.
 *
 * <p>The predicate name is always the bare name — {@code encrypted}, {@code ENCRYPTED} — never
 * {@code !encrypted}. Encoding the negation into the name would invent a predicate no rule declares
 * and M4's pairing would then miss the real one.
 */
public enum Polarity {

    /** The reference asks for the predicate to hold. */
    POSITIVE,

    /** The reference asks for the predicate <em>not</em> to hold: CrySL's {@code !p[...]}. */
    NEGATED
}
