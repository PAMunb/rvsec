package presto.android.gui.clients.wtg.model;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotSame;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

/**
 * Value-semantics locks for the two pure-POJO WTG model nodes: {@link Window}
 * (a WTG vertex) and {@link Result} (the top-level container of windows +
 * transitions). Both are zero-dependency POJOs — no Soot, no GATOR graph —
 * so the whole of {@code Window} and the null-safe accumulation half of
 * {@code Result} are exercised here without any fixture scaffolding.
 *
 * <p>Every negative assertion is paired with a same-shape positive control so
 * a future regression that inverts a guard (e.g. a broken {@code equals} that
 * always returns {@code true}, or an {@code addWindow} that stops null-checking)
 * fails loudly rather than silently passing.</p>
 *
 * <p><b>Scope note.</b> {@link Result#addTransition(Transition)} is deliberately
 * NOT covered here: {@link Transition}'s only constructor takes a GATOR
 * {@code WTGEdge} and dereferences the source/target window graph, so a valid
 * non-null {@code Transition} — the positive control the null-guard needs —
 * cannot be built without WTG scaffolding. That belongs with the Transition/Event
 * batch, where the {@code WTGEdge} stub is constructed anyway.</p>
 */
public class WtgModelValueSemanticsTest {

	// ── Window: identity + equals/hashCode contract ──────────────────────

	/**
	 * The reflexive fast-path (this == obj) short-circuits equals to true, and
	 * the constructor faithfully surfaces id/name through the getters. Concrete
	 * values: Window(42, "com.example.MainActivity") equals itself; getId()==42;
	 * getName() returns the exact class name.
	 */
	@Test
	public void windowIsReflexivelyEqualAndExposesConstructorFields() {
		Window w = new Window(42, "com.example.MainActivity");

		assertEquals(42, w.getId());
		assertEquals("com.example.MainActivity", w.getName());
		assertTrue("a Window must equal itself (reflexive fast-path)", w.equals(w));
	}

	/**
	 * Two DISTINCT instances with identical id+name are equal and share a hash
	 * code — the value-equality contract that lets Windows dedup inside the
	 * HashSet backing {@link Result}. Exercises the full happy path of equals:
	 * this!=obj, obj!=null, same class, id==id, name.equals(name) all true.
	 */
	@Test
	public void windowsWithSameFieldsAreEqualAndShareHashCode() {
		Window a = new Window(7, "Foo");
		Window b = new Window(7, "Foo");

		assertNotSame(a, b);
		assertTrue("distinct Windows with equal id+name must be equal", a.equals(b));
		assertEquals("equal Windows must share a hash code", a.hashCode(), b.hashCode());
	}

	/**
	 * equals against null takes the (obj == null) arm and returns false — a
	 * Window is never equal to null. Positive control: the same instance IS
	 * equal to an equal-valued sibling (proves the method can still say true).
	 */
	@Test
	public void windowIsNotEqualToNull() {
		Window w = new Window(1, "Foo");

		assertFalse("a Window must never equal null", w.equals(null));
		assertTrue("positive control: still equal to an equal-valued Window",
				w.equals(new Window(1, "Foo")));
	}

	/**
	 * equals against a foreign type takes the (getClass() != obj.getClass())
	 * arm and returns false — a Window is not equal to a String even when the
	 * String looks like its name. Positive control: equal to a real Window.
	 */
	@Test
	public void windowIsNotEqualToForeignType() {
		Window w = new Window(1, "Foo");

		assertFalse("a Window must not equal a non-Window object",
				w.equals("Foo"));
		assertTrue("positive control: equal to a same-typed, same-valued Window",
				w.equals(new Window(1, "Foo")));
	}

	/**
	 * A differing id breaks equality via the (id == other.id) conjunct — even
	 * when the name matches. Window(1,"Foo") != Window(2,"Foo"). Positive
	 * control: same id+name still equal.
	 */
	@Test
	public void windowWithDifferentIdIsNotEqual() {
		Window base = new Window(1, "Foo");

		assertFalse("different id must break equality despite matching name",
				base.equals(new Window(2, "Foo")));
		assertTrue("positive control: matching id+name is equal",
				base.equals(new Window(1, "Foo")));
	}

	/**
	 * A differing name breaks equality via the Objects.equals(name, other.name)
	 * conjunct — even when the id matches. Window(1,"Foo") != Window(1,"Bar").
	 * Positive control: same id+name still equal.
	 */
	@Test
	public void windowWithDifferentNameIsNotEqual() {
		Window base = new Window(1, "Foo");

		assertFalse("different name must break equality despite matching id",
				base.equals(new Window(1, "Bar")));
		assertTrue("positive control: matching id+name is equal",
				base.equals(new Window(1, "Foo")));
	}

	/**
	 * toString renders both fields in the documented {@code Window [id=.., name=..]}
	 * shape — the human-readable form used in GATOR/WTG debug logs.
	 */
	@Test
	public void windowToStringContainsIdAndName() {
		String s = new Window(9, "com.example.Login").toString();

		assertTrue("toString must include the id, got: " + s, s.contains("9"));
		assertTrue("toString must include the name, got: " + s,
				s.contains("com.example.Login"));
	}

	// ── Result: null-safe window accumulation ────────────────────────────

	/**
	 * A freshly constructed Result exposes empty (but non-null) window and
	 * transition sets — the caller can iterate without a null check before any
	 * add. This locks the field initialisers (new HashSet<>()).
	 */
	@Test
	public void freshResultHasEmptyNonNullSets() {
		Result r = new Result();

		assertTrue("windows must start empty", r.getWindows().isEmpty());
		assertTrue("transitions must start empty", r.getTransitions().isEmpty());
	}

	/**
	 * addWindow accumulates distinct windows into the backing set and dedups by
	 * value equality — adding an equal-valued Window a second time does not grow
	 * the set (proves Window.equals/hashCode are wired into the HashSet).
	 */
	@Test
	public void addWindowAccumulatesAndDedupsByValue() {
		Result r = new Result();
		r.addWindow(new Window(1, "A"));
		r.addWindow(new Window(2, "B"));
		assertEquals("two distinct windows accumulate", 2, r.getWindows().size());

		r.addWindow(new Window(1, "A")); // equal to the first → no growth
		assertEquals("an equal-valued window must not grow the set",
				2, r.getWindows().size());
	}

	/**
	 * addWindow(null) hits the (window != null) guard's false arm and is a
	 * silent no-op — the set is unchanged. Positive control in the same test:
	 * a real add DOES land, proving the guard admits non-null values rather
	 * than dropping everything.
	 */
	@Test
	public void addNullWindowIsSilentNoOp() {
		Result r = new Result();

		r.addWindow(null);
		assertTrue("null window must be ignored", r.getWindows().isEmpty());

		r.addWindow(new Window(5, "Real")); // positive control
		assertEquals("a non-null window must be added", 1, r.getWindows().size());

		r.addWindow(null); // no-op again, alongside an existing entry
		assertEquals("a trailing null must not disturb existing entries",
				1, r.getWindows().size());
	}
}
