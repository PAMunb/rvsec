package presto.android.gui.clients;

import static org.junit.Assert.*;

import java.io.InputStreamReader;
import java.util.Set;
import java.util.TreeSet;

import org.junit.Assume;
import org.junit.BeforeClass;
import org.junit.Test;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

/**
 * Integration test: compare RvsecAnalysisClient output against the
 * 3-tool baseline (saved in test resources).
 *
 * Baseline was captured from cryptoapp.apk analysis and contains
 * exact counts for windows, transitions, methods, and directlyReachesTarget.
 * Reachable and reachesTarget use ±10% tolerance (BFS vs old all-reachable).
 *
 * Run with: mvn verify -DskipTests=false -DskipITs=false
 */
public class BaselineComparisonIT {

	private static JsonObject result;
	private static JsonObject baseline;

	// Baseline metrics extracted from analysis result
	private static int totalMethods;
	private static int reachable;
	private static int reachesTarget;
	private static int directlyReachesTarget;
	private static int windowCount;
	private static int transitionCount;
	private static int classCount;

	@BeforeClass
	public static void setUp() throws Exception {
		String rvsecHome = System.getenv("RVSEC_HOME");
		Assume.assumeTrue("RVSEC_HOME must be set", rvsecHome != null && !rvsecHome.isEmpty());

		// Load baseline
		try (InputStreamReader reader = new InputStreamReader(
				BaselineComparisonIT.class.getClassLoader()
						.getResourceAsStream("baseline/cryptoapp_baseline.json"))) {
			baseline = JsonParser.parseReader(reader).getAsJsonObject();
		}
		assertNotNull("Baseline must be loadable", baseline);

		// Run analysis (reuses cached result from GatorTestHelper)
		result = GatorTestHelper.getAnalysisResult();
		assertNotNull("Analysis result must not be null", result);

		// Extract counts
		JsonArray reachabilityArray = result.getAsJsonArray("reachability");
		classCount = reachabilityArray.size();
		totalMethods = 0;
		reachable = 0;
		reachesTarget = 0;
		directlyReachesTarget = 0;

		for (JsonElement classElem : reachabilityArray) {
			JsonArray methods = classElem.getAsJsonObject().getAsJsonArray("methods");
			totalMethods += methods.size();
			for (JsonElement methodElem : methods) {
				JsonObject method = methodElem.getAsJsonObject();
				if (method.get("reachable").getAsBoolean()) reachable++;
				if (method.get("reachesTarget").getAsBoolean()) reachesTarget++;
				if (method.get("directlyReachesTarget").getAsBoolean()) directlyReachesTarget++;
			}
		}

		windowCount = result.getAsJsonArray("windows").size();
		transitionCount = result.getAsJsonArray("transitions").size();

		System.out.println("[BaselineComparisonIT] Analysis counts:");
		System.out.println("  classes=" + classCount
				+ " methods=" + totalMethods
				+ " reachable=" + reachable
				+ " reachesTarget=" + reachesTarget
				+ " directlyReachesTarget=" + directlyReachesTarget
				+ " windows=" + windowCount
				+ " transitions=" + transitionCount);
	}

	// -----------------------------------------------------------------
	// Exact matches
	// -----------------------------------------------------------------

	@Test
	public void testPackageMatch() {
		assertEquals(baseline.get("package").getAsString(),
				result.get("package").getAsString());
	}

	@Test
	public void testMainActivityMatch() {
		assertEquals(baseline.get("mainActivity").getAsString(),
				result.get("mainActivity").getAsString());
	}

	@Test
	public void testClassCountExact() {
		int expected = baseline.get("classes").getAsInt();
		assertEquals("Class count must match baseline exactly", expected, classCount);
	}

	@Test
	public void testMethodCountExact() {
		int expected = baseline.get("total_methods").getAsInt();
		assertEquals("Method count must match baseline exactly", expected, totalMethods);
	}

	@Test
	public void testDirectlyReachesMopExact() {
		int expected = baseline.get("directly_reaches_target").getAsInt();
		assertEquals("directlyReachesTarget count must match baseline exactly",
				expected, directlyReachesTarget);
	}

