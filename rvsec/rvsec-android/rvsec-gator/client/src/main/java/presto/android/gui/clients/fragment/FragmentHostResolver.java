package presto.android.gui.clients.fragment;

import java.io.File;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Deque;
import java.util.HashMap;
import java.util.Iterator;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;

import org.w3c.dom.Attr;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NamedNodeMap;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

import presto.android.gui.FixpointSolver;
import presto.android.gui.GUIAnalysisOutput;
import presto.android.gui.graph.NActivityNode;
import presto.android.gui.graph.NInflate1OpNode;
import presto.android.gui.graph.NInflate2OpNode;
import presto.android.gui.graph.NLayoutIdNode;
import presto.android.gui.graph.NNode;
import presto.android.gui.graph.NOpNode;
import presto.android.gui.graph.NWindowNode;
import presto.android.xml.XMLParser;
import soot.Body;
import soot.jimple.toolkits.callgraph.Edge;
import soot.jimple.ThisRef;
import soot.jimple.ParameterRef;
import soot.jimple.IdentityStmt;
import soot.jimple.FieldRef;
import soot.SootField;
import soot.Local;
import soot.RefType;
import soot.Scene;
import soot.SootClass;
import soot.SootMethod;
import soot.Type;
import soot.Unit;
import soot.Value;
import soot.jimple.AssignStmt;
import soot.jimple.CastExpr;
import soot.jimple.InstanceInvokeExpr;
import soot.jimple.ClassConstant;
import soot.jimple.InvokeExpr;
import soot.jimple.NewExpr;
import soot.jimple.ReturnStmt;
import soot.jimple.Stmt;
import soot.toolkits.graph.BriefUnitGraph;
import soot.toolkits.scalar.LocalDefs;
import soot.toolkits.scalar.SimpleLocalDefs;

/**
 * Attributes application fragments to the activities that host them (F1).
 *
 * <p>GATOR models activities, dialogs and menus as windows; a fragment is none of
 * them, so its UI never reaches a window. This class answers the first half of the
 * gap: which activity shows which fragment. Four sources feed one ownership
 * relation {@code context class -> fragment class}:
 * <ol>
 *   <li>{@code FragmentTransaction.add/replace} call sites (android.app, support-v4,
 *       androidx). The fragment class comes from a {@code const-class} argument or
 *       from the allocations reaching the fragment argument; the walk sees through
 *       copies, casts, parameters (into every call site), fields (into every write)
 *       and application factory methods (into their returns). The context is the
 *       activity or fragment whose {@code get*FragmentManager()} produced the
 *       transaction's receiver, else the activities and fragments that call into
 *       the method, else the class the call is in.</li>
 *   <li>{@code <fragment android:name>} and {@code <FragmentContainerView
 *       android:name>} in a layout inflated as the context's own UI, following
 *       {@code <include>}.</li>
 *   <li>Navigation graphs: the destinations of the graph named by a
 *       {@code NavHostFragment}'s {@code app:navGraph} in such a layout.</li>
 *   <li>Pager adapters: fragments allocated in {@code createFragment}/{@code getItem}
 *       of a {@code FragmentStateAdapter}/{@code FragmentPagerAdapter} subclass.</li>
 * </ol>
 * A context class is mapped to host activities by {@link #hostsOfContext}: an
 * activity stands for itself and its manifest-declared subclasses (code in a base
 * activity runs in each concrete one), a fragment passes on its own hosts (nested
 * fragments), an inner class passes on its outer class's hosts, and any other class
 * passes on the hosts of the classes that allocate it (a pager adapter allocated in
 * an activity). The relation is closed by fixpoint because fragment hosts depend on
 * each other.
 *
 * <p>Fragments created by reflection, by a {@code FragmentFactory} or by dependency
 * injection, navigation graphs set from code, and walks that exceed their bounds are
 * not attributed: the loss is recall, not a wrong host.
 */
public final class FragmentHostResolver {

	private static final Set<String> FRAGMENT_BASES = Set.of(
			"android.app.Fragment",
			"android.support.v4.app.Fragment",
			"androidx.fragment.app.Fragment");

	/** Dialog fragments are dialogs, shown with {@code show()}; dialog windows are out of scope here. */
	private static final Set<String> DIALOG_FRAGMENT_BASES = Set.of(
			"android.app.DialogFragment",
			"android.support.v4.app.DialogFragment",
			"androidx.fragment.app.DialogFragment");

	private static final Set<String> TRANSACTION_CLASSES = Set.of(
			"android.app.FragmentTransaction",
			"android.app.BackStackRecord",
			"android.support.v4.app.FragmentTransaction",
			"android.support.v4.app.BackStackRecord",
			"androidx.fragment.app.FragmentTransaction",
			"androidx.fragment.app.BackStackRecord");

