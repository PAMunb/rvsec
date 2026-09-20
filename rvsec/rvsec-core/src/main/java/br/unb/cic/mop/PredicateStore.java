package br.unb.cic.mop;

import java.lang.ref.Reference;
import java.lang.ref.ReferenceQueue;
import java.lang.ref.WeakReference;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicReference;

/**
 * The predicate substrate of the {@code jca_android} specification set: it records the
 * {@code ENSURES} clauses a monitored program satisfied and answers the {@code REQUIRES} clauses
 * that read them.
 *
 * <h2>The four properties it is built around</h2>
 *
 * <ul>
 * <li><b>Identity keying.</b> The generated monitors index their parameter bindings by object
 * identity ({@code CachedWeakReference}). A store keyed by {@code equals} answers about a
 * <em>different</em> object whenever the API defines value equality — two {@code SecretKeySpec}s
 * over the same bytes are {@code equals}, and one of them being securely generated says nothing
 * about the other.</li>
 * <li><b>Arity N.</b> CrySL predicates carry argument lists ({@code generatedKey[key, "AES"]}),
 * and a large share of the oracle's clauses need at least two places. A store that records only
 * the object cannot tell {@code generatedKey[key, "AES"]} from
 * {@code generatedKey[key, "DES"]}.</li>
 * <li><b>Three-valued reads.</b> See {@link PredicateVerdict}.</li>
 * <li><b>Weak keys.</b> A marked object is held only weakly, so marking it never keeps it alive
 * for the lifetime of the process.</li>
 * </ul>
 *
 * <p>
 * <b>Why {@code bound} is a separate parameter and not the head of the varargs.</b> A signature of
 * the form {@code ensure(Property, Object...)} silently spreads a reference-array argument: the
 * TLS chain binds {@code KeyManager[]} and {@code TrustManager[]}, and passing one of those to a
 * varargs head makes each element a separate argument (an empty array yields no arguments at
 * all). The compiler only warns, and the warning is off in every build path here. Naming the bound
 * object makes the spread impossible.
 *
 * <p>
 * <b>Value positions.</b> Only positions whose declared type is {@code String}, {@code int} or
 * {@code Integer} are compared by value, case-insensitively — those are the types the oracle's
 * tracked values have. Every other position is compared by identity, like the bound object. The
 * oracle's splitters ({@code part(0,"/",transformation)}) are applied by the caller, which is the
 * side that holds the clause.
 *
 * <p>
 * <b>Null tolerance.</b> These methods run inside woven advice in the application under test, so
 * they never throw: a {@code null} bound object makes {@code ensure}/{@code negate} a no-op and
 * makes a read answer as if nothing were recorded. A monitor that crashed the app it monitors
 * would destroy the measurement it exists to produce.
 *
 * <p>
 * Deliberately not offered: a predicate-wide query ("does this object carry any predicate?") and a
 * removal that names a property without naming an object. The first has no call site in any
 * specification, and the second would negate a predicate for every object that ever satisfied it,
 * which is not a semantics CrySL has. {@link #validateAny(Property, Object)} is not the first of
 * those in disguise: it names the property and asks only about the positions the rule itself
 * leaves anonymous.
 */
public final class PredicateStore {

	/**
	 * The state every negation swaps in: nothing recorded, and positively negated.
	 *
	 * <p>
	 * The flag is what makes an explicit {@code NEGATES} distinguishable from never having
	 * observed the predicate: dropping the entry instead would answer {@code NOT_OBSERVED}, which
	 * reads as "the producer is not instrumented" and stays silent, whereas a negated predicate is
	 * positive evidence and must accuse.
	 */
	private static final State NEGATED = new State(true, Collections.<ValueTuple>emptySet());

