package presto.android.gui.clients;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Queue;
import java.util.Set;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;

import org.jgrapht.graph.DefaultDirectedGraph;
import org.jgrapht.graph.DefaultEdge;
import org.jgrapht.graph.EdgeReversedGraph;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;

import com.google.gson.stream.JsonWriter;

import br.unb.cic.mop.extractor.JavamopFacade;
import br.unb.cic.mop.extractor.model.MopMethod;
import javamop.util.MOPException;
import presto.android.Configs;
import presto.android.gui.PropertyManager;
import presto.android.gui.GUIAnalysisClient;
import presto.android.gui.GUIAnalysisOutput;
import presto.android.gui.wtg.intent.IntentFilter;
import presto.android.gui.wtg.intent.IntentFilterManager;
import presto.android.xml.XMLParser;
import presto.android.gui.clients.energy.VarUtil;
import presto.android.gui.graph.NDialogNode;
import presto.android.gui.graph.NNode;
import presto.android.gui.graph.NObjectNode;
import presto.android.gui.graph.NOptionsMenuNode;
import presto.android.gui.listener.EventType;
import presto.android.gui.wtg.WTGAnalysisOutput;
import presto.android.gui.wtg.WTGBuilder;
import presto.android.gui.wtg.ds.WTG;
import presto.android.gui.wtg.ds.WTGEdge;
import presto.android.gui.wtg.ds.WTGNode;
import soot.Body;
import soot.Scene;
import soot.SootClass;
import soot.SootMethod;
import soot.SootMethodRef;
import soot.Unit;
import soot.jimple.InvokeExpr;
import soot.jimple.Stmt;
import soot.jimple.toolkits.callgraph.CallGraph;
import soot.jimple.toolkits.callgraph.Edge;

/**
 * Unified GATOR analysis client that produces a single JSON file containing
 * reachability, windows, and transitions data. Replaces the separate GESDA,
 * GATOR (RvsecWtgClient), and REACH tools.
 *
 * JSON sections are written in priority order with flush between each:
 * 1. reachability — coverage denominator (most critical)
 * 2. windows — widget inventory for navigation
 * 3. transitions — WTG for navigation
 *
 * On timeout, partial JSON preserves the most critical data first.
 */
public class RvsecAnalysisClient implements GUIAnalysisClient {

	@Override
	public void run(GUIAnalysisOutput output) {
		VarUtil.v().guiOutput = output;

		String mopDir = getMopDir();
		String outputPath = Configs.pathoutfilename;

		// Resolve the package to filter classes: prefer codePackage clientParam
		// (detected by Python-side PackageDetector via Androguard component analysis),
		// fall back to manifest package from AndroidManifest.xml
		String codePackage = getCodePackage();
		String manifestPackage = output.getAppPackageName();
		String filterPackage = (codePackage != null) ? codePackage : manifestPackage;

		System.out.println("[RvsecAnalysisClient] Starting unified analysis");
		System.out.println("[RvsecAnalysisClient] MOP dir: " + mopDir);
		System.out.println("[RvsecAnalysisClient] Output: " + outputPath);
		System.out.println("[RvsecAnalysisClient] Code package: " + codePackage);
		System.out.println("[RvsecAnalysisClient] Manifest package: " + manifestPackage);
		System.out.println("[RvsecAnalysisClient] Filter package: " + filterPackage);

		// 1. Enumerate application classes filtered by app package
		Map<SootClass, List<SootMethod>> appClasses = extractClasses(filterPackage);
		System.out.println("[RvsecAnalysisClient] Application classes: " + appClasses.size());

		// 2. Load MOP signatures and resolve to SootMethods
		Set<MopMethod> mopSignatures = Collections.emptySet();
		Set<SootMethod> mopMethods = Collections.emptySet();
		if (mopDir != null) {
			mopSignatures = loadMopSignatures(mopDir);
			mopMethods = resolveMopInScene(mopSignatures);
			System.out.println("[RvsecAnalysisClient] MOP methods resolved: " + mopMethods.size());
		}

		// 3. Compute reachability via multi-source BFS on JGraphT graph
		CallGraph cg = Scene.v().getCallGraph();
		DefaultDirectedGraph<SootMethod, DefaultEdge> graph = buildJGraph(cg);
		System.out.println("[RvsecAnalysisClient] JGraphT graph: " + graph.vertexSet().size()
				+ " vertices, " + graph.edgeSet().size() + " edges");

		Set<SootMethod> entryPoints = getEntryPoints(output);
		System.out.println("[RvsecAnalysisClient] Entry points: " + entryPoints.size());

		Set<SootMethod> reachableSet = multiSourceBfs(graph, entryPoints);
		EdgeReversedGraph<SootMethod, DefaultEdge> reversed = new EdgeReversedGraph<>(graph);
		Set<SootMethod> reachesMopSet = multiSourceBfs(reversed, mopMethods);
		Set<SootMethod> directMopSet = findDirectMopCallers(graph, mopMethods);
		int directCgCount = directMopSet.size();

		// 3b. Bytecode-scan complement (BUG-INV-ANA-19): SPARK omits library
		// targets (java.security.*, javax.crypto.*) from the call graph, so
		// findDirectMopCallers cannot see app methods that literally invoke
		// MOP signatures on those classes. Walk every app method body and
		// match InvokeExpr against MopMethod (className, methodName) pairs —
		// independent of CG edges. Symmetric with reachesMopSet's transitive
		// completion in complementWithCallbacks.
		Set<SootMethod> directBcSet = findDirectMopCallersByBytecodeScan(appClasses, mopSignatures);
		Set<SootMethod> intersection = new HashSet<>(directMopSet);
		intersection.retainAll(directBcSet);
		directMopSet.addAll(directBcSet);
		System.out.println("[RvsecAnalysisClient] directlyReachesMop: " + directMopSet.size()
				+ " (CG: " + directCgCount + ", bytecode: " + directBcSet.size()
				+ ", intersection: " + intersection.size() + ")");

		// 4. Complement with lifecycle and listener callbacks
		complementWithCallbacks(output, reachableSet, reachesMopSet, directMopSet, graph, mopMethods);

		System.out.println("[RvsecAnalysisClient] Reachable: " + reachableSet.size()
				+ ", reachesMop: " + reachesMopSet.size()
				+ ", directlyReachesMop: " + directMopSet.size());

		// 5. Write JSON with reachability FIRST (survives timeout during WTG)
		SootClass mainActivity = output.getMainActivity();
		String appPackage = output.getAppPackageName();
		writeJson(outputPath, appPackage, mainActivity, appClasses, output,
				reachableSet, reachesMopSet, directMopSet, null, new HashMap<>());
		System.out.println("[RvsecAnalysisClient] Reachability JSON written (WTG pending): " + outputPath);

		// 6. Build WTG (may timeout on complex APKs — reachability already saved)
		WTG wtg = null;
		Map<String, Integer> windowNodeIds = new HashMap<>();
		try {
			WTGBuilder wtgBuilder = new WTGBuilder();
			wtgBuilder.build(output);
			WTGAnalysisOutput wtgAO = new WTGAnalysisOutput(output, wtgBuilder);
			wtg = wtgAO.getWTG();

			for (WTGNode node : wtg.getNodes()) {
				NObjectNode win = node.getWindow();
				windowNodeIds.put(win.getClassType().getName(), win.id);
			}

			// 7. Rewrite JSON with full data (reachability + WTG)
			writeJson(outputPath, appPackage, mainActivity, appClasses, output,
					reachableSet, reachesMopSet, directMopSet, wtg, windowNodeIds);
		} catch (Exception e) {
			System.out.println("[RvsecAnalysisClient] WTG construction failed: " + e.getMessage()
					+ " — JSON already contains reachability data");
		}

		System.out.println("[RvsecAnalysisClient] Analysis complete. File saved: " + outputPath);
	}

