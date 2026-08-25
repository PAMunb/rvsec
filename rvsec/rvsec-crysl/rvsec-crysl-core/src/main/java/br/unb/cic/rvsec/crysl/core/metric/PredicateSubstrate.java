package br.unb.cic.rvsec.crysl.core.metric;

import br.unb.cic.rvsec.crysl.core.model.Polarity;
import br.unb.cic.rvsec.crysl.core.model.PredicateRef;
import java.util.Optional;

/**
 * The two relations a {@code .mop} file can hold a predicate in, and what each of them can and
 * cannot say.
 *
 * <p>Both are read, and the reason is historical rather than defensive. The frozen {@code jca} set
 * is entirely on {@link #EXECUTION_CONTEXT} and the current {@code jca_android} set is entirely on
 * {@link #PREDICATE_STORE}; the published measurements were taken over the first. A reader that
 * knew only the substrate of today's working tree could not compute a number comparable with any
 * number already published, which is the comparison the calibration gate exists to make.
 *
 * <p>The two are not one relation with two spellings. Substrate A binds exactly one object per
 * predicate, compares it with {@code equals} and answers a boolean, so "the predicate was never
 * written" and "the predicate was written and does not hold" are the same answer. Substrate B binds
 * an object plus further value arguments, compares by identity, answers three-valued and offers
 * {@code validateAbsent}.
 *
 * <p>The consequence is a <em>structural ceiling</em> on A, and {@link #ceiling(PredicateRef)}
 * states it at the two strengths the corpus actually exhibits. A clause of arity 2 is
 * {@link Ceiling.Kind#INEXPRESSIBLE} on A: there is no second argument to bind, and no way of
 * writing the specification recovers it. A negated clause is weaker than that and stronger than
 * nothing: substrate A has no {@code validateAbsent}, but the frozen set writes the same demand
 * from the violating branch - {@code condition(! ExecutionContext.instance().validate(p, x))},
 * {@code jca/PBEKeySpecSpec.mop:56} - so the clause is written, and what it loses is the third
 * value. The read fires both when the predicate was written and is false and when it was never
 * written at all, which is {@link Ceiling.Kind#DEGRADED}: a projection of the clause, not its
 * absence. Calling that "inexpressible" would contradict a file of the corpus; calling it faithful
 * would claim a distinction the boolean substrate does not carry.
 *
 * <p>The ceiling is a property of the set it is measured over. At the stamp this component was
 * written against, {@code jca_android} has zero substrate-A sites, so the ceiling does not bind it;
 * reporting it as a defect of the current corpus would move a fact about the frozen set onto a set
 * that no longer has it. {@link SubstrateTrajectory} carries the measurement that makes that
 * sentence checkable.
 */
public enum PredicateSubstrate {

    /**
     * {@code br.unb.cic.mop.ExecutionContext}: one bound object per predicate, keyed by
     * {@code equals}, answering a boolean. The substrate of the frozen {@code jca} set.
     */
    EXECUTION_CONTEXT("context", 1, false, Keying.EQUALS, "boolean"),

    /**
     * {@code br.unb.cic.mop.PredicateStore}: a bound object plus further value arguments, keyed by
     * identity, answering {@code SATISFIED | VIOLATED | NOT_OBSERVED}, with {@code validateAbsent}.
     * The substrate of the current {@code jca_android} set.
     */
    PREDICATE_STORE("store", Integer.MAX_VALUE, true, Keying.IDENTITY,
            "SATISFIED | VIOLATED | NOT_OBSERVED");

    /** How a substrate decides that the object at a read is the object that was written. */
    public enum Keying {
        /** {@code equals}: a reconstructed value with the same contents is the same key. */
        EQUALS,
        /** Reference identity: a reconstructed value is a different key, whatever it contains. */
        IDENTITY
    }

    /**
     * What a substrate costs one rule reference.
     *
     * @param kind   how badly the substrate limits the reference
     * @param reason the limit stated in full, for the row that carries it
     */
    public record Ceiling(Kind kind, String reason) {

        /** The two strengths of limit the corpora exhibit. */
        public enum Kind {
            /** No specification on this substrate can state the clause at all. */
            INEXPRESSIBLE,
            /** The clause can be written, but the substrate loses part of what it says. */
            DEGRADED
        }
    }

    private final String mechanism;
    private final int maxArity;
    private final boolean distinguishesUnobserved;
    private final Keying keying;
    private final String verdictDomain;

    PredicateSubstrate(String mechanism, int maxArity, boolean distinguishesUnobserved,
                       Keying keying, String verdictDomain) {
        this.mechanism = mechanism;
        this.maxArity = maxArity;
        this.distinguishesUnobserved = distinguishesUnobserved;
        this.keying = keying;
        this.verdictDomain = verdictDomain;
    }

    /** The value the {@code mechanism} column of {@code predicate_graph.csv} carries for a site. */
    public String mechanism() {
        return mechanism;
    }

    /** How many arguments a reference on this substrate can carry. */
    public int maxArity() {
        return maxArity;
    }

    /** Whether a read can tell "never written" apart from "written and false". */
    public boolean distinguishesUnobserved() {
        return distinguishesUnobserved;
    }

    /** How the substrate decides two objects are the same key. */
    public Keying keying() {
        return keying;
    }

    /** What a read answers. */
    public String verdictDomain() {
        return verdictDomain;
    }

    /** Whether a rule reference can be stated at all in a file on this substrate. */
    public boolean canExpress(PredicateRef ref) {
        return ceiling(ref)
                .map(ceiling -> ceiling.kind() != Ceiling.Kind.INEXPRESSIBLE)
                .orElse(true);
    }

    /**
     * What this substrate costs the reference, or empty when it costs nothing.
     *
     * <p>The sentence travels with the finding because the ceiling is reported beside a
     * specification that could otherwise be read as having omitted the clause on purpose. "Arity 2
     * on a substrate that binds one object" is a different finding from "the author did not write
     * it", and only the first is unfixable without changing the substrate.
     */
    public Optional<Ceiling> ceiling(PredicateRef ref) {
        if (ref.arguments().size() > maxArity) {
            return Optional.of(new Ceiling(Ceiling.Kind.INEXPRESSIBLE,
                    "arity " + ref.arguments().size() + " on " + name() + ", which binds at most "
                            + maxArity + " object per predicate: the clause is inexpressible in "
                            + "this file however the specification is written"));
        }
        if (ref.polarity() == Polarity.NEGATED && !distinguishesUnobserved) {
            return Optional.of(new Ceiling(Ceiling.Kind.DEGRADED,
                    "a negated reference on " + name() + ", which answers a boolean: the demand is "
                            + "written as condition(!validate(...)) and fires both when the "
                            + "predicate is written and false and when it was never written, so "
                            + "the clause is projected rather than stated"));
        }
        return Optional.empty();
    }
}
