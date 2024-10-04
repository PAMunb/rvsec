package presto.android.gui.clients.wtg;

import java.util.Objects;

import presto.android.gui.graph.NObjectNode;

@Deprecated
public class Widget {
	private int id;
	private String clazz;
	private String name;

	public Widget(int id, String clazz, String name) {
		this.id = id;
		this.clazz = clazz;
		this.name = name;
	}
	
	public Widget(NObjectNode node) {
		this.id = node.id;
		this.clazz = node.getClassType().getName();
		if(node.idNode != null) {
			this.name = node.idNode.getIdName();
		}
	}

	public int getId() {
		return id;
	}

	public String getClazz() {
		return clazz;
	}

	public String getName() {
		return name;
	}

	@Override
	public int hashCode() {
		return Objects.hash(clazz, id, name);
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj)
			return true;
		if ((obj == null) || (getClass() != obj.getClass()))
			return false;
		Widget other = (Widget) obj;
		return Objects.equals(clazz, other.clazz) && id == other.id && Objects.equals(name, other.name);
	}

	@Override
	public String toString() {
		return String.format("Widget [id=%s, clazz=%s, name=%s]", id, clazz, name);
	}

}
