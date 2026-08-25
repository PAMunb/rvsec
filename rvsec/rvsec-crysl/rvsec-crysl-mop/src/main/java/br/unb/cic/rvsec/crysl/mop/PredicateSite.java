package br.unb.cic.rvsec.crysl.mop;

import br.unb.cic.rvsec.crysl.core.model.PredicateRef;
import java.util.Objects;
import java.util.Optional;

/**
 * One recognised predicate idiom in a {@code .mop} file, with everything about it that
 * {@link PredicateRef} has nowhere to put.
 *
 * <p>The polarity of the site lives on the reference itself, as
 * {@link PredicateRef#polarity()}: {@code validateAbsent(p, x)} is the CrySL {@code !p[x]} — a
 * requirement that the predicate does not hold — and {@code condition(!validate(p, x))} is the same
 * requirement seen from the violating branch, the event firing exactly when {@code p} is absent so
 * that the handler can accuse. Both lift to {@link
 * br.unb.cic.rvsec.crysl.core.model.Polarity#NEGATED}, which is what a CrySL {@code !} lifts to on
 * the other side, so M4 can compare them.
 *
 * <p>What remains here is the one fact the shared model has no room for: which <em>substrate</em>
 * wrote the site, plus the verdict it was compared against. The substrates are not the same
 * relation — {@code ExecutionContext} is arity 1, keyed by {@code equals} and boolean, while {@code
 * PredicateStore} is arity N, keyed by identity and three-valued — and a predicate count that does
 * not say which substrate produced it is not comparable across the two corpora.
 *
 * <p>The predicate name is always the bare property constant, {@code GENERATED_MAC} and never
 * {@code !GENERATED_MAC}. Encoding the negation in the name would invent a predicate no CrySL rule
 * declares and M4's pairing would then miss the real one.
 *
 * @param kind      the section this site belongs to
 * @param substrate which predicate substrate wrote it
 * @param verdict   the {@code PredicateVerdict} constant the call is compared against on the same
 *                  statement, when it is compared there at all; empty when the verdict is bound to
 *                  a local and tested later, as {@code IvChainJunction.mop:141} does
 * @param ref       the reference itself, with its polarity and its {@code file:line}
 */
public record PredicateSite(Kind kind, Substrate substrate,
                            Optional<String> verdict, PredicateRef ref) {

    public PredicateSite {
        Objects.requireNonNull(kind, "PredicateSite.kind is mandatory");
        Objects.requireNonNull(substrate, "PredicateSite.substrate is mandatory");
        Objects.requireNonNull(verdict, "PredicateSite.verdict is mandatory (use Optional.empty())");
        Objects.requireNonNull(ref, "PredicateSite.ref is mandatory");
    }

    /** Which of the model's three predicate sections the site belongs to. */
    public enum Kind {
        /** The specification writes the predicate. */
        ENSURES,
        /** The specification reads the predicate as a precondition. */
        REQUIRES,
        /** The specification withdraws the predicate. */
        NEGATES
    }

    /**
     * The two predicate substrates the corpora use.
     *
     * <p>They are not interchangeable and both must be read. Measured over the five corpora:
     * {@code jca} has 110 {@code ExecutionContext} sites and no {@code PredicateStore} site;
     * {@code jca_android} has 70 {@code PredicateStore} sites and no {@code ExecutionContext} site;
     * {@code jca_android_bug_predicate} has 152 {@code ExecutionContext} sites; {@code generic} and
     * {@code generic_new} have neither.
     */
    public enum Substrate {
        /**
         * {@code br.unb.cic.mop.ExecutionContext}: one bound object per predicate, keyed by
         * {@code equals}, answering a boolean. The substrate of the frozen {@code jca} set.
         */
        EXECUTION_CONTEXT,
        /**
         * {@code br.unb.cic.mop.PredicateStore}: a bound object plus further value arguments, keyed
         * by identity, answering {@code SATISFIED | VIOLATED | NOT_OBSERVED}. The substrate of the
         * current {@code jca_android} set.
         */
        PREDICATE_STORE
    }
}
