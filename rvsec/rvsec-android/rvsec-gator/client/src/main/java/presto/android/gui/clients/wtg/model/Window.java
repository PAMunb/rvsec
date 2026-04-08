package presto.android.gui.clients.wtg.model;

import java.util.Objects;

/**
 * Represents a window (Activity, Dialog, or other top-level UI container)
 * within the Window Transition Graph (WTG).
 *
 * <p>Each Window is identified by a numeric ID (derived from the GATOR
 * object-node ID) and its fully-qualified class name. Windows serve as
 * nodes in the WTG; {@link Transition} objects connect them as edges.</p>
 *
 * <p>Equality is based on both {@code id} and {@code name}, so two Window
 * instances are equal only when both fields match.</p>
 */
public class Window {

	private int id;
	private String name;

	/**
	 * Constructs a Window with the given numeric ID and class name.
	 *
	 * @param id   the numeric identifier for this window (from the GATOR node)
	 * @param name the fully-qualified class name of the window
	 */
	public Window(int id, String name) {
		this.id = id;
		this.name = name;
	}

	public int getId() {
		return id;
	}

	public String getName() {
		return name;
	}

	@Override
	public int hashCode() {
		return Objects.hash(id, name);
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj)
			return true;
		if ((obj == null) || (getClass() != obj.getClass()))
			return false;
		Window other = (Window) obj;
		return id == other.id && Objects.equals(name, other.name);
	}

	@Override
	public String toString() {
		return String.format("Window [id=%s, name=%s]", id, name);
	}

}