	private static final class Entry {
		/**
		 * The two facts an entry carries, held as one value behind one reference.
		 *
		 * <p>
		 * Whether the predicate is negated and which argument lists are recorded have to be
		 * read together or not at all. As two fields they cannot be, however they are
		 * ordered: a reader that samples {@code negated} and then {@code tuples} can be
		 * descheduled between the two reads and land on a pair that never existed at any one
		 * instant. The pair it lands on is {@code negated == false} with no tuples, which
		 * {@link PredicateStore#validate(Property, Object, Object...)} reads as
		 * {@code NOT_OBSERVED} -- the one answer that suppresses an accusation about an object
		 * the store positively knows something about. A single volatile reference to an
		 * immutable state makes every read a snapshot.
		 */
		private final AtomicReference<State> state = new AtomicReference<State>(State.EMPTY);
	}

	/**
	 * One entry's whole content: negated or not, and the argument lists recorded so far.
	 *
	 * <p>
	 * Immutable, so a reader that holds one never sees it change under itself. {@code ensure}
	 * copies on write; the sets are one to three tuples in every clause of the oracle, so the
	 * copy is cheaper than the lock that would be needed to avoid it.
	 */
	private static final class State {
		private static final State EMPTY = new State(false, Collections.<ValueTuple>emptySet());

		private final boolean negated;
		private final Set<ValueTuple> tuples;

		private State(boolean negated, Set<ValueTuple> tuples) {
			this.negated = negated;
			this.tuples = tuples;
		}

		private State withTuple(ValueTuple tuple) {
			Set<ValueTuple> next = new HashSet<ValueTuple>(tuples);
			next.add(tuple);
			return new State(false, Collections.unmodifiableSet(next));
		}
	}

	/**
	 * One recorded argument list, compared position by position under the tracked-type rule.
	 */
	private static final class ValueTuple {
		private final ValueKey[] keys;
		private final int hash;

		private ValueTuple(Object[] values) {
			keys = new ValueKey[values.length];
			for (int i = 0; i < values.length; i++) {
				keys[i] = new ValueKey(values[i]);
			}
			hash = Arrays.hashCode(keys);
		}

		@Override
		public int hashCode() {
			return hash;
		}

		@Override
		public boolean equals(Object other) {
			if (this == other) {
				return true;
			}
			if (!(other instanceof ValueTuple)) {
				return false;
			}
			return Arrays.equals(keys, ((ValueTuple) other).keys);
		}
	}

	/**
	 * One argument position. Tracked types collapse to a normalized string; everything else is
	 * held weakly and compared by identity, so a value position never pins the object it names.
	 */
	private static final class ValueKey {
		private final String text;
		private final WeakReference<Object> ref;
		private final int hash;

		private ValueKey(Object value) {
			if (value == null) {
				text = null;
				ref = null;
				hash = 0;
			} else if (value instanceof String) {
				text = ((String) value).toLowerCase(Locale.ROOT);
				ref = null;
				hash = text.hashCode();
			} else if (value instanceof Integer) {
				text = value.toString();
				ref = null;
				hash = text.hashCode();
			} else {
				text = null;
				ref = new WeakReference<Object>(value);
				hash = System.identityHashCode(value);
			}
		}

		@Override
		public int hashCode() {
			return hash;
		}

		@Override
		public boolean equals(Object other) {
			if (this == other) {
				return true;
			}
			if (!(other instanceof ValueKey)) {
				return false;
			}
			ValueKey that = (ValueKey) other;
			if (text != null) {
				return text.equals(that.text);
			}
			if (that.text != null) {
				return false;
			}
			if (ref == null || that.ref == null) {
				return ref == that.ref;
			}
			Object mine = ref.get();
			return mine != null && mine == that.ref.get();
		}
	}

	/**
	 * The map key for a bound object: identity equality over a weakly held referent.
	 *
	 * <p>
	 * The identity hash is captured at construction because it must survive the referent being
	 * collected — otherwise the dead entry could never be located and removed.
	 */
	private static final class BoundKey extends WeakReference<Object> {
		private final int hash;

		private BoundKey(Object referent) {
			super(referent);
			hash = System.identityHashCode(referent);
		}

		private BoundKey(Object referent, ReferenceQueue<Object> queue) {
			super(referent, queue);
			hash = System.identityHashCode(referent);
		}

		@Override
		public int hashCode() {
			return hash;
		}

