package presto.android.gui.clients.reach;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

import soot.Body;
import soot.FastHierarchy;
import soot.Scene;
import soot.SootClass;
import soot.SootMethod;
import soot.SootMethodRef;
import soot.Unit;
import soot.jimple.InstanceInvokeExpr;
import soot.jimple.InvokeExpr;
import soot.jimple.SpecialInvokeExpr;
import soot.jimple.Stmt;
import soot.jimple.toolkits.callgraph.CallGraph;
import soot.jimple.toolkits.callgraph.Edge;

/**
 * Adds to the call graph the edges of instance-invoke sites in app methods that SPARK left with
 * no edge at all (INV-ANA-96).
 *
 * <p>SPARK resolves a virtual call from the points-to set of its receiver, and that set holds
 * only the allocations SPARK sees. On Android the framework, reflection or a dependency-injection
 * container creates the activity, fragment, application or service whose {@code this} is the
 * receiver, the ViewModel a provider hands out, and the dependency stored in an injected field.
 * None of these has an allocation SPARK follows, so the receiver's set is empty and the call
 * site gets no edge. The callee then looks unreachable from its caller, and a handler that
 * reaches a target through it carries {@code reachesTarget: false}.
 *
 * <p>For every concrete app method whose body can be retrieved, each statement holding an
 * instance invoke with no outgoing edge receives one edge per callee:
 * <ul>
 *   <li>a special invoke goes to the method its reference resolves to;</li>
 *   <li>a virtual or interface invoke goes to the method
 *       {@link FastHierarchy#resolveConcreteDispatch} yields on each concrete app class that the
 *       declared type admits (the declared type itself included). The declared type is the
 *       class the invoke names, which is the static type of the receiver expression the
 *       compiler wrote.</li>
 * </ul>
 * Only concrete app methods are callees, so no edge leads into library code and every target,
 * which is a library method, keeps the direct callers it had. A site that holds an edge, a static
 * invoke, and a method whose body cannot be retrieved are left as they are. This is the
 * class-hierarchy answer for the sites SPARK had no answer for: a dead site also receives edges,
 * which over-approximates {@code reachesTarget} and the distances, and the log line reports the
 * largest fan-out so the width can be judged per run.
 *
 * <p>The client runs this on {@code Scene.v().getCallGraph()} after {@link LambdaEdges}, so a
 * wrapper site that pass filled is no longer empty, and before the reachability search, so
 * {@code reachesTarget} and the distances see these edges. The client removes the edges in {@code added}
 * again before the fragment windows and the WTG, which (with {@code cgDelegation=true}) read the
 * graph SPARK and {@link LambdaEdges} built. Besides the counters, the ten sites with the most callees are logged with their declared
 * type, sorted by fan-out and then by method signature and statement position.
 */
public final class EmptySiteEdges {

	private static final int TOP_SITES = 10;

	private EmptySiteEdges() {
		// static API
	}

	/** One empty site that received edges, as listed in the top fan-out lines. */
	private static final class Site {
		final int fanOut;
		final String method;
		final int index;
		final Stmt stmt;
		final SootClass declared;

		Site(int fanOut, String method, int index, Stmt stmt, SootClass declared) {
			this.fanOut = fanOut;
			this.method = method;
			this.index = index;
			this.stmt = stmt;
			this.declared = declared;
		}
	}

	private static final Comparator<Site> BY_FAN_OUT = Comparator
			.comparingInt((Site s) -> -s.fanOut)
			.thenComparing(s -> s.method)
			.thenComparingInt(s -> s.index);

