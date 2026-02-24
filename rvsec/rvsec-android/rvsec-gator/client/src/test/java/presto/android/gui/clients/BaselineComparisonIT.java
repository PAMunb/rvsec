package presto.android.gui.clients;

import static org.junit.Assert.*;

import java.io.InputStreamReader;

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
 * exact counts for windows, transitions, methods, and directlyReachesMop.
 * Reachable and reachesMop use ±10% tolerance (BFS vs old all-reachable).
 *
 * Run with: mvn verify -DskipTests=false -DskipITs=false
 */
public class BaselineComparisonIT {

	private static JsonObject result;
	private static JsonObject baseline;

	// Baseline metrics extracted from analysis result
	private static int totalMethods;
	private static int reachable;
	private static int reachesMop;
	private static int directlyReachesMop;
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
		reachesMop = 0;
		directlyReachesMop = 0;

		for (JsonElement classElem : reachabilityArray) {
			JsonArray methods = classElem.getAsJsonObject().getAsJsonArray("methods");
			totalMethods += methods.size();
			for (JsonElement methodElem : methods) {
				JsonObject method = methodElem.getAsJsonObject();
				if (method.get("reachable").getAsBoolean()) reachable++;
				if (method.get("reachesMop").getAsBoolean()) reachesMop++;
				if (method.get("directlyReachesMop").getAsBoolean()) directlyReachesMop++;
			}
		}

		windowCount = result.getAsJsonArray("windows").size();
		transitionCount = result.getAsJsonArray("transitions").size();

		System.out.println("[BaselineComparisonIT] Analysis counts:");
		System.out.println("  classes=" + classCount
				+ " methods=" + totalMethods
				+ " reachable=" + reachable
				+ " reachesMop=" + reachesMop
				+ " directlyReachesMop=" + directlyReachesMop
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
		int expected = baseline.get("directly_reaches_mop").getAsInt();
		assertEquals("directlyReachesMop count must match baseline exactly",
				expected, directlyReachesMop);
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
		int expected = baseline.get("reaches_mop").getAsInt();
		double tolerance = expected * 0.10;
		assertTrue(
				String.format("ReachesMop count %d outside ±10%% of baseline %d (range: %.0f-%.0f)",
						reachesMop, expected, expected - tolerance, expected + tolerance),
				Math.abs(reachesMop - expected) <= tolerance);
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
		printRow("reaches_mop (±10%)", baseline.get("reaches_mop").getAsInt(), reachesMop, false);
		printRow("directly_reaches_mop", baseline.get("directly_reaches_mop").getAsInt(),
				directlyReachesMop, true);
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
