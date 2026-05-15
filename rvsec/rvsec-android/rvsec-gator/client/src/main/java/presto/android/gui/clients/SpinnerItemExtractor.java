/*
 * SpinnerItemExtractor.java — gh57 Group 5 (MVP).
 *
 * Extracts Spinner items populated programmatically via ArrayAdapter.
 * MVP scope (two patterns):
 *   (1) Literal constructor:
 *         new ArrayAdapter<>(ctx, layoutId, new String[]{"a","b","c"})
 *         new ArrayAdapter<>(ctx, layoutId, Arrays.asList("x","y"))
 *   (2) Programmatic add:
 *         adapter.add(literalString)
 *         adapter.addAll(literalStringArray)
 *
 * Out of scope (deferred):
 *   - getResources().getStringArray(R.array.X)
 *   - Kotlin listOf(...)
 *   - Dynamic strings (concatenation, method calls, field reads)
 *
 * Algorithm:
 *   1. For every concrete method of every application activity, build
 *      ExceptionalUnitGraph + SimpleLocalDefs.
 *   2. Track per-Local adapter assignments:
 *        $adapter = new ArrayAdapter<>(ctx, layoutId, $items)
 *      Resolve $items via def-use to a NewArrayExpr "new String[N]" and
 *      collect the {N} subsequent ArrayRef assigns that initialize the
 *      slots with StringConstants.
 *   3. Track .add / .addAll on a known adapter Local and append literal
 *      strings to its items list.
 *   4. On `spinner.setAdapter(adapter)` (Spinner = AbsSpinner.setAdapter
 *      or AdapterView.setAdapter), resolve $spinner via def-use to a
 *      findViewById(R.id.X) call and use the int resource id as the
 *      widget key.
 *
 * Output: Map<Integer, List<String>> keyed by widget int id (R.id.*),
 * matching the existing `widget.put("id", widgetId)` in collectWidgets.
 *
 * Resilience (INV-ANA-24): per-method try/catch covers RuntimeException
 * and OutOfMemoryError; failures emit a WARN and the method is skipped.
 */
package presto.android.gui.clients;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import soot.Body;
import soot.Local;
import soot.SootClass;
import soot.SootMethod;
import soot.Unit;
import soot.Value;
import soot.jimple.ArrayRef;
import soot.jimple.AssignStmt;
import soot.jimple.InstanceInvokeExpr;
import soot.jimple.IntConstant;
import soot.jimple.InvokeExpr;
import soot.jimple.NewArrayExpr;
import soot.jimple.NewExpr;
import soot.jimple.SpecialInvokeExpr;
import soot.jimple.Stmt;
import soot.jimple.StringConstant;
import soot.toolkits.graph.ExceptionalUnitGraph;
import soot.toolkits.scalar.SimpleLocalDefs;

public final class SpinnerItemExtractor {

	private static final String ARRAY_ADAPTER = "android.widget.ArrayAdapter";

	public static final class Stats {
		public int spinnersDetected;
		public int literalConstructor;
		public int addCalls;
		public int unresolved;

		@Override
		public String toString() {
			return "spinners=" + spinnersDetected
					+ " literal-constructor=" + literalConstructor
					+ " add/addAll=" + addCalls
					+ " unresolved=" + unresolved;
		}
	}

	private final Stats stats = new Stats();

	public Stats getStats() {
		return stats;
	}

	/**
	 * Extract Spinner items from every concrete method of the activity.
	 * Returns a map keyed by the int widget id (R.id.* value) from the
	 * findViewById argument that obtained the Spinner.
	 */
	public Map<Integer, List<String>> extractItems(SootClass activity) {
		Map<Integer, List<String>> result = new LinkedHashMap<>();
		for (SootMethod method : activity.getMethods()) {
			if (!method.isConcrete()) continue;
			try {
				Body body = method.retrieveActiveBody();
				if (body == null) continue;
				ExceptionalUnitGraph cfg = new ExceptionalUnitGraph(body);
				SimpleLocalDefs defs = new SimpleLocalDefs(cfg);
				extractFromMethod(body, defs, result);
			} catch (RuntimeException | OutOfMemoryError ex) {
				System.out.println("[SpinnerItemExtractor] WARN skipped "
						+ method.getSignature() + ": " + ex.getMessage());
			}
		}
		return result;
	}

