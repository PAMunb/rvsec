package presto.android.gui.clients.reach;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.function.BiPredicate;
import java.util.function.Function;

import org.junit.Test;

/**
 * {@link TargetDistances#paths} on synthetic call graphs with string vertices: the vertex is its
 * own signature, app methods are listed explicitly and every other vertex is a library method.
 * Callers are held in insertion-ordered sets, so a search that did not sort them would follow
 * the order in which the fixture added the edges.
 */
public class TargetDistancesPathsTest {

	private static final BiPredicate<String, int[]> EVERY_PAIR = (m, pair) -> true;

	private final Map<String, Set<String>> callers = new HashMap<>();
	private final Set<String> app = new HashSet<>();

	/** Adds the call edge {@code src -> tgt}. */
	private void call(String src, String tgt) {
		callers.computeIfAbsent(tgt, k -> new LinkedHashSet<>()).add(src);
	}

	private void app(String... methods) {
		app.addAll(Arrays.asList(methods));
	}

	private static Set<String> set(String... values) {
		return new HashSet<>(Arrays.asList(values));
	}

	private TargetDistances<String> compute(Set<String> direct, Set<String> targets) {
		return TargetDistances.compute(callers, app, direct, targets, Function.identity());
	}

	/** Step {@code [i, v, n]} with the method indices resolved to signatures. */
	private static String step(int i, String v, String n) {
		return i + ": " + v + " -> " + n;
	}

	private static Set<String> steps(DistancePaths p) {
		Set<String> out = new HashSet<>();
		for (int[] s : p.steps()) {
			out.add(step(s[0], p.methods().get(s[1]), p.methods().get(s[2])));
		}
		return out;
	}

	/**
	 * The chain of the pair {@code [i, d]} on {@code m}, from {@code m} to the target: the
	 * {@code d + 1} methods reached by following the steps. Fails when a step is missing.
	 */
	private static List<String> chain(DistancePaths p, int i, String m, int d) {
		Map<String, String> next = new HashMap<>();
		for (int[] s : p.steps()) {
			if (s[0] == i) {
				next.put(p.methods().get(s[1]), p.methods().get(s[2]));
			}
		}
		List<String> out = new ArrayList<>();
		out.add(m);
		String v = m;
		for (int k = 0; k < d; k++) {
			v = next.get(v);
			assertNotNull("chain of [" + i + ", " + d + "] on " + m + " breaks after " + out, v);
			out.add(v);
		}
		return out;
	}

	/**
	 * INV-ANA-91 and -93 for one run: every written pair's chain is complete, has {@code d}
	 * steps over call-graph edges and ends at its target, and every step lies on such a chain.
	 * Also checks the shape of the output: sorted method table, steps sorted by {@code (i, v)},
	 * one step per {@code (i, v)}.
	 */
	private void assertChainsOfWrittenPairs(TargetDistances<String> d, DistancePaths p,
			BiPredicate<String, int[]> written) {
		List<String> sortedMethods = new ArrayList<>(p.methods());
		Collections.sort(sortedMethods);
		assertEquals("pathMethods sorted by signature", sortedMethods, p.methods());
		for (int k = 1; k < p.steps().length; k++) {
			int[] a = p.steps()[k - 1];
			int[] b = p.steps()[k];
			assertTrue("steps sorted by (i, v), one per (i, v)",
					a[0] < b[0] || (a[0] == b[0] && a[1] < b[1]));
		}

		Set<String> onChains = new HashSet<>();
		for (String m : app) {
			for (int[] pair : d.pairs(m)) {
				if (!written.test(m, pair)) {
					continue;
				}
				List<String> c = chain(p, pair[0], m, pair[1]);
				assertEquals(d.targets().get(pair[0]), c.get(c.size() - 1));
				for (int k = 0; k < pair[1]; k++) {
					String v = c.get(k);
					String n = c.get(k + 1);
					assertTrue(v + " -> " + n + " is a call-graph edge",
							callers.getOrDefault(n, Collections.emptySet()).contains(v));
					onChains.add(step(pair[0], v, n));
				}
			}
		}
		assertEquals("every step lies on a written pair's chain", onChains, steps(p));
	}

