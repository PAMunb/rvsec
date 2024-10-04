package presto.android.gui.clients.wtg;

import java.util.Objects;

import presto.android.gui.graph.NObjectNode;

@Deprecated
public class Window {
	private int id;
	private String clazz;

	public Window(NObjectNode node) {
		this(node.id, node.getClassType().getName());
	}

	public Window(int id, String clazz) {
		this.id = id;
		this.clazz = clazz;
	}

	public int getId() {
		return id;
	}

	public void setId(int id) {
		this.id = id;
	}

	public String getClazz() {
		return clazz;
	}

	public void setClazz(String clazz) {
		this.clazz = clazz;
	}

	@Override
	public int hashCode() {
		return Objects.hash(clazz, id);
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj)
			return true;
		if ((obj == null) || (getClass() != obj.getClass()))
			return false;
		Window other = (Window) obj;
		return Objects.equals(clazz, other.clazz) && id == other.id;
	}

	@Override
	public String toString() {
		return String.format("Window [id=%s, clazz=%s]", id, clazz);
	}

}
