/*
 * MenuExtractor.java — gh57 Group 4
 *
 * Extracts options-menu items from activities that build the menu
 * programmatically inside onCreateOptionsMenu(Menu) via Menu.add(...) /
 * Menu.addSubMenu(...) calls (the XML-inflation path is handled separately
 * by RvsecAnalysisClient.extractWindows walking NOptionsMenuNode children;
 * see design.md D7).
 *
 * Algorithm:
 *   1. For each activity, locate onCreateOptionsMenu(Menu).
 *   2. Build an ExceptionalUnitGraph over its body.
 *   3. Scan units for InterfaceInvokeExpr / VirtualInvokeExpr targeting
 *      android.view.Menu.add(int,int,int,CharSequence) /
 *      android.view.Menu.add(int,int,int,int) /
 *      android.view.Menu.addSubMenu(...) (same four-arg shapes).
 *   4. Resolve the four arguments (groupId, itemId, order, title) via:
 *        - direct Constant arg (the common case in Jimple), or
 *        - SimpleLocalDefs back-walk to the latest DefinitionStmt of the
 *          local in the current unit's predecessors.
 *      Int title arg is treated as a @string resource id and resolved
 *      against the existing string-resource helper passed in from the
 *      caller (RvsecAnalysisClient.resolveStringByResId).
 *   5. addSubMenu return value is tracked: subsequent SubMenu.add(...)
 *      invokes on that local (via def-use equivalence) become the
 *      submenu's items[] entries.
 *
 * Resilience: per-method try/catch covers RuntimeException and
 * OutOfMemoryError; failures emit a WARN and the activity's menu list
 * remains empty. INV-ANA-24.
 */
package presto.android.gui.clients;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Function;

import presto.android.util.JimpleDefUtils;
import soot.Body;
import soot.Local;
import soot.SootClass;
import soot.SootMethod;
import soot.Unit;
import soot.Value;
import soot.jimple.AssignStmt;
import soot.jimple.IntConstant;
import soot.jimple.InvokeExpr;
import soot.jimple.Stmt;
import soot.jimple.StringConstant;
import soot.toolkits.graph.ExceptionalUnitGraph;
import soot.toolkits.scalar.SimpleLocalDefs;

public final class MenuExtractor {

	// android.view.Menu#add and addSubMenu — four-arg overloads only (MVP).
	// The single-arg overloads (CharSequence) and (int) are rarely seen in
	// non-trivial menus and are out of MVP scope; cover them if corpus
	// scans surface a meaningful population.
	private static final String MENU_CLASS = "android.view.Menu";
	private static final String SUBMENU_CLASS = "android.view.SubMenu";

	private final Function<Integer, String> resIdResolver;

	/**
	 * @param resIdResolver maps a resource id (int title from
	 *     Menu.add(int,int,int,int)) to its localized string, or returns
	 *     null when not resolvable. Caller supplies a closure over
	 *     RvsecAnalysisClient's R.string lookup chain.
	 */
	public MenuExtractor(Function<Integer, String> resIdResolver) {
		this.resIdResolver = resIdResolver;
	}

	/**
	 * Extract menu items from an activity's onCreateOptionsMenu method.
	 * Returns an empty list when the method is absent, abstract, or fails
	 * to retrieve a body. Each item map carries: id, groupId, order, text,
	 * type ("MenuItem" or "SubMenu"); SubMenu maps include an items[] list
	 * of nested item maps.
	 */
	public List<Map<String, Object>> extractItems(SootClass activity) {
		SootMethod onCreate = findOnCreateOptionsMenu(activity);
		if (onCreate == null || !onCreate.isConcrete()) {
			return Collections.emptyList();
		}
		try {
			Body body = onCreate.retrieveActiveBody();
			if (body == null) {
				return Collections.emptyList();
			}
			ExceptionalUnitGraph cfg = new ExceptionalUnitGraph(body);
			SimpleLocalDefs defs = new SimpleLocalDefs(cfg);
			return extractItemsFromBody(cfg, defs);
		} catch (RuntimeException | OutOfMemoryError ex) {
			System.out.println("[MenuExtractor] WARN body retrieval failed for "
					+ activity.getName() + ".onCreateOptionsMenu: " + ex.getMessage());
			return Collections.emptyList();
		}
	}

	private SootMethod findOnCreateOptionsMenu(SootClass activity) {
		for (SootMethod m : activity.getMethods()) {
			if (!"onCreateOptionsMenu".equals(m.getName())) continue;
			if (m.getParameterCount() != 1) continue;
			if (!"android.view.Menu".equals(m.getParameterType(0).toString())) continue;
			return m;
		}
		return null;
	}

