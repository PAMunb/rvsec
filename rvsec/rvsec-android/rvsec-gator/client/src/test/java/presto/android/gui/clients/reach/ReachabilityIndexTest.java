package presto.android.gui.clients.reach;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.fail;

import java.util.Collections;
import java.util.HashSet;
import java.util.Set;

import org.junit.Test;

import soot.SootMethod;

/**
 * Unit tests for the immutable {@link ReachabilityIndex} data type that
 * do not require a Soot {@link soot.Scene}. Real per-method membership
 * checks are covered by the end-to-end {@code BaselineComparisonIT}.
 * The properties pinned here are the ones that hold independent of any
 * specific {@link SootMethod} instance:
 *
 * <ul>
 *   <li>Null-set rejection at construction (each of the three).</li>
 *   <li>Empty construction yields immutable empty published sets.</li>
 *   <li>Engine working-set mutation after publish does NOT leak into
 *       the index (defensive copy).</li>
 *   <li>Cardinality of the signature sets mirrors the input set
 *       cardinality (verified with empty input).</li>
 * </ul>
 */
public class ReachabilityIndexTest {

	@Test
	public void emptyConstructionProducesEmptyPublishedSets() {
		ReachabilityIndex idx = new ReachabilityIndex(
				Collections.emptySet(),
				Collections.emptySet(),
				Collections.emptySet());

		assertNotNull(idx.reachableMethods());
		assertEquals(0, idx.reachableMethods().size());
		assertEquals(0, idx.reachesTargetMethods().size());
		assertEquals(0, idx.directlyReachesTargetMethods().size());
		assertEquals(0, idx.reachesTargetSignatures().size());
		assertEquals(0, idx.directlyReachesTargetSignatures().size());
	}

	@Test
	public void publishedReachableSetIsUnmodifiable() {
		ReachabilityIndex idx = new ReachabilityIndex(
				new HashSet<>(),
				Collections.emptySet(),
				Collections.emptySet());

		try {
			idx.reachableMethods().add(null);
			fail("reachableMethods() MUST return an unmodifiable view");
		} catch (UnsupportedOperationException expected) {
			// pass
		}
	}

	@Test
	public void publishedReachesTargetSetIsUnmodifiable() {
		ReachabilityIndex idx = new ReachabilityIndex(
				Collections.emptySet(),
				new HashSet<>(),
				Collections.emptySet());

		try {
			idx.reachesTargetMethods().add(null);
			fail("reachesTargetMethods() MUST return an unmodifiable view");
		} catch (UnsupportedOperationException expected) {
			// pass
		}
	}

	@Test
	public void publishedDirectTargetSetIsUnmodifiable() {
		ReachabilityIndex idx = new ReachabilityIndex(
				Collections.emptySet(),
				Collections.emptySet(),
				new HashSet<>());

		try {
			idx.directlyReachesTargetMethods().add(null);
			fail("directlyReachesTargetMethods() MUST return an unmodifiable view");
		} catch (UnsupportedOperationException expected) {
			// pass
		}
	}

	@Test
	public void signatureSetsAreUnmodifiable() {
		ReachabilityIndex idx = new ReachabilityIndex(
				Collections.emptySet(),
				Collections.emptySet(),
				Collections.emptySet());

		try {
			idx.reachesTargetSignatures().add("<X: void m()>");
			fail("reachesTargetSignatures() MUST return an unmodifiable view");
		} catch (UnsupportedOperationException expected) {
			// pass
		}
		try {
			idx.directlyReachesTargetSignatures().add("<X: void m()>");
			fail("directlyReachesTargetSignatures() MUST return an unmodifiable view");
		} catch (UnsupportedOperationException expected) {
			// pass
		}
	}

	@Test
	public void engineWorkingSetMutationDoesNotLeakIntoIndex() {
		// The engine hands its working sets in by reference. Mutating them
		// after publishing the index MUST not affect the index's view.
		Set<SootMethod> working = new HashSet<>();
		ReachabilityIndex idx = new ReachabilityIndex(working, working, working);
		assertEquals(0, idx.reachableMethods().size());

		// SootMethod is hard to instantiate without Soot bootstrapping; the
		// type-erased Object insertion below proves the input-mutation safety
		// without depending on a real SootMethod. The published set still has
		// 0 entries even though `working` now has 1.
		((HashSet<Object>) (HashSet) working).add(new Object());
		assertEquals(1, working.size());
		assertEquals(0, idx.reachableMethods().size());
		assertEquals(0, idx.reachesTargetMethods().size());
		assertEquals(0, idx.directlyReachesTargetMethods().size());
	}

	@Test(expected = NullPointerException.class)
	public void nullReachableSetRejected() {
		new ReachabilityIndex(null, Collections.emptySet(), Collections.emptySet());
	}

	@Test(expected = NullPointerException.class)
	public void nullReachesTargetSetRejected() {
		new ReachabilityIndex(Collections.emptySet(), null, Collections.emptySet());
	}

	@Test(expected = NullPointerException.class)
	public void nullDirectTargetSetRejected() {
		new ReachabilityIndex(Collections.emptySet(), Collections.emptySet(), null);
	}
}