	private static final Set<String> TRANSACTION_METHODS = Set.of("add", "replace");

	private static final Set<String> MANAGER_GETTERS = Set.of(
			"getSupportFragmentManager", "getFragmentManager", "requireFragmentManager",
			"getParentFragmentManager", "getChildFragmentManager");

	private static final Set<String> PAGER_ADAPTER_BASES = Set.of(
			"androidx.viewpager2.adapter.FragmentStateAdapter",
			"androidx.fragment.app.FragmentPagerAdapter",
			"androidx.fragment.app.FragmentStatePagerAdapter",
			"android.support.v4.app.FragmentPagerAdapter",
			"android.support.v4.app.FragmentStatePagerAdapter",
			"android.support.v13.app.FragmentPagerAdapter",
			"android.support.v13.app.FragmentStatePagerAdapter");

	private static final Set<String> PAGER_FACTORY_METHODS = Set.of("createFragment", "getItem");

	private static final String NAV_HOST_FRAGMENT = "androidx.navigation.fragment.NavHostFragment";

	/** Bound on the def-use walk (copies, parameters, fields) behind a transaction. */
	private static final int MAX_DEF_DEPTH = 6;

	/** Bound on the reverse call-graph search for the activity or fragment behind a helper. */
	private static final int MAX_CALLER_DEPTH = 4;

	private static final Set<String> ACTIVITY_GETTERS = Set.of("getActivity", "requireActivity");

	/** Bound on the allocator chain used to place a helper class under a host. */
	private static final int MAX_ALLOCATOR_DEPTH = 3;

	private final GUIAnalysisOutput output;
	private final Map<SootClass, List<SootMethod>> appClasses;
	private final String resDir;
	private final String appPackage;
	private final Set<SootClass> activities;

	/** context class -> fragments it shows, with the evidence label per pair. */
	private final Map<SootClass, Map<SootClass, Set<String>>> owned = new LinkedHashMap<>();
	/** allocated class -> classes whose code allocates it. */
	private final Map<SootClass, Set<SootClass>> allocators = new HashMap<>();
	private final Map<String, Set<String>> layoutFragmentsCache = new HashMap<>();
	/** field -> {method, write statement} for every application write of the field. */
	private final Map<SootField, List<Object[]>> fieldWrites = new HashMap<>();
	private final Map<SootMethod, LocalDefs> defsCache = new HashMap<>();
	private Set<SootClass> declaredActivities;
	/** sub-signature -> {method, statement} for every application call site. */
	private final Map<String, List<Object[]>> callSitesBySubSignature = new HashMap<>();

	private int transactionSites;
	private int transactionSitesUnresolved;

	public FragmentHostResolver(GUIAnalysisOutput output,
			Map<SootClass, List<SootMethod>> appClasses, String resDir) {
		this.output = output;
		this.appClasses = appClasses;
		this.resDir = resDir;
		this.appPackage = output.getAppPackageName();
		this.activities = output.getActivities();
	}

	// ------------------------------------------------------------------
	// Type tests
	// ------------------------------------------------------------------

	public static boolean isFragment(SootClass c) {
		return extendsAny(c, FRAGMENT_BASES);
	}

	public static boolean isDialogFragment(SootClass c) {
		return extendsAny(c, DIALOG_FRAGMENT_BASES);
	}

	private static boolean extendsAny(SootClass c, Set<String> bases) {
		SootClass cur = c;
		int guard = 0;
		while (cur != null && guard++ < 32) {
			if (bases.contains(cur.getName())) {
				return true;
			}
			cur = cur.getSuperclassUnsafe();
		}
		return false;
	}

	/** Application fragment classes this analysis builds windows for. */
	public List<SootClass> appFragments() {
		List<SootClass> result = new ArrayList<>();
		for (SootClass c : appClasses.keySet()) {
			if (!c.isAbstract() && !c.isInterface() && isFragment(c) && !isDialogFragment(c)) {
				result.add(c);
			}
		}
		result.sort((a, b) -> a.getName().compareTo(b.getName()));
		return result;
	}

	// ------------------------------------------------------------------
	// Resolution
	// ------------------------------------------------------------------

	/**
	 * Builds the fragment -> host-activities map.
	 *
	 * @param fragmentLayouts layouts each fragment inflates as its own view (from F2),
	 *        so a {@code <fragment>} or nav host inside a fragment's layout is
	 *        attributed to that fragment and, through it, to its hosts.
	 * @return fragment -> sorted host activities; fragments with no host are absent.
	 */
	public Map<SootClass, Set<SootClass>> resolve(Map<SootClass, Set<String>> fragmentLayouts) {
		scanCode();
		Map<SootClass, Set<String>> contextLayouts = activityLayouts();
		contextLayouts.putAll(fragmentLayouts);
		for (Map.Entry<SootClass, Set<String>> e : contextLayouts.entrySet()) {
			for (String layout : e.getValue()) {
				for (String entry : fragmentsInLayout(layout)) {
					addFromXmlEntry(e.getKey(), entry);
				}
			}
		}
		return closeHosts();
	}

