package presto.android.gui.clients.wtg;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

@Deprecated
public class Graph {
	private Map<Window, Map<Window, Set<Event>>> adjacency;
	private Set<Window> windows;

	public Graph() {
		adjacency = new HashMap<>();
		windows = new HashSet<>();
	}

	public void addWindow(Window vertex) {
		if (windows.add(vertex)) {
			adjacency.put(vertex, new HashMap<>());
		}
	}

	public void addTransition(Window source, Window target, Event event) {
		if (source.equals(target)) {
			return;
		}

		addWindow(source);
		addWindow(target);

		Set<Event> events = adjacency.get(source).get(target);
		if (events == null) {
			events = new HashSet<>();
			adjacency.get(source).put(target, events);
		}
		events.add(event);
	}

	public Set<Window> getWindows() {
		return windows;
	}

	public Map<Window, Set<Event>> getSuccessors(Window window) {
		if(window == null || !adjacency.containsKey(window)) {
			return new HashMap<>();
		}
		return adjacency.get(window);
	}
}
