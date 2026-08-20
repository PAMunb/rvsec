package br.unb.cic.mop.eh;

/**
 * What kind of misuse a violation report is about.
 *
 * <p>
 * This is the first thing a developer reads on a report, and it decides where they go looking.
 * The vocabulary therefore follows the CrySL clause families the specifications encode, so that
 * a report never sends the reader to the wrong place: an argument outside an allow-list is not a
 * call-order defect, and a call that must not exist at all is neither.
 *
 * <p>
 * {@code ForbiddenMethod} is the type of a CrySL {@code FORBIDDEN} clause — a per-call
 * prohibition, not a predicate and not a sequencing rule. {@code jca_android}'s
 * {@code PBEKeySpecSpec} encodes the two {@code FORBIDDEN} constructors that
 * {@code generated/api30/PBEKeySpec.cryptsl} declares; before this type existed they reported
 * {@code InvalidSequenceOfMethodCalls}, which sent the reader hunting for a missing call when
 * the finding is the constructor itself.
 *
 * <p>
 * There is deliberately no {@code RequiredPredicate}. Every predicate-guarded accuser of the set
 * reports {@code UnsatisfiedConstraint}, which is what a failed CrySL {@code REQUIRES} is: the
 * constraint the clause states went unsatisfied. A second name for one condition would split it
 * across two vocabularies, and a value no specification emits reads as live to the next reader.
 */
public enum ErrorType {
    UnsafeAlgorithm,
    InvalidSequenceOfMethodCalls,
    UnsatisfiedConstraint,
    InvalidKeySize,
    InvalidKeyStoreType,
    UnsafeProtocol,
    ForbiddenMethod
}