		@Override
		public boolean equals(Object other) {
			if (this == other) {
				return true;
			}
			if (!(other instanceof BoundKey)) {
				return false;
			}
			Object mine = get();
			return mine != null && mine == ((BoundKey) other).get();
		}
	}

	/**
	 * Holder idiom: the class initializes on first use and the JVM guarantees the publication, so
	 * the singleton needs no lazy null check of its own and no two threads can race to build it.
	 */
	private static final class Holder {
		private static final PredicateStore INSTANCE = new PredicateStore();
	}

	private final ConcurrentHashMap<BoundKey, ConcurrentHashMap<Property, Entry>> context =
			new ConcurrentHashMap<BoundKey, ConcurrentHashMap<Property, Entry>>();

	private final ReferenceQueue<Object> collected = new ReferenceQueue<Object>();

	private PredicateStore() {
	}

	/**
	 * Obtain the process-wide store.
	 *
	 * <p>
	 * The instance is built on first use and published by the class initializer, so every monitor
	 * woven into the application shares one store and a mark written by one specification is
	 * readable by another.
	 *
	 * @return the singleton store shared by every {@code jca_android} monitor in the process.
	 */
	public static PredicateStore instance() {
		return Holder.INSTANCE;
	}

	/**
	 * Record that {@code bound} satisfies {@code p} with the given argument list — the runtime
	 * translation of an {@code ENSURES} clause.
	 *
	 * <p>
	 * Idempotent per (property, object identity, values). Recording the same predicate with a
	 * different argument list adds a second tuple rather than replacing the first: an object can
	 * legitimately satisfy {@code randomized} more than once, and a read matches if any recorded
	 * tuple matches. An {@code ensure} after a {@link #negate(Property, Object)} reinstates the
	 * predicate.
	 *
	 * @param p the predicate being recorded
	 * @param bound the object the predicate is about; {@code null} makes the call a no-op
	 * @param values the remaining argument positions of the clause, splitters already applied
	 */
	public void ensure(Property p, Object bound, Object... values) {
		if (bound == null) {
			return;
		}
		purge();
		Entry entry = entryFor(bound, p, true);
		// Read-modify-write under a compare-and-set loop, because two threads ensuring
		// different argument lists for one object must not lose either. The swap is a
		// single reference write, so a concurrent reader sees the state before it or the
		// state after it and never a half of each.
		ValueTuple tuple = new ValueTuple(values);
		State current;
		do {
			current = entry.state.get();
		} while (!entry.state.compareAndSet(current, current.withTuple(tuple)));
	}

	/**
	 * Negate {@code p} for exactly this object — the runtime translation of a {@code NEGATES}
	 * clause, whose live case is {@code PBEKeySpec.clearPassword}.
	 *
	 * <p>
	 * The negation is remembered rather than forgotten: a later {@link #validate} answers
	 * {@link PredicateVerdict#VIOLATED}, not {@link PredicateVerdict#NOT_OBSERVED}, because the
	 * store positively knows that the predicate does not hold for this object.
	 *
	 * @param p the predicate being negated
	 * @param bound the object it is negated for; {@code null} makes the call a no-op
	 */
	public void negate(Property p, Object bound) {
		if (bound == null) {
			return;
		}
		purge();
		Entry entry = entryFor(bound, p, true);
		// A negation discards whatever is recorded, so it needs no read of the current
		// state: one unconditional swap to the negated state, which a reader sees whole.
		entry.state.set(NEGATED);
	}

