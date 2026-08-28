package presto.android.gui.clients;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.junit.Assume;
import org.junit.BeforeClass;
import org.junit.Test;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;

/**
 * The subtype/wildcard matching capability, exercised on a real Soot Scene.
 *
 * <p>The unit tests decide whether the predicate is correct; this decides whether it is
 * <i>reached</i> — whether the flags survive the extractor → source → resolver → scan chain and
 * whether the declared owners actually force-resolve inside the analysis GATOR really runs.
 *
 * <p>Runs GATOR twice on the same APK, once per spec set, and compares. Skipped unless
 * {@code RVSEC_HOME} is set. Note that the ITs are gated by <b>two</b> independent properties:
 * {@code client/pom.xml} sets {@code skipITs}, and failsafe also honours {@code skipTests}, so
 * {@code -DskipITs=false} alone leaves them skipped —
 * {@code mvn verify -DskipTests=false -DskipITs=false}.
 */
public class GenericSubtypeMatchingIT {

	private static JsonObject generic;
	private static JsonObject jca;
	private static String genericLog;

	@BeforeClass
	public static void runBothAnalyses() throws Exception {
		String rvsecHome = System.getenv("RVSEC_HOME");
		Assume.assumeTrue("RVSEC_HOME must be set", rvsecHome != null && !rvsecHome.isEmpty());

		generic = GatorTestHelper.getAnalysisResult(GatorTestHelper.GENERIC_NEW);
		genericLog = GatorTestHelper.getAnalysisLog(GatorTestHelper.GENERIC_NEW);
		jca = GatorTestHelper.getAnalysisResult(GatorTestHelper.JCA);
	}

	// ── 4.3 — targets load and owners resolve on the real scene ───────────────

	@Test
	public void targetsAreLoadedForTheHierarchyDeclaredSpecSet() {
		Matcher m = Pattern.compile("Loaded (\\d+) MOP signatures").matcher(genericLog);
		assertTrue("the MopSpecsTargetSource load line must appear in the GATOR log", m.find());
		int loaded = Integer.parseInt(m.group(1));
		System.out.println("[IT] generic_new MOP signatures loaded: " + loaded);
		assertTrue("generic_new must load a non-empty target set (it loaded 0 before this"
				+ " capability existed)", loaded > 0);
	}

	@Test
	public void everyDeclaredOwnerForceResolvesWithNoDegradation() {
		// A degrade on a generic_new owner blocks the sweep: all 21 are JDK types and must
		// force-resolve non-phantom. This is the hard gate of RISK-001.
		Matcher m = Pattern.compile(
				"\\[TargetMatching\\] Target owners force-resolved: (\\d+) usable, (\\d+) degraded")
				.matcher(genericLog);
		assertTrue("the force-resolve summary must appear in the GATOR log", m.find());
		int usable = Integer.parseInt(m.group(1));
		int degraded = Integer.parseInt(m.group(2));
		System.out.println("[IT] generic_new owners force-resolved: " + usable + " usable, "
				+ degraded + " degraded");

		assertEquals("no declared owner may degrade — every one is a JDK type", 0, degraded);
		assertEquals("all 21 owners carrying targets must resolve", 21, usable);
		assertFalse("no degrade warning may appear at all",
				genericLog.contains("[TargetMatching] WARN"));
	}

	// ── 4.3 — the load-bearing flag is the direct one ─────────────────────────

	@Test
	public void directAxisDiscriminatesWhereTheTransitiveAxisSaturates() {
		Ratio genericRatio = ratios(generic);
		Ratio jcaRatio = ratios(jca);
		System.out.println("[IT] generic_new: " + genericRatio);
		System.out.println("[IT] jca:         " + jcaRatio);

		// reachesTarget is smoke only. Over this fixture the transitive flag saturates (it
		// reaches 84-94% of app methods on corpus APKs against 11-47% under jca), so
		// "> 0" passes trivially and proves nothing. It is asserted because a zero would
		// still be a real failure — not because a non-zero is evidence.
		assertTrue("reachesTarget smoke check", genericRatio.reaches > 0);

		// This is the assertion that carries the change: the direct flag must actually move.
		// The reference point is the jca *sweep* baseline of 0,0-0,3% of app methods, not the
		// jca run on this APK. cryptoapp is a JCA demo: its whole point is calling the jca
		// targets, so jca marks more direct callers here (23/106 = 21,7%) than generic_new does
		// (13/106 = 12,3%) — under spark and under CHA alike. A `generic > jca` assertion would
		// therefore be measuring the fixture's subject matter, not the matcher, and it is not
		// what the capability asks for.
		assertTrue("directlyReachesTarget must be non-empty under generic_new",
				genericRatio.direct > 0);
		double directPct = 100.0 * genericRatio.direct / genericRatio.total;
		assertTrue("the direct axis must clear the jca sweep baseline of 0,0-0,3% by an order of"
				+ " magnitude — that gap is the capability's signal, and the transitive flag"
				+ " cannot show it because it saturates (measured " + directPct + "%)",
				directPct >= 2.0);
	}