	@Test
	public void testWindowCountExact() {
		int expected = baseline.get("windows").getAsInt();
		assertEquals("Window count must match baseline exactly", expected, windowCount);
	}

	@Test
	public void testTransitionCountExact() {
		int expected = baseline.get("transitions").getAsInt();
		assertEquals("Transition count must match baseline exactly", expected, transitionCount);
	}

	/**
	 * Edge-set diff-zero gate for the gh66 buildFlowThroughContainer optimization
	 * (INV-ANA-39): the produced {@code transitions[]} must be the *same set of edges*,
	 * not merely the same count. A count-only check (testTransitionCountExact) would pass
	 * even if the optimization dropped one edge and added another.
	 *
	 * Each edge is keyed on STABLE identifiers — GATOR's numeric node IDs are not stable
	 * across builds, so source/target window IDs are resolved to their window {@code name}
	 * via {@code windows[]}, and widget identity comes from each event's inline
	 * {@code widgetName}/{@code widgetClass}. The key is the same 6-field tuple the corpus
	 * comparator (scripts/wtg_edge_diff.py) uses: (source window name, target window name,
	 * event type, widget name, widget class, handler).
	 *
	 * Baseline capture (one-time): the pre-change JAR has no {@code transition_edges} in
	 * the baseline resource, so on the FIRST run (against the pre-change JAR) this test
	 * PRINTS the computed edge set and skips. Paste that array into
	 * {@code cryptoapp_baseline.json} as {@code "transition_edges": [...]}; subsequent runs
	 * (against the gh66 JAR) then assert set equality.
	 */
	@Test
	public void testTransitionEdgeSetExact() {
		Set<String> actualEdges = extractTransitionEdges(result);

		if (!baseline.has("transition_edges")) {
			System.out.println("[BaselineComparisonIT] No 'transition_edges' baseline yet. "
					+ "Capture from the PRE-change JAR by pasting the following into "
					+ "cryptoapp_baseline.json as \"transition_edges\":");
			System.out.println("[BaselineComparisonIT] BEGIN transition_edges");
			for (String e : actualEdges) {
				System.out.println("    " + gsonQuote(e) + ",");
			}
			System.out.println("[BaselineComparisonIT] END transition_edges (" + actualEdges.size() + " edges)");
			Assume.assumeTrue("Baseline lacks 'transition_edges' — capture it from the pre-change JAR (see test output)",
					false);
			return;
		}

		Set<String> expectedEdges = new TreeSet<>();
		for (JsonElement e : baseline.getAsJsonArray("transition_edges")) {
			expectedEdges.add(e.getAsString());
		}

		Set<String> added = new TreeSet<>(actualEdges);
		added.removeAll(expectedEdges);
		Set<String> removed = new TreeSet<>(expectedEdges);
		removed.removeAll(actualEdges);

		assertTrue("transitions[] edge set diverged from baseline (INV-ANA-39): "
				+ added.size() + " added, " + removed.size() + " removed.\n"
				+ "  added:   " + added + "\n"
				+ "  removed: " + removed,
				added.isEmpty() && removed.isEmpty());
	}