	@Test
	public void theChainOfAHandlerTwoCallsFromADirectCaller() {
		app("A.onClick", "A.save", "Crypto.encrypt");
		call("A.onClick", "A.save");
		call("A.save", "Crypto.encrypt");
		call("Crypto.encrypt", "Cipher.doFinal");
		TargetDistances<String> d = compute(set("Crypto.encrypt"), set("Cipher.doFinal"));

		DistancePaths p = d.paths(EVERY_PAIR);

		assertArrayEquals(new int[][] { { 0, 2 } }, d.pairs("A.onClick"));
		assertEquals(Arrays.asList("A.onClick", "A.save", "Crypto.encrypt"), p.methods());
		assertArrayEquals(new int[][] { { 0, 0, 1 }, { 0, 1, 2 } }, p.steps());
		assertChainsOfWrittenPairs(d, p, EVERY_PAIR);
	}

	@Test
	public void aChainPassesThroughALibraryMethod() {
		app("UI.onClick", "Repo.save");
		call("UI.onClick", "kotlinx.coroutines.BuildersKt.launch");
		call("kotlinx.coroutines.BuildersKt.launch", "Repo.save");
		call("Repo.save", "Cipher.doFinal");
		TargetDistances<String> d = compute(set("Repo.save"), set("Cipher.doFinal"));

		DistancePaths p = d.paths(EVERY_PAIR);

		assertArrayEquals(new int[][] { { 0, 2 } }, d.pairs("UI.onClick"));
		assertTrue(p.methods().contains("kotlinx.coroutines.BuildersKt.launch"));
		assertEquals(Arrays.asList("UI.onClick", "kotlinx.coroutines.BuildersKt.launch",
				"Repo.save"), chain(p, 0, "UI.onClick", 2));
		assertChainsOfWrittenPairs(d, p, EVERY_PAIR);
	}

	@Test
	public void equallyShortPathsAreChosenBySignatureOnEveryRun() {
		// M reaches T through any of X00..X19, each at distance 2. The step from M goes to
		// X00, the first by signature, whatever order the edges were added in.
		List<String[]> edges = new ArrayList<>();
		for (int k = 0; k < 20; k++) {
			String x = String.format("X%02d.run", k);
			app(x);
			edges.add(new String[] { "M.run", x });
			edges.add(new String[] { x, "T.run" });
		}
		edges.add(new String[] { "T.run", "Cipher.init" });
		app("M.run", "T.run");

		Set<String> first = null;
		for (int run = 0; run < 10; run++) {
			callers.clear();
			List<String[]> shuffled = new ArrayList<>(edges);
			Collections.shuffle(shuffled, new Random(run));
			for (String[] e : shuffled) {
				call(e[0], e[1]);
			}
			TargetDistances<String> d = compute(set("T.run"), set("Cipher.init"));

			DistancePaths p = d.paths(EVERY_PAIR);

			Set<String> s = steps(p);
			assertTrue(s.contains(step(0, "M.run", "X00.run")));
			for (int k = 1; k < 20; k++) {
				assertFalse(s.contains(step(0, "M.run", String.format("X%02d.run", k))));
			}
			if (first == null) {
				first = s;
			}
			assertEquals("run " + run + " writes the steps of the first run", first, s);
		}
	}

	@Test
	public void compactKeepsTheStepsOfTheKeptPairsOnly() {
		// M is 1, 2, 3 and 6 calls from T1..T4. Compact output drops the pair at 6, and with it
		// the step from M towards T4; C1..C5 keep their own pairs for T4, so their steps stay.
		app("M.run", "T1.run", "T2.run", "T3.run", "T4.run", "A.run", "B1.run", "B2.run",
				"C1.run", "C2.run", "C3.run", "C4.run", "C5.run");
		call("M.run", "T1.run");
		call("M.run", "A.run");
		call("A.run", "T2.run");
		call("M.run", "B1.run");
		call("B1.run", "B2.run");
		call("B2.run", "T3.run");
		call("M.run", "C1.run");
		call("C1.run", "C2.run");
		call("C2.run", "C3.run");
		call("C3.run", "C4.run");
		call("C4.run", "C5.run");
		call("C5.run", "T4.run");
		for (String t : Arrays.asList("T1.run", "T2.run", "T3.run", "T4.run")) {
			call(t, "Cipher.init");
		}
		TargetDistances<String> d = compute(set("T1.run", "T2.run", "T3.run", "T4.run"),
				set("Cipher.init"));
		assertArrayEquals(new int[][] { { 0, 1 }, { 1, 2 }, { 2, 3 }, { 3, 6 } },
				d.pairs("M.run"));

		BiPredicate<String, int[]> compact = d.keptByCompact();
		DistancePaths p = d.paths(compact);

		Set<String> s = steps(p);
		assertFalse("the step lies only on the dropped pair's chain",
				s.contains(step(3, "M.run", "C1.run")));
		assertTrue(s.contains(step(3, "C1.run", "C2.run")));
		assertChainsOfWrittenPairs(d, p, compact);

		DistancePaths full = d.paths(EVERY_PAIR);
		assertTrue(steps(full).contains(step(3, "M.run", "C1.run")));
		assertChainsOfWrittenPairs(d, full, EVERY_PAIR);
	}