	/**
	 * Adds the edges of the empty instance-invoke sites of the app methods to {@code cg} and to
	 * {@code added}, so the caller can remove them before the WTG reads the graph (INV-ANA-96).
	 * Each edge enters {@code added} as it enters {@code cg}, so a pass that throws midway still
	 * leaves the caller every edge it added. A method whose body cannot be retrieved is skipped and
	 * counted in the log line.
	 */
	public static void addTo(CallGraph cg, Map<SootClass, List<SootMethod>> appClasses,
			List<Edge> added) {
		Set<SootMethod> appMethods = new HashSet<>();
		List<SootClass> concreteAppClasses = new ArrayList<>();
		for (Map.Entry<SootClass, List<SootMethod>> entry : appClasses.entrySet()) {
			appMethods.addAll(entry.getValue());
			SootClass c = entry.getKey();
			if (!c.isInterface() && !c.isAbstract() && !c.isPhantom()) {
				concreteAppClasses.add(c);
			}
		}
		FastHierarchy hierarchy = Scene.v().getOrMakeFastHierarchy();
		Map<SootClass, List<SootClass>> subtypes = new HashMap<>();
		Map<SootMethodRef, Set<SootMethod>> dispatched = new HashMap<>();

		int sites = 0;
		int emptySites = 0;
		int edgesAdded = 0;
		int bodiesSkipped = 0;
		int largestFanOut = 0;
		TreeSet<Site> top = new TreeSet<>(BY_FAN_OUT);
		for (List<SootMethod> methods : appClasses.values()) {
			for (SootMethod m : methods) {
				if (!m.isConcrete()) {
					continue;
				}
				Body body;
				try {
					body = m.retrieveActiveBody();
				} catch (RuntimeException e) {
					bodiesSkipped++;
					continue;
				}
				int index = -1;
				for (Unit u : body.getUnits()) {
					index++;
					if (!(u instanceof Stmt) || !((Stmt) u).containsInvokeExpr()) {
						continue;
					}
					Stmt stmt = (Stmt) u;
					InvokeExpr ie = stmt.getInvokeExpr();
					if (!(ie instanceof InstanceInvokeExpr)) {
						continue;
					}
					sites++;
					if (cg.edgesOutOf(stmt).hasNext()) {
						continue;
					}
					emptySites++;
					SootMethodRef ref = ie.getMethodRef();
					Set<SootMethod> callees;
					if (ie instanceof SpecialInvokeExpr) {
						SootMethod resolved = ref.tryResolve();
						callees = resolved != null && resolved.isConcrete() && appMethods.contains(resolved)
								? Collections.singleton(resolved)
								: Collections.emptySet();
					} else {
						callees = dispatched.computeIfAbsent(ref, r -> dispatch(r, hierarchy,
								subtypes.computeIfAbsent(r.declaringClass(),
										d -> concreteSubtypes(d, concreteAppClasses, hierarchy)),
								appMethods));
					}
					int fanOut = 0;
					for (SootMethod callee : callees) {
						Edge edge = new Edge(m, stmt, callee);
						if (cg.addEdge(edge)) {
							added.add(edge);
							fanOut++;
						}
					}
					if (fanOut == 0) {
						continue;
					}
					edgesAdded += fanOut;
					largestFanOut = Math.max(largestFanOut, fanOut);
					if (top.size() < TOP_SITES || fanOut >= top.last().fanOut) {
						top.add(new Site(fanOut, m.getSignature(), index, stmt, ref.declaringClass()));
						if (top.size() > TOP_SITES) {
							top.pollLast();
						}
					}
				}
			}
		}
		System.out.println("[EmptySiteEdges] added " + edgesAdded + " edges (instance-invoke sites: "
				+ sites + ", empty sites: " + emptySites + ", bodies skipped: " + bodiesSkipped
				+ ", largest fan-out: " + largestFanOut + ")");
		for (Site s : top) {
			System.out.println("[EmptySiteEdges] fan-out " + s.fanOut + " at " + s.method + " #"
					+ s.index + " (declared " + s.declared.getName() + "): " + s.stmt);
		}
	}

	/** The concrete app classes the declared class admits, itself included; none for a phantom. */
	private static List<SootClass> concreteSubtypes(SootClass declared,
			List<SootClass> concreteAppClasses, FastHierarchy hierarchy) {
		List<SootClass> out = new ArrayList<>();
		if (declared.isPhantom()) {
			return out;
		}
		for (SootClass c : concreteAppClasses) {
			if (hierarchy.canStoreClass(c, declared)) {
				out.add(c);
			}
		}
		return out;
	}

	/** The concrete app methods the invoke dispatches to on each of {@code receivers}, in order. */
	private static Set<SootMethod> dispatch(SootMethodRef ref, FastHierarchy hierarchy,
			List<SootClass> receivers, Set<SootMethod> appMethods) {
		Set<SootMethod> out = new LinkedHashSet<>();
		for (SootClass receiver : receivers) {
			SootMethod callee = hierarchy.resolveConcreteDispatch(receiver, ref);
			if (callee != null && callee.isConcrete() && appMethods.contains(callee)) {
				out.add(callee);
			}
		}
		return out;
	}
}