	// ========================================================================
	// MOP Loading
	// ========================================================================

	private String getMopDir() {
		String param = Configs.getClientParamCode("mopDir=");
		if (param == null) {
			System.out.println("[RvsecAnalysisClient] WARNING: no mopDir parameter. MOP reachability will be empty.");
			return null;
		}
		return param.substring("mopDir=".length());
	}

	private String getCodePackage() {
		String param = Configs.getClientParamCode("codePackage=");
		if (param == null) {
			return null;
		}
		return param.substring("codePackage=".length());
	}

	private Set<MopMethod> loadMopSignatures(String mopDir) {
		try {
			JavamopFacade facade = new JavamopFacade();
			Set<MopMethod> methods = facade.listUsedMethods(mopDir, false);
			System.out.println("[RvsecAnalysisClient] Loaded " + methods.size() + " MOP signatures from " + mopDir);
			return methods;
		} catch (MOPException e) {
			System.err.println("[RvsecAnalysisClient] ERROR loading MOP specs: " + e.getMessage());
			return Collections.emptySet();
		}
	}

	/**
	 * Resolve MOP signatures to SootMethods in the Scene.
	 * Matches by class+method name ONLY (no params) — consistent with MopFacade.
	 * All overloads are included: if Cipher.init is in a MOP spec, both
	 * init(int,Key) and init(int,Key,AlgorithmParameterSpec) become seeds.
	 */
	private Set<SootMethod> resolveMopInScene(Set<MopMethod> mopSignatures) {
		Set<SootMethod> resolved = new HashSet<>();
		for (SootClass cls : Scene.v().getClasses()) {
			for (SootMethod method : cls.getMethods()) {
				for (MopMethod mop : mopSignatures) {
					if (mop.getClassName().equals(cls.getName())
							&& mop.getName().equals(method.getName())) {
						resolved.add(method);
					}
				}
			}
		}
		return resolved;
	}

	// ========================================================================
	// Class/Method Enumeration
	// ========================================================================

	/**
	 * Enumerate application classes filtered by package prefix.
	 * Only classes whose fully-qualified name starts with filterPackage are
	 * included. Generated classes (R, R$*, BuildConfig) are excluded — they
	 * are not real app code and would inflate the coverage denominator.
	 */
	private Map<SootClass, List<SootMethod>> extractClasses(String filterPackage) {
		Map<SootClass, List<SootMethod>> result = new LinkedHashMap<>();
		int skipped = 0;
		for (SootClass cls : Scene.v().getApplicationClasses()) {
			if (!isAppClass(cls.getName(), filterPackage)) {
				skipped++;
				continue;
			}
			List<SootMethod> methods = new ArrayList<>(cls.getMethods());
			result.put(cls, methods);
		}
		System.out.println("[RvsecAnalysisClient] Filtered " + skipped
				+ " classes (libraries/generated) using package: " + filterPackage);
		return result;
	}

	/**
	 * Check if a fully-qualified class name belongs to the application package.
	 * Returns false for library classes (different package prefix) and for
	 * generated classes (R, R$*, BuildConfig) which inflate coverage denominator.
	 */
	// Package-private for unit testing
	static boolean isAppClass(String className, String filterPackage) {
		if (!className.startsWith(filterPackage)) {
			return false;
		}
		String suffix = className.substring(filterPackage.length());
		if (suffix.equals(".R") || suffix.startsWith(".R$") || suffix.equals(".BuildConfig")) {
			return false;
		}
		return true;
	}

	// ========================================================================
	// Entry Points
	// ========================================================================