	public int transactionSites() {
		return transactionSites;
	}

	public int transactionSitesUnresolved() {
		return transactionSitesUnresolved;
	}

	private void own(SootClass context, SootClass fragment, String source) {
		if (fragment == null || !isFragment(fragment) || isDialogFragment(fragment)) {
			return;
		}
		owned.computeIfAbsent(context, k -> new LinkedHashMap<>())
				.computeIfAbsent(fragment, k -> new LinkedHashSet<>()).add(source);
	}

	/**
	 * Sources 2 and 4. A first pass indexes allocations, field writes and transaction
	 * sites; the second resolves each site, because resolving a fragment held in a
	 * field needs every write of that field.
	 */
	private void scanCode() {
		List<Object[]> sites = new ArrayList<>();
		for (Map.Entry<SootClass, List<SootMethod>> entry : appClasses.entrySet()) {
			SootClass owner = entry.getKey();
			boolean pagerAdapter = extendsAny(owner, PAGER_ADAPTER_BASES);
			for (SootMethod method : entry.getValue()) {
				Body body = bodyOf(method);
				if (body == null) {
					continue;
				}
				boolean factory = pagerAdapter && PAGER_FACTORY_METHODS.contains(method.getName());
				for (Unit unit : body.getUnits()) {
					Stmt stmt = (Stmt) unit;
					if (stmt instanceof AssignStmt) {
						AssignStmt as = (AssignStmt) stmt;
						if (as.getRightOp() instanceof NewExpr) {
							SootClass allocated = ((NewExpr) as.getRightOp()).getBaseType().getSootClass();
							if (allocated != owner) {
								allocators.computeIfAbsent(allocated, k -> new HashSet<>()).add(owner);
							}
							if (factory) {
								own(owner, allocated, "pager");
							}
						}
						if (as.getLeftOp() instanceof FieldRef) {
							fieldWrites.computeIfAbsent(((FieldRef) as.getLeftOp()).getField(),
									k -> new ArrayList<>()).add(new Object[] { method, as });
						}
					}
					if (!stmt.containsInvokeExpr()) {
						continue;
					}
					InvokeExpr ie = stmt.getInvokeExpr();
					callSitesBySubSignature.computeIfAbsent(ie.getMethodRef().getSubSignature().toString(),
							k -> new ArrayList<>()).add(new Object[] { method, stmt });
					if (factory && stmt instanceof AssignStmt) {
						own(owner, classOfType(ie.getMethodRef().getReturnType()), "pager");
					}
					if (TRANSACTION_CLASSES.contains(ie.getMethodRef().getDeclaringClass().getName())
							&& TRANSACTION_METHODS.contains(ie.getMethodRef().getName())) {
						sites.add(new Object[] { method, stmt });
					}
				}
			}
		}
		for (Object[] site : sites) {
			SootMethod method = (SootMethod) site[0];
			Stmt stmt = (Stmt) site[1];
			transactionSites++;
			Set<SootClass> fragments = fragmentsOfArguments(method, stmt);
			if (fragments.isEmpty()) {
				transactionSitesUnresolved++;
				continue;
			}
			Set<SootClass> contexts = transactionContexts(method, stmt);
			String label = "transaction";
			if (contexts.isEmpty()) {
				contexts = callerContexts(method);
				label = "transaction-caller";
			}
			if (contexts.isEmpty()) {
				contexts = Set.of(method.getDeclaringClass());
				label = "transaction-site";
			}
			for (SootClass context : contexts) {
				for (SootClass f : fragments) {
					own(context, f, label);
				}
			}
		}
	}

	private Body bodyOf(SootMethod method) {
		if (!method.isConcrete()) {
			return null;
		}
		try {
			return method.retrieveActiveBody();
		} catch (RuntimeException ex) {
			return null;
		}
	}

	private LocalDefs defsOf(SootMethod method) {
		return defsCache.computeIfAbsent(method, m -> {
			Body body = bodyOf(m);
			return body == null ? null : new SimpleLocalDefs(new BriefUnitGraph(body));
		});
	}

	/** Receives the definitions a {@link #walk} cannot see through. */
	@FunctionalInterface
	private interface DefSink {
		void accept(SootMethod method, Unit def, Value rhs, int depth);
	}

