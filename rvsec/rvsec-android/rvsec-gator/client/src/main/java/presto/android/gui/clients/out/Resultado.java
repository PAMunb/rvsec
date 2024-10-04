package presto.android.gui.clients.out;

import java.util.HashSet;
import java.util.Set;

public class Resultado {

	private Set<Janela> windows = new HashSet<>();
	private Set<Transicao> transitions = new HashSet<>();

	public Set<Janela> getWindows() {
		return windows;
	}

	public void setWindows(Set<Janela> windows) {
		this.windows = windows;
	}

	public Set<Transicao> getTransitions() {
		return transitions;
	}

	public void setTransitions(Set<Transicao> transitions) {
		this.transitions = transitions;
	}

	public void addWindow(Janela window) {
		windows.add(window);
	}
	
	public void addTransition(Transicao transition) {
		transitions.add(transition);
	}

}
