package presto.android.gui.clients;

import org.jgrapht.graph.DefaultDirectedGraph;
import org.jgrapht.graph.DefaultEdge;
import org.jgrapht.graph.EdgeReversedGraph;
import org.junit.*;
import static org.junit.Assert.*;
import java.util.*;

/**
 * Unit tests for the graph-traversal helpers in RvsecAnalysisClient:
 * multiSourceBfs() and findDirectTargetCallers().
 *
 * Uses String vertices ("A", "B", ...) to build synthetic JGraphT graphs,
 * exercising the package-private generic methods without Soot dependencies.
 */
public class ReachabilityBfsTest {

	// ── helpers ──────────────────────────────────────────────────────────

	private static DefaultDirectedGraph<String, DefaultEdge> newGraph() {
		return new DefaultDirectedGraph<>(DefaultEdge.class);
	}

	private static void addEdge(DefaultDirectedGraph<String, DefaultEdge> g,
								String src, String tgt) {
		g.addVertex(src);
		g.addVertex(tgt);
		g.addEdge(src, tgt);
	}

	private static Set<String> setOf(String... values) {
		return new HashSet<>(Arrays.asList(values));
	}

	// ── multiSourceBfs tests ────────────────────────────────────────────

	@Test
	public void testBfsLinearChain() {
		DefaultDirectedGraph<String, DefaultEdge> g = newGraph();
		addEdge(g, "A", "B");
		addEdge(g, "B", "C");
		addEdge(g, "C", "D");

		Set<String> result = RvsecAnalysisClient.multiSourceBfs(g, setOf("A"));
		assertEquals(setOf("A", "B", "C", "D"), result);
	}

	@Test
	public void testBfsTwoEntryPoints() {
		DefaultDirectedGraph<String, DefaultEdge> g = newGraph();
		addEdge(g, "A", "B");
		addEdge(g, "B", "C");
		addEdge(g, "C", "D");
		addEdge(g, "E", "C");

		Set<String> result = RvsecAnalysisClient.multiSourceBfs(g, setOf("A", "E"));
		assertEquals(setOf("A", "B", "C", "D", "E"), result);
	}

	@Test
	public void testBfsDisconnected() {
		DefaultDirectedGraph<String, DefaultEdge> g = newGraph();
		addEdge(g, "A", "B");
		addEdge(g, "C", "D");

		Set<String> result = RvsecAnalysisClient.multiSourceBfs(g, setOf("A"));
		assertEquals(setOf("A", "B"), result);
		assertFalse(result.contains("C"));
		assertFalse(result.contains("D"));
	}

	@Test
	public void testBfsEmptyGraph() {
		DefaultDirectedGraph<String, DefaultEdge> g = newGraph();

		Set<String> result = RvsecAnalysisClient.multiSourceBfs(g, Collections.emptySet());
		assertTrue(result.isEmpty());
	}

	@Test
	public void testBfsEmptySeeds() {
		DefaultDirectedGraph<String, DefaultEdge> g = newGraph();
		addEdge(g, "A", "B");

		Set<String> result = RvsecAnalysisClient.multiSourceBfs(g, Collections.emptySet());
		assertTrue(result.isEmpty());
	}

	@Test
	public void testBfsSeedNotInGraph() {
		// Codex fix #1 (INV-ANA-25): seeds without any CG edge are
		// force-added to the graph and survive into the result. Pre-fix
		// behavior was assertTrue(result.isEmpty()); the new contract is
		// that the seed itself is always present (an isolated entry point
		// IS reachable from itself).
		DefaultDirectedGraph<String, DefaultEdge> g = newGraph();
		addEdge(g, "A", "B");

		Set<String> result = RvsecAnalysisClient.multiSourceBfs(g, setOf("X"));
		assertEquals(setOf("X"), result);
	}

	@Test
	public void testBfsCyclic() {
		DefaultDirectedGraph<String, DefaultEdge> g = newGraph();
		addEdge(g, "A", "B");
		addEdge(g, "B", "C");
		addEdge(g, "C", "A");

		Set<String> result = RvsecAnalysisClient.multiSourceBfs(g, setOf("A"));
		assertEquals(setOf("A", "B", "C"), result);
	}

	// ── reverse BFS (reachesTarget) ────────────────────────────────────────

	@Test
	public void testReverseBfsForReachesMop() {
		// Forward graph: A→B→C→D, E→C
		DefaultDirectedGraph<String, DefaultEdge> g = newGraph();
		addEdge(g, "A", "B");
		addEdge(g, "B", "C");
		addEdge(g, "C", "D");
		addEdge(g, "E", "C");

		// Reverse the graph and BFS from MOP={D}.
		// In the reversed graph edges are D→C→B and D→C, C→E, C→B, B→A.
		// BFS from D traverses: D -> C -> B, E -> B already visited, -> A
		EdgeReversedGraph<String, DefaultEdge> reversed = new EdgeReversedGraph<>(g);
		Set<String> reachesTarget = RvsecAnalysisClient.multiSourceBfs(reversed, setOf("D"));

		// D itself, plus everything that can reach D in the forward graph
		assertTrue(reachesTarget.contains("D"));
		assertTrue(reachesTarget.contains("C"));
		assertTrue(reachesTarget.contains("B"));
		assertTrue(reachesTarget.contains("E"));
		assertTrue(reachesTarget.contains("A"));
	}

	// ── reaches ⊇ direct, by construction (INV-ANA-64) ─────────────────────

	// These lock the COMPOSITION the engine performs — seed the reverse BFS with
	// targets ∪ directTargetSet — rather than the call site that performs it.
	// ReachabilityEngine.run() reads Scene.v().getCallGraph(), so the wiring itself is
	// reachable only from the integration tests; what is testable here, and what actually
	// carries the invariant, is that the composition has the property the design claims.