	/**
	 * Visits the definitions of {@code local} at {@code at}, seeing through copies,
	 * casts, parameters (into each call-graph caller's argument) and fields (into
	 * each write of the field). Every other right-hand side, and {@code @this}, goes
	 * to {@code sink}. Bounded by {@link #MAX_DEF_DEPTH} and a visited set.
	 */
	private void walk(SootMethod method, Local local, Unit at, int depth, Set<Unit> seen, DefSink sink) {
		if (depth > MAX_DEF_DEPTH) {
			return;
		}
		LocalDefs defs = defsOf(method);
		if (defs == null) {
			return;
		}
		for (Unit def : defs.getDefsOfAt(local, at)) {
			if (!seen.add(def)) {
				continue;
			}
			if (def instanceof IdentityStmt) {
				Value rhs = ((IdentityStmt) def).getRightOp();
				if (rhs instanceof ParameterRef) {
					int index = ((ParameterRef) rhs).getIndex();
					for (Object[] site : callSitesOf(method)) {
						Stmt callSite = (Stmt) site[1];
						InvokeExpr call = callSite.getInvokeExpr();
						if (index < call.getArgCount() && call.getArg(index) instanceof Local) {
							walk((SootMethod) site[0], (Local) call.getArg(index), callSite, depth + 1, seen, sink);
						}
					}
				} else {
					sink.accept(method, def, rhs, depth);
				}
				continue;
			}
			if (!(def instanceof AssignStmt)) {
				continue;
			}
			Value rhs = ((AssignStmt) def).getRightOp();
			if (rhs instanceof Local) {
				walk(method, (Local) rhs, def, depth + 1, seen, sink);
			} else if (rhs instanceof CastExpr && ((CastExpr) rhs).getOp() instanceof Local) {
				walk(method, (Local) ((CastExpr) rhs).getOp(), def, depth + 1, seen, sink);
			} else if (rhs instanceof FieldRef) {
				for (Object[] w : fieldWrites.getOrDefault(((FieldRef) rhs).getField(),
						Collections.emptyList())) {
					AssignStmt write = (AssignStmt) w[1];
					if (!seen.add(write)) {
						continue;
					}
					if (write.getRightOp() instanceof Local) {
						walk((SootMethod) w[0], (Local) write.getRightOp(), write, depth + 1, seen, sink);
					} else {
						sink.accept((SootMethod) w[0], write, write.getRightOp(), depth + 1);
					}
				}
			} else {
				sink.accept(method, def, rhs, depth);
			}
		}
	}

	/** Application methods a call statement may invoke: call-graph targets, else the static target. */
	private List<SootMethod> appCallees(Stmt call) {
		List<SootMethod> result = new ArrayList<>();
		if (Scene.v().hasCallGraph()) {
			for (Iterator<Edge> it = Scene.v().getCallGraph().edgesOutOf(call); it.hasNext();) {
				SootMethod tgt = it.next().tgt();
				if (tgt != null && appClasses.containsKey(tgt.getDeclaringClass()) && !result.contains(tgt)) {
					result.add(tgt);
				}
			}
		}
		if (result.isEmpty()) {
			try {
				SootMethod tgt = call.getInvokeExpr().getMethod();
				if (appClasses.containsKey(tgt.getDeclaringClass())) {
					result.add(tgt);
				}
			} catch (RuntimeException e) {
				// unresolvable reference: no callee
			}
		}
		return result;
	}

	/**
	 * {method, statement} call sites of {@code target}: call-graph edges, plus the
	 * application call sites whose reference names it (same sub-signature, declared on
	 * its class or a subclass). The second set matters because the call graph
	 * omits code its entry points do not reach, which is common in UI callbacks.
	 */
	private List<Object[]> callSitesOf(SootMethod target) {
		List<Object[]> result = new ArrayList<>();
		Set<Stmt> seen = new HashSet<>();
		if (Scene.v().hasCallGraph()) {
			for (Iterator<Edge> it = Scene.v().getCallGraph().edgesInto(target); it.hasNext();) {
				Edge e = it.next();
				Stmt s = e.srcStmt();
				if (s != null && s.containsInvokeExpr() && e.src() != null && seen.add(s)) {
					result.add(new Object[] { e.src(), s });
				}
			}
		}
		for (Object[] site : callSitesBySubSignature.getOrDefault(
				target.getSubSignature(), Collections.emptyList())) {
			Stmt s = (Stmt) site[1];
			SootClass declared = s.getInvokeExpr().getMethodRef().getDeclaringClass();
			if (seen.contains(s) || !extendsClass(declared, target.getDeclaringClass())) {
				continue;
			}
			seen.add(s);
			result.add(site);
		}
		return result;
	}

	private static boolean extendsClass(SootClass c, SootClass base) {
		SootClass cur = c;
		int guard = 0;
		while (cur != null && guard++ < 32) {
			if (cur == base) {
				return true;
			}
			cur = cur.getSuperclassUnsafe();
		}
		return false;
	}