	/**
	 * Read a positive {@code REQUIRES} clause: does {@code bound} carry {@code p} with exactly
	 * these remaining argument positions?
	 *
	 * <p>
	 * Each of the three answers says something different, and a caller has to act on all three.
	 * {@link PredicateVerdict#SATISFIED} means a recorded tuple matches position for position,
	 * under the tracked-type rule this class documents — the clause is met and nothing is
	 * reported. {@link PredicateVerdict#VIOLATED} is positive evidence of a misuse: the store
	 * holds the predicate for this very object with other values, or
	 * {@link #negate(Property, Object)} negated it, so the clause is broken by something the
	 * instrumentation actually saw. {@link PredicateVerdict#NOT_OBSERVED} means the store has no
	 * entry at all for this object under this predicate, which must not be reported as a misuse:
	 * the producing call may simply be one the weaving does not reach.
	 *
	 * <p>
	 * A {@code null} bound object answers {@link PredicateVerdict#NOT_OBSERVED} rather than
	 * throwing, for the reason the class states: this runs inside woven advice in the program
	 * under test.
	 *
	 * @param p the required predicate
	 * @param bound the object the clause is about
	 * @param values the remaining argument positions, splitters already applied
	 * @return {@link PredicateVerdict#SATISFIED} when a recorded tuple matches,
	 *         {@link PredicateVerdict#VIOLATED} when the object carries the predicate with other
	 *         values or had it negated, {@link PredicateVerdict#NOT_OBSERVED} when nothing was
	 *         ever recorded for this object under this predicate
	 */
	public PredicateVerdict validate(Property p, Object bound, Object... values) {
		if (bound == null) {
			return PredicateVerdict.NOT_OBSERVED;
		}
		purge();
		Entry entry = entryFor(bound, p, false);
		if (entry == null) {
			return PredicateVerdict.NOT_OBSERVED;
		}
		// One read. Every question below is asked of the same instant.
		State state = entry.state.get();
		if (state.negated) {
			return PredicateVerdict.VIOLATED;
		}
		if (state.tuples.isEmpty()) {
			return PredicateVerdict.NOT_OBSERVED;
		}
		return state.tuples.contains(new ValueTuple(values))
				? PredicateVerdict.SATISFIED
				: PredicateVerdict.VIOLATED;
	}

	/**
	 * Read a positive {@code REQUIRES} clause whose remaining positions the rule leaves
	 * <em>anonymous</em> — CrySL's {@code pred[bound, _]}.
	 *
	 * <p>
	 * {@link #validate(Property, Object, Object...)} compares the whole argument list, which is
	 * what a clause naming every position asks for. A clause writing {@code _} asks something
	 * else: <em>this object carries the predicate, whatever it carries it with</em>. Reading such
	 * a clause through {@code validate} with no values compares against the empty tuple, which no
	 * producer of a one-place-or-wider clause ever records, so every conforming object comes back
	 * {@link PredicateVerdict#VIOLATED} — positive evidence of a misuse, about a program that
	 * committed none.
	 *
	 * <p>
	 * Filling the {@code _} in at the call site is not the same thing: the three producers of
	 * {@code generatedKey} do not agree on what they write there —
	 * {@code KeyGeneratorSpec} writes the string the program handed {@code getInstance},
	 * {@code KeyStoreSpec} and {@code SecretKeySpecSpec} write the key's own algorithm — so a
	 * reader that guessed one of them would answer {@code VIOLATED} whenever a program spelled the
	 * algorithm the other way, which on this platform is an ordinary Conscrypt alias.
	 *
	 * <p>
	 * The negation flag is honoured exactly as in {@code validate}: a predicate that
	 * {@link #negate(Property, Object)} negated is {@code VIOLATED} and not merely absent.
	 *
	 * @param p the required predicate
	 * @param bound the object the clause is about
	 * @return {@link PredicateVerdict#SATISFIED} when any tuple is recorded for this object under
	 *         this predicate, {@link PredicateVerdict#VIOLATED} when it was negated,
	 *         {@link PredicateVerdict#NOT_OBSERVED} when nothing was ever recorded
	 */
	public PredicateVerdict validateAny(Property p, Object bound) {
		if (bound == null) {
			return PredicateVerdict.NOT_OBSERVED;
		}
		purge();
		Entry entry = entryFor(bound, p, false);
		if (entry == null) {
			return PredicateVerdict.NOT_OBSERVED;
		}
		// One read, for the reason validate states: the pair has to be sampled at one instant.
		State state = entry.state.get();
		if (state.negated) {
			return PredicateVerdict.VIOLATED;
		}
		return state.tuples.isEmpty()
				? PredicateVerdict.NOT_OBSERVED
				: PredicateVerdict.SATISFIED;
	}