	@Test
	public void testScanOnlyCallerIsMarkedWhenSeeded() {
		// The shape of the defect: the bytecode scan sees M calling a target through an
		// invoke SPARK quarantined, so M has no vertex in the call graph at all (12 of the
		// 14 violations measured in the tree are of exactly this kind). Before the repair M
		// was directlyReachesTarget=true and reachesTarget=false.
		DefaultDirectedGraph<String, DefaultEdge> g = newGraph();
		addEdge(g, "caller", "M");
		Set<String> targets = setOf("T");
		Set<String> directFromScan = setOf("M");

		Set<String> seeds = new HashSet<>(targets);
		seeds.addAll(directFromScan);
		EdgeReversedGraph<String, DefaultEdge> reversed = new EdgeReversedGraph<>(g);
		Set<String> reachesTarget = RvsecAnalysisClient.multiSourceBfs(reversed, seeds);

		assertTrue("a scan-discovered direct caller must land in reachesTarget",
				reachesTarget.containsAll(directFromScan));
	}

	@Test
	public void testCallerOfAScanOnlyCallerIsAlsoMarked() {
		// This is the property that rules out the one-line alternative. A post-hoc
		// reachesTargetSet.addAll(directTargetSet) would satisfy the containment and stop
		// there, leaving "caller" false — a transitive false negative asserted away rather
		// than fixed. Seeding propagates.
		DefaultDirectedGraph<String, DefaultEdge> g = newGraph();
		addEdge(g, "grandCaller", "caller");
		addEdge(g, "caller", "M");

		Set<String> seeds = new HashSet<>(setOf("T"));
		seeds.add("M");
		EdgeReversedGraph<String, DefaultEdge> reversed = new EdgeReversedGraph<>(g);
		Set<String> reachesTarget = RvsecAnalysisClient.multiSourceBfs(reversed, seeds);

		assertTrue("the direct caller itself", reachesTarget.contains("M"));
		assertTrue("its caller, which only seeding reaches", reachesTarget.contains("caller"));
		assertTrue("and on up the chain", reachesTarget.contains("grandCaller"));
	}

	@Test
	public void testEmptyDirectSetLeavesTheResultIdentical() {
		// The JCA path: when the scan adds nothing, seeding with targets ∪ ∅ must produce
		// byte-identical output to seeding with targets alone (INV-ANA-35).
		DefaultDirectedGraph<String, DefaultEdge> g = newGraph();
		addEdge(g, "A", "B");
		addEdge(g, "B", "T");
		EdgeReversedGraph<String, DefaultEdge> reversed = new EdgeReversedGraph<>(g);

		Set<String> targets = setOf("T");
		Set<String> before = RvsecAnalysisClient.multiSourceBfs(reversed, targets);

		Set<String> seeds = new HashSet<>(targets);
		seeds.addAll(Collections.<String>emptySet());
		Set<String> after = RvsecAnalysisClient.multiSourceBfs(reversed, seeds);

		assertEquals(before, after);
	}

	@Test
	public void testContainmentHoldsForAMixedDirectSet() {
		// Direct set from both oracles at once: "cg" has a real edge to the target, "scan"
		// has none. Both must end up in reachesTarget.
		DefaultDirectedGraph<String, DefaultEdge> g = newGraph();
		addEdge(g, "cg", "T");
		Set<String> targets = setOf("T");
		Set<String> direct = setOf("cg", "scan");

		Set<String> seeds = new HashSet<>(targets);
		seeds.addAll(direct);
		EdgeReversedGraph<String, DefaultEdge> reversed = new EdgeReversedGraph<>(g);
		Set<String> reachesTarget = RvsecAnalysisClient.multiSourceBfs(reversed, seeds);

		assertTrue("reachesTarget must contain directlyReachesTarget",
				reachesTarget.containsAll(direct));
	}

	// ── findDirectTargetCallers tests ──────────────────────────────────────

	@Test
	public void testFindDirectMopCallersSimple() {
		DefaultDirectedGraph<String, DefaultEdge> g = newGraph();
		addEdge(g, "A", "B");
		addEdge(g, "B", "C");
		addEdge(g, "C", "D");

		Set<String> callers = RvsecAnalysisClient.findDirectTargetCallers(g, setOf("D"));
		assertEquals(setOf("C"), callers);
	}

	@Test
	public void testFindDirectMopCallersMultiple() {
		DefaultDirectedGraph<String, DefaultEdge> g = newGraph();
		addEdge(g, "A", "D");
		addEdge(g, "B", "D");
		addEdge(g, "C", "E");
		g.addVertex("D"); // already added via edges, but explicit for clarity

		Set<String> callers = RvsecAnalysisClient.findDirectTargetCallers(g, setOf("D"));
		assertEquals(setOf("A", "B"), callers);
	}

	@Test
	public void testFindDirectMopCallersNone() {
		DefaultDirectedGraph<String, DefaultEdge> g = newGraph();
		addEdge(g, "A", "B");
		addEdge(g, "B", "C");

		// D is not in the graph at all
		Set<String> callers = RvsecAnalysisClient.findDirectTargetCallers(g, setOf("D"));
		assertTrue(callers.isEmpty());
	}

	// ── edge case: self-loop ────────────────────────────────────────────

	@Test
	public void testSelfLoopNoCrash() {
		DefaultDirectedGraph<String, DefaultEdge> g = newGraph();
		g.addVertex("A");
		g.addEdge("A", "A");
		addEdge(g, "A", "B");

		Set<String> result = RvsecAnalysisClient.multiSourceBfs(g, setOf("A"));
		assertEquals(setOf("A", "B"), result);
	}
}