	private Set<SootClass> fragmentsOfArguments(SootMethod method, Stmt stmt) {
		InvokeExpr ie = stmt.getInvokeExpr();
		Set<SootClass> result = new LinkedHashSet<>();
		for (Value arg : ie.getArgs()) {
			if (arg instanceof ClassConstant) {
				SootClass c = classOfType(((ClassConstant) arg).toSootType());
				if (c != null && isFragment(c)) {
					result.add(c);
				}
			} else if (arg instanceof Local && arg.getType() instanceof RefType
					&& isFragment(((RefType) arg.getType()).getSootClass())) {
				resolveFragment(method, (Local) arg, stmt, result);
			}
		}
		return result;
	}

	/**
	 * Concrete fragment classes reaching {@code local}: allocations, and calls whose
	 * declared return type is already a concrete application fragment (a
	 * {@code newInstance()} factory), through the {@link #walk}. When the walk finds
	 * none, a concrete declared type is accepted.
	 */
	private void resolveFragment(SootMethod method, Local local, Unit at, Set<SootClass> out) {
		int before = out.size();
		Set<Unit> seen = new HashSet<>();
		DefSink sink = new DefSink() {
			@Override
			public void accept(SootMethod m, Unit def, Value rhs, int depth) {
				if (rhs instanceof NewExpr) {
					addConcrete(((NewExpr) rhs).getBaseType().getSootClass(), out);
				} else if (rhs instanceof InvokeExpr) {
					int found = out.size();
					addConcrete(classOfType(((InvokeExpr) rhs).getMethodRef().getReturnType()), out);
					if (out.size() == found && depth < MAX_DEF_DEPTH) {
						// A factory such as FragmentProvider.forId(id): walk what it returns.
						for (SootMethod callee : appCallees((Stmt) def)) {
							Body body = bodyOf(callee);
							if (body == null) {
								continue;
							}
							for (Unit u : body.getUnits()) {
								if (u instanceof ReturnStmt && ((ReturnStmt) u).getOp() instanceof Local) {
									walk(callee, (Local) ((ReturnStmt) u).getOp(), u, depth + 1, seen, this);
								}
							}
						}
					}
				}
			}
		};
		walk(method, local, at, 0, seen, sink);
		if (out.size() == before && local.getType() instanceof RefType) {
			addConcrete(((RefType) local.getType()).getSootClass(), out);
		}
	}

	/**
	 * The activity or fragment whose fragment manager a transaction belongs to,
	 * found by walking the receiver back through {@code beginTransaction()} and the
	 * {@code FragmentTransaction} builder calls to the
	 * {@code getSupportFragmentManager()}-style call and reading its receiver. This is
	 * what attributes a transaction made in a helper class that was handed the
	 * activity or its manager. Empty when the walk does not end in such a call.
	 */
	private Set<SootClass> transactionContexts(SootMethod method, Stmt stmt) {
		Set<SootClass> result = new LinkedHashSet<>();
		InvokeExpr ie = stmt.getInvokeExpr();
		if (ie instanceof InstanceInvokeExpr && ((InstanceInvokeExpr) ie).getBase() instanceof Local) {
			managerOwners(method, (Local) ((InstanceInvokeExpr) ie).getBase(), stmt, result, 0);
		}
		return result;
	}

	private void managerOwners(SootMethod method, Local local, Unit at, Set<SootClass> out, int depth) {
		walk(method, local, at, depth, new HashSet<>(), (m, def, rhs, d) -> {
			if (!(rhs instanceof InstanceInvokeExpr)
					|| !(((InstanceInvokeExpr) rhs).getBase() instanceof Local)) {
				return;
			}
			Local base = (Local) ((InstanceInvokeExpr) rhs).getBase();
			String name = ((InvokeExpr) rhs).getMethodRef().getName();
			if (MANAGER_GETTERS.contains(name)) {
				out.addAll(uiOwners(m, base, def, d + 1));
			} else if (d < MAX_DEF_DEPTH && (TRANSACTION_CLASSES.contains(
					((InvokeExpr) rhs).getMethodRef().getDeclaringClass().getName())
					|| "beginTransaction".equals(name))) {
				managerOwners(m, base, def, out, d + 1);
			}
		});
	}

