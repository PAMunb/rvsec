package presto.android.gui.clients.wtg.model;

import java.util.HashSet;
import java.util.Set;

public class Result {

	private Set<Window> windows = new HashSet<>();
	private Set<Transition> transitions = new HashSet<>();

	public Set<Window> getWindows() {
		return windows;
	}

	public Set<Transition> getTransitions() {
		return transitions;
	}

	public void addWindow(Window window) {
		if (window != null) {
			windows.add(window);
		}
	}

	public void addTransition(Transition transition) {
		if (transition != null) {
			transitions.add(transition);
		}
	}

}
