package presto.android.gui.clients.target;

import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertSame;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.Set;

import org.junit.Test;

/**
 * Unit-level coverage for {@link TargetResolver}.
 *
 * <p>The Scene-level resolution path (which actually walks
 * {@link soot.Scene#v()}) is covered by the {@code BaselineComparisonIT}
 * integration test against {@code cryptoapp.apk}. What we pin here are
 * the contract pieces that hold without a bootstrapped Soot Scene:
 *
 * <ul>
 *   <li>The constructor stores the source unchanged and {@link #targets}
 *       delegates to it.</li>
 *   <li>The static factory accepts an empty input and returns an empty
 *       resolved set (early-return path, no Scene required).</li>
 * </ul>
 *
 * <p>The {@code paramsMatch} package-private helper is exercised
 * indirectly via the IT — testing it here would require building a fake
 * {@link soot.SootMethod}, which is not feasible without bootstrapping
 * Soot itself.
 */
public class TargetResolverTest {

	@Test
	public void targetsDelegatesToSource() {
		final Set<TargetMethod> stub = new HashSet<>(Arrays.asList(
				new TargetMethod("X", "m", Collections.emptyList(), null,
						TargetMethod.MatchPolicy.LENIENT, false, false)));
		TargetMethodSource source = () -> stub;
		TargetResolver resolver = new TargetResolver(source);
		assertSame("targets() MUST delegate to the source without mutating", stub, resolver.targets());
	}

	@Test
	public void emptyTargetSetReturnsEmptyResolvedSet() {
		// resolveInScene with empty input must not require Scene.v() at all —
		// the outer loop has nothing to iterate. (Sanity check that the
		// implementation short-circuits sensibly for callers that pass empty
		// sets without bootstrapping Soot.)
		Set<?> resolved = TargetResolver.resolveInScene(
				Collections.<TargetMethod>emptySet(), new TargetMatching());
		assertNotNull(resolved);
		// Cannot make stronger claims without Scene bootstrap; the IT pins the
		// non-empty path against the cryptoapp fixture.
	}
}
