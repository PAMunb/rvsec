package presto.android.gui.clients.reach;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertSame;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;

import org.junit.Test;

import soot.SootMethod;

/**
 * Unit-level coverage for {@link ReachabilityEnricher}.
 *
 * <p>Tests rely on the {@code SootMethod}-free corners of the enricher
 * contract that are testable without bootstrapping Soot:
 * <ul>
 *   <li>{@link ReachabilityEnricher#enrichMethod} returns a 3-key map
 *       and the value of each key matches the underlying
 *       {@link ReachabilityIndex} state (verified with empty index —
 *       all flags are {@code false}).</li>
 *   <li>{@link ReachabilityEnricher#enrichWidget},
 *       {@link ReachabilityEnricher#enrichTransition}, and
 *       {@link ReachabilityEnricher#enrichComponent} return empty maps
 *       (placeholders until C3).</li>
 *   <li>{@link ReachabilityEnricher#topLevelMetadata} returns exactly
 *       {@code {manifestPackage, codePackage, mainActivity}}.</li>
 *   <li>Calls are idempotent — back-to-back invocations on the same
 *       (empty) input produce equal maps with no internal mutation
 *       (verified by comparing object identity of the underlying
 *       signature sets across calls).</li>
 *   <li>Null index rejection at construction.</li>
 * </ul>
 *
 * <p>The non-empty membership branch (real reachable / reaches-target /
 * directly-reaches-target methods) is covered by the end-to-end
 * {@code BaselineComparisonIT}.
 */
public class ReachabilityEnricherTest {

	private ReachabilityIndex emptyIndex() {
		return new ReachabilityIndex(
				Collections.emptySet(),
				Collections.emptySet(),
				Collections.emptySet());
	}

	@Test(expected = NullPointerException.class)
	public void nullIndexRejected() {
		new ReachabilityEnricher(null, "p", "p", "MainActivity");
	}

	@Test
	public void enrichMethodHasThreeReachabilityKeys() {
		ReachabilityEnricher enricher = new ReachabilityEnricher(
				emptyIndex(), "p", "p", "MainActivity");

		// SootMethod is hard to instantiate without a Soot Scene; passing
		// null is safe here because the index is empty (contains(null)
		// returns false). The keys + types are the load-bearing contract.
		Map<String, Object> ann = enricher.enrichMethod(null);
		assertEquals(3, ann.size());
		assertEquals(Boolean.FALSE, ann.get("reachable"));
		assertEquals(Boolean.FALSE, ann.get("reachesTarget"));
		assertEquals(Boolean.FALSE, ann.get("directlyReachesTarget"));
	}

	@Test
	public void enrichWidgetReturnsEmptyMap() {
		ReachabilityEnricher enricher = new ReachabilityEnricher(
				emptyIndex(), "p", "p", "MainActivity");
		Map<String, Object> out = enricher.enrichWidget(Collections.emptyMap());
		assertNotNull(out);
		assertTrue("Widget annotations are a C3 placeholder — empty in C1d", out.isEmpty());
	}

	@Test
	public void enrichTransitionReturnsEmptyMap() {
		ReachabilityEnricher enricher = new ReachabilityEnricher(
				emptyIndex(), "p", "p", "MainActivity");
		assertTrue(enricher.enrichTransition(new Object()).isEmpty());
	}

	@Test
	public void enrichComponentReturnsEmptyMap() {
		ReachabilityEnricher enricher = new ReachabilityEnricher(
				emptyIndex(), "p", "p", "MainActivity");
		assertTrue(enricher.enrichComponent(null).isEmpty());
	}

	@Test
	public void topLevelMetadataReturnsExactlyThreeKeys() {
		ReachabilityEnricher enricher = new ReachabilityEnricher(
				emptyIndex(), "com.app.manifest", "com.app.code", "com.app.MainActivity");
		Map<String, Object> md = enricher.topLevelMetadata();
		assertEquals(new LinkedHashSet<>(Arrays.asList(
						"manifestPackage", "codePackage", "mainActivity")),
				md.keySet());
		assertEquals("com.app.manifest", md.get("manifestPackage"));
		assertEquals("com.app.code", md.get("codePackage"));
		assertEquals("com.app.MainActivity", md.get("mainActivity"));
	}

	@Test
	public void nullMetadataCoercesToEmptyString() {
		ReachabilityEnricher enricher = new ReachabilityEnricher(
				emptyIndex(), null, null, null);
		Map<String, Object> md = enricher.topLevelMetadata();
		assertEquals("", md.get("manifestPackage"));
		assertEquals("", md.get("codePackage"));
		assertEquals("", md.get("mainActivity"));
	}

	@Test
	public void enrichMethodIsIdempotent() {
		ReachabilityEnricher enricher = new ReachabilityEnricher(
				emptyIndex(), "p", "p", "MainActivity");
		Map<String, Object> first = enricher.enrichMethod(null);
		Map<String, Object> second = enricher.enrichMethod(null);
		assertEquals("Same input → same output", first, second);
		// Distinct Map instances (no internal cache leaking shared state)
		first.put("reachable", "MUTATED");
		assertEquals(Boolean.FALSE, second.get("reachable"));
	}

	@Test
	public void targetSignaturesDelegateToIndex() {
		Set<String> none = Collections.emptySet();
		ReachabilityIndex idx = new ReachabilityIndex(
				Collections.emptySet(),
				Collections.emptySet(),
				Collections.emptySet());
		ReachabilityEnricher enricher = new ReachabilityEnricher(idx, "p", "p", "M");
		assertEquals(none, enricher.targetSignatures());
		assertEquals(none, enricher.directTargetSignatures());

		// Signature-set identity preserved across calls (no recomputation,
		// no allocation in the hot path of the writer's per-section walk).
		assertSame(enricher.targetSignatures(), enricher.targetSignatures());
		assertSame(enricher.directTargetSignatures(), enricher.directTargetSignatures());
	}

	@Test
	public void indexAccessorReturnsConstructedIndex() {
		ReachabilityIndex idx = emptyIndex();
		ReachabilityEnricher enricher = new ReachabilityEnricher(idx, "p", "p", "M");
		assertSame(idx, enricher.index());
	}
}
