package presto.android.gui.clients.hosted;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

import presto.android.Hierarchy;
import presto.android.gui.listener.ListenerRegistration;
import presto.android.gui.listener.ListenerSpecification;
import soot.Body;
import soot.Local;
import soot.Scene;
import soot.SootClass;
import soot.SootField;
import soot.SootMethod;
import soot.Unit;
import soot.Value;
import soot.jimple.AssignStmt;
import soot.jimple.CastExpr;
import soot.jimple.IdentityStmt;
import soot.jimple.InstanceFieldRef;
import soot.jimple.InstanceInvokeExpr;
import soot.jimple.InvokeExpr;
import soot.jimple.NewExpr;
import soot.jimple.Stmt;
import soot.jimple.ThisRef;

/**
 * Recovers listeners registered through a binding field,
 * {@code binding.someView.setOnClickListener(l)}.
 *
 * <p>DataBinding fills its view fields from an {@code Object[]} that the
 * library builds, so the flowgraph never connects a binding field to the view
 * it holds and the solver attaches no listener. The generated field is named
 * after the view id ({@code settings_btn} becomes {@code settingsBtn}), which is
 * enough to find the widget: the registration's receiver is read from a field
 * of a binding class, the field name matched against the widget ids of the
 * windows the registering code is hosted on. The listener object must be a
 * local allocation ({@code new K}, which covers lambdas) or {@code this}; any
 * other origin is skipped rather than guessed. ViewBinding fields are matched
 * the same way; a listener the solver already attached through a modelled
 * {@code findChildViewById} is not added twice.
 */
final class BindingListenerRecovery {

	/** One registration: code in {@code owner} sets a listener on the view behind {@code field}. */
	static final class Site {
		final SootClass owner;
		final String key;
		final String eventType;
		final String handler;

		Site(SootClass owner, String key, String eventType, String handler) {
			this.owner = owner;
			this.key = key;
			this.eventType = eventType;
			this.handler = handler;
		}
	}

	private BindingListenerRecovery() {
	}

	/** Normalized id used on both sides: lower case, no underscores. */
	static String key(String idOrField) {
		return idOrField.replace("_", "").toLowerCase(Locale.ROOT);
	}

	static List<Site> scan(HostResolver hosts) {
		List<Site> sites = new ArrayList<>();
		SootClass vdb = classOrNull("androidx.databinding.ViewDataBinding");
		SootClass vb = classOrNull("androidx.viewbinding.ViewBinding");
		if (vdb == null && vb == null) return sites;
		ListenerSpecification specs = ListenerSpecification.v();
		for (SootClass d : Hierarchy.v().appClasses) {
			if (d.isPhantom()) continue;
			for (SootMethod m : d.getMethods()) {
				if (!m.isConcrete() || !m.hasActiveBody()) continue;
				Body b = m.getActiveBody();
				Map<Local, Value> defs = singleDefs(b);
				for (Unit u : b.getUnits()) {
					Stmt s = (Stmt) u;
					if (!s.containsInvokeExpr() || !(s.getInvokeExpr() instanceof InstanceInvokeExpr)) continue;
					ListenerRegistration reg;
					try {
						reg = specs.getListenerRegistration(s);
					} catch (RuntimeException e) {
						continue;
					}
					if (reg == null) continue;
					InvokeExpr ie = s.getInvokeExpr();
					SootField field = bindingField(((InstanceInvokeExpr) ie).getBase(), defs, vdb, vb);
					if (field == null) continue;
					if (reg.position < 0 || reg.position >= ie.getArgCount()) continue;
					SootClass listener = listenerClass(ie.getArg(reg.position), defs, d);
					if (listener == null) continue;
					for (SootMethod proto : reg.getHandlerPrototypes()) {
						SootMethod h = findMethod(listener, proto.getSubSignature());
						if (h != null) {
							sites.add(new Site(d, key(field.getName()), reg.eventType.toString().toLowerCase(),
									h.getSignature()));
						}
					}
				}
			}
		}
		return sites;
	}

	private static Map<Local, Value> singleDefs(Body b) {
		Map<Local, Value> defs = new HashMap<>();
		Map<Local, Integer> count = new HashMap<>();
		for (Unit u : b.getUnits()) {
			Value lhs = null;
			Value rhs = null;
			if (u instanceof AssignStmt) {
				lhs = ((AssignStmt) u).getLeftOp();
				rhs = ((AssignStmt) u).getRightOp();
			} else if (u instanceof IdentityStmt) {
				lhs = ((IdentityStmt) u).getLeftOp();
				rhs = ((IdentityStmt) u).getRightOp();
			}
			if (lhs instanceof Local) {
				count.merge((Local) lhs, 1, Integer::sum);
				defs.put((Local) lhs, rhs);
			}
		}
		count.forEach((l, n) -> {
			if (n > 1) defs.remove(l);
		});
		return defs;
	}

	private static Value strip(Value v, Map<Local, Value> defs) {
		for (int i = 0; i < 4 && v instanceof Local; i++) {
			Value d = defs.get(v);
			if (d == null) return v;
			v = d instanceof CastExpr ? ((CastExpr) d).getOp() : d;
		}
		return v;
	}

	private static SootField bindingField(Value receiver, Map<Local, Value> defs, SootClass vdb, SootClass vb) {
		Value v = strip(receiver, defs);
		if (!(v instanceof InstanceFieldRef)) return null;
		SootField f;
		try {
			f = ((InstanceFieldRef) v).getField();
		} catch (RuntimeException e) {
			return null;
		}
		return isBinding(f.getDeclaringClass(), vdb, vb) ? f : null;
	}

	private static boolean isBinding(SootClass c, SootClass vdb, SootClass vb) {
		for (SootClass x = c; x != null; x = x.hasSuperclass() ? x.getSuperclass() : null) {
			if (x == vdb) return true;
			if (vb != null && x.getInterfaces().contains(vb)) return true;
		}
		return false;
	}

	private static SootClass listenerClass(Value arg, Map<Local, Value> defs, SootClass owner) {
		Value v = strip(arg, defs);
		if (v instanceof NewExpr) return ((NewExpr) v).getBaseType().getSootClass();
		if (v instanceof ThisRef) return owner;
		return null;
	}

	private static SootMethod findMethod(SootClass c, String subsig) {
		for (SootClass x = c; x != null; x = x.hasSuperclass() ? x.getSuperclass() : null) {
			SootMethod m = x.getMethodUnsafe(subsig);
			if (m != null && m.isConcrete()) return m;
		}
		return null;
	}

	private static SootClass classOrNull(String name) {
		return Scene.v().containsClass(name) ? Scene.v().getSootClass(name) : null;
	}
}