	/**
	 * Activities and application fragments the receiver of a manager getter may be:
	 * its declared type when that is one; {@code this} of an activity or fragment;
	 * the fragment whose {@code getActivity()}/{@code requireActivity()} produced it
	 * (the fragment's hosts flow from it).
	 */
	private Set<SootClass> uiOwners(SootMethod method, Local local, Unit at, int depth) {
		Set<SootClass> result = new LinkedHashSet<>();
		if (local.getType() instanceof RefType && isUiOwner(((RefType) local.getType()).getSootClass())) {
			result.add(((RefType) local.getType()).getSootClass());
			return result;
		}
		walk(method, local, at, depth, new HashSet<>(), (m, def, rhs, d) -> {
			if (rhs instanceof ThisRef && isUiOwner(m.getDeclaringClass())) {
				result.add(m.getDeclaringClass());
			} else if (rhs instanceof InstanceInvokeExpr
					&& ACTIVITY_GETTERS.contains(((InvokeExpr) rhs).getMethodRef().getName())
					&& ((InstanceInvokeExpr) rhs).getBase().getType() instanceof RefType) {
				SootClass c = ((RefType) ((InstanceInvokeExpr) rhs).getBase().getType()).getSootClass();
				if (appClasses.containsKey(c) && isFragment(c)) {
					result.add(c);
				} else if (isUiOwner(m.getDeclaringClass())) {
					result.add(m.getDeclaringClass());
				}
			}
		});
		return result;
	}

	private boolean isUiOwner(SootClass c) {
		return activities.contains(c) || (appClasses.containsKey(c) && isFragment(c));
	}

	/**
	 * Activities and application fragments whose code calls into {@code method},
	 * by reverse call-graph search, stopping at the first such class on each path.
	 * Used when the transaction's receiver does not reveal its owner.
	 */
	private Set<SootClass> callerContexts(SootMethod method) {
		Set<SootClass> result = new LinkedHashSet<>();
		Set<SootMethod> seen = new HashSet<>();
		List<SootMethod> frontier = new ArrayList<>();
		frontier.add(method);
		seen.add(method);
		for (int d = 0; d < MAX_CALLER_DEPTH && !frontier.isEmpty(); d++) {
			List<SootMethod> next = new ArrayList<>();
			for (SootMethod m : frontier) {
				for (Object[] site : callSitesOf(m)) {
					SootMethod src = (SootMethod) site[0];
					if (!seen.add(src)) {
						continue;
					}
					SootClass c = src.getDeclaringClass();
					SootClass outer = c;
					while (outer != null && !isUiOwner(outer)) {
						outer = outerClass(outer);
					}
					if (outer != null) {
						result.add(outer);
					} else if (appClasses.containsKey(c)) {
						next.add(src);
					}
				}
			}
			frontier = next;
		}
		return result;
	}

	private void addConcrete(SootClass c, Set<SootClass> out) {
		if (c != null && !c.isAbstract() && !c.isInterface() && appClasses.containsKey(c)
				&& isFragment(c)) {
			out.add(c);
		}
	}

	private static SootClass classOfType(Type t) {
		if (t instanceof RefType) {
			return ((RefType) t).getSootClass();
		}
		return null;
	}

	// ------------------------------------------------------------------
	// Layout sources (1) and (3)
	// ------------------------------------------------------------------

	/** Layout names inflated as each activity's content view, read off the solver. */
	private Map<SootClass, Set<String>> activityLayouts() {
		Map<SootClass, Set<String>> result = new LinkedHashMap<>();
		FixpointSolver solver = output.getSolver();
		Map<NNode, SootClass> rootOwner = new HashMap<>();
		for (SootClass activity : activities) {
			for (NNode root : output.getActivityRoots(activity)) {
				rootOwner.put(root, activity);
			}
		}
		for (Map.Entry<NOpNode, Set<NLayoutIdNode>> e : solver.reachingLayoutIds.entrySet()) {
			NOpNode op = e.getKey();
			Set<SootClass> owners = new HashSet<>();
			if (op instanceof NInflate2OpNode) {
				Set<NWindowNode> windows = solver.reachingWindows.get(op);
				if (windows != null) {
					for (NWindowNode w : windows) {
						if (w instanceof NActivityNode) {
							owners.add(w.getClassType());
						}
					}
				}
			} else if (op instanceof NInflate1OpNode) {
				Set<NNode> results = solver.solutionResults.get(op);
				if (results != null) {
					for (NNode r : results) {
						SootClass a = rootOwner.get(r);
						if (a != null) {
							owners.add(a);
						}
					}
				}
			}
			for (SootClass owner : owners) {
				for (NLayoutIdNode id : e.getValue()) {
					String name = layoutName(id.getIdValue());
					if (name != null) {
						result.computeIfAbsent(owner, k -> new LinkedHashSet<>()).add(name);
					}
				}
			}
		}
		return result;
	}

	/** Layout name for a layout id, or null when the id is not a known layout. */
	public static String layoutName(Integer id) {
		if (id == null) {
			return null;
		}
		String name = XMLParser.Factory.getXMLParser().getApplicationRLayoutName(id);
		return (name == null || name.isEmpty()) ? null : name;
	}

	private void addFromXmlEntry(SootClass context, String entry) {
		// entry is "fragment:<class>" or "nav:<class>"
		int colon = entry.indexOf(':');
		String kind = entry.substring(0, colon);
		SootClass c = Scene.v().getSootClassUnsafe(entry.substring(colon + 1), false);
		if (c != null) {
			own(context, c, kind);
		}
	}