	/**
	 * Collect entry points: public/protected methods of activity classes,
	 * lifecycle handlers, and event handlers from GATOR's analysis.
	 */
	private Set<SootMethod> getEntryPoints(GUIAnalysisOutput output) {
		Set<SootMethod> entryPoints = new HashSet<>();
		for (SootClass activity : output.getActivities()) {
			// Lifecycle handlers
			entryPoints.addAll(output.getLifecycleHandlers(activity));

			// Public/protected methods of activities
			for (SootMethod m : activity.getMethods()) {
				if (m.isPublic() || m.isProtected()) {
					entryPoints.add(m);
				}
			}
		}

		// Service entry points
		XMLParser xmlParser = XMLParser.Factory.getXMLParser();
		Iterator<String> serviceIt = xmlParser.getServices();
		while (serviceIt.hasNext()) {
			String className = serviceIt.next();
			SootClass sootClass = Scene.v().getSootClassUnsafe(className);
			if (sootClass == null) {
				System.out.println("[RvsecAnalysisClient] WARNING: Service class not found in Soot Scene: " + className);
				continue;
			}
			for (SootMethod m : sootClass.getMethods()) {
				String methodName = m.getName();
				// Service lifecycle methods
				if (methodName.equals("onCreate") || methodName.equals("onStartCommand") ||
					methodName.equals("onBind") || methodName.equals("onUnbind") ||
					methodName.equals("onRebind") || methodName.equals("onDestroy") ||
					methodName.equals("onHandleIntent")) {
					entryPoints.add(m);
				}
				// Public/protected methods
				if (m.isPublic() || m.isProtected()) {
					entryPoints.add(m);
				}
			}
		}

		// Receiver entry points
		Iterator<String> receiverIt = xmlParser.getReceivers();
		while (receiverIt.hasNext()) {
			String className = receiverIt.next();
			SootClass sootClass = Scene.v().getSootClassUnsafe(className);
			if (sootClass == null) {
				System.out.println("[RvsecAnalysisClient] WARNING: Receiver class not found in Soot Scene: " + className);
				continue;
			}
			for (SootMethod m : sootClass.getMethods()) {
				if (m.getName().equals("onReceive")) {
					entryPoints.add(m);
				}
				if (m.isPublic() || m.isProtected()) {
					entryPoints.add(m);
				}
			}
		}

		// Provider entry points
		Iterator<String> providerIt = xmlParser.getProviders();
		while (providerIt.hasNext()) {
			String className = providerIt.next();
			SootClass sootClass = Scene.v().getSootClassUnsafe(className);
			if (sootClass == null) {
				System.out.println("[RvsecAnalysisClient] WARNING: Provider class not found in Soot Scene: " + className);
				continue;
			}
			for (SootMethod m : sootClass.getMethods()) {
				String methodName = m.getName();
				// Provider lifecycle methods
				if (methodName.equals("onCreate") || methodName.equals("query") ||
					methodName.equals("insert") || methodName.equals("update") ||
					methodName.equals("delete") || methodName.equals("call") ||
					methodName.equals("openFile")) {
					entryPoints.add(m);
				}
				if (m.isPublic() || m.isProtected()) {
					entryPoints.add(m);
				}
			}
		}

		return entryPoints;
	}

	// ========================================================================
	// JGraphT Graph Construction
	// ========================================================================

	private DefaultDirectedGraph<SootMethod, DefaultEdge> buildJGraph(CallGraph cg) {
		DefaultDirectedGraph<SootMethod, DefaultEdge> graph =
				new DefaultDirectedGraph<>(DefaultEdge.class);

		Iterator<Edge> edges = cg.iterator();
		while (edges.hasNext()) {
			Edge edge = edges.next();
			SootMethod src = edge.src();
			SootMethod tgt = edge.tgt();
			// Filter self-loops
			if (!src.equals(tgt)) {
				graph.addVertex(src);
				graph.addVertex(tgt);
				graph.addEdge(src, tgt);
			}
		}
		return graph;
	}

	// ========================================================================
	// Multi-source BFS — O(V + E) per traversal
	// ========================================================================

	// Package-private and generic for unit testing with synthetic graphs
	static <V> Set<V> multiSourceBfs(
			org.jgrapht.Graph<V, DefaultEdge> graph,
			Set<V> seeds) {

		Set<V> visited = new HashSet<>();
		Queue<V> queue = new ArrayDeque<>();

		for (V seed : seeds) {
			if (graph.containsVertex(seed) && visited.add(seed)) {
				queue.add(seed);
			}
		}

		while (!queue.isEmpty()) {
			V current = queue.poll();
			for (DefaultEdge edge : graph.outgoingEdgesOf(current)) {
				V neighbor = graph.getEdgeTarget(edge);
				if (visited.add(neighbor)) {
					queue.add(neighbor);
				}
			}
		}
		return visited;
	}

	/**
	 * Find methods that directly call a MOP method (outgoing edge to MOP set).
	 */
	// Package-private and generic for unit testing with synthetic graphs
	static <V> Set<V> findDirectMopCallers(
			DefaultDirectedGraph<V, DefaultEdge> graph,
			Set<V> targetMethods) {

		Set<V> result = new HashSet<>();
		for (V method : graph.vertexSet()) {
			for (DefaultEdge edge : graph.outgoingEdgesOf(method)) {
				V target = graph.getEdgeTarget(edge);
				if (targetMethods.contains(target)) {
					result.add(method);
					break;
				}
			}
		}
		return result;
	}

	/**
	 * Bytecode-scan complement to {@link #findDirectMopCallers}.
	 *
	 * Walks each app method's body and inspects every {@link InvokeExpr},
	 * matching against MOP signatures by ({@code declaringClass.getName()},
	 * {@code methodRef.name()}) — the same FQN/name policy used by
	 * {@link #resolveMopInScene}. Independent of the call graph, so it
	 * captures app → library calls (e.g. {@code SecureRandom.nextInt}) that
	 * SPARK quarantines and therefore omits as CG edges (BUG-INV-ANA-19).
	 *
	 * Body retrieval is wrapped in try-catch ({@link RuntimeException},
	 * {@link OutOfMemoryError}) — same resilience policy as Flowgraph.java
	 * (FIX 2). A single corrupted method does not abort the pass.
	 *
	 * @param appClasses application classes (already filtered by package
	 *                   in {@link #extractClasses}); the caller universe.
	 * @param mopSignatures MOP signatures loaded from the .mop specs.
	 * @return app methods whose body contains a literal invocation of any
	 *         MOP signature, regardless of CG visibility.
	 */
	private Set<SootMethod> findDirectMopCallersByBytecodeScan(
			Map<SootClass, List<SootMethod>> appClasses,
			Set<MopMethod> mopSignatures) {

		Set<SootMethod> result = new HashSet<>();
		if (mopSignatures.isEmpty()) {
			return result;
		}

		// Build a fast lookup keyed by "fqClassName#methodName" — matches
		// resolveMopInScene's policy (class FQN + method name, ignoring
		// parameter overloads). Same MopMethod entry covers all overloads.
		Set<String> mopKeys = buildMopKeys(mopSignatures);

		int methodsScanned = 0;
		int bodiesSkipped = 0;
		for (Map.Entry<SootClass, List<SootMethod>> entry : appClasses.entrySet()) {
			for (SootMethod method : entry.getValue()) {
				methodsScanned++;
				if (!method.isConcrete()) {
					continue;
				}
				Body body;
				try {
					body = method.retrieveActiveBody();
				} catch (RuntimeException | OutOfMemoryError ex) {
					bodiesSkipped++;
					System.out.println("[RvsecAnalysisClient] WARN bytecode-scan skipped "
							+ method.getSignature() + ": " + ex.getMessage());
					continue;
				}
				if (body == null) {
					continue;
				}
				for (Unit unit : body.getUnits()) {
					if (!(unit instanceof Stmt)) {
						continue;
					}
					Stmt stmt = (Stmt) unit;
					if (!stmt.containsInvokeExpr()) {
						continue;
					}
					InvokeExpr ie = stmt.getInvokeExpr();
					SootMethodRef ref = ie.getMethodRef();
					if (ref == null) {
						continue;
					}
					if (matchesMopSignature(ref.getDeclaringClass().getName(), ref.getName(), mopKeys)) {
						result.add(method);
						break;
					}
				}
			}
		}
		System.out.println("[RvsecAnalysisClient] Bytecode scan: " + methodsScanned
				+ " methods scanned, " + bodiesSkipped + " body-retrieval skips, "
				+ result.size() + " direct MOP callers detected");
		return result;
	}

