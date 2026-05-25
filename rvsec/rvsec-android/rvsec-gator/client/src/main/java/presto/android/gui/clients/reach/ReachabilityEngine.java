package presto.android.gui.clients.reach;

import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.jgrapht.graph.DefaultDirectedGraph;
import org.jgrapht.graph.DefaultEdge;
import org.jgrapht.graph.EdgeReversedGraph;

import presto.android.gui.GUIAnalysisOutput;
import presto.android.gui.clients.RvsecAnalysisClient;
import soot.Scene;
import soot.SootClass;
import soot.SootMethod;
import soot.jimple.toolkits.callgraph.CallGraph;

/**
 * Pipeline orchestrator that turns the resolved target {@link SootMethod}
 * set into a {@link ReachabilityIndex}.
 *
 * <p>The reachability pipeline has five steps:
 * <ol>
 *   <li>Build a JGraphT view of the SPARK call graph (self-loops filtered).</li>
 *   <li>Multi-source BFS from entry points → {@code reachableSet}.</li>
 *   <li>Reverse-graph multi-source BFS from resolved targets →
 *       {@code reachesTargetSet}.</li>
 *   <li>{@code directTargetSet} = CG-edge direct callers ∪ bytecode-scan
 *       complement (BUG-INV-ANA-19 — SPARK quarantines library targets so
 *       the scanner catches app→library invokes the CG drops).</li>
 *   <li>Lifecycle + listener callbacks complement: callbacks marked
 *       reachable, target flags propagated when callbacks fan into the
 *       target set.</li>
 * </ol>
 *
 * <p>Step bodies still live as package-private statics on
 * {@link RvsecAnalysisClient} (this is the C1c stepping-stone; the full
 * physical code move is a follow-up cleanup that does NOT block the public
 * API contract here). What the engine does own is the orchestration and
 * the publication boundary — once {@link #run} returns, the
 * {@link ReachabilityIndex} is immutable, so downstream code (the
 * {@code ReachabilityEnricher} arriving in C1d, the {@code JsonReportWriter}
 * arriving in C1e) cannot retroactively mutate reachability state.
 */
public final class ReachabilityEngine {

	private final GUIAnalysisOutput output;
	private final Map<SootClass, List<SootMethod>> appClasses;
	private final Set<SootMethod> targets;

	public ReachabilityEngine(
			GUIAnalysisOutput output,
			Map<SootClass, List<SootMethod>> appClasses,
			Set<SootMethod> targets) {
		this.output = output;
		this.appClasses = appClasses;
		this.targets = targets;
	}

	public ReachabilityIndex run() {
		CallGraph cg = Scene.v().getCallGraph();
		DefaultDirectedGraph<SootMethod, DefaultEdge> graph = RvsecAnalysisClient.buildJGraph(cg);
		System.out.println("[ReachabilityEngine] JGraphT graph: "
				+ graph.vertexSet().size() + " vertices, "
				+ graph.edgeSet().size() + " edges");

		Set<SootMethod> entryPoints = RvsecAnalysisClient.getEntryPoints(output);
		System.out.println("[ReachabilityEngine] Entry points: " + entryPoints.size());

		Set<SootMethod> reachableSet = RvsecAnalysisClient.multiSourceBfs(graph, entryPoints);
		EdgeReversedGraph<SootMethod, DefaultEdge> reversed = new EdgeReversedGraph<>(graph);
		Set<SootMethod> reachesTargetSet = RvsecAnalysisClient.multiSourceBfs(reversed, targets);
		Set<SootMethod> directTargetSet =
				new HashSet<>(RvsecAnalysisClient.findDirectTargetCallers(graph, targets));
		int directCgCount = directTargetSet.size();

		Set<SootMethod> directBcSet =
				RvsecAnalysisClient.findDirectTargetCallersByBytecodeScan(appClasses, targets);
		Set<SootMethod> intersection = new HashSet<>(directTargetSet);
		intersection.retainAll(directBcSet);
		directTargetSet.addAll(directBcSet);
		System.out.println("[ReachabilityEngine] directlyReachesTarget: " + directTargetSet.size()
				+ " (CG: " + directCgCount + ", bytecode: " + directBcSet.size()
				+ ", intersection: " + intersection.size() + ")");

		RvsecAnalysisClient.complementWithCallbacks(
				output, reachableSet, reachesTargetSet, directTargetSet, graph, targets);

		System.out.println("[ReachabilityEngine] Reachable: " + reachableSet.size()
				+ ", reachesTarget: " + reachesTargetSet.size()
				+ ", directlyReachesTarget: " + directTargetSet.size());

		return new ReachabilityIndex(reachableSet, reachesTargetSet, directTargetSet);
	}
}
