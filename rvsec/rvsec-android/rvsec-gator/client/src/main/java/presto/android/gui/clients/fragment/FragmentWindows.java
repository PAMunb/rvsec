package presto.android.gui.clients.fragment;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import presto.android.gui.FixpointSolver;
import presto.android.gui.GUIAnalysisOutput;
import presto.android.gui.VariableValueQueryInterface;
import presto.android.gui.graph.NDialogNode;
import presto.android.gui.graph.NInflNode;
import presto.android.gui.graph.NInflate1OpNode;
import presto.android.gui.graph.NViewAllocNode;
import presto.android.Hierarchy;
import presto.android.gui.graph.NLayoutIdNode;
import presto.android.gui.graph.NNode;
import presto.android.gui.graph.NObjectNode;
import presto.android.gui.graph.NOpNode;
import soot.Body;
import soot.Local;
import soot.RefType;
import soot.SootClass;
import soot.SootMethod;
import soot.Unit;
import soot.jimple.ReturnStmt;

/**
 * Puts each attributed fragment's UI into a window named {@code Host#Fragment} (F2).
 *
 * <p>GATOR already models the {@code inflate} in a fragment's {@code onCreateView}
 * and builds the view subtree, but nothing ties the subtree to a window. Here the
 * subtree roots are read off the solver as the GUI objects that reach the value
 * {@code onCreateView} returns (which also covers ViewBinding's
 * {@code Binding.inflate(...).getRoot()}), falling back to the results of the
 * {@code inflate} calls inside {@code onCreateView}. Widgets and listeners are
 * collected from those roots by the client's own widget walk, so a fragment window
 * carries exactly the fields an activity window does.
 *
 * <p>The window type is {@code FRAGMENT}, never {@code DIALOG}: the consumer folds any
 * {@code Host#Suffix} window into the host's bucket, and a DIALOG-typed window with
 * that name would make the dialog re-keying move the host's whole bucket.
 *
 * <p>Everything here reads the solver, which is finished before the pre-WTG JSON
 * write, so fragment windows are present also when the WTG does not finish.
 */
public final class FragmentWindows {

	public static final String WINDOW_TYPE = "FRAGMENT";
	public static final String SEPARATOR = "#";

	/** The client's widget walk, so fragment widgets are serialised like any other. */
	@FunctionalInterface
	public interface WidgetCollector {
		void collect(NNode root, List<Map<String, Object>> widgets, Set<NNode> visited);
	}

	/** One (host, fragment) pair with the view roots of the fragment. */
	public static final class Pair {
		public final SootClass host;
		public final SootClass fragment;
		public final Set<NNode> roots;

		Pair(SootClass host, SootClass fragment, Set<NNode> roots) {
			this.host = host;
			this.fragment = fragment;
			this.roots = roots;
		}
	}

	private final List<Pair> pairs;

	private FragmentWindows(List<Pair> pairs) {
		this.pairs = pairs;
	}

	public List<Pair> pairs() {
		return pairs;
	}

	/**
	 * Runs F1 and the root lookup once. The result is reused by both JSON writes; the
	 * widget maps are rebuilt per write in {@link #windows} because the client's XML
	 * enrichment mutates them in place.
	 */
	public static FragmentWindows analyze(GUIAnalysisOutput output,
			Map<SootClass, List<SootMethod>> appClasses, String resDir) {
		long start = System.currentTimeMillis();
		FragmentHostResolver resolver = new FragmentHostResolver(output, appClasses, resDir);
		List<SootClass> fragments = resolver.appFragments();

		Map<NNode, Set<String>> layoutsOfRoot = layoutsOfInflateResults(output.getSolver());
		Set<NNode> windowRoots = new HashSet<>();
		for (SootClass activity : output.getActivities()) {
			windowRoots.addAll(output.getActivityRoots(activity));
		}
		for (NDialogNode dialog : output.getDialogs()) {
			windowRoots.addAll(output.getDialogRoots(dialog));
		}
		Map<SootClass, Set<NNode>> rootsByFragment = new LinkedHashMap<>();
		Map<SootClass, Set<String>> fragmentLayouts = new LinkedHashMap<>();
		int fromReturn = 0;
		int fromInflate = 0;
		for (SootClass fragment : fragments) {
			Set<NNode> roots = returnedViews(output, fragment);
			roots.removeIf(r -> !isViewRoot(r) || windowRoots.contains(r));
			if (!roots.isEmpty()) {
				fromReturn++;
			} else {
				roots = inflateResults(output.getSolver(), fragment);
				roots.removeIf(r -> !isViewRoot(r) || windowRoots.contains(r));
				if (!roots.isEmpty()) {
					fromInflate++;
				}
			}
			if (roots.isEmpty()) {
				continue;
			}
			rootsByFragment.put(fragment, roots);
			Set<String> layouts = new LinkedHashSet<>();
			for (NNode r : roots) {
				layouts.addAll(layoutsOfRoot.getOrDefault(r, Set.of()));
			}
			fragmentLayouts.put(fragment, layouts);
		}

		Map<SootClass, Set<SootClass>> hosts = resolver.resolve(fragmentLayouts);

		List<Pair> pairs = new ArrayList<>();
		int attributedWithoutRoots = 0;
		for (Map.Entry<SootClass, Set<SootClass>> e : hosts.entrySet()) {
			Set<NNode> roots = rootsByFragment.get(e.getKey());
			if (roots == null) {
				attributedWithoutRoots++;
				continue;
			}
			for (SootClass host : e.getValue()) {
				pairs.add(new Pair(host, e.getKey(), roots));
			}
		}

		System.out.println("[FragmentWindows] app fragments=" + fragments.size()
				+ " withRoots=" + rootsByFragment.size()
				+ " (return=" + fromReturn + ", inflate=" + fromInflate + ")"
				+ " attributed=" + hosts.size()
				+ " attributedWithoutRoots=" + attributedWithoutRoots
				+ " pairs=" + pairs.size()
				+ " transactionSites=" + resolver.transactionSites()
				+ " unresolvedTransactionSites=" + resolver.transactionSitesUnresolved()
				+ " (" + (System.currentTimeMillis() - start) + " ms)");
		return new FragmentWindows(pairs);
	}