	/**
	 * Build the {@code "className#methodName"} key set used by the bytecode
	 * scanner to match {@link InvokeExpr} targets against MOP signatures.
	 *
	 * Same matching policy as {@link #resolveMopInScene}: FQN class +
	 * method name, ignoring parameter overloads. Package-private for unit
	 * tests that exercise the matching policy without a Soot Scene.
	 */
	static Set<String> buildMopKeys(Set<MopMethod> mopSignatures) {
		Set<String> keys = new HashSet<>();
		for (MopMethod mop : mopSignatures) {
			keys.add(mop.getClassName() + "#" + mop.getName());
		}
		return keys;
	}

	/**
	 * Test whether a given (className, methodName) pair matches any MOP
	 * signature in the precomputed {@code mopKeys} set.
	 *
	 * Package-private for unit tests; production code calls it implicitly
	 * via {@code mopKeys.contains(...)} after {@link #buildMopKeys}.
	 */
	static boolean matchesMopSignature(String className, String methodName, Set<String> mopKeys) {
		return mopKeys.contains(className + "#" + methodName);
	}

	// ========================================================================
	// Callback Complement
	// ========================================================================

	/**
	 * Mark lifecycle and listener callbacks as reachable. These methods are
	 * invoked by the Android framework at runtime but may not appear in the
	 * call graph.
	 */
	private void complementWithCallbacks(
			GUIAnalysisOutput output,
			Set<SootMethod> reachableSet,
			Set<SootMethod> reachesMopSet,
			Set<SootMethod> directMopSet,
			DefaultDirectedGraph<SootMethod, DefaultEdge> graph,
			Set<SootMethod> mopMethods) {

		Set<SootMethod> callbacks = new HashSet<>();

		// Lifecycle handlers for all activities
		for (SootClass activity : output.getActivities()) {
			callbacks.addAll(output.getLifecycleHandlers(activity));
		}

		// Event handlers from all GUI objects (widgets with listeners)
		Set<NNode> visited = new HashSet<>();
		for (SootClass activity : output.getActivities()) {
			Set<NNode> roots = output.getActivityRoots(activity);
			for (NNode root : roots) {
				collectEventHandlers(output, root, callbacks, visited);
			}
		}

		// Add Service/Receiver/Provider lifecycle methods to callbacks
		XMLParser xmlParser = XMLParser.Factory.getXMLParser();
		for (Iterator<String> it = xmlParser.getServices(); it.hasNext(); ) {
			SootClass sc = Scene.v().getSootClassUnsafe(it.next());
			if (sc == null) continue;
			for (SootMethod m : sc.getMethods()) {
				String name = m.getName();
				if (name.equals("onCreate") || name.equals("onStartCommand") ||
					name.equals("onBind") || name.equals("onUnbind") ||
					name.equals("onRebind") || name.equals("onDestroy") ||
					name.equals("onHandleIntent")) {
					callbacks.add(m);
				}
			}
		}
		for (Iterator<String> it = xmlParser.getReceivers(); it.hasNext(); ) {
			SootClass sc = Scene.v().getSootClassUnsafe(it.next());
			if (sc == null) continue;
			for (SootMethod m : sc.getMethods()) {
				if (m.getName().equals("onReceive")) {
					callbacks.add(m);
				}
			}
		}
		for (Iterator<String> it = xmlParser.getProviders(); it.hasNext(); ) {
			SootClass sc = Scene.v().getSootClassUnsafe(it.next());
			if (sc == null) continue;
			for (SootMethod m : sc.getMethods()) {
				String name = m.getName();
				if (name.equals("onCreate") || name.equals("query") ||
					name.equals("insert") || name.equals("update") ||
					name.equals("delete") || name.equals("call") ||
					name.equals("openFile")) {
					callbacks.add(m);
				}
			}
		}

		// Mark callbacks as reachable and propagate MOP flags
		for (SootMethod callback : callbacks) {
			reachableSet.add(callback);
			// Check if this callback can reach MOP via graph
			if (graph.containsVertex(callback)) {
				for (DefaultEdge edge : graph.outgoingEdgesOf(callback)) {
					SootMethod target = graph.getEdgeTarget(edge);
					if (mopMethods.contains(target)) {
						directMopSet.add(callback);
						reachesMopSet.add(callback);
						break;
					}
					if (reachesMopSet.contains(target)) {
						reachesMopSet.add(callback);
					}
				}
			}
		}
	}

	private void collectEventHandlers(GUIAnalysisOutput output, NNode node,
			Set<SootMethod> handlers, Set<NNode> visited) {
		if (!visited.add(node)) {
			return;
		}
		if (node instanceof NObjectNode) {
			NObjectNode objNode = (NObjectNode) node;
			Map<EventType, Set<SootMethod>> events = output.getAllEventsAndTheirHandlers(objNode);
			for (Set<SootMethod> methods : events.values()) {
				handlers.addAll(methods);
			}
		}
		for (NNode child : node.getChildren()) {
			collectEventHandlers(output, child, handlers, visited);
		}
	}