	@Test
	public void keptByCompactAgreesWithCompact() {
		app("M.run", "N.run", "T1.run", "T2.run", "T3.run", "T4.run", "C1.run", "C2.run",
				"C3.run", "C4.run", "C5.run");
		call("N.run", "M.run");
		call("M.run", "T1.run");
		call("M.run", "T2.run");
		call("M.run", "T3.run");
		call("M.run", "C1.run");
		call("C1.run", "C2.run");
		call("C2.run", "C3.run");
		call("C3.run", "C4.run");
		call("C4.run", "T4.run");
		TargetDistances<String> d = compute(set("T1.run", "T2.run", "T3.run", "T4.run"),
				set("Cipher.init"));

		BiPredicate<String, int[]> kept = d.keptByCompact();
		for (String m : Arrays.asList("M.run", "N.run", "M.run", "C1.run")) {
			Set<Integer> expected = new HashSet<>();
			for (int[] pair : TargetDistances.compact(d.pairs(m))) {
				expected.add(pair[0]);
			}
			for (int[] pair : d.pairs(m)) {
				assertEquals(m + " " + Arrays.toString(pair), expected.contains(pair[0]),
						kept.test(m, pair));
			}
		}
	}

	@Test
	public void aPairAtDistanceZeroHasNoStep() {
		app("T.run");
		call("T.run", "Cipher.init");
		TargetDistances<String> d = compute(set("T.run"), set("Cipher.init"));

		DistancePaths p = d.paths(EVERY_PAIR);

		assertArrayEquals(new int[][] { { 0, 0 } }, d.pairs("T.run"));
		assertEquals(0, p.methods().size());
		assertEquals(0, p.steps().length);
	}

	@Test
	public void everyStepLiesOnAWrittenChain() {
		// Two targets sharing tails, a branch, a library hop and a boundary target.
		app("H.onClick", "H.onLong", "S.save", "S.load", "Crypto.enc", "Net.connect", "U.util");
		call("H.onClick", "S.save");
		call("H.onClick", "U.util");
		call("H.onLong", "S.load");
		call("S.save", "Crypto.enc");
		call("S.load", "Lib.wrap");
		call("Lib.wrap", "Crypto.enc");
		call("U.util", "Net.connect");
		call("S.load", "Net.connect");
		call("Crypto.enc", "Cipher.doFinal");
		call("Net.connect", "OkHttp.newCall");
		call("OkHttp.newCall", "Cipher.doFinal");
		TargetDistances<String> d = compute(set("Crypto.enc", "OkHttp.newCall"),
				set("Cipher.doFinal"));
		assertEquals(Arrays.asList("Crypto.enc", "Net.connect"), d.targets());

		DistancePaths full = d.paths(EVERY_PAIR);
		assertChainsOfWrittenPairs(d, full, EVERY_PAIR);
		BiPredicate<String, int[]> compact = d.keptByCompact();
		assertChainsOfWrittenPairs(d, d.paths(compact), compact);

		DistancePaths none = d.paths((m, pair) -> false);
		assertEquals(0, none.steps().length);
		assertEquals("no written pair, no method", 0, none.methods().size());
	}

	@Test
	public void releasingTheCallersKeepsThePairsAndRefusesThePathPass() {
		app("A.a");
		call("A.a", "Cipher.getInstance");
		TargetDistances<String> d = compute(set("A.a"), set("Cipher.getInstance"));
		d.releaseCallers();

		assertArrayEquals(new int[][] { { 0, 0 } }, d.pairs("A.a"));
		try {
			d.paths(EVERY_PAIR);
			fail("paths ran without the callers map");
		} catch (IllegalStateException expected) {
			// the client computes the paths before it releases the map
		}
	}
}
