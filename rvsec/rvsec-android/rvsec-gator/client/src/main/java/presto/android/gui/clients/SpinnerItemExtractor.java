/*
 * SpinnerItemExtractor.java — gh57 Group 5 (MVP).
 *
 * Extracts Spinner items populated programmatically via ArrayAdapter.
 * Item sources:
 *   (1) Literal constructor:
 *         new ArrayAdapter<>(ctx, layoutId, new String[]{"a","b","c"})
 *         new ArrayAdapter<>(ctx, layoutId, Arrays.asList("x","y"))
 *         new ArrayAdapter<>(ctx, layoutId, getResources().getStringArray(R.array.X))
 *   (2) Programmatic add:
 *         adapter.add(literalString)
 *         adapter.addAll(literalStringArray | getStringArray(R.array.X))
 *   (3) Array resource adapter:
 *         adapter = ArrayAdapter.createFromResource(ctx, R.array.X, layoutId)
 *   An R.array id resolves to its items through the function the client
 *   passes in (decoded arrays.xml keyed by the app's array ids).
 *
 * Resource ids (the findViewById argument and the R.array argument) are
 * int constants when the app's R class is final, and reads of a static
 * field of <pkg>.R$<type> when it is not; the field is resolved by its
 * type and name through the app's resource id map.
 *
 * Out of scope:
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
import java.util.function.BiFunction;
import java.util.function.IntFunction;

import presto.android.util.JimpleDefUtils;
import soot.Body;
import soot.Local;
import soot.SootClass;
import soot.SootFieldRef;
import soot.SootMethod;
import soot.Unit;
import soot.Value;
import soot.jimple.ArrayRef;
import soot.jimple.AssignStmt;
import soot.jimple.CastExpr;
import soot.jimple.InstanceInvokeExpr;
import soot.jimple.IntConstant;
import soot.jimple.InvokeExpr;
import soot.jimple.NewArrayExpr;
import soot.jimple.NewExpr;
import soot.jimple.SpecialInvokeExpr;
import soot.jimple.StaticFieldRef;
import soot.jimple.StaticInvokeExpr;
import soot.jimple.Stmt;
import soot.jimple.StringConstant;
import soot.toolkits.graph.ExceptionalUnitGraph;
import soot.toolkits.scalar.SimpleLocalDefs;

public final class SpinnerItemExtractor {

	private static final String ARRAY_ADAPTER = "android.widget.ArrayAdapter";
	private static final String RESOURCES = "android.content.res.Resources";

	public static final class Stats {
		public int spinnersDetected;
		public int literalConstructor;
		public int addCalls;
		public int resourceArrays;
		public int unresolved;

		@Override
		public String toString() {
			return "spinners=" + spinnersDetected
					+ " literal-constructor=" + literalConstructor
					+ " add/addAll=" + addCalls
					+ " resource-arrays=" + resourceArrays
					+ " unresolved=" + unresolved;
		}
	}

	private final Stats stats = new Stats();
	private final IntFunction<List<String>> arrayItems;
	private final BiFunction<String, String, Integer> resourceId;

	/**
	 * @param arrayItems items of an app array resource by its R.array id, or
	 *        {@code null} when the id is not an app array
	 * @param resourceId the app's resource id for a (type, name) pair, e.g.
	 *        ("array", "TimeZones"), or {@code null} when unknown
	 */
	public SpinnerItemExtractor(IntFunction<List<String>> arrayItems,
			BiFunction<String, String, Integer> resourceId) {
		this.arrayItems = arrayItems;
		this.resourceId = resourceId;
	}

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
		// Adapter creation statement → accumulated items. Keyed by the statement
		// that creates the adapter (createFromResource, or `$a = new ArrayAdapter`),
		// found through the reaching definitions of the adapter local, because the
		// compiler reuses one local for several adapters in the same method.
		Map<Unit, List<String>> siteItems = new LinkedHashMap<>();

		for (Unit unit : body.getUnits()) {
			if (!(unit instanceof Stmt)) continue;
			Stmt stmt = (Stmt) unit;
			if (!stmt.containsInvokeExpr()) continue;

			InvokeExpr ie = stmt.getInvokeExpr();
			String declClass = ie.getMethodRef().getDeclaringClass().getName();
			String name = ie.getMethodRef().getName();

			// (3) $adapter = ArrayAdapter.createFromResource(ctx, R.array.X, layoutId)
			if (ie instanceof StaticInvokeExpr
					&& "createFromResource".equals(name)
					&& ARRAY_ADAPTER.equals(declClass)
					&& ie.getArgCount() == 3
					&& stmt instanceof AssignStmt
					&& ((AssignStmt) stmt).getLeftOp() instanceof Local) {
				List<String> items = resolveArrayResource(ie.getArg(1), stmt, defs);
				if (items != null && !items.isEmpty()) {
					siteItems.put(stmt, new ArrayList<>(items));
					stats.resourceArrays++;
				} else {
					stats.unresolved++;
				}
				continue;
			}

			// (1) Literal constructor: $adapter = new ArrayAdapter; specialinvoke <init>(ctx, layoutId, items)
			if (ie instanceof SpecialInvokeExpr
					&& "<init>".equals(name)
					&& ARRAY_ADAPTER.equals(declClass)
					&& ie.getArgCount() >= 3) {
				List<Unit> sites = adapterSites(receiverLocal(ie), stmt, defs);
				if (sites.isEmpty()) continue;
				Value itemsArg = ie.getArg(ie.getArgCount() - 1);
				List<String> literals = resolveStringArray(itemsArg, stmt, defs, body);
				if (literals != null && !literals.isEmpty()) {
					for (Unit site : sites) {
						siteItems.computeIfAbsent(site, k -> new ArrayList<>()).addAll(literals);
					}
					stats.literalConstructor++;
				}
				continue;
			}

			// (2) adapter.add(s) / adapter.addAll(arr)
			if (ARRAY_ADAPTER.equals(declClass) && ie instanceof InstanceInvokeExpr) {
				List<Unit> sites = adapterSites(receiverLocal(ie), stmt, defs);
				if (sites.isEmpty()) continue;
				if ("add".equals(name) && ie.getArgCount() == 1) {
					String lit = JimpleDefUtils.resolveStr(ie.getArg(0), stmt, defs);
					if (lit != null) {
						for (Unit site : sites) {
							siteItems.computeIfAbsent(site, k -> new ArrayList<>()).add(lit);
						}
						stats.addCalls++;
					} else {
						stats.unresolved++;
					}
					continue;
				}
				if ("addAll".equals(name) && ie.getArgCount() == 1) {
					List<String> arr = resolveStringArray(ie.getArg(0), stmt, defs, body);
					if (arr != null && !arr.isEmpty()) {
						for (Unit site : sites) {
							siteItems.computeIfAbsent(site, k -> new ArrayList<>()).addAll(arr);
						}
						stats.addCalls++;
					} else {
						stats.unresolved++;
					}
					continue;
				}
			}

			// spinner.setAdapter(adapter) — bind items to a widget id.
			if ("setAdapter".equals(name)
					&& ie instanceof InstanceInvokeExpr
					&& ie.getArgCount() == 1) {
				Local adapter = (ie.getArg(0) instanceof Local) ? (Local) ie.getArg(0) : null;
				List<String> items = null;
				for (Unit site : adapterSites(adapter, stmt, defs)) {
					List<String> created = siteItems.get(site);
					if (created == null) continue;
					if (items == null) items = new ArrayList<>();
					items.addAll(created);
				}
				if (items == null) continue;
				Integer widgetId = resolveSpinnerWidgetId(
						((InstanceInvokeExpr) ie).getBase(), stmt, defs);
				if (widgetId == null) {
					stats.unresolved++;
					continue;
				}
				// The same spinner is often bound in several methods (create and
				// edit flows) with the same array; keep each item once.
				List<String> entries = result.computeIfAbsent(widgetId, k -> new ArrayList<>());
				for (String item : items) {
					if (!entries.contains(item)) entries.add(item);
				}
				stats.spinnersDetected++;
			}
		}
	}

	/**
	 * The statements that created the adapter held by {@code adapter} at
	 * {@code site}: every reaching definition, through casts. An adapter
	 * assigned in both branches of an if/else has two, and the spinner it is
	 * bound to takes the items of both.
	 */
	private static List<Unit> adapterSites(Local adapter, Stmt site, SimpleLocalDefs defs) {
		List<Unit> sites = new ArrayList<>();
		if (adapter != null) collectAdapterSites(adapter, site, defs, sites, 8);
		return sites;
	}

	private static void collectAdapterSites(
			Local local, Stmt site, SimpleLocalDefs defs, List<Unit> sites, int castGuard) {
		List<Unit> reaching;
		try {
			reaching = defs.getDefsOfAt(local, site);
		} catch (RuntimeException ex) {
			// SimpleLocalDefs throws on malformed bodies; treat as unresolved.
			return;
		}
		for (Unit u : reaching) {
			if (!(u instanceof AssignStmt)) continue;
			AssignStmt def = (AssignStmt) u;
			if (def.getRightOp() instanceof CastExpr) {
				Value op = ((CastExpr) def.getRightOp()).getOp();
				if (op instanceof Local && castGuard > 0) {
					collectAdapterSites((Local) op, def, defs, sites, castGuard - 1);
				}
			} else if (!sites.contains(def)) {
				sites.add(def);
			}
		}
	}

	/**
	 * Resolve {@code base} (the receiver of setAdapter) to its underlying
	 * Spinner widget id by walking back to a findViewById(R.id.X) call.
	 *
	 * <p>The canonical Jimple shape for {@code Spinner s = (Spinner) findViewById(R.id.foo)}
	 * is two statements: {@code $r1 = findViewById($id); $r2 = (Spinner) $r1}.
	 * The def of {@code s} therefore points at a {@link CastExpr}, not the
	 * {@link InvokeExpr}. We recurse on {@code castExpr.getOp()} (bounded by
	 * the chain length — typically 1) until we reach the underlying invoke
	 * or fail (no single reaching def). Without this, every Spinner declared
	 * with the typical cast pattern surfaces in {@code widgets[]} with an
	 * empty {@code entries[]} even when the ArrayAdapter items were
	 * recovered (codex review 2026-05-15, defect #7).
	 */
	private Integer resolveSpinnerWidgetId(Value base, Stmt useSite, SimpleLocalDefs defs) {
		if (!(base instanceof Local)) return null;
		AssignStmt def = singleDef((Local) base, useSite, defs);
		// Unwrap one or more chained CastExpr defs (e.g. `(View) $r1` then
		// `(Spinner) $r2` — uncommon but seen in interop code).
		int castGuard = 8;
		while (def != null && def.getRightOp() instanceof CastExpr && castGuard-- > 0) {
			Value op = ((CastExpr) def.getRightOp()).getOp();
			if (!(op instanceof Local)) return null;
			def = singleDef((Local) op, def, defs);
		}
		if (def != null && def.getRightOp() instanceof InvokeExpr) {
			InvokeExpr call = (InvokeExpr) def.getRightOp();
			if ("findViewById".equals(call.getMethodRef().getName())
					&& call.getArgCount() == 1) {
				// Resolved at the findViewById statement, not at setAdapter: the
				// compiler reuses the id register, so between the two statements
				// it can be overwritten (e.g. by the R.array id of createFromResource).
				return resolveResourceId(call.getArg(0), def, defs);
			}
		}
		return null;
	}

	/** The single assignment of {@code local} reaching {@code site}, or null. */
	private static AssignStmt singleDef(Local local, Stmt site, SimpleLocalDefs defs) {
		try {
			List<Unit> reaching = defs.getDefsOfAt(local, site);
			if (reaching.size() == 1 && reaching.get(0) instanceof AssignStmt) {
				return (AssignStmt) reaching.get(0);
			}
		} catch (RuntimeException ex) {
			// SimpleLocalDefs throws on malformed bodies; treat as unresolved.
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
		AssignStmt def = singleDef(local, useSite, defs);
		Value rhs = def == null ? null : def.getRightOp();
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
			String name = ie.getMethodRef().getName();
			// getResources().getStringArray(R.array.X) / getTextArray(R.array.X)
			if (RESOURCES.equals(declClass)
					&& ("getStringArray".equals(name) || "getTextArray".equals(name))
					&& ie.getArgCount() == 1) {
				List<String> items = resolveArrayResource(ie.getArg(0), def, defs);
				if (items != null) stats.resourceArrays++;
				return items;
			}
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

	/** Items of the app array resource whose R.array id is {@code idArg}, or null. */
	private List<String> resolveArrayResource(Value idArg, Stmt useSite, SimpleLocalDefs defs) {
		Integer id = resolveResourceId(idArg, useSite, defs);
		return id == null ? null : arrayItems.apply(id);
	}

	/**
	 * A resource id passed as an int constant, or read from a static field of
	 * {@code <pkg>.R$<type>} and resolved by (type, field name).
	 */
	private Integer resolveResourceId(Value arg, Stmt useSite, SimpleLocalDefs defs) {
		Integer constant = JimpleDefUtils.resolveInt(arg, useSite, defs);
		if (constant != null) return constant;
		Value v = (arg instanceof Local)
				? JimpleDefUtils.definitionRhs((Local) arg, useSite, defs) : arg;
		if (!(v instanceof StaticFieldRef)) return null;
		SootFieldRef field = ((StaticFieldRef) v).getFieldRef();
		String owner = field.declaringClass().getShortName();
		if (!owner.startsWith("R$")) return null;
		return resourceId.apply(owner.substring(2), field.name());
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