	/**
	 * Fragment classes declared in a layout, following {@code <include>}: each entry
	 * is {@code fragment:<fqcn>} for a static fragment tag or {@code nav:<fqcn>} for a
	 * navigation-graph destination reached through a nav host in the layout.
	 */
	private Set<String> fragmentsInLayout(String layout) {
		Set<String> cached = layoutFragmentsCache.get(layout);
		if (cached != null) {
			return cached;
		}
		Set<String> result = new LinkedHashSet<>();
		layoutFragmentsCache.put(layout, result); // guards include cycles
		for (File file : resourceFiles("layout", layout)) {
			Element root = parse(file);
			if (root != null) {
				collectLayoutFragments(root, result);
			}
		}
		return result;
	}

	private void collectLayoutFragments(Element elem, Set<String> out) {
		String tag = elem.getTagName();
		if ("include".equals(tag)) {
			String ref = attr(elem, "layout");
			if (ref != null && ref.startsWith("@layout/")) {
				out.addAll(fragmentsInLayout(ref.substring("@layout/".length())));
			}
		} else if ("fragment".equals(tag) || tag.endsWith("FragmentContainerView")) {
			String name = attr(elem, "name");
			if (name == null) {
				name = attr(elem, "class");
			}
			String fqcn = name != null ? qualify(name) : null;
			if (fqcn != null) {
				out.add("fragment:" + fqcn);
				SootClass c = Scene.v().getSootClassUnsafe(fqcn, false);
				boolean navHost = NAV_HOST_FRAGMENT.equals(fqcn)
						|| (c != null && extendsAny(c, Set.of(NAV_HOST_FRAGMENT)));
				String graph = attr(elem, "navGraph");
				if (navHost && graph != null && graph.startsWith("@navigation/")) {
					for (String dest : navigationDestinations(
							graph.substring("@navigation/".length()), new HashSet<>())) {
						out.add("nav:" + dest);
					}
				}
			}
		}
		NodeList children = elem.getChildNodes();
		for (int i = 0; i < children.getLength(); i++) {
			Node n = children.item(i);
			if (n instanceof Element) {
				collectLayoutFragments((Element) n, out);
			}
		}
	}

	private Set<String> navigationDestinations(String graph, Set<String> seen) {
		Set<String> result = new LinkedHashSet<>();
		if (!seen.add(graph)) {
			return result;
		}
		for (File file : resourceFiles("navigation", graph)) {
			Element root = parse(file);
			if (root != null) {
				collectDestinations(root, result, seen);
			}
		}
		return result;
	}

	private void collectDestinations(Element elem, Set<String> out, Set<String> seen) {
		String tag = elem.getTagName();
		if ("include".equals(tag)) {
			String ref = attr(elem, "graph");
			if (ref != null && ref.startsWith("@navigation/")) {
				out.addAll(navigationDestinations(ref.substring("@navigation/".length()), seen));
			}
		} else if (!"activity".equals(tag) && !"dialog".equals(tag) && !"navigation".equals(tag)) {
			String name = attr(elem, "name");
			String fqcn = name != null ? qualify(name) : null;
			if (fqcn != null) {
				out.add(fqcn);
			}
		}
		NodeList children = elem.getChildNodes();
		for (int i = 0; i < children.getLength(); i++) {
			Node n = children.item(i);
			if (n instanceof Element) {
				collectDestinations((Element) n, out, seen);
			}
		}
	}

	/** {@code res/<type>/<name>.xml} first, then qualified variants ({@code layout-land}, ...). */
	private List<File> resourceFiles(String type, String name) {
		if (resDir == null || resDir.isEmpty()) {
			return Collections.emptyList();
		}
		List<File> result = new ArrayList<>();
		File base = new File(resDir, type + File.separator + name + ".xml");
		if (base.isFile()) {
			result.add(base);
		}
		File[] dirs = new File(resDir).listFiles(
				f -> f.isDirectory() && f.getName().startsWith(type + "-"));
		if (dirs != null) {
			java.util.Arrays.sort(dirs);
			for (File dir : dirs) {
				File f = new File(dir, name + ".xml");
				if (f.isFile()) {
					result.add(f);
				}
			}
		}
		return result;
	}

	private static Element parse(File file) {
		try {
			DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
			DocumentBuilder builder = factory.newDocumentBuilder();
			Document doc = builder.parse(file);
			return doc.getDocumentElement();
		} catch (Exception e) {
			return null;
		}
	}

