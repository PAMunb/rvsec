package presto.android.gui.clients.hosted;

import java.io.File;
import java.util.ArrayDeque;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;

import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NamedNodeMap;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

import presto.android.Configs;
import presto.android.gui.GUIAnalysisOutput;
import presto.android.gui.graph.NNode;
import presto.android.gui.graph.NObjectNode;
import soot.Scene;
import soot.SootClass;

/**
 * Hosts the destinations of a Navigation graph on the activity that shows it.
 *
 * <p>Navigation instantiates its fragments by reflection from
 * {@code res/navigation/*.xml}, so no code edge leads from the activity to them.
 * The graph is bound in a layout: the {@code NavHostFragment} /
 * {@code FragmentContainerView} element carries {@code app:navGraph} and an
 * {@code android:id}. An activity whose view tree holds a view with that id
 * shows the graph, and each destination class (and nested graph, followed
 * through {@code <include app:graph>}) is recorded as used by it.
 */
final class NavGraphUses {

	private NavGraphUses() {
	}

	static int record(GUIAnalysisOutput output, HostResolver hosts) {
		String res = Configs.resourceLocation;
		if (res == null || res.isEmpty()) return 0;
		Map<String, Set<String>> destinations = new HashMap<>(); // graph -> classes
		Map<String, Set<String>> includes = new HashMap<>(); // graph -> graphs
		Map<String, Set<String>> graphsByHostId = new HashMap<>(); // view id -> graphs
		File[] dirs = new File(res).listFiles();
		if (dirs == null) return 0;
		for (File dir : dirs) {
			boolean nav = dir.getName().startsWith("navigation");
			boolean layout = dir.getName().startsWith("layout");
			if (!nav && !layout) continue;
			File[] files = dir.listFiles((d, n) -> n.endsWith(".xml"));
			if (files == null) continue;
			for (File f : files) {
				Document doc = parse(f);
				if (doc == null) continue;
				String graph = f.getName().substring(0, f.getName().length() - 4);
				NodeList all = doc.getElementsByTagName("*");
				for (int i = 0; i < all.getLength(); i++) {
					Element e = (Element) all.item(i);
					if (nav) {
						String name = attr(e, "name");
						if (name != null && !"navigation".equals(e.getTagName())) {
							destinations.computeIfAbsent(graph, k -> new HashSet<>()).add(name);
						}
						String inc = attr(e, "graph");
						if (inc != null && inc.startsWith("@navigation/")) {
							includes.computeIfAbsent(graph, k -> new HashSet<>()).add(inc.substring(12));
						}
					} else {
						String g = attr(e, "navGraph");
						String id = attr(e, "id");
						if (g != null && g.startsWith("@navigation/") && id != null && id.contains("/")) {
							graphsByHostId.computeIfAbsent(id.substring(id.indexOf('/') + 1), k -> new HashSet<>())
									.add(g.substring(12));
						}
					}
				}
			}
		}
		if (graphsByHostId.isEmpty()) return 0;
		int edges = 0;
		for (SootClass activity : output.getActivities()) {
			for (String graph : graphsShownBy(output.getActivityRoots(activity), graphsByHostId)) {
				for (String cls : closure(graph, destinations, includes)) {
					if (!Scene.v().containsClass(cls)) continue;
					hosts.use(Scene.v().getSootClass(cls), activity);
					edges++;
				}
			}
		}
		return edges;
	}

	private static Set<String> graphsShownBy(Set<NNode> roots, Map<String, Set<String>> graphsByHostId) {
		Set<String> graphs = new LinkedHashSet<>();
		ArrayDeque<NNode> stack = new ArrayDeque<>(roots);
		Set<NNode> seen = new HashSet<>(roots);
		while (!stack.isEmpty()) {
			NNode n = stack.pop();
			if (n instanceof NObjectNode && ((NObjectNode) n).idNode != null) {
				Set<String> g = graphsByHostId.get(((NObjectNode) n).idNode.getIdName());
				if (g != null) graphs.addAll(g);
			}
			for (NNode c : n.getChildren()) {
				if (seen.add(c)) stack.push(c);
			}
		}
		return graphs;
	}

	private static Set<String> closure(String graph, Map<String, Set<String>> destinations,
			Map<String, Set<String>> includes) {
		Set<String> classes = new HashSet<>();
		Set<String> seen = new HashSet<>();
		ArrayDeque<String> todo = new ArrayDeque<>();
		todo.add(graph);
		while (!todo.isEmpty()) {
			String g = todo.pop();
			if (!seen.add(g)) continue;
			classes.addAll(destinations.getOrDefault(g, new HashSet<>()));
			todo.addAll(includes.getOrDefault(g, new HashSet<>()));
		}
		return classes;
	}

	/** Attribute by local name, whatever the namespace prefix apktool kept. */
	private static String attr(Element e, String local) {
		NamedNodeMap attrs = e.getAttributes();
		for (int i = 0; i < attrs.getLength(); i++) {
			Node a = attrs.item(i);
			String n = a.getNodeName();
			int colon = n.indexOf(':');
			if ((colon >= 0 ? n.substring(colon + 1) : n).equals(local)) return a.getNodeValue();
		}
		return null;
	}

	private static Document parse(File f) {
		try {
			DocumentBuilder b = DocumentBuilderFactory.newInstance().newDocumentBuilder();
			return b.parse(f);
		} catch (Exception e) {
			return null;
		}
	}
}
