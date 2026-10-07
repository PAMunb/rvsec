package presto.android.gui.clients.reach;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.function.Function;

import org.junit.Test;

/**
 * {@link TargetDistances} on synthetic call graphs with string vertices: the vertex is its own
 * signature, app methods are listed explicitly and every other vertex is a library method.
 */
public class TargetDistancesTest {

	private final Map<String, Set<String>> callers = new HashMap<>();
	private final Set<String> app = new HashSet<>();

	/** Adds the call edge {@code src -> tgt}. */
	private void call(String src, String tgt) {
		callers.computeIfAbsent(tgt, k -> new HashSet<>()).add(src);
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

	@Test
	public void aHandlerTwoCallsAwayFromADirectCaller() {
		app("A.onClick", "A.save", "Crypto.encrypt");
		call("A.onClick", "A.save");
		call("A.save", "Crypto.encrypt");
		call("Crypto.encrypt", "Cipher.doFinal");

		TargetDistances<String> d = compute(set("Crypto.encrypt"), set("Cipher.doFinal"));

		assertEquals(Collections.singletonList("Crypto.encrypt"), d.targets());
		assertEquals(Collections.singletonList(TargetDistances.KIND_DIRECT), d.kinds());
		assertArrayEquals(new int[][] { { 0, 2 } }, d.pairs("A.onClick"));
		assertArrayEquals(new int[][] { { 0, 1 } }, d.pairs("A.save"));
		assertArrayEquals("a direct caller is at distance 0 from itself",
				new int[][] { { 0, 0 } }, d.pairs("Crypto.encrypt"));
		assertEquals("library methods carry no pair", 0, d.pairs("Cipher.doFinal").length);
	}

	@Test
	public void distanceStopsAtTheCap() {
		// m11 -> m10 -> ... -> m0, m0 the direct caller: m10 is 10 calls away, m11 is 11.
		for (int i = 0; i <= 11; i++) {
			app("m" + i);
		}
		for (int i = 11; i > 0; i--) {
			call("m" + i, "m" + (i - 1));
		}
		call("m0", "T.target");

		TargetDistances<String> d = compute(set("m0"), set("T.target"));

		assertArrayEquals(new int[][] { { 0, TargetDistances.DIST_MAX } }, d.pairs("m10"));
		assertEquals("11 calls away is beyond the cap", 0, d.pairs("m11").length);
		assertEquals(11, d.methodsWithPairs());
	}

	@Test
	public void libraryDirectCallersDoNotSeedTheDistance() {
		// Net.connect -> OkHttp.newCall -> Cipher.doFinal: the only direct caller is a library
		// method, so the app method is a boundary target, not a direct one.
		app("Net.connect", "Ui.onClick");
		call("Ui.onClick", "Net.connect");
		call("Net.connect", "OkHttp.newCall");
		call("OkHttp.newCall", "Cipher.doFinal");

		TargetDistances<String> d = compute(set("OkHttp.newCall"), set("Cipher.doFinal"));

		assertEquals(Collections.singletonList("Net.connect"), d.targets());
		assertEquals(Collections.singletonList(TargetDistances.KIND_BOUNDARY), d.kinds());
		assertArrayEquals(new int[][] { { 0, 1 } }, d.pairs("Ui.onClick"));
		assertArrayEquals(new int[][] { { 0, 0 } }, d.pairs("Net.connect"));
	}

	@Test
	public void anEdgeToATargetMakesADirectCallerNotABoundaryOne() {
		// P calls the target and also a library method that reaches it: P is listed once, as
		// direct. Q reaches the target only through a library path that passes through app
		// code (Lib.callback -> App.cb -> target), so Q is not a boundary target.
		app("P.run", "Q.run", "App.cb");
		call("P.run", "Cipher.init");
		call("P.run", "Lib.wrap");
		call("Lib.wrap", "Cipher.init");
		call("Q.run", "Lib.callback");
		call("Lib.callback", "App.cb");
		call("App.cb", "Cipher.init");

		TargetDistances<String> d = compute(set("P.run", "App.cb"), set("Cipher.init"));

		assertEquals(Arrays.asList("App.cb", "P.run"), d.targets());
		assertEquals(Arrays.asList(TargetDistances.KIND_DIRECT, TargetDistances.KIND_DIRECT),
				d.kinds());
		assertArrayEquals("the search walks library methods",
				new int[][] { { 0, 2 } }, d.pairs("Q.run"));
	}

	@Test
	public void targetsAreDirectSortedThenBoundarySorted() {
		app("Z.direct", "A.direct", "Y.boundary", "B.boundary", "H.handler");
		call("Z.direct", "T.t");
		call("A.direct", "T.t");
		call("Y.boundary", "Lib.l");
		call("B.boundary", "Lib.l");
		call("Lib.l", "T.t");
		call("H.handler", "Z.direct");
		call("H.handler", "B.boundary");
		call("H.handler", "A.direct");

		TargetDistances<String> d = compute(set("Z.direct", "A.direct", "Lib.l"), set("T.t"));

		assertEquals(Arrays.asList("A.direct", "Z.direct", "B.boundary", "Y.boundary"),
				d.targets());
		assertEquals(Arrays.asList(TargetDistances.KIND_DIRECT, TargetDistances.KIND_DIRECT,
				TargetDistances.KIND_BOUNDARY, TargetDistances.KIND_BOUNDARY), d.kinds());
		assertArrayEquals("pairs sorted by target index",
				new int[][] { { 0, 1 }, { 1, 1 }, { 2, 1 } }, d.pairs("H.handler"));
	}

	@Test
	public void noTargetsMeansNoPairs() {
		app("A.a", "A.b");
		call("A.a", "A.b");

		TargetDistances<String> d = compute(set(), set("T.t"));

		assertEquals(0, d.targets().size());
		assertEquals(0, d.methodsWithPairs());
		assertEquals(0, d.pairs("A.a").length);
	}
}