	// ── 4.4 — schema invariance ───────────────────────────────────────────────

	@Test
	public void jsonKeySetIsIdenticalAcrossSpecSets() {
		Set<String> genericKeys = new TreeSet<>();
		Set<String> jcaKeys = new TreeSet<>();
		collectKeys(generic, "", genericKeys);
		collectKeys(jca, "", jcaKeys);

		assertEquals("only reachesTarget/directlyReachesTarget VALUES may differ between spec"
				+ " sets; the key set is part of the contract three independent raw-JSON readers"
				+ " depend on", jcaKeys, genericKeys);
	}

	// ── 4.6 — negative: the non-match comes from the name axis ────────────────

	@Test
	public void aSubtypeReceiverWithANonMatchingNameStaysUnmatched() {
		// generic_new declares Object+ owners (wait/notify/notifyAll), so EVERY declaring type
		// is a subtype of some declared owner and a pure "not a subtype" example does not
		// exist. A non-match can only be decided on the method name — which is also why
		// nameMatches runs first.
		int inspected = 0;
		int unmatched = 0;
		for (JsonElement classElem : generic.getAsJsonArray("reachability")) {
			for (JsonElement methodElem : classElem.getAsJsonObject().getAsJsonArray("methods")) {
				JsonObject method = methodElem.getAsJsonObject();
				inspected++;
				if (!method.get("directlyReachesTarget").getAsBoolean()) {
					unmatched++;
				}
			}
		}
		System.out.println("[IT] generic_new: " + unmatched + " of " + inspected
				+ " methods are NOT direct callers");
		assertTrue("if every method matched, the predicate would be answering `true` rather than"
				+ " matching — the name axis must reject something", unmatched > 0);
	}

	// ── 4.7 — the scan-only path really gained the subtype predicate ──────────

	@Test
	public void theBytecodeScanContributesSeedsTheCallGraphDoesNot() {
		// If the CG path covered for the scan, the hybrid scan of the cascade would be
		// untested by anything. This reads the counter line the engine prints.
		Matcher m = Pattern.compile("directlyReachesTarget: (\\d+) \\(CG: (\\d+), bytecode: (\\d+),"
				+ " intersection: (\\d+), bytecode-only seeds: (\\d+)\\)").matcher(genericLog);
		assertTrue("the ReachabilityEngine counter line must appear", m.find());
		int total = Integer.parseInt(m.group(1));
		int bytecode = Integer.parseInt(m.group(3));
		int scanOnly = Integer.parseInt(m.group(5));
		System.out.println("[IT] generic_new direct set: " + total + " total, " + bytecode
				+ " from the bytecode scan, " + scanOnly + " from the scan alone");

		assertTrue("the bytecode scan must find subtype callers — an empty scan would mean the"
				+ " hybrid path never ran", bytecode > 0);
		// The requirement is scan-ONLY, not scan-at-all: a method the scan reaches and the call
		// graph does not. This is the assertion that would have caught a hybrid scan that never
		// contributed anything, and it is only observable on spark — CHA over-approximates
		// enough to absorb every scan hit, which is why GatorTestHelper stopped passing
		// -withCHA (see the comment there).
		assertTrue("the scan must contribute at least one seed the call graph does not have —"
				+ " otherwise the CG path is covering for the hybrid scan and BUG-INV-ANA-19"
				+ " is asserted by nothing", scanOnly > 0);
	}

	// ── INV-ANA-64 — containment on a real run ────────────────────────────────

