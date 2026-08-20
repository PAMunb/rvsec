package br.unb.cic.mop;

/**
 * The result of reading a CrySL predicate in a {@code jca_android} specification.
 *
 * <p>
 * The old substrate answered a predicate read with a boolean, which forced two very different
 * situations into the same answer: <em>the object carries the predicate with the wrong values</em>
 * and <em>nothing about this object was ever observed</em>. The first is positive evidence of a
 * misuse; the second is usually a reach artifact — the producing call was not woven, ran before
 * the monitor attached, or happens in a library the instrumentation does not cover. Reporting
 * both as a violation is what makes a runtime verifier accuse conforming code, so the two are
 * separated here and carry different codes in {@code codes.csv}.
 *
 * @see PredicateStore
 */
public enum PredicateVerdict {

	/** An entry exists for the object under this predicate and its value positions match. */
	SATISFIED,

	/**
	 * Positive evidence of a mismatch: an entry exists for the object under this predicate but
	 * its value positions differ, or the predicate was explicitly withdrawn by
	 * {@link PredicateStore#negate(Property, Object)}.
	 */
	VIOLATED,

	/**
	 * No entry at all. The producing event was never seen for this object, so the store has
	 * nothing to say — this is not a violation, and it reaches the report envelope under its own
	 * code precisely so that instrumentation reach can be told apart from misuse.
	 */
	NOT_OBSERVED
}