	// ========================================================================
	// Window Extraction
	// ========================================================================

	/**
	 * Build window data from GATOR's analysis. Includes activities, dialogs,
	 * and options menus. Each window has widgets with listeners, text, hint.
	 */
	private List<Map<String, Object>> extractWindows(
			GUIAnalysisOutput output, Map<String, Integer> windowNodeIds, WTG wtg) {

		List<Map<String, Object>> windows = new ArrayList<>();
		Set<Integer> extractedIds = new HashSet<>();
		int fallbackId = 100000; // Fallback for windows not in WTG

		SootClass mainActivity = output.getMainActivity();

		// Activity windows — use NObjectNode.id from WTG for consistency
		// with transition sourceId/targetId
		for (SootClass activity : output.getActivities()) {
			Map<String, Object> window = new LinkedHashMap<>();
			Integer nodeId = windowNodeIds.get(activity.getName());
			window.put("id", nodeId != null ? nodeId : fallbackId++);
			window.put("name", activity.getName());
			window.put("type", "ACTIVITY");
			window.put("isMain", activity.equals(mainActivity));

			List<Map<String, Object>> widgets = new ArrayList<>();
			Set<NNode> roots = output.getActivityRoots(activity);
			Set<NNode> widgetVisited = new HashSet<>();
			for (NNode root : roots) {
				collectWidgets(output, root, widgets, widgetVisited);
			}
			window.put("widgets", widgets);
			windows.add(window);
			extractedIds.add((int) window.get("id"));
		}

		// Dialog windows
		for (NDialogNode dialog : output.getDialogs()) {
			Map<String, Object> window = new LinkedHashMap<>();
			Integer nodeId = windowNodeIds.get(dialog.getClassType().getName());
			window.put("id", nodeId != null ? nodeId : dialog.id);
			window.put("name", dialog.getClassType().getName());
			window.put("type", "DIALOG");
			window.put("isMain", false);

			List<Map<String, Object>> widgets = new ArrayList<>();
			Set<NNode> roots = output.getDialogRoots(dialog);
			Set<NNode> dialogVisited = new HashSet<>();
			for (NNode root : roots) {
				collectWidgets(output, root, widgets, dialogVisited);
			}
			window.put("widgets", widgets);
			windows.add(window);
			extractedIds.add((int) window.get("id"));
		}

		// Options menus — use the menu node's own ID
		for (SootClass activity : output.getActivities()) {
			NOptionsMenuNode menu = output.getOptionsMenu(activity);
			if (menu != null) {
				Map<String, Object> window = new LinkedHashMap<>();
				String menuName = activity.getName() + "#OptionsMenu";
				Integer nodeId = windowNodeIds.get(menuName);
				window.put("id", nodeId != null ? nodeId : menu.id);
				window.put("name", menuName);
				window.put("type", "OPTIONSMENU");
				window.put("isMain", false);
				window.put("widgets", Collections.emptyList());
				windows.add(window);
				extractedIds.add((int) window.get("id"));
			}
		}

		// Catch-all: WTG nodes not captured above (context menus, fragments, etc.)
		for (WTGNode node : wtg.getNodes()) {
			NObjectNode win = node.getWindow();
			if (isGatorStubNode(win)) continue;
			if (extractedIds.contains(win.id)) continue;

			Map<String, Object> window = new LinkedHashMap<>();
			window.put("id", win.id);
			window.put("name", win.getClassType().getName());

			// Determine type from NObjectNode subclass
			String type;
			if (win instanceof NDialogNode) {
				type = "DIALOG";
			} else if (win instanceof NOptionsMenuNode) {
				type = "OPTIONSMENU";
			} else {
				type = "ACTIVITY";
			}
			window.put("type", type);
			window.put("isMain", false);
			window.put("widgets", Collections.emptyList());
			windows.add(window);
			extractedIds.add(win.id);

			System.out.println("[RvsecAnalysisClient] Added WTG-only window: "
					+ win.getClassType().getName() + " (id=" + win.id + ", type=" + type + ")");
		}

		return windows;
	}

	private void collectWidgets(GUIAnalysisOutput output, NNode node,
			List<Map<String, Object>> widgets, Set<NNode> visited) {
		if (!visited.add(node)) {
			return;
		}
		if (node instanceof NObjectNode) {
			NObjectNode objNode = (NObjectNode) node;
			Map<String, Object> widget = new LinkedHashMap<>();

			int widgetId = objNode.id;
			String idName = "";
			if (objNode.idNode != null) {
				widgetId = objNode.idNode.getIdValue();
				idName = objNode.idNode.getIdName();
			}

			widget.put("id", widgetId);
			widget.put("idName", idName != null ? idName : "");
			widget.put("type", objNode.getClassType().getName());

			// Text and hint from PropertyManager
			Set<String> texts = PropertyManager.v().getTextsOrTitlesOfView(objNode);
			widget.put("text", texts.isEmpty() ? "" : texts.iterator().next());

			Set<String> hints = PropertyManager.v().getHintOfView(objNode);
			widget.put("hint", hints.isEmpty() ? "" : hints.iterator().next());

			// inputType and entries will be enriched from XML (Task Group 3)
			widget.put("inputType", "");
			widget.put("entries", Collections.emptyList());

			// Event listeners
			List<Map<String, Object>> listeners = new ArrayList<>();
			Map<EventType, Set<SootMethod>> events = output.getAllEventsAndTheirHandlers(objNode);
			for (Map.Entry<EventType, Set<SootMethod>> entry : events.entrySet()) {
				String eventType = entry.getKey().toString().toLowerCase();
				for (SootMethod handler : entry.getValue()) {
					Map<String, Object> listener = new LinkedHashMap<>();
					listener.put("eventType", eventType);
					listener.put("handler", handler.getSignature());
					listeners.add(listener);
				}
			}
			widget.put("listeners", listeners);

			widgets.add(widget);
		}

		for (NNode child : node.getChildren()) {
			collectWidgets(output, child, widgets, visited);
		}
	}

