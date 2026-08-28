package presto.android.gui.clients.target;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import org.junit.Test;

import soot.BooleanType;
import soot.IntType;
import soot.LongType;
import soot.SootMethod;
import soot.Type;
import soot.VoidType;

/**
 * STRICT parameter-list matching for {@link TargetResolver#paramsMatch}
 * (INV-ANA-35 / design.md §D7). This is the discriminator that
 * distinguishes overloads under {@link TargetMethod.MatchPolicy#STRICT}:
 * a target only resolves to a {@link SootMethod} whose parameter arity
 * AND per-index type spelling both agree.
 *
 * <p>Scene-free by construction. A real {@link SootMethod} is a plain
 * Soot data object — {@link SootMethod#getParameterCount()} and
 * {@link SootMethod#getParameterType(int)} read the list handed to the
 * constructor, and primitive {@link Type} singletons ({@code int},
 * {@code boolean}, {@code long}) stringify without touching
 * {@link soot.Scene}. The comparison target's params arrive as the raw
 * strings the source parsed from the MOP/signature file, so
 * {@code "int".equals(IntType.v().toString())} is exactly the production
 * comparison. (The outer {@code resolveInScene} walk over
 * {@code Scene.v().getClasses()} is the IT-only path, covered by
 * {@code BaselineComparisonIT} against {@code cryptoapp.apk}.)
 *
 * <p>Every rejection below is paired with a same-shape positive control
 * so a helper that always returned {@code false} could not pass.
 */
public class TargetResolverParamsMatchTest {

	/** Build a real, Scene-free SootMethod with the given primitive param types. */
	private static SootMethod methodWithParams(Type... params) {
		return new SootMethod("m", Arrays.asList(params), VoidType.v());
	}

	private static TargetMethod strictTarget(List<String> params) {
		return new TargetMethod("X", "m", params, null,
				TargetMethod.MatchPolicy.STRICT, false, false);
	}

	@Test
	public void parameterArityMismatchRejects() {
		// NEG: method takes (int, boolean) — two params — but the target
		// expects a single-param overload. The count guard rejects before
		// any per-index comparison runs.
		SootMethod twoParam = methodWithParams(IntType.v(), BooleanType.v());
		assertFalse("arity 2 must not match a single-param target",
				TargetResolver.paramsMatch(twoParam, strictTarget(
						Collections.singletonList("int"))));

		// POS control: same target, but a genuinely single-param (int)
		// overload — count agrees, the one type agrees, so it matches.
		SootMethod oneParam = methodWithParams(IntType.v());
		assertTrue("arity 1 (int) must match the single-param int target",
				TargetResolver.paramsMatch(oneParam, strictTarget(
						Collections.singletonList("int"))));
	}

	@Test
	public void perIndexTypeMismatchRejects() {
		// The target wants (int, boolean). NEG: an overload whose second
		// param is `long` — same arity, first type agrees, so the reject
		// happens INSIDE the loop at index 1 (not at the arity guard).
		SootMethod intLong = methodWithParams(IntType.v(), LongType.v());
		assertFalse("(int, long) must not match target (int, boolean) — index-1 differs",
				TargetResolver.paramsMatch(intLong, strictTarget(
						Arrays.asList("int", "boolean"))));

		// POS control: the matching (int, boolean) overload — every index
		// agrees, the loop runs to completion and the method matches.
		SootMethod intBool = methodWithParams(IntType.v(), BooleanType.v());
		assertTrue("(int, boolean) must match target (int, boolean)",
				TargetResolver.paramsMatch(intBool, strictTarget(
						Arrays.asList("int", "boolean"))));
	}

	@Test
	public void zeroParameterOverloadMatchesWithoutEnteringLoop() {
		// expected == 0: the arity guard passes (0 == 0) and the per-index
		// loop is skipped entirely, so a no-arg overload resolves to a
		// no-arg target. This isolates the loop-not-entered arm distinctly
		// from the arity-reject and per-index paths above.
		SootMethod noArg = methodWithParams();
		assertTrue("no-arg method must match a no-arg target via the empty-param fast path",
				TargetResolver.paramsMatch(noArg, strictTarget(Collections.emptyList())));

		// POS/NEG boundary control: the SAME no-arg method must NOT match a
		// one-param target — the arity guard alone rejects it.
		assertFalse("no-arg method must not match a single-param target",
				TargetResolver.paramsMatch(noArg, strictTarget(
						Collections.singletonList("int"))));
	}
}
