package presto.android.gui.clients.hosted;

import java.util.ArrayDeque;
import java.util.Collections;
import java.util.Deque;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

import presto.android.Hierarchy;
import soot.Body;
import soot.Scene;
import soot.SootClass;
import soot.SootMethod;
import soot.Unit;
import soot.Value;
import soot.ValueBox;
import soot.jimple.ClassConstant;
import soot.jimple.InvokeExpr;
import soot.jimple.NewExpr;
import soot.jimple.StaticInvokeExpr;
import soot.jimple.Stmt;

/**
 * Answers "on which activity can code of class C put a view on screen?".
 *
 * <p>An activity hosts itself. Any other application class is hosted by the
 * activities that reach it backwards through three relations, followed
 * transitively:
 * <ul>
 *   <li><b>nesting</b> — {@code Act$1}, {@code Act$Adapter} and Kotlin lambda
 *       classes run on behalf of their outer class;</li>
 *   <li><b>use</b> — class D uses C when D's code allocates C ({@code new C}),
 *       calls a static method of C ({@code C.newInstance()},
 *       {@code CBinding.inflate(...)}), names {@code C.class} (fragment
 *       transactions), or inflates a layout holding a view of class C (a
 *       custom view declared in XML, recorded by the caller);</li>
 *   <li><b>subclassing</b> — code inherited from an abstract base runs on the
 *       hosts of its concrete subclasses.</li>
 * </ul>
 * An application activity class that is not declared in the manifest (a base
 * activity) is hosted by its declared subclasses. The search is breadth-first
 * and stops at the first distance that reaches an activity, so a class used
 * directly by one activity is not also attributed to every activity a longer
 * chain (dependency-injection components, shared helpers) happens to reach.
 * Within that distance it over-approximates: a helper used by two activities is
 * reported under both.
 */
final class HostResolver {

	private static final int MAX_DEPTH = 6;

	private final Set<SootClass> activities;
	private final Set<SootClass> appClasses;
	private final Map<SootClass, Set<SootClass>> users = new HashMap<>();
	private final Map<SootClass, Set<SootClass>> memo = new HashMap<>();
	private final SootClass activityRoot;

	HostResolver(Set<SootClass> activities) {
		this.activities = activities;
		this.appClasses = Hierarchy.v().appClasses;
		this.activityRoot = Scene.v().containsClass("android.app.Activity")
				? Scene.v().getSootClass("android.app.Activity") : null;
		indexUses();
	}

	boolean isAppClass(SootClass c) {
		return appClasses.contains(c);
	}

	/** Host activities of {@code c}, sorted by name; empty when none is found. */
	Set<SootClass> hostsOf(SootClass c) {
		Set<SootClass> cached = memo.get(c);
		if (cached != null) return cached;
		Set<SootClass> result = new TreeSet<>((a, b) -> a.getName().compareTo(b.getName()));
		Set<SootClass> seen = new HashSet<>();
		Deque<SootClass> frontier = new ArrayDeque<>();
		frontier.add(c);
		seen.add(c);
		for (int depth = 0; depth <= MAX_DEPTH && !frontier.isEmpty(); depth++) {
			Deque<SootClass> next = new ArrayDeque<>();
			for (SootClass x : frontier) {
				if (activities.contains(x)) {
					result.add(x);
					continue;
				}
				if (isAppActivity(x)) {
					for (SootClass a : activities) {
						if (isSubclass(a, x)) result.add(a);
					}
					continue;
				}
				for (SootClass y : neighbours(x)) {
					if (seen.add(y)) next.add(y);
				}
			}
			if (!result.isEmpty()) break;
			frontier = next;
		}
		Set<SootClass> frozen = Collections.unmodifiableSet(result);
		memo.put(c, frozen);
		return frozen;
	}

	private Set<SootClass> neighbours(SootClass x) {
		Set<SootClass> out = new LinkedHashSet<>();
		SootClass outer = outerOf(x);
		if (outer != null) out.add(outer);
		out.addAll(users.getOrDefault(x, Collections.emptySet()));
		try {
			for (SootClass sub : Hierarchy.v().getSubtypes(x)) {
				if (sub != x && appClasses.contains(sub)) out.add(sub);
			}
		} catch (RuntimeException ignored) {
			// Hierarchy has no entry for the class; nesting and use still apply.
		}
		return out;
	}

	private SootClass outerOf(SootClass x) {
		if (x.hasOuterClass() && appClasses.contains(x.getOuterClass())) {
			return x.getOuterClass();
		}
		String name = x.getName();
		int i = name.lastIndexOf('$');
		while (i > 0) {
			String outerName = name.substring(0, i);
			if (Scene.v().containsClass(outerName)) {
				SootClass o = Scene.v().getSootClass(outerName);
				if (appClasses.contains(o)) return o;
			}
			i = outerName.lastIndexOf('$');
			name = outerName;
		}
		return null;
	}

	private boolean isAppActivity(SootClass x) {
		return activityRoot != null && appClasses.contains(x) && isSubclass(x, activityRoot);
	}

	private static boolean isSubclass(SootClass child, SootClass parent) {
		SootClass c = child;
		while (c != null) {
			if (c == parent) return true;
			c = c.hasSuperclass() ? c.getSuperclass() : null;
		}
		return false;
	}

	private void indexUses() {
		for (SootClass d : appClasses) {
			if (d.isPhantom()) continue;
			for (SootMethod m : d.getMethods()) {
				if (!m.isConcrete()) continue;
				Body b;
				try {
					b = m.hasActiveBody() ? m.getActiveBody() : m.retrieveActiveBody();
				} catch (RuntimeException e) {
					continue;
				}
				for (Unit u : b.getUnits()) {
					Stmt s = (Stmt) u;
					for (ValueBox vb : s.getUseBoxes()) {
						Value v = vb.getValue();
						if (v instanceof NewExpr) {
							use(((NewExpr) v).getBaseType().getSootClass(), d);
						} else if (v instanceof ClassConstant) {
							String t = ((ClassConstant) v).getValue();
							if (t.startsWith("L") && t.endsWith(";")) {
								String cn = t.substring(1, t.length() - 1).replace('/', '.');
								if (Scene.v().containsClass(cn)) use(Scene.v().getSootClass(cn), d);
							}
						}
					}
					if (s.containsInvokeExpr()) {
						InvokeExpr ie = s.getInvokeExpr();
						if (ie instanceof StaticInvokeExpr) {
							try {
								use(ie.getMethodRef().getDeclaringClass(), d);
							} catch (RuntimeException ignored) {
								// unresolved callee
							}
						}
					}
				}
			}
		}
	}

	/** Records that {@code user} uses {@code used}; must precede the first {@link #hostsOf}. */
	void use(SootClass used, SootClass user) {
		if (used == null || used == user || !appClasses.contains(used)) return;
		users.computeIfAbsent(used, k -> new LinkedHashSet<>()).add(user);
	}
}