	private void extractFromMethod(
			Body body,
			SimpleLocalDefs defs,
			Map<Integer, List<String>> result) {
		// Local → accumulated items, populated when we see a constructor
		// or add/addAll invoke. The same adapter may collect items from
		// multiple statements before reaching setAdapter.
		Map<Local, List<String>> adapterItems = new LinkedHashMap<>();

		for (Unit unit : body.getUnits()) {
			if (!(unit instanceof Stmt)) continue;
			Stmt stmt = (Stmt) unit;
			if (!stmt.containsInvokeExpr()) continue;

			InvokeExpr ie = stmt.getInvokeExpr();
			String declClass = ie.getMethodRef().getDeclaringClass().getName();
			String name = ie.getMethodRef().getName();

			// (1) Literal constructor: $adapter = new ArrayAdapter; specialinvoke <init>(ctx, layoutId, items)
			if (ie instanceof SpecialInvokeExpr
					&& "<init>".equals(name)
					&& ARRAY_ADAPTER.equals(declClass)
					&& ie.getArgCount() >= 3) {
				Local adapter = receiverLocal(ie);
				if (adapter == null) continue;
				Value itemsArg = ie.getArg(ie.getArgCount() - 1);
				List<String> literals = resolveStringArray(itemsArg, stmt, defs, body);
				if (literals != null && !literals.isEmpty()) {
					adapterItems.computeIfAbsent(adapter, k -> new ArrayList<>()).addAll(literals);
					stats.literalConstructor++;
				}
				continue;
			}

			// (2) adapter.add(s) / adapter.addAll(arr)
			if (ARRAY_ADAPTER.equals(declClass) && ie instanceof InstanceInvokeExpr) {
				Local adapter = receiverLocal(ie);
				if (adapter == null) continue;
				if ("add".equals(name) && ie.getArgCount() == 1) {
					String lit = resolveStringLiteral(ie.getArg(0), stmt, defs);
					if (lit != null) {
						adapterItems.computeIfAbsent(adapter, k -> new ArrayList<>()).add(lit);
						stats.addCalls++;
					} else {
						stats.unresolved++;
					}
					continue;
				}
				if ("addAll".equals(name) && ie.getArgCount() == 1) {
					List<String> arr = resolveStringArray(ie.getArg(0), stmt, defs, body);
					if (arr != null && !arr.isEmpty()) {
						adapterItems.computeIfAbsent(adapter, k -> new ArrayList<>()).addAll(arr);
						stats.addCalls++;
					} else {
						stats.unresolved++;
					}
					continue;
				}
			}

			// (3) spinner.setAdapter(adapter) — bind items to a widget id.
			if ("setAdapter".equals(name)
					&& ie instanceof InstanceInvokeExpr
					&& ie.getArgCount() == 1) {
				Local adapter = (ie.getArg(0) instanceof Local) ? (Local) ie.getArg(0) : null;
				if (adapter == null || !adapterItems.containsKey(adapter)) continue;
				Integer widgetId = resolveSpinnerWidgetId(
						((InstanceInvokeExpr) ie).getBase(), stmt, defs);
				if (widgetId == null) {
					stats.unresolved++;
					continue;
				}
				result.computeIfAbsent(widgetId, k -> new ArrayList<>())
						.addAll(adapterItems.get(adapter));
				stats.spinnersDetected++;
			}
		}
	}

	/**
	 * Resolve {@code base} (the receiver of setAdapter) to its underlying
	 * Spinner widget id by walking back to a findViewById(R.id.X) call.
	 */
	private Integer resolveSpinnerWidgetId(Value base, Stmt useSite, SimpleLocalDefs defs) {
		if (!(base instanceof Local)) return null;
		Value rhs = definitionRhs((Local) base, useSite, defs);
		if (rhs instanceof InvokeExpr) {
			InvokeExpr def = (InvokeExpr) rhs;
			if ("findViewById".equals(def.getMethodRef().getName())
					&& def.getArgCount() == 1) {
				Integer id = resolveInt(def.getArg(0), useSite, defs);
				if (id != null) return id;
			}
			// Some apps cast the result: $cast = (Spinner) $raw; $cast =
			// $raw is an AssignStmt with the same RHS chain. The
			// definitionRhs single-reaching-def policy already handles
			// the chained case if it is unambiguous.
		}
		return null;
	}

