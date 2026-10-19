package presto.android.gui.clients.reach;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

import org.jgrapht.graph.DefaultDirectedGraph;
import org.jgrapht.graph.DefaultEdge;
import org.jgrapht.graph.EdgeReversedGraph;
import org.junit.Test;

import presto.android.gui.clients.RvsecAnalysisClient;

/**
 * The callback set seeds the forward search, and the target flags of callbacks come out of
 * the two target searches alone (design D7).
 *
 * <p>{@link ReachabilityEngine#run} reads the Scene's call graph, so these tests compose the
 * same static steps on a synthetic String graph, in the order the engine runs them: forward
 * search from entry points ∪ callbacks, direct set (call-graph callers ∪ scan), reverse search
 * from targets ∪ direct set. {@link #callbackFlagRule} states the rule a post-search step would
 * need to apply to callbacks — mark reachable; a callback with an edge to a target is direct and
 * reaches; a callback with an edge to a reaching method reaches — and each test asserts that the
 * rule adds nothing to the sets the searches produce.
 */
public class ReachabilityEngineCallbackSeedTest {

	/** The three sets {@link ReachabilityIndex} is built from. */
	private static final class Flags {
		final Set<String> reachable;
		final Set<String> reachesTarget;
		final Set<String> direct;

		Flags(Set<String> reachable, Set<String> reachesTarget, Set<String> direct) {
			this.reachable = reachable;
			this.reachesTarget = reachesTarget;
			this.direct = direct;
		}

		Flags copy() {
			return new Flags(new HashSet<>(reachable), new HashSet<>(reachesTarget),
					new HashSet<>(direct));
		}
	}

	// ------------------------------------------------------------------------------ cases

	@Test
	public void aCallbackWithAnEdgeToATargetIsDirectAndReaches() {
		DefaultDirectedGraph<String, DefaultEdge> g = newGraph();
		addEdge(g, "Home$1.onClick", "T");

		Flags flags = assertRuleAddsNothing(g, setOf(), setOf("Home$1.onClick"), setOf("T"), setOf());
		assertTrue(flags.direct.contains("Home$1.onClick"));
		assertTrue(flags.reachesTarget.contains("Home$1.onClick"));
	}

	@Test
	public void aCallbackTwoCallsAboveATargetReachesAndWhatItCallsIsReachable() {
		// org.cry.otp_31: Home$1.onClick → HOTP.gen → HOTP.generateOTP → HOTP.hmac_sha1 → T.
		DefaultDirectedGraph<String, DefaultEdge> g = newGraph();
		addEdge(g, "Home$1.onClick", "HOTP.gen");
		addEdge(g, "HOTP.gen", "HOTP.generateOTP");
		addEdge(g, "HOTP.generateOTP", "HOTP.hmac_sha1");
		addEdge(g, "HOTP.hmac_sha1", "T");

		Flags flags = assertRuleAddsNothing(g, setOf(), setOf("Home$1.onClick"), setOf("T"), setOf());
		assertTrue(flags.reachable.containsAll(
				setOf("Home$1.onClick", "HOTP.gen", "HOTP.generateOTP", "HOTP.hmac_sha1")));
		assertTrue(flags.reachesTarget.contains("Home$1.onClick"));
		assertEquals(setOf("HOTP.hmac_sha1"), flags.direct);
	}

	@Test
	public void aCallbackAboveAScanOnlyDirectCallerReaches() {
		// "M" calls the target through an invoke SPARK dropped, so only the bytecode scan sees
		// it; the callback reaches the target through M's seed in the reverse search.
		DefaultDirectedGraph<String, DefaultEdge> g = newGraph();
		addEdge(g, "onReceive", "M");

		Flags flags = assertRuleAddsNothing(g, setOf(), setOf("onReceive"), setOf("T"), setOf("M"));
		assertTrue(flags.reachesTarget.contains("onReceive"));
	}

	@Test
	public void aCallbackWithNoPathToATargetCarriesNoTargetFlag() {
		DefaultDirectedGraph<String, DefaultEdge> g = newGraph();
		addEdge(g, "entry", "caller");
		addEdge(g, "caller", "T");
		addEdge(g, "onPause", "save");

		Flags flags = assertRuleAddsNothing(g, setOf("entry"), setOf("onPause"), setOf("T"), setOf());
		assertTrue(flags.reachable.containsAll(setOf("onPause", "save")));
		assertEquals(setOf("entry", "caller", "T"), flags.reachesTarget);
	}