	// ========================================================================
	// InputType and Entries from Decoded XML (Task Group 3)
	// ========================================================================

	/**
	 * Enrich widget data with inputType and entries from decoded layout XMLs.
	 * GATOR already decoded the APK with apktool; resources are at
	 * Configs.resourceLocation.
	 */
	private void enrichFromXml(List<Map<String, Object>> windows) {
		String resDir = Configs.resourceLocation;
		if (resDir == null || resDir.isEmpty()) {
			return;
		}

		// Parse arrays.xml for @array/ references
		Map<String, List<String>> arrays = parseArraysXml(resDir);

		// For each window, parse its layout XML
		for (Map<String, Object> window : windows) {
			String type = (String) window.get("type");
			if (!"ACTIVITY".equals(type)) continue;

			@SuppressWarnings("unchecked")
			List<Map<String, Object>> widgets = (List<Map<String, Object>>) window.get("widgets");
			if (widgets == null || widgets.isEmpty()) continue;

			// Find layout files in res/layout/
			File layoutDir = new File(resDir, "layout");
			if (!layoutDir.exists()) continue;

			File[] layoutFiles = layoutDir.listFiles((dir, name) -> name.endsWith(".xml"));
			if (layoutFiles == null) continue;

			// Build a map of idName -> widget for quick lookup
			Map<String, Map<String, Object>> widgetByIdName = new HashMap<>();
			for (Map<String, Object> widget : widgets) {
				String idName = (String) widget.get("idName");
				if (idName != null && !idName.isEmpty()) {
					widgetByIdName.put(idName, widget);
				}
			}

			// Parse each layout file looking for inputType and entries attributes
			for (File layoutFile : layoutFiles) {
				enrichWidgetsFromLayout(layoutFile, widgetByIdName, arrays);
			}
		}
	}

	// Package-private for unit testing
	void enrichWidgetsFromLayout(
			File layoutFile,
			Map<String, Map<String, Object>> widgetByIdName,
			Map<String, List<String>> arrays) {
		try {
			DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
			DocumentBuilder builder = factory.newDocumentBuilder();
			Document doc = builder.parse(layoutFile);
			enrichFromElement(doc.getDocumentElement(), widgetByIdName, arrays);
		} catch (Exception e) {
			// Graceful degradation — skip malformed XML
		}
	}

	private void enrichFromElement(
			Element elem,
			Map<String, Map<String, Object>> widgetByIdName,
			Map<String, List<String>> arrays) {

		// Match element to widget by android:id
		String id = elem.getAttribute("android:id");
		if (id != null && id.startsWith("@id/")) {
			String idName = id.substring("@id/".length());
			Map<String, Object> widget = widgetByIdName.get(idName);
			if (widget != null) {
				// inputType
				String inputType = elem.getAttribute("android:inputType");
				if (inputType != null && !inputType.isEmpty()) {
					// Handle pipe-separated flags, take first value
					if (inputType.contains("|")) {
						inputType = inputType.split("\\|")[0];
					}
					widget.put("inputType", inputType);
				}

				// entries (@array/name reference)
				String entries = elem.getAttribute("android:entries");
				if (entries != null && entries.startsWith("@array/")) {
					String arrayName = entries.substring("@array/".length());
					List<String> items = arrays.getOrDefault(arrayName, Collections.emptyList());
					widget.put("entries", items);
				}
			}
		}

		// Recurse into child elements
		NodeList children = elem.getChildNodes();
		for (int i = 0; i < children.getLength(); i++) {
			if (children.item(i) instanceof Element) {
				enrichFromElement((Element) children.item(i), widgetByIdName, arrays);
			}
		}
	}

	// Package-private for unit testing
	Map<String, List<String>> parseArraysXml(String resDir) {
		Map<String, List<String>> arrays = new HashMap<>();
		File arraysFile = new File(resDir, "values/arrays.xml");
		if (!arraysFile.exists()) return arrays;

		try {
			DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
			DocumentBuilder builder = factory.newDocumentBuilder();
			Document doc = builder.parse(arraysFile);

			NodeList arrayNodes = doc.getElementsByTagName("string-array");
			for (int i = 0; i < arrayNodes.getLength(); i++) {
				Element arrayElem = (Element) arrayNodes.item(i);
				String name = arrayElem.getAttribute("name");
				List<String> items = new ArrayList<>();

				NodeList itemNodes = arrayElem.getElementsByTagName("item");
				for (int j = 0; j < itemNodes.getLength(); j++) {
					String value = itemNodes.item(j).getTextContent().trim();
					// Resolve @string/ references
					if (value.startsWith("@string/")) {
						String resolved = resolveStringReference(resDir, value.substring("@string/".length()));
						items.add(resolved != null ? resolved : value);
					} else {
						items.add(value);
					}
				}
				arrays.put(name, items);
			}
		} catch (Exception e) {
			// Graceful degradation
		}
		return arrays;
	}

	// Package-private for unit testing
	String resolveStringReference(String resDir, String stringName) {
		File stringsFile = new File(resDir, "values/strings.xml");
		if (!stringsFile.exists()) return null;
		try {
			DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
			DocumentBuilder builder = factory.newDocumentBuilder();
			Document doc = builder.parse(stringsFile);

			NodeList strings = doc.getElementsByTagName("string");
			for (int i = 0; i < strings.getLength(); i++) {
				Element elem = (Element) strings.item(i);
				if (stringName.equals(elem.getAttribute("name"))) {
					return elem.getTextContent().trim();
				}
			}
		} catch (Exception e) {
			// Graceful degradation
		}
		return null;
	}

	// ========================================================================
	// JSON Output with JsonWriter (incremental flush)
	// ========================================================================