	/** Attribute value by local name, whatever prefix apktool chose for its namespace. */
	private static String attr(Element elem, String localName) {
		NamedNodeMap attrs = elem.getAttributes();
		for (int i = 0; i < attrs.getLength(); i++) {
			Attr a = (Attr) attrs.item(i);
			String n = a.getName();
			int colon = n.indexOf(':');
			String local = colon >= 0 ? n.substring(colon + 1) : n;
			if (local.equals(localName) && !n.startsWith("xmlns")) {
				return a.getValue();
			}
		}
		return null;
	}

	private String qualify(String name) {
		if (name.isEmpty()) {
			return null;
		}
		if (name.charAt(0) == '.') {
			return appPackage + name;
		}
		if (!name.contains(".")) {
			return appPackage + "." + name;
		}
		return name;
	}

	// ------------------------------------------------------------------
	// Host closure
	// ------------------------------------------------------------------

	private Map<SootClass, Set<SootClass>> closeHosts() {
		Map<SootClass, Set<SootClass>> hosts = new HashMap<>();
		boolean changed = true;
		int rounds = 0;
		while (changed && rounds++ < 16) {
			changed = false;
			for (Map.Entry<SootClass, Map<SootClass, Set<String>>> e : owned.entrySet()) {
				Set<SootClass> contextHosts = hostsOfContext(e.getKey(), hosts);
				if (contextHosts.isEmpty()) {
					continue;
				}
				for (SootClass fragment : e.getValue().keySet()) {
					if (hosts.computeIfAbsent(fragment, k -> new HashSet<>()).addAll(contextHosts)) {
						changed = true;
					}
				}
			}
		}
		Map<SootClass, Set<SootClass>> sorted = new TreeMap<>(
				(a, b) -> a.getName().compareTo(b.getName()));
		for (Map.Entry<SootClass, Set<SootClass>> e : hosts.entrySet()) {
			if (e.getValue().isEmpty()) {
				continue;
			}
			Set<SootClass> s = new java.util.TreeSet<>((a, b) -> a.getName().compareTo(b.getName()));
			s.addAll(e.getValue());
			sorted.put(e.getKey(), s);
		}
		return sorted;
	}

	/** Activities a piece of code in {@code context} runs under (see class comment). */
	private Set<SootClass> hostsOfContext(SootClass context, Map<SootClass, Set<SootClass>> hosts) {
		Set<SootClass> result = new HashSet<>();
		Deque<SootClass> work = new ArrayDeque<>();
		Map<SootClass, Integer> depth = new HashMap<>();
		work.add(context);
		depth.put(context, 0);
		while (!work.isEmpty()) {
			SootClass c = work.poll();
			int d = depth.get(c);
			if (activities.contains(c)) {
				result.addAll(launchedActivities(c));
				continue;
			}
			if (isFragment(c)) {
				result.addAll(hosts.getOrDefault(c, Collections.emptySet()));
				continue;
			}
			SootClass outer = outerClass(c);
			if (outer != null && !depth.containsKey(outer)) {
				depth.put(outer, d);
				work.add(outer);
				continue;
			}
			if (d >= MAX_ALLOCATOR_DEPTH) {
				continue;
			}
			for (SootClass a : allocators.getOrDefault(c, Collections.emptySet())) {
				if (!depth.containsKey(a)) {
					depth.put(a, d + 1);
					work.add(a);
				}
			}
		}
		return result;
	}

	/**
	 * The manifest activities that run code declared in activity {@code c}: {@code c}
	 * itself when declared, and every declared subclass. A transaction written in a
	 * shared base activity shows its fragment in each concrete activity, and the
	 * consumer joins on the runtime activity, which is never the base class. A class
	 * with no declared descendant (manifest unavailable) stands for itself.
	 */
	private Set<SootClass> launchedActivities(SootClass c) {
		Set<SootClass> result = new HashSet<>();
		for (SootClass a : declaredActivities()) {
			if (extendsClass(a, c)) {
				result.add(a);
			}
		}
		if (result.isEmpty()) {
			result.add(c);
		}
		return result;
	}

	private Set<SootClass> declaredActivities() {
		if (declaredActivities == null) {
			declaredActivities = new HashSet<>();
			try {
				for (Iterator<String> it = XMLParser.Factory.getXMLParser().getActivities(); it.hasNext();) {
					SootClass a = Scene.v().getSootClassUnsafe(it.next(), false);
					if (a != null && activities.contains(a)) {
						declaredActivities.add(a);
					}
				}
			} catch (RuntimeException e) {
				// no manifest view: every activity stands for itself
			}
		}
		return declaredActivities;
	}

	private static SootClass outerClass(SootClass c) {
		if (c.hasOuterClass()) {
			return c.getOuterClass();
		}
		String name = c.getName();
		int dollar = name.lastIndexOf('$');
		if (dollar <= 0) {
			return null;
		}
		return Scene.v().getSootClassUnsafe(name.substring(0, dollar), false);
	}
}
