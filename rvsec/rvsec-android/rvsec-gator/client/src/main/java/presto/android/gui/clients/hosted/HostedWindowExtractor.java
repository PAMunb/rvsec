package presto.android.gui.clients.hosted;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

import presto.android.gui.GUIAnalysisOutput;
import presto.android.gui.clients.fragment.FragmentWindows;
import presto.android.gui.graph.NDialogNode;
import presto.android.gui.graph.NInflate1OpNode;
import presto.android.gui.graph.NNode;
import presto.android.gui.graph.NObjectNode;
import presto.android.gui.graph.NOpNode;
import soot.SootClass;
import soot.SootMethod;

/**
 * Emits the views that GATOR inflates outside an activity's own content view
 * (dialog bodies, DialogFragment and fragment views, adapter rows, binding
 * layouts) as windows named {@code HostActivity#OwnerClass}.
 *
 * <p>The solver already builds these view trees: every {@code inflate} call
 * site yields a root in {@code operationNodeAndResults()}, and every dialog
 * GATOR allocates has roots of its own. What it lacks is the activity the user
 * sees them on. {@link HostResolver} recovers it from the class that holds the
 * inflating code, so the widgets join the host's bucket in the consumer, which
 * keys every window by the text before {@code #}.
 *
 * <p>The windows carry type {@value #TYPE}, never {@code DIALOG}: the consumer
 * re-keys a DIALOG window onto the source of its first WTG edge and would drag
 * the whole host bucket along with a {@code Host#...} name. They are produced
 * from solver state alone, so they appear in the pre-WTG artefact too.
 *
 * <p>There is one window per (host, owner): a fragment view that the fragment pass
 * already emitted as a {@code FRAGMENT} window of the same name is not emitted again
 * here (D6, INV-ANA-76).
 */
public final class HostedWindowExtractor {

	/** Window type of the emitted windows. */
	public static final String TYPE = "HOSTED";

	/**
	 * An owner whose code is reachable from more activities than this is a
	 * shared helper; emitting it everywhere multiplies the artefact without
	 * telling the explorer where the view appears.
	 */
	private static final int MAX_HOSTS = 20;

	/** Walks one view tree into the client's widget records. */
	@FunctionalInterface
	public interface WidgetCollector {
		void collect(NNode root, List<Map<String, Object>> widgets, Set<NNode> visited);
	}

	private final GUIAnalysisOutput output;
	private final WidgetCollector collector;
	private final HostResolver hosts;

	public HostedWindowExtractor(GUIAnalysisOutput output, WidgetCollector collector) {
		this.output = output;
		this.collector = collector;
		this.hosts = new HostResolver(output.getActivities());
	}

	/**
	 * Appends the hosted windows to {@code windows}, numbered from {@code firstId}
	 * and skipping every name a {@code FRAGMENT} window in {@code windows} already
	 * holds, then attaches the listeners registered through binding fields to the
	 * widgets of every activity, fragment and hosted window.
	 */
	public void extendInto(List<Map<String, Object>> windows, int firstId) {
		// A failure here costs only the hosted windows, never the rest of the report.
		try {
			Set<String> fragmentNames = new HashSet<>();
			for (Map<String, Object> w : windows) {
				if (FragmentWindows.WINDOW_TYPE.equals(w.get("type"))) {
					fragmentNames.add((String) w.get("name"));
				}
			}
			windows.addAll(extract(fragmentNames, firstId));
			applyBindingListeners(windows);
		} catch (RuntimeException e) {
			System.out.println("[RvsecAnalysisClient] Hosted window pass failed: " + e);
		}
	}

	@SuppressWarnings("unchecked")
	private void applyBindingListeners(List<Map<String, Object>> windows) {
		List<BindingListenerRecovery.Site> sites = BindingListenerRecovery.scan(hosts);
		Map<String, List<Map<String, Object>>> windowsByBase = new HashMap<>();
		for (Map<String, Object> w : windows) {
			String type = (String) w.get("type");
			if (!"ACTIVITY".equals(type) && !TYPE.equals(type)
					&& !FragmentWindows.WINDOW_TYPE.equals(type)) continue;
			String name = (String) w.get("name");
			int i = name.indexOf('#');
			windowsByBase.computeIfAbsent(i >= 0 ? name.substring(0, i) : name, k -> new ArrayList<>()).add(w);
		}
		int added = 0;
		for (BindingListenerRecovery.Site site : sites) {
			for (SootClass host : hosts.hostsOf(site.owner)) {
				for (Map<String, Object> w : windowsByBase.getOrDefault(host.getName(), Collections.emptyList())) {
					for (Map<String, Object> widget : (List<Map<String, Object>>) w.get("widgets")) {
						String idName = (String) widget.get("idName");
						if (idName == null || idName.isEmpty()
								|| !BindingListenerRecovery.key(idName).equals(site.key)) continue;
						List<Map<String, Object>> listeners = (List<Map<String, Object>>) widget.get("listeners");
						boolean present = false;
						for (Map<String, Object> l : listeners) {
							present |= site.handler.equals(l.get("handler")) && site.eventType.equals(l.get("eventType"));
						}
						if (present) continue;
						Map<String, Object> listener = new LinkedHashMap<>();
						listener.put("eventType", site.eventType);
						listener.put("handler", site.handler);
						listeners.add(listener);
						added++;
					}
				}
			}
		}
		System.out.println("[HostedWindowExtractor] bindingListenerSites=" + sites.size()
				+ " listenersAdded=" + added);
	}