	private List<Map<String, Object>> extractItemsFromBody(
			ExceptionalUnitGraph cfg, SimpleLocalDefs defs) {
		List<Map<String, Object>> items = new ArrayList<>();
		// Track SubMenu locals → their item maps so subsequent .add(...) on
		// the same receiver are appended to the right submenu.
		Map<Local, List<Map<String, Object>>> submenuItems = new LinkedHashMap<>();

		for (Unit unit : cfg.getBody().getUnits()) {
			if (!(unit instanceof Stmt)) continue;
			Stmt stmt = (Stmt) unit;
			if (!stmt.containsInvokeExpr()) continue;

			InvokeExpr ie = stmt.getInvokeExpr();
			String declClass = ie.getMethodRef().getDeclaringClass().getName();
			String name = ie.getMethodRef().getName();

			boolean onMenu = MENU_CLASS.equals(declClass);
			boolean onSub = SUBMENU_CLASS.equals(declClass);
			if (!onMenu && !onSub) continue;
			if (!"add".equals(name) && !"addSubMenu".equals(name)) continue;
			if (ie.getArgCount() != 4) continue;

			Map<String, Object> item = resolveFourArgItem(ie, stmt, defs);
			if (item == null) continue;

			if ("addSubMenu".equals(name)) {
				item.put("type", "SubMenu");
				List<Map<String, Object>> subItems = new ArrayList<>();
				item.put("items", subItems);
				// Track the receiver of the next SubMenu.add(...) calls.
				Local lhs = lhsLocal(stmt);
				if (lhs != null) {
					submenuItems.put(lhs, subItems);
				}
				items.add(item);
				continue;
			}

			if (onSub) {
				// Append to the matching submenu (receiver-based lookup).
				Local rcv = receiverLocal(ie);
				List<Map<String, Object>> bucket = (rcv != null) ? submenuItems.get(rcv) : null;
				if (bucket != null) {
					item.put("type", "MenuItem");
					bucket.add(item);
					continue;
				}
				// Orphan SubMenu.add — surface at top level so the data is
				// not silently dropped.
				item.put("type", "MenuItem");
				items.add(item);
				continue;
			}

			// Menu.add(int, int, int, CharSequence | int)
			item.put("type", "MenuItem");
			items.add(item);
		}
		return items;
	}

	private Map<String, Object> resolveFourArgItem(
			InvokeExpr ie, Stmt useSite, SimpleLocalDefs defs) {
		Integer groupId = JimpleDefUtils.resolveInt(ie.getArg(0), useSite, defs);
		Integer itemId  = JimpleDefUtils.resolveInt(ie.getArg(1), useSite, defs);
		Integer order   = JimpleDefUtils.resolveInt(ie.getArg(2), useSite, defs);
		// itemId is the only field consumers actually key on. Tolerate
		// unresolved groupId/order so a partly-dynamic call still surfaces
		// (matches the per-Spinner partial-emission rule in Group 5).
		if (itemId == null) return null;

		// Pre-populate every key that writeWidget(JsonWriter) consumes — the
		// MenuExtractor output is unioned with collectWidgets output, so
		// missing keys break the serializer (notably `entries` which is
		// dereferenced as a List, not null-checked).
		Map<String, Object> item = new LinkedHashMap<>();
		item.put("id", itemId);
		item.put("idName", "");
		item.put("groupId", groupId != null ? groupId : 0);
		item.put("order", order != null ? order : 0);
		item.put("text", resolveTitle(ie.getArg(3), useSite, defs));
		item.put("hint", "");
		item.put("inputType", "");
		item.put("entries", java.util.Collections.emptyList());
		item.put("prompt", null);
		item.put("spinnerMode", null);
		item.put("contentDescription", null);
		item.put("tooltipText", null);
		item.put("listeners", java.util.Collections.emptyList());
		return item;
	}

	private String resolveTitle(Value arg, Stmt useSite, SimpleLocalDefs defs) {
		Value v = (arg instanceof Local) ? JimpleDefUtils.definitionRhs((Local) arg, useSite, defs) : arg;
		if (v instanceof StringConstant) {
			return ((StringConstant) v).value;
		}
		if (v instanceof IntConstant && resIdResolver != null) {
			String resolved = resIdResolver.apply(((IntConstant) v).value);
			if (resolved != null) return resolved;
		}
		return "";
	}

	private static Local lhsLocal(Stmt stmt) {
		if (stmt instanceof AssignStmt) {
			Value lhs = ((AssignStmt) stmt).getLeftOp();
			if (lhs instanceof Local) return (Local) lhs;
		}
		return null;
	}

	private static Local receiverLocal(InvokeExpr ie) {
		try {
			if (ie instanceof soot.jimple.InstanceInvokeExpr) {
				Value base = ((soot.jimple.InstanceInvokeExpr) ie).getBase();
				if (base instanceof Local) return (Local) base;
			}
		} catch (RuntimeException ignore) {
			// Defensive: getBase() can throw on some malformed expressions.
		}
		return null;
	}
}
