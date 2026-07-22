package presto.android.gui.clients.wtg.model;

import java.util.HashSet;
import java.util.Set;

/**
 * Aggregates the complete output of a GATOR Window Transition Graph (WTG)
 * analysis for a single Android application.
 *
 * <p>A Result contains the set of discovered {@link Window} nodes and the
 * set of {@link Transition} edges that connect them. It is the top-level
 * object serialized to JSON by {@link presto.android.gui.clients.wtg.writer.Writer}
 * and later consumed by the RV-Android testing tools (rv-static-analysis)
 * to build the application's navigation model.</p>
 *
 * <p>Null-safe: both {@link #addWindow(Window)} and
 * {@link #addTransition(Transition)} silently ignore {@code null} arguments.</p>
 */
public class Result {

	private Set<Window> windows = new HashSet<>();
	private Set<Transition> transitions = new HashSet<>();

	/** @return the set of all discovered windows in the WTG */
	public Set<Window> getWindows() {
		return windows;
	}

	/** @return the set of all transitions (edges) in the WTG */
	public Set<Transition> getTransitions() {
		return transitions;
	}

	/**
	 * Adds a window to the result set. Null values are silently ignored.
	 *
	 * @param window the window to add, or {@code null} (no-op)
	 */
	public void addWindow(Window window) {
		if (window != null) {
			windows.add(window);
		}
	}

	/**
	 * Adds a transition to the result set. Null values are silently ignored.
	 *
	 * @param transition the transition to add, or {@code null} (no-op)
	 */
	public void addTransition(Transition transition) {
		if (transition != null) {
			transitions.add(transition);
		}
	}

}