	private void writeJson(
			String outputPath,
			String appPackage,
			SootClass mainActivity,
			Map<SootClass, List<SootMethod>> appClasses,
			GUIAnalysisOutput output,
			Set<SootMethod> reachableSet,
			Set<SootMethod> reachesMopSet,
			Set<SootMethod> directMopSet,
			WTG wtg,
			Map<String, Integer> windowNodeIds) {

		try (JsonWriter w = new JsonWriter(new FileWriter(outputPath))) {
			w.setIndent("  ");
			w.beginObject();

			// Metadata
			w.name("package").value(appPackage != null ? appPackage : "");
			w.name("mainActivity").value(
					mainActivity != null ? mainActivity.getName() : "");

			// Section 1: reachability (coverage denominator — most critical)
			w.name("reachability");
			writeReachability(w, appClasses, output, reachableSet, reachesMopSet, directMopSet);
			w.flush();

			// Section 2: windows (requires WTG)
			if (wtg != null) {
				List<Map<String, Object>> windows = extractWindows(output, windowNodeIds, wtg);
				enrichFromXml(windows);
				w.name("windows");
				writeWindows(w, windows);
				w.flush();
			} else {
				w.name("windows");
				w.beginArray().endArray();
				w.flush();
			}

			// Section 3: transitions (requires WTG)
			if (wtg != null) {
				w.name("transitions");
				writeTransitions(w, wtg);
				w.flush();
			} else {
				w.name("transitions");
				w.beginArray().endArray();
				w.flush();
			}

			// Section 4: components (activities, services, receivers, providers)
			w.name("components");
			writeComponents(w, reachesMopSet, output.getActivities(), mainActivity);
			w.flush();

			w.endObject();
		} catch (IOException e) {
			System.err.println("[RvsecAnalysisClient] ERROR writing JSON: " + e.getMessage());
			e.printStackTrace();
		}
	}

	private void writeReachability(
			JsonWriter w,
			Map<SootClass, List<SootMethod>> appClasses,
			GUIAnalysisOutput output,
			Set<SootMethod> reachableSet,
			Set<SootMethod> reachesMopSet,
			Set<SootMethod> directMopSet) throws IOException {

		Set<SootClass> activities = output.getActivities();
		SootClass mainActivity = output.getMainActivity();

		// Build component name sets for type resolution
		XMLParser xmlParser = XMLParser.Factory.getXMLParser();
		Set<String> serviceNames = new HashSet<>();
		for (Iterator<String> it = xmlParser.getServices(); it.hasNext(); ) serviceNames.add(it.next());
		Set<String> receiverNames = new HashSet<>();
		for (Iterator<String> it = xmlParser.getReceivers(); it.hasNext(); ) receiverNames.add(it.next());
		Set<String> providerNames = new HashSet<>();
		for (Iterator<String> it = xmlParser.getProviders(); it.hasNext(); ) providerNames.add(it.next());

		w.beginArray();
		for (Map.Entry<SootClass, List<SootMethod>> entry : appClasses.entrySet()) {
			SootClass cls = entry.getKey();
			List<SootMethod> methods = entry.getValue();

			w.beginObject();
			w.name("className").value(cls.getName());
			String componentType = null;
			if (activities.contains(cls)) {
				componentType = "activity";
			} else if (serviceNames.contains(cls.getName())) {
				componentType = "service";
			} else if (receiverNames.contains(cls.getName())) {
				componentType = "receiver";
			} else if (providerNames.contains(cls.getName())) {
				componentType = "provider";
			}
			w.name("componentType").value(componentType);
			w.name("isMain").value(cls.equals(mainActivity));

			w.name("methods");
			w.beginArray();
			for (SootMethod method : methods) {
				w.beginObject();
				w.name("name").value(method.getName());
				w.name("signature").value(method.getSignature());
				w.name("reachable").value(reachableSet.contains(method));
				w.name("reachesMop").value(reachesMopSet.contains(method));
				w.name("directlyReachesMop").value(directMopSet.contains(method));
				w.endObject();
			}
			w.endArray();

			w.endObject();
		}
		w.endArray();
	}

	private void writeWindows(JsonWriter w, List<Map<String, Object>> windows) throws IOException {
		w.beginArray();
		for (Map<String, Object> window : windows) {
			w.beginObject();
			w.name("id").value((int) window.get("id"));
			w.name("name").value((String) window.get("name"));
			w.name("type").value((String) window.get("type"));
			w.name("isMain").value((boolean) window.get("isMain"));

			w.name("widgets");
			w.beginArray();
			@SuppressWarnings("unchecked")
			List<Map<String, Object>> widgets = (List<Map<String, Object>>) window.get("widgets");
			for (Map<String, Object> widget : widgets) {
				writeWidget(w, widget);
			}
			w.endArray();

			w.endObject();
		}
		w.endArray();
	}

	private void writeWidget(JsonWriter w, Map<String, Object> widget) throws IOException {
		w.beginObject();
		w.name("id").value((int) widget.get("id"));
		w.name("idName").value((String) widget.get("idName"));
		w.name("type").value((String) widget.get("type"));
		w.name("text").value((String) widget.get("text"));
		w.name("hint").value((String) widget.get("hint"));
		w.name("inputType").value((String) widget.get("inputType"));

		w.name("entries");
		w.beginArray();
		@SuppressWarnings("unchecked")
		List<String> entries = (List<String>) widget.get("entries");
		for (String entry : entries) {
			w.value(entry);
		}
		w.endArray();

		w.name("listeners");
		w.beginArray();
		@SuppressWarnings("unchecked")
		List<Map<String, Object>> listeners = (List<Map<String, Object>>) widget.get("listeners");
		for (Map<String, Object> listener : listeners) {
			w.beginObject();
			w.name("eventType").value((String) listener.get("eventType"));
			w.name("handler").value((String) listener.get("handler"));
			w.endObject();
		}
		w.endArray();

		w.endObject();
	}

