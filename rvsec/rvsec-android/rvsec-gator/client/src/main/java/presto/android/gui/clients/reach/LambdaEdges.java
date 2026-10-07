package presto.android.gui.clients.reach;

import java.util.Collections;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import soot.Body;
import soot.SootClass;
import soot.SootMethod;
import soot.SootMethodRef;
import soot.Unit;
import soot.jimple.Stmt;
import soot.jimple.toolkits.callgraph.CallGraph;
import soot.jimple.toolkits.callgraph.Edge;

/**
 * Adds to the call graph the edges from function-object wrappers to the app method they
 * forward to (INV-ANA-77).
 *
 * <p>SPARK gives the receiver captured by a D8/desugar lambda wrapper no points-to set, so the
 * wrapper ({@code X$$ExternalSyntheticLambdaN.onClick}) may have no edge to the body
 * ({@code X.lambda$...}) it invokes. A widget handler resolves to the wrapper, so without the
 * edge the handler carries {@code reachesTarget: false} even when the body reaches a target.
 * Two sources of edges, both read from Jimple:
 * <ol>
 *   <li>every method of a lambda class (name contains {@code $$ExternalSyntheticLambda} or
 *       {@code $$Lambda}) gets an edge to each app method its body invokes;</li>
 *   <li>in any other app class, a method implementing the single abstract method of a directly
 *       implemented interface, whose body holds exactly one invoke and that invoke names an app
 *       method, gets an edge to that method (anonymous listener classes, Kotlin function
 *       objects).</li>
 * </ol>
 *
 * <p>The client runs this on {@code Scene.v().getCallGraph()} before the reachability search, so
 * {@code reachesTarget}, the distances and the WTG (with {@code cgDelegation=true}) all see the
 * same graph. The callee is the statically named method; {@code tryResolve} creates no phantom
 * method, so the Scene keeps its classes and methods. An edge from the wrapper to the callee
 * that the call graph already holds is not added again.
 */
public final class LambdaEdges {

	private LambdaEdges() {
		// static API
	}

	/** True for the class names D8 and the desugarer give to lambda wrappers. */
	static boolean isLambdaClass(String className) {
		return className.contains("$$ExternalSyntheticLambda") || className.contains("$$Lambda");
	}

	/**
	 * Adds the wrapper and single-invoke SAM edges to {@code cg}; returns the number of edges
	 * added. A method whose body cannot be retrieved is skipped.
	 */
	public static int addTo(CallGraph cg, Map<SootClass, List<SootMethod>> appClasses) {
		Set<SootMethod> appMethods = new HashSet<>();
		for (List<SootMethod> ms : appClasses.values()) {
			appMethods.addAll(ms);
		}
		int wrapperEdges = 0;
		int samEdges = 0;
		int alreadyInCg = 0;
		int bodiesSkipped = 0;
		for (Map.Entry<SootClass, List<SootMethod>> entry : appClasses.entrySet()) {
			SootClass cls = entry.getKey();
			boolean wrapper = isLambdaClass(cls.getName());
			Set<String> samSubsigs = wrapper ? Collections.emptySet() : singleAbstractMethods(cls);
			if (!wrapper && samSubsigs.isEmpty()) {
				continue;
			}
			for (SootMethod m : entry.getValue()) {
				if (!m.isConcrete() || (!wrapper && !samSubsigs.contains(m.getSubSignature()))) {
					continue;
				}
				Map<SootMethod, Stmt> callees = new LinkedHashMap<>();
				int invokes = appCallees(m, appMethods, callees);
				if (invokes < 0) {
					bodiesSkipped++;
					continue;
				}
				if (!wrapper && !(invokes == 1 && callees.size() == 1)) {
					continue;
				}
				for (Map.Entry<SootMethod, Stmt> call : callees.entrySet()) {
					SootMethod callee = call.getKey();
					if (callee.equals(m)) {
						continue;
					}
					if (hasEdge(cg, m, callee)) {
						alreadyInCg++;
						continue;
					}
					if (cg.addEdge(new Edge(m, call.getValue(), callee))) {
						if (wrapper) {
							wrapperEdges++;
						} else {
							samEdges++;
						}
					}
				}
			}
		}
		System.out.println("[LambdaEdges] added " + (wrapperEdges + samEdges) + " edges (wrapper: "
				+ wrapperEdges + ", sam: " + samEdges + ", already in call graph: " + alreadyInCg
				+ ", bodies skipped: " + bodiesSkipped + ")");
		return wrapperEdges + samEdges;
	}

	private static boolean hasEdge(CallGraph cg, SootMethod src, SootMethod tgt) {
		Iterator<Edge> it = cg.edgesOutOf(src);
		while (it.hasNext()) {
			if (tgt.equals(it.next().tgt())) {
				return true;
			}
		}
		return false;
	}

	/**
	 * Sub-signatures of the single abstract method of each interface the class implements
	 * directly; interfaces with zero or several abstract methods (or no loaded methods) are
	 * ignored.
	 */
	static Set<String> singleAbstractMethods(SootClass cls) {
		Set<String> out = new HashSet<>();
		for (SootClass itf : cls.getInterfaces()) {
			String sam = null;
			int abstracts = 0;
			for (SootMethod im : itf.getMethods()) {
				if (im.isAbstract()) {
					abstracts++;
					sam = im.getSubSignature();
				}
			}
			if (abstracts == 1) {
				out.add(sam);
			}
		}
		return out;
	}

	/**
	 * Collects into {@code out} the app methods named by the invokes in {@code m}'s body, each
	 * with its first call site, and returns the total number of invoke statements in the body,
	 * or {@code -1} when the body cannot be retrieved.
	 */
	private static int appCallees(SootMethod m, Set<SootMethod> appMethods, Map<SootMethod, Stmt> out) {
		Body body;
		try {
			body = m.retrieveActiveBody();
		} catch (RuntimeException | OutOfMemoryError e) {
			System.out.println("[LambdaEdges] body skipped: " + m.getSignature() + " (" + e + ")");
			return -1;
		}
		if (body == null) {
			return -1;
		}
		int invokes = 0;
		for (Unit u : body.getUnits()) {
			if (!(u instanceof Stmt) || !((Stmt) u).containsInvokeExpr()) {
				continue;
			}
			invokes++;
			SootMethodRef ref = ((Stmt) u).getInvokeExpr().getMethodRef();
			if (ref == null) {
				continue;
			}
			SootMethod callee = ref.tryResolve();
			if (callee != null && appMethods.contains(callee)) {
				out.putIfAbsent(callee, (Stmt) u);
			}
		}
		return invokes;
	}
}
