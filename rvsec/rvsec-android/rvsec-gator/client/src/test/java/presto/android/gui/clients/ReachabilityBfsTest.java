package presto.android.gui.clients;

import org.jgrapht.graph.DefaultDirectedGraph;
import org.jgrapht.graph.DefaultEdge;
import org.jgrapht.graph.EdgeReversedGraph;
import org.junit.*;
import static org.junit.Assert.*;
import java.util.*;

/**
 * Unit tests for the graph-traversal helpers in RvsecAnalysisClient:
 * multiSourceBfs() and findDirectMopCallers().
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

	// ── reverse BFS (reachesMop) ────────────────────────────────────────

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
		Set<String> reachesMop = RvsecAnalysisClient.multiSourceBfs(reversed, setOf("D"));

		// D itself, plus everything that can reach D in the forward graph
		assertTrue(reachesMop.contains("D"));
		assertTrue(reachesMop.contains("C"));
		assertTrue(reachesMop.contains("B"));
		assertTrue(reachesMop.contains("E"));
		assertTrue(reachesMop.contains("A"));
	}

	// ── findDirectMopCallers tests ──────────────────────────────────────

	@Test
	public void testFindDirectMopCallersSimple() {
		DefaultDirectedGraph<String, DefaultEdge> g = newGraph();
		addEdge(g, "A", "B");
		addEdge(g, "B", "C");
		addEdge(g, "C", "D");

		Set<String> callers = RvsecAnalysisClient.findDirectMopCallers(g, setOf("D"));
		assertEquals(setOf("C"), callers);
	}

	@Test
	public void testFindDirectMopCallersMultiple() {
		DefaultDirectedGraph<String, DefaultEdge> g = newGraph();
		addEdge(g, "A", "D");
		addEdge(g, "B", "D");
		addEdge(g, "C", "E");
		g.addVertex("D"); // already added via edges, but explicit for clarity

		Set<String> callers = RvsecAnalysisClient.findDirectMopCallers(g, setOf("D"));
		assertEquals(setOf("A", "B"), callers);
	}

	@Test
	public void testFindDirectMopCallersNone() {
		DefaultDirectedGraph<String, DefaultEdge> g = newGraph();
		addEdge(g, "A", "B");
		addEdge(g, "B", "C");

		// D is not in the graph at all
		Set<String> callers = RvsecAnalysisClient.findDirectMopCallers(g, setOf("D"));
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
