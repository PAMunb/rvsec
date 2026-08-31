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

import br.unb.cic.mop.extractor.model.MopMethod;
import presto.android.Configs;
import presto.android.gui.PropertyManager;
import presto.android.gui.GUIAnalysisClient;
import presto.android.gui.GUIAnalysisOutput;
import presto.android.gui.wtg.intent.IntentFilter;
import presto.android.gui.wtg.intent.IntentFilterManager;
import presto.android.gui.wtg.util.PatternMatcher;
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
import soot.SootField;
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
		String targetsFile = getTargetsFile();
		String outputPath = Configs.pathoutfilename;

		// Resolve the package to filter classes: prefer codePackage clientParam
		// (detected by Python-side PackageDetector via Androguard component analysis),
		// fall back to manifest package from AndroidManifest.xml
		String codePackage = getCodePackage();
		String manifestPackage = output.getAppPackageName();
		String filterPackage = (codePackage != null) ? codePackage : manifestPackage;

		// The Python CLI enforces the mutex between --mop-dir and --targets-file,
		// but defend against direct gator-jar callers passing both client params.
		if (mopDir != null && targetsFile != null) {
			throw new IllegalStateException(
					"Both 'mopDir' and 'targetsFile' client params were provided; "
					+ "they are mutually exclusive (INV-ANA-33). mopDir=" + mopDir
					+ " targetsFile=" + targetsFile);
		}

		System.out.println("[RvsecAnalysisClient] Starting unified analysis");
		System.out.println("[RvsecAnalysisClient] MOP dir: " + mopDir);
		System.out.println("[RvsecAnalysisClient] Targets file: " + targetsFile);
		System.out.println("[RvsecAnalysisClient] Output: " + outputPath);
		System.out.println("[RvsecAnalysisClient] Code package: " + codePackage);
		System.out.println("[RvsecAnalysisClient] Manifest package: " + manifestPackage);
		System.out.println("[RvsecAnalysisClient] Filter package: " + filterPackage);

		// 1. Enumerate application classes filtered by app package
		Map<SootClass, List<SootMethod>> appClasses = extractClasses(filterPackage);
		System.out.println("[RvsecAnalysisClient] Application classes: " + appClasses.size());

		// 2. Load and resolve target methods through the decomposed pipeline:
		//    TargetMethodSource -> TargetResolver -> Scene SootMethods.
		Set<presto.android.gui.clients.target.TargetMethod> targetSpecs =
				Collections.emptySet();
		Set<SootMethod> targetMethods = Collections.emptySet();
		// One matcher for the whole run: it owns the resolved-owner cache that both match
		// points read, so the Scene is touched once per declared owner rather than once per
		// match point.
		presto.android.gui.clients.target.TargetMatching matching =
				new presto.android.gui.clients.target.TargetMatching();
		if (targetsFile != null) {
			targetSpecs = new presto.android.gui.clients.target.SignatureFileTargetSource(
					java.nio.file.Paths.get(targetsFile)).load();
			long resolveStart = System.currentTimeMillis();
			targetMethods = presto.android.gui.clients.target.TargetResolver
					.resolveInScene(targetSpecs, matching);
			System.out.println("[RvsecAnalysisClient] Targets resolved from file: "
					+ targetMethods.size() + " (resolveInScene: "
					+ (System.currentTimeMillis() - resolveStart) + " ms)");
		} else if (mopDir != null) {
			targetSpecs = new presto.android.gui.clients.target.MopSpecsTargetSource(mopDir).load();
			// Timed because widening the owner predicate removes the equals(fqn) fast-reject
			// from a Scene.getClasses() x methods x targets loop (NFR04 cost bound).
			long resolveStart = System.currentTimeMillis();
			targetMethods = presto.android.gui.clients.target.TargetResolver
					.resolveInScene(targetSpecs, matching);
			System.out.println("[RvsecAnalysisClient] MOP methods resolved: "
					+ targetMethods.size() + " (resolveInScene: "
					+ (System.currentTimeMillis() - resolveStart) + " ms)");
		}

		// 3. Reachability pipeline (BFS + bytecode-scan + callback complement)
		//    encapsulated in ReachabilityEngine. The ReachabilityIndex it
		//    publishes is immutable — downstream JSON writing reads but does
		//    not mutate reachability state (precondition for INV-ANA-30,
		//    enforced in C1e when JsonReportWriter becomes pure).
		presto.android.gui.clients.reach.ReachabilityIndex index =
				new presto.android.gui.clients.reach.ReachabilityEngine(
						output, appClasses, targetMethods, targetSpecs, matching).run();

		// 4. Build the per-node enricher. The inline writer consults it for
		//    each method/widget/transition/component rather than reading the
		//    raw ReachabilityIndex — C1e enforces this as INV-ANA-30 (the
		//    writer's purity gate) and C3 fills in widget/transition payloads
		//    without modifying the writer.
		SootClass mainActivity = output.getMainActivity();
		String appPackage = output.getAppPackageName();
		// The enricher also carries the run's provenance into the artefact: the effective
		// key, where it came from, and the compiled universe under it (INV-ANA-66). Nothing
		// downstream can recover any of the three from a stored file otherwise.
		presto.android.gui.clients.reach.ReachabilityEnricher enricher =
				new presto.android.gui.clients.reach.ReachabilityEnricher(
						index,
						appPackage,
						codePackage,
						mainActivity != null ? mainActivity.getName() : null,
						getCodePackageSource(),
						countClassDefsUnderKey(filterPackage));

		// 5. Write JSON with reachability FIRST (survives timeout during WTG).
		//    This write claims completeness only when it is the run's last one,
		//    which is the case exactly when WTG is skipped by client parameter:
		//    the client then returns right after this write and nothing a kill
		//    could land in runs afterwards. With WTG enabled the second write
		//    (post-WTG) overwrites the file and emits the sentinel then, so a
		//    run killed inside WTG construction leaves reachability on disk with
		//    NO sentinel — a partial sample the parser and the gh91 predicate
		//    both refuse to count as finished (INV-ANA-31).
		boolean wtgSkipped = skipWtg();
		presto.android.gui.clients.json.JsonReportWriter writer =
				new presto.android.gui.clients.json.JsonReportWriter(enricher);
		try {
			List<Map<String, Object>> preWtgWindows = prepareWindows(output, new HashMap<>(), null);
			writer.write(outputPath, wtgSkipped, appPackage, mainActivity, appClasses, output,
					preWtgWindows, null);
		} catch (IOException e) {
			System.err.println("[RvsecAnalysisClient] ERROR writing pre-WTG JSON: " + e.getMessage());
			e.printStackTrace();
		}
		System.out.println("[RvsecAnalysisClient] Reachability JSON written (WTG pending): " + outputPath);

		// 6. Build WTG (may timeout on complex APKs — reachability already saved).
		//    skipWtg client param short-circuits this for known-slow APKs;
		//    the partial JSON already has windows[] populated (task 2.1).
		if (wtgSkipped) {
			System.out.println("[RvsecAnalysisClient] WTG skipped by client parameter");
			System.out.println("[RvsecAnalysisClient] Analysis complete. File saved: " + outputPath);
			return;
		}
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

			// 7. Rewrite JSON with full data (reachability + WTG). This
			//    overwrites the pre-WTG file and ends with the "complete":true
			//    sentinel after fsync, signaling success to the parser.
			List<Map<String, Object>> postWtgWindows = prepareWindows(output, windowNodeIds, wtg);
			writer.write(outputPath, true, appPackage, mainActivity, appClasses, output,
					postWtgWindows, wtg);
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
			return null;
		}
		return param.substring("mopDir=".length());
	}

	private String getTargetsFile() {
		String param = Configs.getClientParamCode("targetsFile=");
		if (param == null) {
			return null;
		}
		return param.substring("targetsFile=".length());
	}

	private String getCodePackage() {
		String param = Configs.getClientParamCode("codePackage=");
		if (param == null) {
			return null;
		}
		return param.substring("codePackage=".length());
	}

	/**
	 * Origin of the scope key: {@code manifest}, {@code manifest-neutralized} or
	 * {@code detector}. It is decided on the Python side (App.code_package_source) and
	 * has no other channel into the artefact, so a run that does not pass it records an
	 * empty origin rather than a guessed one (INV-ANA-66).
	 */
	private String getCodePackageSource() {
		String param = Configs.getClientParamCode("codePackageSource=");
		if (param == null) {
			return null;
		}
		return param.substring("codePackageSource=".length());
	}

	private boolean skipWtg() {
		String param = Configs.getClientParamCode("skipWtg=");
		return param != null && "true".equalsIgnoreCase(param.substring("skipWtg=".length()));
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
	 * generated resource classes, which inflate the coverage denominator.
	 *
	 * <p>The generated-class test is anchored at the class name's LAST segment, not at
	 * the scope key's root (INV-ANA-71). Anchoring it at the root only removed
	 * {@code <key>.R} and missed both the module-level form ({@code app.pachli.core.database.R},
	 * which a multi-module Gradle build emits once per module) and the case where the key
	 * is an <em>ancestor</em> of the resource namespace ({@code com.github.cvzi} over
	 * {@code com.github.cvzi.screenshottile.R$string}), where every resource class escaped.
	 * Measured over the 162-artefact corpus: 505 such classes were in the denominator,
	 * carrying 547 methods of which zero are non-trivial — constant tables that can never
	 * be covered.
	 *
	 * <p>The rule stops at resource classes. Annotation-processor output
	 * ({@code _Factory}, {@code _Impl}, {@code $$serializer}, {@code Hilt_*}, DataBinding)
	 * is 5,816 classes carrying 36,264 non-trivial methods that DO execute; removing them
	 * would redefine the denominator rather than close a leak, and is a research decision.
	 */
	// Package-private for unit testing
	static boolean isAppClass(String className, String filterPackage) {
		if (!className.startsWith(filterPackage)) {
			return false;
		}
		return !isGeneratedResourceClass(className);
	}

	/**
	 * True when the class name's last dotted segment names a generated resource class:
	 * {@code R}, {@code R$*}, {@code BuildConfig}, {@code Manifest} or {@code Manifest$*}.
	 */
	// Package-private for unit testing
	static boolean isGeneratedResourceClass(String className) {
		int lastDot = className.lastIndexOf('.');
		String segment = (lastDot < 0) ? className : className.substring(lastDot + 1);
		return segment.equals("R")
				|| segment.startsWith("R$")
				|| segment.equals("BuildConfig")
				|| segment.equals("Manifest")
				|| segment.startsWith("Manifest$");
	}

	/**
	 * The compiled class universe under {@code filterPackage} that survives
	 * {@link #isAppClass} — the NET count the denominator gate divides by (INV-ANA-66).
	 *
	 * <p>Read from {@code Scene.v().getClasses()}, not {@code getApplicationClasses()}:
	 * the library demotion in {@code AnalysisEntrypoint} calls {@code setLibraryClass()},
	 * which reclassifies without removing, so {@code getClasses()} is the compiled universe
	 * regardless of what the guard did — which is exactly the property that lets a stale
	 * guard be detected downstream.
	 *
	 * <p>The count is recorded net rather than raw because no consumer can correct a raw
	 * one: the gate receives an {@code int}, and filtering by name needs the names.
	 */
	static int countClassDefsUnderKey(String filterPackage) {
		int count = 0;
		for (SootClass cls : Scene.v().getClasses()) {
			if (isAppClass(cls.getName(), filterPackage)) {
				count++;
			}
		}
		return count;
	}

	// ========================================================================
	// Entry Points
	// ========================================================================

	/**
	 * Collect entry points: public/protected methods of activity classes,
	 * lifecycle handlers, and event handlers from GATOR's analysis.
	 */
	public static Set<SootMethod> getEntryPoints(GUIAnalysisOutput output) {
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

	public static DefaultDirectedGraph<SootMethod, DefaultEdge> buildJGraph(CallGraph cg) {
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

	// Package-private and generic for unit testing with synthetic graphs.
	// Seeds without any CG edge would otherwise be dropped by the
	// containsVertex check — buildJGraph only adds vertices that appear
	// in some edge, so an entry point with zero incident edges in SPARK
	// (e.g. a callback the runtime invokes but no call site reaches via
	// points-to) would silently disappear from reachable[]. Force-add the
	// seed first so legitimate roots are preserved even when the CG is
	// blind to them (INV-ANA-25).
	public static <V> Set<V> multiSourceBfs(
			org.jgrapht.Graph<V, DefaultEdge> graph,
			Set<V> seeds) {

		Set<V> visited = new HashSet<>();
		Queue<V> queue = new ArrayDeque<>();

		for (V seed : seeds) {
			graph.addVertex(seed);
			if (visited.add(seed)) {
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
	public static <V> Set<V> findDirectTargetCallers(
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
	 * Bytecode-scan complement to {@link #findDirectTargetCallers}.
	 *
	 * Walks each app method's body and inspects every {@link InvokeExpr},
	 * matching against MOP signatures by ({@code declaringClass.getName()},
	 * {@code methodRef.name()}) — the same FQN/name policy used by
	 * {@code TargetResolver.resolveInScene}. Independent of the call graph, so it
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
	/**
	 * Visitor callback for {@link #scanInvokesInAppClasses}. Receives the
	 * caller method and a matching invoke statement; implementation
	 * decides what to do (collect callers, collect (caller,target) pairs,
	 * etc.). Returning {@code true} stops the per-method scan early —
	 * the visitor has all it needs for this caller.
	 */
	public interface InvokeVisitor {
		/** @return true to break out of the current method's unit walk. */
		boolean visit(SootMethod caller, Stmt invokeStmt, InvokeExpr ie, SootMethodRef ref);
	}

	/**
	 * Generic bytecode-scan helper extracted from
	 * {@link #findDirectTargetCallersByBytecodeScan}. Iterates application
	 * methods, retrieves bodies under the same try-catch resilience
	 * policy (RuntimeException + OutOfMemoryError → WARN + skip), and
	 * dispatches each invoke statement to the visitor. Used by:
	 *   (a) MOP-caller detection (BUG-INV-ANA-19) via
	 *       {@link #findDirectTargetCallersByBytecodeScan}.
	 *   (b) IGNORED_CLASSES edge recovery (INV-ANA-22) at the WTG level
	 *       to complement SPARK CG queries.
	 *
	 * Telemetry is logged with the supplied {@code passLabel} so multiple
	 * passes can be distinguished in operator-facing logs.
	 *
	 * @return methodsScanned + bodiesSkipped counters for the caller's
	 *         telemetry; the visitor accumulates its own state.
	 */
	public static int[] scanInvokesInAppClasses(
			Map<SootClass, List<SootMethod>> appClasses,
			InvokeVisitor visitor,
			String passLabel) {

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
					System.out.println("[RvsecAnalysisClient] WARN " + passLabel
							+ " skipped " + method.getSignature() + ": " + ex.getMessage());
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
					if (visitor.visit(method, stmt, ie, ref)) {
						break;
					}
				}
			}
		}
		return new int[] { methodsScanned, bodiesSkipped };
	}

	/**
	 * BUG-INV-ANA-19 bytecode-scan complement keyed on a resolved
	 * {@code Set<SootMethod>} target set (C1c API). SPARK quarantines
	 * library targets and drops their incoming edges from the call graph;
	 * the JGraphT-based {@link #findDirectTargetCallers} therefore misses
	 * app methods that literally invoke a target. This pass walks every
	 * app method body, matches each {@link InvokeExpr} by
	 * {@code (declaringClass.getName(), methodRef.name())} against the
	 * target set's class+name pairs, and returns the callers.
	 *
	 * <p>The match is LENIENT for a LENIENT target and STRICT for a STRICT
	 * one — the policy the source attached travels all the way here. An
	 * earlier version of this method was LENIENT unconditionally, on the
	 * stated ground that "{@code methodRef} alone cannot reliably reconstruct
	 * the full Soot signature at the call site". That ground is false for the
	 * parameter list: {@link SootMethodRef#parameterTypes()} returns the types
	 * the invoke instruction's own descriptor carries, which is as reliable as
	 * the class and the name read from the same descriptor. Leaving it LENIENT
	 * had a consequence: a STRICT target collapses to a {@code class#name} key
	 * here, and that key readmits exactly the overloads STRICT exists to
	 * exclude — so the direct axis, and through it the reverse BFS the direct
	 * set seeds, kept the false positives the policy was chosen to remove.
	 *
	 * <p>The pass is <b>hybrid</b>. It receives both the resolved {@code Set<SootMethod>} and
	 * the declared {@code Set<TargetMethod>}, because resolution discards precisely what a
	 * subtype target needs: the declared super-type FQN and the two matching flags.
	 */
	public static Set<SootMethod> findDirectTargetCallersByBytecodeScan(
			Map<SootClass, List<SootMethod>> appClasses,
			Set<SootMethod> targets,
			Set<presto.android.gui.clients.target.TargetMethod> targetSpecs,
			presto.android.gui.clients.target.TargetMatching matching) {

		Set<SootMethod> result = new HashSet<>();

		// Targets that CANNOT be reduced to a class#method key, for two independent reasons that
		// a target may carry at once — so this is one list, not two mutually exclusive ones.
		//   - `includeSubtypes`: a key set is the resolved hierarchy already flattened, and
		//     flattening is the pre-expansion this design rejected — it misses sub-interfaces.
		//   - `STRICT`: a key set IS the lenient policy under another name. `String#valueOf`
		//     readmits every overload, which is exactly what the policy excludes.
		// An earlier version bucketed these with an `else if`, which made a target that is both
		// subtype-declared and STRICT lenient here while `resolveInScene` applied its parameter
		// check — the two axes then disagreed about the same call site, which is the property
		// this method exists to hold.
		List<presto.android.gui.clients.target.TargetMethod> perInvokeTargets = new ArrayList<>();
		boolean anySubtype = false;
		for (presto.android.gui.clients.target.TargetMethod t : targetSpecs) {
			if (t.isIncludeSubtypes()
					|| t.getPolicy() == presto.android.gui.clients.target.TargetMethod.MatchPolicy.STRICT) {
				perInvokeTargets.add(t);
				anySubtype |= t.isIncludeSubtypes();
			}
		}

		// Obtained after resolveInScene has force-resolved the owners. Re-read inside the scan
		// rather than captured: retrieving a body can mint a phantom SootClass, which calls
		// Scene.addClass and invalidates the cached instance. getOrMakeFastHierarchy is a field
		// read once the cache is warm.
		final soot.FastHierarchy hierarchy = anySubtype ? Scene.v().getOrMakeFastHierarchy() : null;

		// The exact half: a resolved Set<SootMethod> collapses to class#method keys, giving an
		// O(1) lookup per invoke.
		//
		// A key is kept only when some target claims that method *leniently*. If every target
		// claiming it is STRICT, the key would readmit the overloads those targets exclude, so
		// the method is left to the per-invoke pass below. Deciding this from what actually
		// matches — rather than from a second key space built out of the STRICT targets'
		// declared names — is what keeps two defects out: a declared name carrying a `*`
		// pattern never equals a resolved key, and a class#method shared by a STRICT and a
		// LENIENT target (`Cipher.init(int,Key)` beside `Cipher.init(..)`, which
		// SignatureFileTargetSource's own javadoc advertises) would otherwise strip the key the
		// LENIENT one needs. For a spec set with no STRICT target the set is identical to the
		// plain one, since every resolved method was resolved by some target: INV-ANA-35 holds
		// by construction here, not by measurement.
		Set<String> targetKeys = new HashSet<>(targets.size());
		for (SootMethod m : targets) {
			for (presto.android.gui.clients.target.TargetMethod t : targetSpecs) {
				if (t.getPolicy() == presto.android.gui.clients.target.TargetMethod.MatchPolicy.STRICT) {
					continue;
				}
				if (matching.matches(m.getDeclaringClass().getType(), m.getName(), t, hierarchy)) {
					targetKeys.add(m.getDeclaringClass().getName() + "#" + m.getName());
					break;
				}
			}
		}

		if (targetKeys.isEmpty() && perInvokeTargets.isEmpty()) {
			return result;
		}

		long scanStart = System.currentTimeMillis();
		int[] counters = scanInvokesInAppClasses(appClasses,
				(caller, stmt, ie, ref) -> {
					String name = ref.getName();
					if (matchesTargetSignature(ref.getDeclaringClass().getName(),
							name, targetKeys)) {
						// (see the hierarchy comment above: re-read, never captured)
						result.add(caller);
						return true;
					}
					for (presto.android.gui.clients.target.TargetMethod t : perInvokeTargets) {
						if (matchesAtCallSite(ref, name, t, matching)) {
							result.add(caller);
							return true;
						}
					}
					return false;
				},
				"Bytecode scan");

		System.out.println("[RvsecAnalysisClient] Bytecode scan: " + counters[0]
				+ " methods scanned, " + counters[1] + " body-retrieval skips, "
				+ targetKeys.size() + " exact keys, " + perInvokeTargets.size()
				+ " per-invoke targets (subtype and/or strict), "
				+ result.size() + " direct target callers detected (bytecodeScan: "
				+ (System.currentTimeMillis() - scanStart) + " ms)");
		return result;
	}

	/**
	 * The one predicate the per-invoke pass uses, so the direct axis cannot drift from what
	 * {@code TargetResolver.resolveInScene} does on the transitive one.
	 *
	 * <p>Owner and name go through {@link presto.android.gui.clients.target.TargetMatching#matches}
	 * — which is subtype-aware when the target declares {@code +} and pattern-aware when it
	 * declares a trailing {@code *} — and the parameter list is checked on top of it when, and
	 * only when, the target's policy is STRICT. That ordering matters: {@code matches} is lenient
	 * about parameters by design, so a STRICT target checked only through it would be matched
	 * leniently here and strictly there.
	 */
	static boolean matchesAtCallSite(SootMethodRef ref, String name,
			presto.android.gui.clients.target.TargetMethod t,
			presto.android.gui.clients.target.TargetMatching matching) {
		if (!matching.matches(ref.getDeclaringClass().getType(), name, t,
				Scene.v().getOrMakeFastHierarchy())) {
			return false;
		}
		return t.getPolicy() != presto.android.gui.clients.target.TargetMethod.MatchPolicy.STRICT
				|| paramsMatchAtCallSite(ref, t);
	}

	/**
	 * Compare a STRICT target's declared parameter list against the descriptor the invoke
	 * instruction carries.
	 *
	 * <p>Package-private so a unit test can exercise the comparison without a Scene. It mirrors
	 * {@code TargetResolver.paramsMatch}, which does the same job against a resolved
	 * {@link SootMethod}; the two must agree, or the direct and transitive axes would disagree
	 * about the same call site. The declared list is compared as written, which is why the
	 * extractor resolves pointcut parameter types to FQN — {@code Object} would never equal the
	 * {@code java.lang.Object} Soot reports here.
	 */
	static boolean paramsMatchAtCallSite(SootMethodRef ref,
			presto.android.gui.clients.target.TargetMethod target) {
		List<String> declared = target.getParams();
		List<soot.Type> actual = ref.parameterTypes();
		if (actual.size() != declared.size()) {
			return false;
		}
		for (int i = 0; i < declared.size(); i++) {
			if (!actual.get(i).toString().equals(declared.get(i))) {
				return false;
			}
		}
		return true;
	}

	/**
	 * Build a {@code "className#methodName"} key set from MOP signatures: FQN class + method
	 * name, ignoring parameter overloads.
	 *
	 * <p>Kept for the unit tests that pin that collapsing policy without a Soot Scene. Production
	 * no longer calls it — {@code findDirectTargetCallersByBytecodeScan} builds its key set from
	 * the <i>resolved</i> methods, and only for the targets that claim them leniently, which is
	 * a decision this method cannot express.
	 */
	public static Set<String> buildTargetKeys(Set<MopMethod> mopSignatures) {
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
	 * via {@code mopKeys.contains(...)} after {@link #buildTargetKeys}.
	 */
	public static boolean matchesTargetSignature(String className, String methodName, Set<String> mopKeys) {
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
	public static void complementWithCallbacks(
			GUIAnalysisOutput output,
			Set<SootMethod> reachableSet,
			Set<SootMethod> reachesTargetSet,
			Set<SootMethod> directMopSet,
			DefaultDirectedGraph<SootMethod, DefaultEdge> graph,
			Set<SootMethod> targetMethods) {

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
					if (targetMethods.contains(target)) {
						directMopSet.add(callback);
						reachesTargetSet.add(callback);
						break;
					}
					if (reachesTargetSet.contains(target)) {
						reachesTargetSet.add(callback);
					}
				}
			}
		}
	}

	private static void collectEventHandlers(GUIAnalysisOutput output, NNode node,
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
		SpinnerItemExtractor spinnerExtractor = new SpinnerItemExtractor();

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

			// Programmatic Spinner items via ArrayAdapter dataflow (Group 5,
			// MVP). Union into widget.entries AFTER enrichFromXml runs so
			// XML-defined entries from android:entries="@array/X" survive
			// (XML first, programmatic appended). Stored on the window for
			// the post-XML pass below.
			Map<Integer, List<String>> programmaticItems =
					spinnerExtractor.extractItems(activity);
			if (!programmaticItems.isEmpty()) {
				window.put("__programmaticSpinnerItems", programmaticItems);
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

		// Options menus — use the menu node's own ID. Two complementary paths:
		//   (1) XML-inflated items: walk menu.getChildren() to surface
		//       NMenuItemInflNode entries that FixpointSolver.doMenuInflate
		//       already populated from R.menu.<name>.xml (D7).
		//   (2) Programmatic items: MenuExtractor walks the CFG of
		//       onCreateOptionsMenu for Menu.add(...) / addSubMenu(...) calls
		//       (Group 4). Both paths emit into the same widgets[] list;
		//       id spaces are disjoint by construction.
		// MenuExtractor needs to resolve R.string.foo (numeric resource id)
		// to the actual string value for menu items declared as
		// Menu.add(group, id, order, R.string.foo). Previously the closure
		// returned null and every such item serialized with text="" — the
		// codex review (2026-05-15) flagged this as a defect because
		// downstream consumers (APE-RV) key off the title. We build a
		// per-call resolver that combines two existing helpers:
		//   - resolveStringIdToName(resId) — maps int constant to symbolic
		//     name via the app's R$string class fields (cached on first use)
		//   - resolveStringReference(resDir, name) — reads strings.xml
		// Either step returning null falls through to the extractor's
		// empty-string default; no exception propagates.
		String resDirForMenu = Configs.resourceLocation;
		MenuExtractor menuExtractor = new MenuExtractor(resId -> {
			String name = resolveStringIdToName(resId, output.getAppPackageName());
			if (name == null || resDirForMenu == null) return null;
			return resolveStringReference(resDirForMenu, name);
		});
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

				List<Map<String, Object>> widgets = new ArrayList<>();
				Set<NNode> menuVisited = new HashSet<>();
				for (NNode child : menu.getChildren()) {
					collectWidgets(output, child, widgets, menuVisited);
				}
				widgets.addAll(menuExtractor.extractItems(activity));
				window.put("widgets", widgets);
				windows.add(window);
				extractedIds.add((int) window.get("id"));
			}
		}

		// Catch-all: WTG nodes not captured above (context menus, fragments,
		// etc.). Only available when the WTG build completed; on the partial
		// path (wtg == null) the above ACTIVITY/DIALOG/OPTIONSMENU enumeration
		// is the complete set of windows the analysis can surface.
		if (wtg != null) {
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

			// XML-attribute fields seeded null; enrichFromXml overrides when the
			// corresponding android:* attribute is present in the layout file.
			// Missing attributes stay null so the JSON consumer can distinguish
			// "absent" from "empty".
			widget.put("inputType", "");
			widget.put("entries", Collections.emptyList());
			widget.put("prompt", null);
			widget.put("spinnerMode", null);
			widget.put("contentDescription", null);
			widget.put("tooltipText", null);

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
	/**
	 * Union the per-window programmatic Spinner items stashed by
	 * extractWindows() into widget.entries. XML-defined entries are
	 * preserved (XML first, programmatic appended) per Group 5 spec.
	 * The transient `__programmaticSpinnerItems` key is removed afterwards
	 * so it does not leak into the JSON.
	 */
	private void unionProgrammaticSpinnerItems(List<Map<String, Object>> windows) {
		int totalSpinners = 0;
		for (Map<String, Object> window : windows) {
			@SuppressWarnings("unchecked")
			Map<Integer, List<String>> items =
					(Map<Integer, List<String>>) window.remove("__programmaticSpinnerItems");
			if (items == null || items.isEmpty()) continue;
			@SuppressWarnings("unchecked")
			List<Map<String, Object>> widgets =
					(List<Map<String, Object>>) window.get("widgets");
			if (widgets == null) continue;
			for (Map<String, Object> widget : widgets) {
				Object idObj = widget.get("id");
				if (!(idObj instanceof Integer)) continue;
				List<String> programmatic = items.get(idObj);
				if (programmatic == null || programmatic.isEmpty()) continue;
				@SuppressWarnings("unchecked")
				List<String> entries = (List<String>) widget.get("entries");
				List<String> merged = new ArrayList<>(
						entries != null ? entries : Collections.emptyList());
				merged.addAll(programmatic);
				widget.put("entries", merged);
				totalSpinners++;
			}
		}
		if (totalSpinners > 0) {
			System.out.println("[SpinnerItemExtractor] processed "
					+ totalSpinners + " spinners via ArrayAdapter dataflow");
		}
	}

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
				enrichWidgetsFromLayout(layoutFile, widgetByIdName, arrays, resDir);
			}
		}
	}

	// Package-private for unit testing
	void enrichWidgetsFromLayout(
			File layoutFile,
			Map<String, Map<String, Object>> widgetByIdName,
			Map<String, List<String>> arrays,
			String resDir) {
		try {
			DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
			DocumentBuilder builder = factory.newDocumentBuilder();
			Document doc = builder.parse(layoutFile);
			enrichFromElement(doc.getDocumentElement(), widgetByIdName, arrays, resDir);
		} catch (Exception e) {
			// Graceful degradation — skip malformed XML
		}
	}

	private void enrichFromElement(
			Element elem,
			Map<String, Map<String, Object>> widgetByIdName,
			Map<String, List<String>> arrays,
			String resDir) {

		// Match element to widget by android:id. Both "@id/foo" (reference
		// form) and "@+id/foo" (declaration form — dominant in real
		// layouts) MUST match; previously only "@id/" was accepted, which
		// silently skipped the majority of widgets actually defined inline
		// in layout XML and left their inputType/entries/prompt/etc. null.
		String id = elem.getAttribute("android:id");
		String idPrefix = null;
		if (id != null) {
			if (id.startsWith("@+id/")) {
				idPrefix = "@+id/";
			} else if (id.startsWith("@id/")) {
				idPrefix = "@id/";
			}
		}
		if (idPrefix != null) {
			String idName = id.substring(idPrefix.length());
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

				// prompt (Spinner dialog title — may be @string/ ref)
				putStringAttr(widget, "prompt",
						elem.getAttribute("android:prompt"), resDir);
				// spinnerMode (enum literal: dropdown | dialog)
				putStringAttr(widget, "spinnerMode",
						elem.getAttribute("android:spinnerMode"), resDir);
				// contentDescription (accessibility label — may be @string/ ref)
				putStringAttr(widget, "contentDescription",
						elem.getAttribute("android:contentDescription"), resDir);
				// tooltipText (long-press hint — may be @string/ ref)
				putStringAttr(widget, "tooltipText",
						elem.getAttribute("android:tooltipText"), resDir);
				// hint — inline literal or @string/ ref. PropertyManager
				// (path A in collectWidgets) only sees CG-tracked / @string
				// hints; inline literals were silently dropped pre-gh60-fix.
				putStringAttr(widget, "hint",
						elem.getAttribute("android:hint"), resDir);
				// text — same dual-path gap as hint. putStringAttr
				// short-circuits on empty raw, so the PropertyManager seed
				// survives when the layout omits the attribute.
				putStringAttr(widget, "text",
						elem.getAttribute("android:text"), resDir);
			}
		}

		// Recurse into child elements
		NodeList children = elem.getChildNodes();
		for (int i = 0; i < children.getLength(); i++) {
			if (children.item(i) instanceof Element) {
				enrichFromElement((Element) children.item(i), widgetByIdName, arrays, resDir);
			}
		}
	}

	// Helper: set widget[key] = resolved attribute, with @string/ resolution.
	// Empty/absent values leave the widget unchanged (preserves the null seed
	// from collectWidgets, distinguishing "attribute absent" from "empty string").
	private void putStringAttr(
			Map<String, Object> widget,
			String key,
			String raw,
			String resDir) {
		if (raw == null || raw.isEmpty()) {
			return;
		}
		if (raw.startsWith("@string/")) {
			String resolved = resolveStringReference(resDir, raw.substring("@string/".length()));
			if (resolved != null) {
				widget.put(key, resolved);
			}
			return;
		}
		widget.put(key, raw);
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

			// Iterate all three resource-array kinds Android supports.
			// <string-array> covers most cases (textual entries for Spinners);
			// <integer-array> shows up on numeric pickers / color-palette
			// indices; generic <array> is the catch-all for mixed
			// @drawable/@string/@dimen lists. Pre-2026-05-26 this loop only
			// looked at <string-array>, so any spinner whose
			// android:entries="@array/foo" referenced an <integer-array> or
			// <array> resource silently got entries=[] and the agent's
			// inventory missed it. See design.md §D13.
			String[] arrayTagNames = {"string-array", "integer-array", "array"};
			for (String tagName : arrayTagNames) {
				NodeList arrayNodes = doc.getElementsByTagName(tagName);
				for (int i = 0; i < arrayNodes.getLength(); i++) {
					Element arrayElem = (Element) arrayNodes.item(i);
					String name = arrayElem.getAttribute("name");
					List<String> items = new ArrayList<>();

					NodeList itemNodes = arrayElem.getElementsByTagName("item");
					for (int j = 0; j < itemNodes.getLength(); j++) {
						String value = itemNodes.item(j).getTextContent().trim();
						// @string/ resolution applies uniformly — an
						// <array> can legitimately mix literal values with
						// @string/ refs; <integer-array> items are
						// numeric literals so the @string/ branch is a
						// harmless no-op there.
						if (value.startsWith("@string/")) {
							String resolved = resolveStringReference(resDir, value.substring("@string/".length()));
							items.add(resolved != null ? resolved : value);
						} else {
							items.add(value);
						}
					}
					arrays.put(name, items);
				}
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

	// Lazy cache for resource-id → symbolic name lookup. Built on first
	// call from <appPkg>.R$string fields tagged with IntegerConstantValueTag
	// (the same source GATOR already reads in DefaultXMLParser.readIntConstFields).
	// Null when the R$string class is absent or phantom, in which case
	// every resolveStringIdToName(resId, _) returns null.
	private Map<Integer, String> stringIdNameCache = null;

	private String resolveStringIdToName(int resId, String appPackage) {
		if (stringIdNameCache == null) {
			stringIdNameCache = buildStringIdNameCache(appPackage);
		}
		return stringIdNameCache.get(resId);
	}

	private Map<Integer, String> buildStringIdNameCache(String appPackage) {
		Map<Integer, String> cache = new HashMap<>();
		if (appPackage == null || appPackage.isEmpty()) return cache;
		String rStringClass = appPackage + ".R$string";
		SootClass cls;
		try {
			cls = Scene.v().getSootClassUnsafe(rStringClass);
		} catch (Exception e) {
			return cache;
		}
		if (cls == null || cls.isPhantom()) return cache;
		for (SootField f : cls.getFields()) {
			try {
				Object tag = f.getTag("IntegerConstantValueTag");
				if (tag == null) continue;
				String s = tag.toString();
				int val = Integer.parseInt(s.substring("ConstantValue: ".length()));
				cache.put(val, f.getName());
			} catch (RuntimeException ignore) {
				// Skip non-int fields (array residuals etc.) — same
				// resilience as DefaultXMLParser.readIntConstFields.
			}
		}
		return cache;
	}

	// ========================================================================
	// JSON Output with JsonWriter (incremental flush)
	// ========================================================================

	/**
	 * Prepare the windows[] section: extract widget data from the
	 * {@link GUIAnalysisOutput}, enrich with XML attributes, and union
	 * the programmatic Spinner items. The result is what
	 * {@link JsonReportWriter} emits as the {@code windows} section.
	 *
	 * <p>Called twice per analysis (once pre-WTG to populate the partial
	 * JSON that survives a WTG-phase timeout, once post-WTG with the
	 * full data). This is the only non-emission piece that used to live
	 * inside the old {@code writeJson}; it stays on the client because
	 * it consumes GATOR's internal data prep helpers (extractWindows,
	 * enrichFromXml, unionProgrammaticSpinnerItems) and there is no
	 * value in re-homing them in C1e.
	 */
	private List<Map<String, Object>> prepareWindows(
			GUIAnalysisOutput output,
			Map<String, Integer> windowNodeIds,
			WTG wtg) {
		List<Map<String, Object>> windows = extractWindows(output, windowNodeIds, wtg);
		enrichFromXml(windows);
		unionProgrammaticSpinnerItems(windows);
		return windows;
	}

	public static void writeReachabilitySection(
			JsonWriter w,
			Map<SootClass, List<SootMethod>> appClasses,
			GUIAnalysisOutput output,
			presto.android.gui.clients.reach.ReachabilityEnricher enricher) throws IOException {

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
				// Per-method reachability comes from the enricher — the writer
				// itself never touches ReachabilityIndex (gateway for the
				// INV-ANA-30 purity gate that lands fully in C1e).
				Map<String, Object> ann = enricher.enrichMethod(method);
				w.name("reachable").value((Boolean) ann.get("reachable"));
				w.name("reachesTarget").value((Boolean) ann.get("reachesTarget"));
				w.name("directlyReachesTarget").value((Boolean) ann.get("directlyReachesTarget"));
				w.endObject();
			}
			w.endArray();

			w.endObject();
		}
		w.endArray();
	}

	public static void writeWindowsSection(JsonWriter w, List<Map<String, Object>> windows) throws IOException {
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

	private static void writeWidget(JsonWriter w, Map<String, Object> widget) throws IOException {
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
		if (entries != null) {
			for (String entry : entries) {
				w.value(entry);
			}
		}
		w.endArray();

		// XML widget attributes (gh57 Group 3): null when the corresponding
		// android:* attribute was absent from the layout XML.
		w.name("prompt").value((String) widget.get("prompt"));
		w.name("spinnerMode").value((String) widget.get("spinnerMode"));
		w.name("contentDescription").value((String) widget.get("contentDescription"));
		w.name("tooltipText").value((String) widget.get("tooltipText"));

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

	public static void writeComponentsSection(JsonWriter w,
			presto.android.gui.clients.reach.ReachabilityEnricher enricher,
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
			writeComponentEntry(w, className, activity, allFilters, enricher, xmlParser,
					new String[]{"onCreate", "onStart", "onResume", "onPause", "onStop", "onDestroy", "onRestart"}, isMain);
		}
		w.endArray();

		// Write receivers
		w.name("receivers");
		w.beginArray();
		for (Iterator<String> it = xmlParser.getReceivers(); it.hasNext(); ) {
			String className = it.next();
			SootClass sc = Scene.v().getSootClassUnsafe(className);
			writeComponentEntry(w, className, sc, allFilters, enricher, xmlParser,
					new String[]{"onReceive"}, false);
		}
		w.endArray();

		// Write services
		w.name("services");
		w.beginArray();
		for (Iterator<String> it = xmlParser.getServices(); it.hasNext(); ) {
			String className = it.next();
			SootClass sc = Scene.v().getSootClassUnsafe(className);
			writeComponentEntry(w, className, sc, allFilters, enricher, xmlParser,
					new String[]{"onCreate", "onStartCommand", "onBind", "onUnbind", "onRebind", "onDestroy", "onHandleIntent"}, false);
		}
		w.endArray();

		// Write providers
		w.name("providers");
		w.beginArray();
		for (Iterator<String> it = xmlParser.getProviders(); it.hasNext(); ) {
			String className = it.next();
			SootClass sc = Scene.v().getSootClassUnsafe(className);
			writeProviderEntry(w, className, sc, enricher, xmlParser,
					new String[]{"onCreate", "query", "insert", "update", "delete", "call", "openFile"});
		}
		w.endArray();

		w.endObject();
	}

	private static void writeComponentEntry(JsonWriter w, String className, SootClass sc,
			Map<String, Set<IntentFilter>> allFilters,
			presto.android.gui.clients.reach.ReachabilityEnricher enricher,
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
				// D15 (2026-05-29) — data block always emitted (empty
				// lists when filter has no <data>); consistent shape
				// lets consumers iterate without absence checks.
				writeIntentFilterDataBlock(w, filter);
				w.endObject();
			}
		}
		w.endArray();

		w.name("exported").value(xmlParser.isComponentExported(className));
		// D15 — manifest android:permission for activity/receiver/service.
		w.name("permission").value(xmlParser.getComponentPermission(className));

		// MOP reachability via the enricher — writer never reads
		// ReachabilityIndex directly (precondition for INV-ANA-30).
		List<String> targetMethods = new ArrayList<>();
		boolean reachesTarget = false;
		for (SootMethod m : sc.getMethods()) {
			String methodName = m.getName();
			for (String lifecycle : lifecycleMethodNames) {
				if (methodName.equals(lifecycle)
						&& Boolean.TRUE.equals(enricher.enrichMethod(m).get("reachesTarget"))) {
					reachesTarget = true;
					targetMethods.add(m.getSignature());
				}
			}
		}
		w.name("reachesTarget").value(reachesTarget);
		w.name("targetMethods");
		w.beginArray();
		for (String sig : targetMethods) {
			w.value(sig);
		}
		w.endArray();

		w.endObject();
	}

	private static void writeProviderEntry(JsonWriter w, String className, SootClass sc,
			presto.android.gui.clients.reach.ReachabilityEnricher enricher,
			XMLParser xmlParser, String[] lifecycleMethodNames) throws IOException {
		if (sc == null) return;

		w.beginObject();
		w.name("className").value(className);
		w.name("isMain").value(false);
		w.name("authorities").value(xmlParser.getProviderAuthorities(className));
		w.name("exported").value(xmlParser.isComponentExported(className));
		// D15 (2026-05-29) — provider permissions. The component-level
		// `permission` field is the fallback per Android semantics;
		// `readPermission`/`writePermission` override it granularly when
		// declared. All three are emitted (null when absent) so consumers
		// see a consistent schema.
		w.name("permission").value(xmlParser.getComponentPermission(className));
		w.name("readPermission").value(xmlParser.getProviderReadPermission(className));
		w.name("writePermission").value(xmlParser.getProviderWritePermission(className));

		// MOP reachability via the enricher (see writeComponentEntry note).
		List<String> targetMethods = new ArrayList<>();
		boolean reachesTarget = false;
		for (SootMethod m : sc.getMethods()) {
			String methodName = m.getName();
			for (String lifecycle : lifecycleMethodNames) {
				if (methodName.equals(lifecycle)
						&& Boolean.TRUE.equals(enricher.enrichMethod(m).get("reachesTarget"))) {
					reachesTarget = true;
					targetMethods.add(m.getSignature());
				}
			}
		}
		w.name("reachesTarget").value(reachesTarget);
		w.name("targetMethods");
		w.beginArray();
		for (String sig : targetMethods) {
			w.value(sig);
		}
		w.endArray();

		w.endObject();
	}

	/**
	 * D15 (2026-05-29) — emit the intent-filter {@code data} block. Always
	 * called, even when the filter has no {@code <data>} element — empty
	 * lists are emitted so consumers see a stable shape and never have to
	 * branch on key absence.
	 *
	 * <p>Path matchers are split into three flat string lists keyed by
	 * their type discriminator ({@code PATTERN_LITERAL → paths},
	 * {@code PATTERN_PREFIX → pathPrefixes},
	 * {@code PATTERN_SIMPLE_GLOB → pathPatterns}). The discriminator is
	 * carried by the JSON key name rather than per-entry, matching how
	 * Android's manifest XML attributes (android:path / android:pathPrefix
	 * / android:pathPattern) declare the same partition.
	 *
	 * <p>Ports are emitted only when explicitly declared
	 * ({@code AuthorityEntry.getPort() >= 0}); an unset port surfaces as
	 * absence from the list, not as -1.
	 */
	private static void writeIntentFilterDataBlock(JsonWriter w, IntentFilter filter) throws IOException {
		w.name("data");
		w.beginObject();

		w.name("schemes");
		w.beginArray();
		for (String scheme : filter.getDataSchemes()) {
			w.value(scheme);
		}
		w.endArray();

		// hosts + ports come from AuthorityEntry; ports are only emitted
		// when explicitly declared (mPort != -1).
		w.name("hosts");
		w.beginArray();
		for (IntentFilter.AuthorityEntry auth : filter.getDataAuthorities()) {
			w.value(auth.getHost());
		}
		w.endArray();

		w.name("ports");
		w.beginArray();
		for (IntentFilter.AuthorityEntry auth : filter.getDataAuthorities()) {
			int p = auth.getPort();
			if (p >= 0) {
				w.value(p);
			}
		}
		w.endArray();

		// Paths partitioned by PatternMatcher type — literal/prefix/glob
		// map to three independent JSON lists, mirroring Android's
		// android:path / android:pathPrefix / android:pathPattern
		// distinction.
		List<String> pathLiterals = new ArrayList<>();
		List<String> pathPrefixes = new ArrayList<>();
		List<String> pathPatterns = new ArrayList<>();
		for (PatternMatcher pm : filter.getDataPaths()) {
			switch (pm.getType()) {
				case PatternMatcher.PATTERN_LITERAL:
					pathLiterals.add(pm.getPattern());
					break;
				case PatternMatcher.PATTERN_PREFIX:
					pathPrefixes.add(pm.getPattern());
					break;
				case PatternMatcher.PATTERN_SIMPLE_GLOB:
					pathPatterns.add(pm.getPattern());
					break;
				default:
					// Unknown type — skip rather than guess
					break;
			}
		}
		w.name("paths");
		w.beginArray();
		for (String p : pathLiterals) { w.value(p); }
		w.endArray();
		w.name("pathPrefixes");
		w.beginArray();
		for (String p : pathPrefixes) { w.value(p); }
		w.endArray();
		w.name("pathPatterns");
		w.beginArray();
		for (String p : pathPatterns) { w.value(p); }
		w.endArray();

		w.name("mimeTypes");
		w.beginArray();
		for (String t : filter.getDataMimeTypes()) {
			w.value(t);
		}
		w.endArray();

		w.endObject();
	}

	private static boolean isGatorStubNode(NObjectNode node) {
		String className = node.getClassType().getName();
		return className.startsWith("presto.android.gui.stubs.");
	}

	public static void writeTransitionsSection(JsonWriter w, WTG wtg) throws IOException {
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