	/**
	 * Build the stable edge-key set of {@code json}'s {@code transitions[]}. Mirrors
	 * scripts/wtg_edge_diff.py: window IDs → names via {@code windows[]}, widget identity
	 * from inline event fields, set semantics (duplicate-keyed events collapse).
	 */
	private static Set<String> extractTransitionEdges(JsonObject json) {
		java.util.Map<Long, String> winName = new java.util.HashMap<>();
		JsonArray windows = json.getAsJsonArray("windows");
		if (windows != null) {
			for (JsonElement we : windows) {
				JsonObject w = we.getAsJsonObject();
				if (w.has("id")) {
					winName.put(w.get("id").getAsLong(),
							w.has("name") && !w.get("name").isJsonNull() ? w.get("name").getAsString() : "");
				}
			}
		}

		Set<String> edges = new TreeSet<>();
		JsonArray transitions = json.getAsJsonArray("transitions");
		if (transitions == null) {
			return edges;
		}
		// SOH (U+0001) field separator: it cannot occur in window/class names, event
		// types, or handler signatures, so the six key fields join unambiguously.
		final String SEP = "";
		for (JsonElement te : transitions) {
			JsonObject tr = te.getAsJsonObject();
			if (!tr.has("sourceId") || !tr.has("targetId")) {
				continue;
			}
			String src = nameOf(winName, tr.get("sourceId").getAsLong());
			String tgt = nameOf(winName, tr.get("targetId").getAsLong());
			JsonArray events = tr.has("events") && !tr.get("events").isJsonNull()
					? tr.getAsJsonArray("events") : null;
			if (events == null || events.size() == 0) {
				edges.add(src + SEP + tgt + SEP + SEP + SEP + SEP);
				continue;
			}
			for (JsonElement ee : events) {
				JsonObject ev = ee.getAsJsonObject();
				edges.add(src + SEP + tgt + SEP
						+ str(ev, "type") + SEP
						+ str(ev, "widgetName") + SEP
						+ str(ev, "widgetClass") + SEP
						+ str(ev, "handler"));
			}
		}
		return edges;
	}

	private static String nameOf(java.util.Map<Long, String> winName, long id) {
		return winName.containsKey(id) ? winName.get(id) : "<unresolved:" + id + ">";
	}

	private static String str(JsonObject o, String key) {
		return o.has(key) && !o.get(key).isJsonNull() ? o.get(key).getAsString() : "";
	}

	private static String gsonQuote(String s) {
		return new com.google.gson.JsonPrimitive(s).toString();
	}

	// -----------------------------------------------------------------
	// ±10% tolerance (BFS vs old all-reachable may differ slightly)
	// -----------------------------------------------------------------

	@Test
	public void testReachableWithinTolerance() {
		int expected = baseline.get("reachable").getAsInt();
		double tolerance = expected * 0.10;
		assertTrue(
				String.format("Reachable count %d outside ±10%% of baseline %d (range: %.0f-%.0f)",
						reachable, expected, expected - tolerance, expected + tolerance),
				Math.abs(reachable - expected) <= tolerance);
	}

	@Test
	public void testReachesMopWithinTolerance() {
		int expected = baseline.get("reaches_target").getAsInt();
		double tolerance = expected * 0.10;
		assertTrue(
				String.format("ReachesMop count %d outside ±10%% of baseline %d (range: %.0f-%.0f)",
						reachesTarget, expected, expected - tolerance, expected + tolerance),
				Math.abs(reachesTarget - expected) <= tolerance);
	}

	// -----------------------------------------------------------------
	// Summary
	// -----------------------------------------------------------------

	@Test
	public void testPrintSummary() {
		System.out.println("[BaselineComparisonIT] COMPARISON SUMMARY:");
		System.out.println(String.format("  %-25s %-10s %-10s %-10s",
				"Metric", "Baseline", "Actual", "Status"));
		System.out.println(String.format("  %-25s %-10s %-10s",
				"-------------------------", "----------", "----------"));

		printRow("classes", baseline.get("classes").getAsInt(), classCount, true);
		printRow("total_methods", baseline.get("total_methods").getAsInt(), totalMethods, true);
		printRow("reachable (±10%)", baseline.get("reachable").getAsInt(), reachable, false);
		printRow("reaches_target (±10%)", baseline.get("reaches_target").getAsInt(), reachesTarget, false);
		printRow("directly_reaches_target", baseline.get("directly_reaches_target").getAsInt(),
				directlyReachesTarget, true);
		printRow("windows", baseline.get("windows").getAsInt(), windowCount, true);
		printRow("transitions", baseline.get("transitions").getAsInt(), transitionCount, true);
	}

	private void printRow(String metric, int expected, int actual, boolean exact) {
		String status;
		if (exact) {
			status = (expected == actual) ? "PASS" : "FAIL (exact)";
		} else {
			double tolerance = expected * 0.10;
			status = (Math.abs(actual - expected) <= tolerance) ? "PASS" : "FAIL (±10%)";
		}
		System.out.println(String.format("  %-25s %-10d %-10d %-10s", metric, expected, actual, status));
	}
}