	@Test
	public void aCallbackAbsentFromTheCallGraphIsReachableOnly() {
		DefaultDirectedGraph<String, DefaultEdge> g = newGraph();
		addEdge(g, "entry", "T");

		Flags flags = assertRuleAddsNothing(g, setOf("entry"), setOf("onDestroy"), setOf("T"), setOf());
		assertTrue(flags.reachable.contains("onDestroy"));
		assertEquals(setOf("entry", "T"), flags.reachesTarget);
	}

	@Test
	public void aMixedGraphKeepsEveryFlag() {
		DefaultDirectedGraph<String, DefaultEdge> g = newGraph();
		addEdge(g, "entry", "a");
		addEdge(g, "a", "T1");
		addEdge(g, "cb1", "a");
		addEdge(g, "cb2", "T2");
		addEdge(g, "cb3", "b");
		addEdge(g, "b", "scanOnly");
		addEdge(g, "cb4", "c");
		addEdge(g, "cb1", "cb4");

		assertRuleAddsNothing(g, setOf("entry"), setOf("cb1", "cb2", "cb3", "cb4", "cb5"),
				setOf("T1", "T2"), setOf("scanOnly"));
	}

	// ---------------------------------------------------------------------------- helpers

	/**
	 * Runs the engine's steps, then applies {@link #callbackFlagRule} to a copy of the result
	 * and asserts the copy is unchanged.
	 */
	private static Flags assertRuleAddsNothing(DefaultDirectedGraph<String, DefaultEdge> g,
			Set<String> entryPoints, Set<String> callbacks, Set<String> targets,
			Set<String> scanDirect) {
		Flags seeded = engineSteps(g, entryPoints, callbacks, targets, scanDirect);
		Flags withRule = seeded.copy();
		callbackFlagRule(callbacks, withRule, g, targets);

		assertEquals("reachable", seeded.reachable, withRule.reachable);
		assertEquals("reachesTarget", seeded.reachesTarget, withRule.reachesTarget);
		assertEquals("directlyReachesTarget", seeded.direct, withRule.direct);
		return seeded;
	}

	/** {@link ReachabilityEngine#run}'s composition, with the scan result given. */
	private static Flags engineSteps(DefaultDirectedGraph<String, DefaultEdge> g,
			Set<String> entryPoints, Set<String> callbacks, Set<String> targets,
			Set<String> scanDirect) {
		Set<String> forwardSeeds = new HashSet<>(entryPoints);
		forwardSeeds.addAll(callbacks);
		Set<String> reachable = RvsecAnalysisClient.multiSourceBfs(g, forwardSeeds);

		Set<String> direct = new HashSet<>(RvsecAnalysisClient.findDirectTargetCallers(g, targets));
		direct.addAll(scanDirect);

		Set<String> reverseSeeds = new HashSet<>(targets);
		reverseSeeds.addAll(direct);
		Set<String> reachesTarget =
				RvsecAnalysisClient.multiSourceBfs(new EdgeReversedGraph<>(g), reverseSeeds);
		return new Flags(reachable, reachesTarget, direct);
	}

	/** The per-callback flag rule of design D7, applied after the searches. */
	private static void callbackFlagRule(Set<String> callbacks, Flags flags,
			DefaultDirectedGraph<String, DefaultEdge> g, Set<String> targets) {
		for (String callback : callbacks) {
			flags.reachable.add(callback);
			if (g.containsVertex(callback)) {
				for (DefaultEdge edge : g.outgoingEdgesOf(callback)) {
					String callee = g.getEdgeTarget(edge);
					if (targets.contains(callee)) {
						flags.direct.add(callback);
						flags.reachesTarget.add(callback);
						break;
					}
					if (flags.reachesTarget.contains(callee)) {
						flags.reachesTarget.add(callback);
					}
				}
			}
		}
	}

	private static DefaultDirectedGraph<String, DefaultEdge> newGraph() {
		return new DefaultDirectedGraph<>(DefaultEdge.class);
	}

	private static void addEdge(DefaultDirectedGraph<String, DefaultEdge> g, String src, String tgt) {
		g.addVertex(src);
		g.addVertex(tgt);
		g.addEdge(src, tgt);
	}

	private static Set<String> setOf(String... values) {
		return new HashSet<>(Arrays.asList(values));
	}
}