	/** One window per (host, fragment) pair, ids from {@code firstId} up. */
	public List<Map<String, Object>> windows(WidgetCollector collector, int firstId) {
		List<Map<String, Object>> windows = new ArrayList<>();
		int id = firstId;
		for (Pair p : pairs) {
			Map<String, Object> window = new LinkedHashMap<>();
			window.put("id", id++);
			window.put("name", p.host.getName() + SEPARATOR + p.fragment.getName());
			window.put("type", WINDOW_TYPE);
			window.put("isMain", false);
			List<Map<String, Object>> widgets = new ArrayList<>();
			Set<NNode> visited = new HashSet<>();
			for (NNode root : p.roots) {
				collector.collect(root, widgets, visited);
			}
			window.put("widgets", widgets);
			windows.add(window);
		}
		return windows;
	}

	/** GUI objects reaching the value returned by the fragment's {@code onCreateView}. */
	private static Set<NNode> returnedViews(GUIAnalysisOutput output, SootClass fragment) {
		Set<NNode> roots = new LinkedHashSet<>();
		VariableValueQueryInterface query = output.getVariableValueQueryInterface();
		for (SootMethod m : onCreateViews(fragment)) {
			Body body;
			try {
				body = m.retrieveActiveBody();
			} catch (RuntimeException ex) {
				continue;
			}
			for (Unit u : body.getUnits()) {
				if (!(u instanceof ReturnStmt)) {
					continue;
				}
				if (!(((ReturnStmt) u).getOp() instanceof Local)) {
					continue;
				}
				Local l = (Local) ((ReturnStmt) u).getOp();
				if (!(l.getType() instanceof RefType)) {
					continue;
				}
				try {
					for (NObjectNode n : query.guiVariableValues(l)) {
						roots.add(n);
					}
				} catch (RuntimeException ex) {
					// The local's declared type is not a GUI class for GATOR: no value set.
				}
			}
		}
		return roots;
	}

	/**
	 * A fragment root must be a view object built by the app ({@code inflate} or
	 * {@code new SomeView}). The returned-value query is context-insensitive, so a
	 * value that flows through a generic container (a Kotlin {@code Flow}, a
	 * {@code lazy}) also brings unrelated objects; those are not views and drop here.
	 * A root that is already another window's root (the host's own content) drops
	 * too, so the fragment window never duplicates the activity.
	 */
	private static boolean isViewRoot(NNode n) {
		if (!(n instanceof NInflNode) && !(n instanceof NViewAllocNode)) {
			return false;
		}
		SootClass c = ((NObjectNode) n).getClassType();
		return c != null && Hierarchy.v().viewClasses.contains(c);
	}

	/** Results of the inflate calls inside the fragment's {@code onCreateView}. */
	private static Set<NNode> inflateResults(FixpointSolver solver, SootClass fragment) {
		Set<SootMethod> methods = new HashSet<>(onCreateViews(fragment));
		Set<NNode> roots = new LinkedHashSet<>();
		if (methods.isEmpty()) {
			return roots;
		}
		for (NOpNode op : NOpNode.getNodes(NInflate1OpNode.class)) {
			if (op.callSite == null || !methods.contains(op.callSite.getO2())) {
				continue;
			}
			Set<NNode> results = solver.solutionResults.get(op);
			if (results != null) {
				roots.addAll(results);
			}
		}
		return roots;
	}

	/**
	 * The {@code onCreateView} the fragment runs: its own, else the nearest one an
	 * application superclass declares (a shared base fragment). The solver is
	 * context-insensitive, so a base whose layout depends on a virtual call gives each
	 * subclass the union of the layouts.
	 */
	private static List<SootMethod> onCreateViews(SootClass fragment) {
		List<SootMethod> result = new ArrayList<>();
		SootClass cur = fragment;
		while (cur != null && result.isEmpty() && Hierarchy.v().appClasses.contains(cur)) {
			for (SootMethod m : cur.getMethods()) {
				if ("onCreateView".equals(m.getName()) && m.isConcrete()) {
					result.add(m);
				}
			}
			cur = cur.getSuperclassUnsafe();
		}
		return result;
	}

	/** Inflated root node -> layout names, for the {@code inflate} calls the solver resolved. */
	private static Map<NNode, Set<String>> layoutsOfInflateResults(FixpointSolver solver) {
		Map<NNode, Set<String>> result = new HashMap<>();
		for (Map.Entry<NOpNode, Set<NLayoutIdNode>> e : solver.reachingLayoutIds.entrySet()) {
			if (!(e.getKey() instanceof NInflate1OpNode)) {
				continue;
			}
			Set<NNode> results = solver.solutionResults.get(e.getKey());
			if (results == null) {
				continue;
			}
			for (NLayoutIdNode id : e.getValue()) {
				String name = FragmentHostResolver.layoutName(id.getIdValue());
				if (name == null) {
					continue;
				}
				for (NNode r : results) {
					result.computeIfAbsent(r, k -> new LinkedHashSet<>()).add(name);
				}
			}
		}
		return result;
	}
}
