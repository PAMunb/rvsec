package presto.android.gui.clients.wtg;

import java.util.Objects;
import java.util.Set;
import java.util.stream.Collectors;

import presto.android.gui.wtg.ds.WTGEdge;
import soot.SootMethod;

@Deprecated
public class Event {
	private String type;
	private Set<String> eventHandlers;

	private Widget widget;

	public Event(WTGEdge e) {
		this.type = e.getEventType().name();
		this.eventHandlers = e.getEventHandlers().stream().map(SootMethod::getSignature).collect(Collectors.toSet());
		this.widget = new Widget(e.getGUIWidget());
	}

	public String getType() {
		return type;
	}


	public Set<String> getEventHandlers() {
		return eventHandlers;
	}

	public Widget getWidget() {
		return widget;
	}

	@Override
	public int hashCode() {
		return Objects.hash(eventHandlers, type, widget);
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj)
			return true;
		if ((obj == null) || (getClass() != obj.getClass()))
			return false;
		Event other = (Event) obj;
		return Objects.equals(eventHandlers, other.eventHandlers) && Objects.equals(type, other.type) && Objects.equals(widget, other.widget);
	}

	@Override
	public String toString() {
		return String.format("Event [type=%s, eventHandlers=%s, widget=%s]", type, eventHandlers, widget);
	}

}
