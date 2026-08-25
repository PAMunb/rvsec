package br.unb.cic.rvsec.crysl.core.model;

/**
 * A typed refusal: the metric could not decide, and says why in a form that can be counted.
 *
 * <p>A refusal is not an error. "Could not read" and "is not there" are different columns of every
 * table this component emits, and collapsing them is how a coverage figure quietly turns an
 * instrument limitation into a subject defect.
 *
 * <p>The hierarchy is sealed to exactly six tags (INV-CONF-06). Closing it in the type system is
 * what makes adding one a visible contract change rather than a commit nobody reviews; the count of
 * each tag travels beside every coverage number, so a rising refusal rate is visible rather than
 * absorbed.
 *
 * <p>{@link UnreachableAccusationSite} is the sixth, added by researcher decision on 2026-08-24 and
 * not by drift. The taxonomy had five, INV-CONF-09 requires M0's refusal to be emitted as a typed
 * {@code Unknown}, and none of the five named what M0 refuses: the nearest,
 * {@link UnresolvedSignature}, asserts something else — a signature the platform lacks. Design D-11
 * does not forbid a sixth tag; it requires that adding one be visible, and this paragraph, the
 * amended invariant and the exact count asserted by {@code UnknownTaxonomyTest} are that
 * visibility. A seventh must go through the same door.
 */
public sealed interface Unknown
        permits UnrecognizedConstraint, OverlappingDispatch, MultiSlicedOrder,
                UnresolvedSignature, UntranslatableConstraint, UnreachableAccusationSite {

    /** Where the refusal happened, as {@code file:line}. */
    Provenance site();
}
