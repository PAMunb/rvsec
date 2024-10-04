package presto.android.gui.clients.wtg;

import java.util.Objects;

import presto.android.gui.wtg.ds.WTGEdge;

@Deprecated
public class Edge {
	private Window source;
	private Window target;
	private String event;
	
	public Edge(WTGEdge edges) {
		//TODO
	}

	public Window getSource() {
		return source;
	}

	public void setSource(Window source) {
		this.source = source;
	}

	public Window getTarget() {
		return target;
	}

	public void setTarget(Window target) {
		this.target = target;
	}

	public String getEvent() {
		return event;
	}

	public void setEvent(String event) {
		this.event = event;
	}

	@Override
	public int hashCode() {
		return Objects.hash(event, source, target);
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj)
			return true;
		if ((obj == null) || (getClass() != obj.getClass()))
			return false;
		Edge other = (Edge) obj;
		return Objects.equals(event, other.event) && Objects.equals(source, other.source) && Objects.equals(target, other.target);
	}

	@Override
	public String toString() {
		return String.format("Edge [source=%s, target=%s, event=%s]", source.getClazz(), target.getClazz(), event);
	}
	
	

}
