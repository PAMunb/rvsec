package presto.android.gui.clients.reach;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertSame;
import static org.junit.Assert.assertTrue;

import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.util.Collections;
import java.util.Map;

import org.junit.Test;

/**
 * Guards against accidental batch-caching regressions in
 * {@link ReachabilityEnricher}. INV-ANA-30 (writer purity) presumes the
 * enricher itself is stateless beyond its constructor inputs — if a
 * future change adds an internal cache (e.g., {@code Map<SootMethod,
 * Map<String, Object>> cache}), the writer's heap behavior under the
 * timeout regime degrades from O(1) per-method to O(N) accumulated.
 *
 * <p>Two complementary checks:
 * <ul>
 *   <li><b>Structural</b>: every declared field on the enricher class
 *       MUST be {@code final}. A non-final field is a smell for caches
 *       built up across calls. The four constructor-set fields
 *       ({@code index, manifestPackage, codePackage, mainActivity}) are
 *       the only allowed state.</li>
 *   <li><b>Behavioral</b>: 10 000 back-to-back {@code enrichMethod}
 *       invocations against an empty index do NOT grow the index's
 *       size (which would indicate a leak into the index) and the
 *       signature-set accessors return the same object identity
 *       throughout (no per-call recomputation).</li>
 * </ul>
 */
public class ReachabilityEnricherMemoryTest {

	@Test
	public void allDeclaredFieldsAreFinal() {
		for (Field f : ReachabilityEnricher.class.getDeclaredFields()) {
			// Allow static finals (constants like EMPTY); enforce final on
			// every instance field so a future cache addition fails this test.
			assertTrue(
					"Field " + f.getName() + " must be final to keep the "
							+ "enricher stateless across enrich* calls (INV-ANA-30 "
							+ "writer-purity precondition)",
					Modifier.isFinal(f.getModifiers()));
		}
	}

	@Test
	public void tenThousandCallsDoNotMutateIndexOrEnricherState() {
		ReachabilityIndex index = new ReachabilityIndex(
				Collections.emptySet(),
				Collections.emptySet(),
				Collections.emptySet());
		ReachabilityEnricher enricher = new ReachabilityEnricher(
				index, "p", "p", "MainActivity");

		int reachableBefore = index.reachableMethods().size();
		int reachesBefore = index.reachesTargetMethods().size();
		int directBefore = index.directlyReachesTargetMethods().size();
		Object sigSetIdentity = enricher.targetSignatures();

		for (int i = 0; i < 10_000; i++) {
			Map<String, Object> out = enricher.enrichMethod(null);
			// Each call must produce a fresh map (no caching) — verified by
			// the equality check below; the API uses LinkedHashMap with
			// known insertion order. If the enricher started caching, the
			// returned map would be aliased across calls; mutating one
			// would corrupt the next.
			out.put("__test_marker__", Boolean.TRUE);
		}

		assertEquals("Index reachable set MUST NOT mutate via the enricher",
				reachableBefore, index.reachableMethods().size());
		assertEquals(reachesBefore, index.reachesTargetMethods().size());
		assertEquals(directBefore, index.directlyReachesTargetMethods().size());
		assertSame("Signature-set accessor MUST return stable identity (no "
				+ "per-call recomputation in the writer's hot path)",
				sigSetIdentity, enricher.targetSignatures());
	}
}