	/** Builds the hosted windows not named in {@code skipNames}; never null. */
	List<Map<String, Object>> extract(Set<String> skipNames, int firstId) {
		// owner class -> view roots built by code in that class
		Map<SootClass, Set<NNode>> rootsByOwner = new LinkedHashMap<>();
		int inflateSites = 0;
		for (Map.Entry<NOpNode, Set<NNode>> e : output.operationNodeAndResults().entrySet()) {
			NOpNode op = e.getKey();
			if (!(op instanceof NInflate1OpNode) || op.callSite == null) continue;
			SootMethod m = op.callSite.getO2();
			if (m == null || !hosts.isAppClass(m.getDeclaringClass())) continue;
			Set<NNode> roots = objectRoots(e.getValue());
			if (roots.isEmpty()) continue;
			inflateSites++;
			rootsByOwner.computeIfAbsent(m.getDeclaringClass(), k -> new LinkedHashSet<>()).addAll(roots);
		}
		int dialogs = 0;
		for (NDialogNode dialog : output.getDialogs()) {
			if (dialog.allocMethod == null) continue;
			SootClass owner = dialog.allocMethod.getDeclaringClass();
			if (!hosts.isAppClass(owner)) continue;
			Set<NNode> roots = objectRoots(output.getDialogRoots(dialog));
			if (roots.isEmpty()) continue;
			dialogs++;
			rootsByOwner.computeIfAbsent(owner, k -> new LinkedHashSet<>()).addAll(roots);
		}

		// A custom view class placed in a layout is used by whoever inflates
		// that layout; its own inflations (and binding classes it calls) are
		// then hosted where the layout is shown.
		for (SootClass activity : output.getActivities()) {
			markLayoutUsers(output.getActivityRoots(activity), activity);
		}
		for (Map.Entry<SootClass, Set<NNode>> e : rootsByOwner.entrySet()) {
			markLayoutUsers(e.getValue(), e.getKey());
		}
		int navEdges = NavGraphUses.record(output, hosts);

		// window name -> roots, sorted so ids are stable across runs
		Map<String, Set<NNode>> rootsByWindow = new TreeMap<>();
		int orphanOwners = 0;
		int sharedOwners = 0;
		for (Map.Entry<SootClass, Set<NNode>> e : rootsByOwner.entrySet()) {
			Set<SootClass> owners = hosts.hostsOf(e.getKey());
			if (owners.isEmpty()) {
				orphanOwners++;
				continue;
			}
			if (owners.size() > MAX_HOSTS) {
				sharedOwners++;
				continue;
			}
			for (SootClass host : owners) {
				String name = host.getName() + "#" + e.getKey().getName();
				rootsByWindow.computeIfAbsent(name, k -> new LinkedHashSet<>()).addAll(e.getValue());
			}
		}

		List<Map<String, Object>> windows = new ArrayList<>();
		int nextId = firstId;
		int widgetCount = 0;
		int fragmentDuplicates = 0;
		for (Map.Entry<String, Set<NNode>> e : rootsByWindow.entrySet()) {
			if (skipNames.contains(e.getKey())) {
				fragmentDuplicates++;
				continue;
			}
			List<Map<String, Object>> widgets = new ArrayList<>();
			Set<NNode> visited = new HashSet<>();
			for (NNode root : e.getValue()) {
				collector.collect(root, widgets, visited);
			}
			if (widgets.isEmpty()) continue;
			Map<String, Object> window = new LinkedHashMap<>();
			window.put("id", nextId++);
			window.put("name", e.getKey());
			window.put("type", TYPE);
			window.put("isMain", false);
			window.put("widgets", widgets);
			windows.add(window);
			widgetCount += widgets.size();
		}
		System.out.println("[HostedWindowExtractor] inflateSites=" + inflateSites
				+ " dialogs=" + dialogs + " navEdges=" + navEdges + " owners=" + rootsByOwner.size()
				+ " orphanOwners=" + orphanOwners + " sharedOwners=" + sharedOwners
				+ " fragmentDuplicates=" + fragmentDuplicates
				+ " windows=" + windows.size() + " widgets=" + widgetCount);
		return windows;
	}

	private void markLayoutUsers(Set<NNode> roots, SootClass user) {
		ArrayDeque<NNode> stack = new ArrayDeque<>(roots);
		Set<NNode> seen = new HashSet<>(roots);
		while (!stack.isEmpty()) {
			NNode n = stack.pop();
			if (n instanceof NObjectNode) {
				hosts.use(((NObjectNode) n).getClassType(), user);
			}
			for (NNode c : n.getChildren()) {
				if (seen.add(c)) stack.push(c);
			}
		}
	}

	private static Set<NNode> objectRoots(Set<NNode> nodes) {
		if (nodes == null) return Collections.emptySet();
		Set<NNode> roots = new LinkedHashSet<>();
		for (NNode n : nodes) {
			if (n instanceof NObjectNode) roots.add(n);
		}
		return roots;
	}
}