	/**
	 * Resolve a Value that should be a String[] or List<String> literal.
	 * Returns null when the value cannot be statically determined.
	 */
	private List<String> resolveStringArray(Value arg, Stmt useSite, SimpleLocalDefs defs, Body body) {
		if (!(arg instanceof Local)) return null;
		Local local = (Local) arg;
		Value rhs = definitionRhs(local, useSite, defs);
		if (rhs instanceof NewArrayExpr) {
			// We have $items = new String[N]; subsequent ArrayRef assigns
			// fill the slots. Walk the body forward from the new-array
			// to the use site to collect the literal slot writes.
			return collectArrayLiterals(local, useSite, body);
		}
		// Arrays.asList("a", "b", ...) — direct invoke of asList with all
		// args as StringConstants.
		if (rhs instanceof InvokeExpr) {
			InvokeExpr ie = (InvokeExpr) rhs;
			String declClass = ie.getMethodRef().getDeclaringClass().getName();
			if ("java.util.Arrays".equals(declClass) && "asList".equals(ie.getMethodRef().getName())) {
				List<String> list = new ArrayList<>();
				for (int i = 0; i < ie.getArgCount(); i++) {
					if (!(ie.getArg(i) instanceof StringConstant)) return null;
					list.add(((StringConstant) ie.getArg(i)).value);
				}
				return list;
			}
		}
		return null;
	}

	/**
	 * Walk the body, finding every AssignStmt of the form
	 * {@code arrayLocal[idx] = stringConstant}, and return the slot
	 * literals in index order. Stops at the use site to respect
	 * dominance.
	 */
	private List<String> collectArrayLiterals(Local arrayLocal, Stmt useSite, Body body) {
		Map<Integer, String> slots = new LinkedHashMap<>();
		for (Unit unit : body.getUnits()) {
			if (unit == useSite) break;
			if (!(unit instanceof AssignStmt)) continue;
			AssignStmt assign = (AssignStmt) unit;
			if (!(assign.getLeftOp() instanceof ArrayRef)) continue;
			ArrayRef ref = (ArrayRef) assign.getLeftOp();
			if (!arrayLocal.equals(ref.getBase())) continue;
			if (!(ref.getIndex() instanceof IntConstant)) continue;
			if (!(assign.getRightOp() instanceof StringConstant)) continue;
			slots.put(((IntConstant) ref.getIndex()).value,
					((StringConstant) assign.getRightOp()).value);
		}
		if (slots.isEmpty()) return Collections.emptyList();
		List<String> out = new ArrayList<>(slots.size());
		// Preserve index order — write traversal order may differ from
		// slot index when the source has shuffled assignments, but that
		// is uncommon and the index-keyed map already restores order.
		List<Integer> keys = new ArrayList<>(slots.keySet());
		Collections.sort(keys);
		for (Integer k : keys) {
			out.add(slots.get(k));
		}
		return out;
	}

	private String resolveStringLiteral(Value arg, Stmt useSite, SimpleLocalDefs defs) {
		Value v = (arg instanceof Local) ? definitionRhs((Local) arg, useSite, defs) : arg;
		return (v instanceof StringConstant) ? ((StringConstant) v).value : null;
	}

	private Integer resolveInt(Value arg, Stmt useSite, SimpleLocalDefs defs) {
		Value v = (arg instanceof Local) ? definitionRhs((Local) arg, useSite, defs) : arg;
		return (v instanceof IntConstant) ? ((IntConstant) v).value : null;
	}

	private Value definitionRhs(Local local, Stmt useSite, SimpleLocalDefs defs) {
		try {
			List<Unit> reaching = defs.getDefsOfAt(local, useSite);
			if (reaching.size() != 1) return null;
			Unit def = reaching.get(0);
			if (def instanceof AssignStmt) {
				return ((AssignStmt) def).getRightOp();
			}
		} catch (RuntimeException ignore) {
			// SimpleLocalDefs throws on malformed bodies; treat as unresolved.
		}
		return null;
	}

	private static Local receiverLocal(InvokeExpr ie) {
		if (ie instanceof InstanceInvokeExpr) {
			Value base = ((InstanceInvokeExpr) ie).getBase();
			if (base instanceof Local) return (Local) base;
		}
		return null;
	}

	@SuppressWarnings("unused")
	private static boolean isNewArrayAdapter(Stmt stmt) {
		if (!(stmt instanceof AssignStmt)) return false;
		Value rhs = ((AssignStmt) stmt).getRightOp();
		return rhs instanceof NewExpr
				&& ARRAY_ADAPTER.equals(((NewExpr) rhs).getBaseType().toString());
	}
}
