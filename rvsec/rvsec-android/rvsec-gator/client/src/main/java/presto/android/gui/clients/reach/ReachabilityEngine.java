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
import presto.android.gui.clients.target.TargetMatching;
import presto.android.gui.clients.target.TargetMethod;
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
 *   <li>{@code directTargetSet} = CG-edge direct callers ∪ bytecode-scan
 *       complement (BUG-INV-ANA-19 — SPARK quarantines library targets so
 *       the scanner catches app→library invokes the CG drops).</li>
 *   <li>Reverse-graph multi-source BFS seeded with
 *       {@code targets ∪ directTargetSet} → {@code reachesTargetSet}. The direct set is
 *       part of the seed so that {@code reachesTarget ⊇ directlyReachesTarget} holds by
 *       construction rather than by luck (INV-ANA-64).</li>
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
	/**
	 * The DECLARED targets, carrying the owner FQN and the subtype/pattern flags that
	 * {@code targets} has already lost by resolving to concrete {@link SootMethod}s. The
	 * bytecode scan needs them: a subtype target cannot be reduced to exact class#method keys
	 * without pre-expanding the hierarchy, which is the design this capability rejected.
	 */
	private final Set<TargetMethod> targetSpecs;
	/** Shared with {@code TargetResolver.resolveInScene}: same resolved-owner cache. */
	private final TargetMatching matching;

	public ReachabilityEngine(
			GUIAnalysisOutput output,
			Map<SootClass, List<SootMethod>> appClasses,
			Set<SootMethod> targets,
			Set<TargetMethod> targetSpecs,
			TargetMatching matching) {
		this.output = output;
		this.appClasses = appClasses;
		this.targets = targets;
		this.targetSpecs = targetSpecs;
		this.matching = matching;
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

		// The direct set is computed FIRST, and the reverse BFS is then seeded with it.
		//
		// reachesTarget must contain directlyReachesTarget — a direct caller is a path of
		// length 1, so the containment is definitional. It did not hold, because the two
		// fields answer to two different oracles and only one of them was ever repaired: the
		// direct axis is the call graph UNION the bytecode scan (the scan exists precisely
		// because SPARK quarantines app->library invokes and drops those edges), while the
		// transitive axis was a reverse BFS over the call graph alone. A method the scan alone
		// discovered therefore came out direct-but-not-transitive.
		//
		// Seeding — rather than unioning the two sets afterwards — is what makes the
		// containment derived instead of merely asserted: the seed propagates upward, so the
		// CALLERS of a scan-discovered method are marked too. A post-hoc addAll would fix the
		// containment and leave those callers wrongly false.
		//
		// multiSourceBfs already calls graph.addVertex(seed) before its visited check, so a
		// seed with no call-graph vertex at all (the common case here: most violating methods
		// were never processed by SPARK) needs no defensive code.
		Set<SootMethod> directTargetSet =
				new HashSet<>(RvsecAnalysisClient.findDirectTargetCallers(graph, targets));
		int directCgCount = directTargetSet.size();

		Set<SootMethod> directBcSet =
				RvsecAnalysisClient.findDirectTargetCallersByBytecodeScan(
						appClasses, targets, targetSpecs, matching);
		Set<SootMethod> intersection = new HashSet<>(directTargetSet);
		intersection.retainAll(directBcSet);
		directTargetSet.addAll(directBcSet);
		Set<SootMethod> scanOnly = new HashSet<>(directBcSet);
		scanOnly.removeAll(intersection);
		System.out.println("[ReachabilityEngine] directlyReachesTarget: " + directTargetSet.size()
				+ " (CG: " + directCgCount + ", bytecode: " + directBcSet.size()
				+ ", intersection: " + intersection.size()
				+ ", bytecode-only seeds: " + scanOnly.size() + ")");

		Set<SootMethod> bfsSeeds = new HashSet<>(targets);
		bfsSeeds.addAll(directTargetSet);
		EdgeReversedGraph<SootMethod, DefaultEdge> reversed = new EdgeReversedGraph<>(graph);
		// Timed alongside the two match points: this is the stage that grows least visibly,
		// since resolveInScene hands it every matching library method in the Scene once an
		// owner is quasi-universal (NFR04 cost bound).
		long bfsStart = System.currentTimeMillis();
		Set<SootMethod> reachesTargetSet = RvsecAnalysisClient.multiSourceBfs(reversed, bfsSeeds);
		System.out.println("[ReachabilityEngine] reverseBfs: "
				+ (System.currentTimeMillis() - bfsStart) + " ms from " + bfsSeeds.size()
				+ " seeds");

		RvsecAnalysisClient.complementWithCallbacks(
				output, reachableSet, reachesTargetSet, directTargetSet, graph, targets);

		System.out.println("[ReachabilityEngine] Reachable: " + reachableSet.size()
				+ ", reachesTarget: " + reachesTargetSet.size()
				+ ", directlyReachesTarget: " + directTargetSet.size());

		return new ReachabilityIndex(reachableSet, reachesTargetSet, directTargetSet);
	}
}