	/**
	 * Read a negated {@code REQUIRES} clause ({@code !pred[…]}) — the oracle has exactly three,
	 * {@code Cipher: !macced[_, plainText]} and the two {@code Mac: !encrypted[…]}.
	 *
	 * <p>
	 * The table is inverted: absence is the conforming case. Reading such a clause through
	 * {@link #validate} would emit <em>not observed</em> on every conforming {@code Mac.doFinal},
	 * which is exactly backwards.
	 *
	 * <p>
	 * The argument list is accepted for symmetry with {@link #validate} and deliberately not
	 * compared. The clause asks whether the object carries a same-name predicate at all — the
	 * oracle's own branch for negated clauses fails on any ensured predicate of that name,
	 * whatever its arguments — so narrowing by values here would let a violation through whenever
	 * the recorded arguments happened to differ.
	 *
	 * @param p the predicate that must be absent
	 * @param bound the object the clause is about
	 * @param values accepted for symmetry; not compared
	 * @return {@link PredicateVerdict#SATISFIED} when the object carries no live entry for
	 *         {@code p}, {@link PredicateVerdict#VIOLATED} when it does. Never
	 *         {@link PredicateVerdict#NOT_OBSERVED}: for a negated clause, having observed nothing
	 *         <em>is</em> conformance.
	 */
	public PredicateVerdict validateAbsent(Property p, Object bound, Object... values) {
		if (bound == null) {
			return PredicateVerdict.SATISFIED;
		}
		purge();
		Entry entry = entryFor(bound, p, false);
		if (entry == null) {
			return PredicateVerdict.SATISFIED;
		}
		State state = entry.state.get();
		if (state.negated || state.tuples.isEmpty()) {
			return PredicateVerdict.SATISFIED;
		}
		return PredicateVerdict.VIOLATED;
	}

	/**
	 * Clear every recorded predicate.
	 *
	 * <p>
	 * Test-only, and production has no caller — but it is not optional scaffolding. The
	 * differential trace harness rebuilds a class loader per trace, while this singleton resolves
	 * through the parent loader and therefore survives a whole directory replay: without an
	 * explicit reset between traces, a satisfying trace silently satisfies the violating trace
	 * that follows it, and the pair evidence reports a pass it did not earn.
	 */
	public void reset() {
		context.clear();
		while (collected.poll() != null) {
			// drain the queue too, so a reset leaves no stale notification behind
		}
	}

	/**
	 * Count the bound objects the store still holds entries for, after draining the queue.
	 *
	 * <p>
	 * Package-private and used by one test: purge is otherwise unobservable from outside, and an
	 * invariant that cannot be checked is an invariant that drifts.
	 *
	 * @return the live entry count
	 */
	int boundObjectCount() {
		purge();
		return context.size();
	}

	/**
	 * Locate the entry for (object, property), creating it only for a write.
	 */
	private Entry entryFor(Object bound, Property p, boolean create) {
		// The lookup key is unregistered: only the key the map actually keeps may sit in the
		// reference queue, or a collected object would enqueue one notification per write and
		// all but the first would find nothing to remove.
		ConcurrentHashMap<Property, Entry> byProperty = context.get(new BoundKey(bound));
		if (!create) {
			return byProperty == null ? null : byProperty.get(p);
		}
		if (byProperty == null) {
			ConcurrentHashMap<Property, Entry> created = new ConcurrentHashMap<Property, Entry>();
			byProperty = context.putIfAbsent(new BoundKey(bound, collected), created);
			if (byProperty == null) {
				byProperty = created;
			}
		}
		Entry entry = byProperty.get(p);
		if (entry == null) {
			Entry created = new Entry();
			entry = byProperty.putIfAbsent(p, created);
			if (entry == null) {
				entry = created;
			}
		}
		return entry;
	}

	/**
	 * Drop the entries whose bound object has been collected. Draining the queue on every
	 * operation keeps the map proportional to the live objects without a background thread.
	 */
	private void purge() {
		Reference<?> dead;
		while ((dead = collected.poll()) != null) {
			context.remove(dead);
		}
	}
}