	@Test
	public void reachesTargetContainsDirectlyReachesTarget() {
		for (JsonObject result : new JsonObject[] { generic, jca }) {
			List<String> violations = new ArrayList<>();
			for (JsonElement classElem : result.getAsJsonArray("reachability")) {
				JsonObject cls = classElem.getAsJsonObject();
				for (JsonElement methodElem : cls.getAsJsonArray("methods")) {
					JsonObject method = methodElem.getAsJsonObject();
					if (method.get("directlyReachesTarget").getAsBoolean()
							&& !method.get("reachesTarget").getAsBoolean()) {
						violations.add(cls.get("className").getAsString() + "."
								+ method.get("name").getAsString());
					}
				}
			}
			assertEquals("a direct caller is a path of length 1, so the containment is"
					+ " definitional: " + violations, 0, violations.size());
		}
	}

	// ── 4.8 — cost bound (NFR04) ──────────────────────────────────────────────

	@Test
	public void everyWidenedStageStaysWithinTwiceTheJcaBaseline() {
		// Three stages, not two. resolveInScene and the bytecode scan are the obvious ones —
		// they lost the exact-key fast path. The reverse BFS is here because it is the stage
		// that grows least visibly: resolveInScene iterates Scene.getClasses(), so a
		// quasi-universal owner hands the BFS every matching library method in the Scene
		// rather than the ~120 JCA ones, and timing only the match points would miss it.
		String jcaLog = jcaLog();
		for (String stage : new String[] { "resolveInScene", "bytecodeScan", "reverseBfs" }) {
			long genericMs = elapsed(genericLog, stage);
			long jcaMs = elapsed(jcaLog, stage);
			System.out.println("[IT] " + stage + ": generic_new=" + genericMs + " ms, jca="
					+ jcaMs + " ms");

			// A sub-second baseline makes a ratio meaningless — 3 ms against 1 ms is a 3x
			// that measures scheduler noise. Guard with an absolute floor before the ratio.
			if (genericMs <= 250) {
				continue;
			}
			assertTrue(stage + " must stay within 2x its jca baseline (generic_new=" + genericMs
					+ " ms, jca=" + jcaMs + " ms). First suspects: the lost equals(fqn)"
					+ " fast-reject, and a superType RefType resolved per invoke instead of"
					+ " cached per target.", genericMs <= 2 * Math.max(jcaMs, 125));
		}
	}

	private static long elapsed(String log, String stage) {
		Matcher m = Pattern.compile(stage + ": (\\d+) ms").matcher(log);
		assertTrue("no timing line for " + stage + " in the GATOR log", m.find());
		return Long.parseLong(m.group(1));
	}

	private static String jcaLog() {
		try {
			return GatorTestHelper.getAnalysisLog(GatorTestHelper.JCA);
		} catch (Exception e) {
			throw new AssertionError("could not read the jca run's log", e);
		}
	}

	private static void collectKeys(JsonElement element, String prefix, Set<String> keys) {
		if (element.isJsonObject()) {
			for (String key : element.getAsJsonObject().keySet()) {
				keys.add(prefix + "." + key);
				collectKeys(element.getAsJsonObject().get(key), prefix + "." + key, keys);
			}
		} else if (element.isJsonArray()) {
			for (JsonElement child : element.getAsJsonArray()) {
				collectKeys(child, prefix + "[]", keys);
			}
		}
	}

	private static Ratio ratios(JsonObject result) {
		int total = 0;
		int reaches = 0;
		int direct = 0;
		for (JsonElement classElem : result.getAsJsonArray("reachability")) {
			for (JsonElement methodElem : classElem.getAsJsonObject().getAsJsonArray("methods")) {
				JsonObject method = methodElem.getAsJsonObject();
				total++;
				if (method.get("reachesTarget").getAsBoolean()) {
					reaches++;
				}
				if (method.get("directlyReachesTarget").getAsBoolean()) {
					direct++;
				}
			}
		}
		return new Ratio(total, reaches, direct);
	}

	private static final class Ratio {
		final int total;
		final int reaches;
		final int direct;

		Ratio(int total, int reaches, int direct) {
			this.total = total;
			this.reaches = reaches;
			this.direct = direct;
		}

		@Override
		public String toString() {
			return String.format("%d methods, reachesTarget=%d (%.1f%%), directlyReachesTarget=%d (%.1f%%)",
					total, reaches, 100.0 * reaches / total, direct, 100.0 * direct / total);
		}
	}
}