	private void writeComponents(JsonWriter w, Set<SootMethod> reachesMopSet,
			Set<SootClass> activities, SootClass mainActivity) throws IOException {
		XMLParser xmlParser = XMLParser.Factory.getXMLParser();
		Map<String, Set<IntentFilter>> allFilters = IntentFilterManager.v().getAllFilters();

		w.beginObject();

		// Write activities (first — most important for triggering)
		w.name("activities");
		w.beginArray();
		for (SootClass activity : activities) {
			String className = activity.getName();
			boolean isMain = activity.equals(mainActivity);
			writeComponentEntry(w, className, activity, allFilters, reachesMopSet, xmlParser,
					new String[]{"onCreate", "onStart", "onResume", "onPause", "onStop", "onDestroy", "onRestart"}, isMain);
		}
		w.endArray();

		// Write receivers
		w.name("receivers");
		w.beginArray();
		for (Iterator<String> it = xmlParser.getReceivers(); it.hasNext(); ) {
			String className = it.next();
			SootClass sc = Scene.v().getSootClassUnsafe(className);
			writeComponentEntry(w, className, sc, allFilters, reachesMopSet, xmlParser,
					new String[]{"onReceive"}, false);
		}
		w.endArray();

		// Write services
		w.name("services");
		w.beginArray();
		for (Iterator<String> it = xmlParser.getServices(); it.hasNext(); ) {
			String className = it.next();
			SootClass sc = Scene.v().getSootClassUnsafe(className);
			writeComponentEntry(w, className, sc, allFilters, reachesMopSet, xmlParser,
					new String[]{"onCreate", "onStartCommand", "onBind", "onUnbind", "onRebind", "onDestroy", "onHandleIntent"}, false);
		}
		w.endArray();

		// Write providers
		w.name("providers");
		w.beginArray();
		for (Iterator<String> it = xmlParser.getProviders(); it.hasNext(); ) {
			String className = it.next();
			SootClass sc = Scene.v().getSootClassUnsafe(className);
			writeProviderEntry(w, className, sc, reachesMopSet, xmlParser,
					new String[]{"onCreate", "query", "insert", "update", "delete", "call", "openFile"});
		}
		w.endArray();

		w.endObject();
	}

	private void writeComponentEntry(JsonWriter w, String className, SootClass sc,
			Map<String, Set<IntentFilter>> allFilters, Set<SootMethod> reachesMopSet,
			XMLParser xmlParser, String[] lifecycleMethodNames, boolean isMain) throws IOException {
		if (sc == null) return;

		w.beginObject();
		w.name("className").value(className);
		w.name("isMain").value(isMain);

		// Intent filters
		w.name("intentFilters");
		w.beginArray();
		Set<IntentFilter> filters = allFilters.get(className);
		if (filters != null) {
			for (IntentFilter filter : filters) {
				w.beginObject();
				w.name("actions");
				w.beginArray();
				for (String action : filter.getActions()) {
					w.value(action);
				}
				w.endArray();
				w.name("categories");
				w.beginArray();
				for (String category : filter.getCategories()) {
					w.value(category);
				}
				w.endArray();
				w.endObject();
			}
		}
		w.endArray();

		w.name("exported").value(xmlParser.isComponentExported(className));

		// MOP reachability
		List<String> mopMethods = new ArrayList<>();
		boolean reachesMop = false;
		for (SootMethod m : sc.getMethods()) {
			String methodName = m.getName();
			for (String lifecycle : lifecycleMethodNames) {
				if (methodName.equals(lifecycle) && reachesMopSet.contains(m)) {
					reachesMop = true;
					mopMethods.add(m.getSignature());
				}
			}
		}
		w.name("reachesMop").value(reachesMop);
		w.name("mopMethods");
		w.beginArray();
		for (String sig : mopMethods) {
			w.value(sig);
		}
		w.endArray();

		w.endObject();
	}

	private void writeProviderEntry(JsonWriter w, String className, SootClass sc,
			Set<SootMethod> reachesMopSet, XMLParser xmlParser,
			String[] lifecycleMethodNames) throws IOException {
		if (sc == null) return;

		w.beginObject();
		w.name("className").value(className);
		w.name("isMain").value(false);
		w.name("authorities").value(xmlParser.getProviderAuthorities(className));
		w.name("exported").value(xmlParser.isComponentExported(className));

		// MOP reachability
		List<String> mopMethods = new ArrayList<>();
		boolean reachesMop = false;
		for (SootMethod m : sc.getMethods()) {
			String methodName = m.getName();
			for (String lifecycle : lifecycleMethodNames) {
				if (methodName.equals(lifecycle) && reachesMopSet.contains(m)) {
					reachesMop = true;
					mopMethods.add(m.getSignature());
				}
			}
		}
		w.name("reachesMop").value(reachesMop);
		w.name("mopMethods");
		w.beginArray();
		for (String sig : mopMethods) {
			w.value(sig);
		}
		w.endArray();

		w.endObject();
	}

	private boolean isGatorStubNode(NObjectNode node) {
		String className = node.getClassType().getName();
		return className.startsWith("presto.android.gui.stubs.");
	}

	private void writeTransitions(JsonWriter w, WTG wtg) throws IOException {
		w.beginArray();
		for (WTGNode node : wtg.getNodes()) {
			NObjectNode sourceWindow = node.getWindow();
			// Skip GATOR synthetic nodes (e.g. fake launcher)
			if (isGatorStubNode(sourceWindow)) continue;
			int sourceId = sourceWindow.id;

			Collection<WTGEdge> outEdges = node.getOutEdges();
			for (WTGEdge edge : outEdges) {
				NObjectNode targetWindow = edge.getTargetNode().getWindow();
				// Skip transitions to GATOR synthetic nodes
				if (isGatorStubNode(targetWindow)) continue;
				int targetId = targetWindow.id;

				w.beginObject();
				w.name("sourceId").value(sourceId);
				w.name("targetId").value(targetId);

				w.name("events");
				w.beginArray();
				for (presto.android.gui.wtg.EventHandler handler : edge.getWTGHandlers()) {
					w.beginObject();
					w.name("type").value(handler.getEvent().toString().toLowerCase());
					w.name("handler").value(
							handler.getEventHandler() != null
									? handler.getEventHandler().getSignature()
									: "");

					if (handler.getWidget() != null) {
						NObjectNode widget = handler.getWidget();
						w.name("widgetId").value(
								widget.idNode != null ? widget.idNode.getIdValue() : widget.id);
						w.name("widgetClass").value(widget.getClassType().getName());
						w.name("widgetName").value(
								widget.idNode != null ? widget.idNode.getIdName() : "");
					} else {
						w.name("widgetId").value(0);
						w.name("widgetClass").value("");
						w.name("widgetName").value("");
					}

					w.endObject();
				}
				w.endArray();

				w.endObject();
			}
		}
		w.endArray();
	}
}
