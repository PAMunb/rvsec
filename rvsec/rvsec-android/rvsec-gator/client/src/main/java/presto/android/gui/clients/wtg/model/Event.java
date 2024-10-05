package presto.android.gui.clients.wtg.model;

import java.util.Objects;
import java.util.Set;
import java.util.stream.Collectors;

import presto.android.gui.graph.NObjectNode;
import presto.android.gui.wtg.ds.WTGEdge;
import soot.SootMethod;

public class Event {

	private String type;
	private Set<String> handlers;
	private int widgetId;
	private String widgetClass;
	private String widgetName;

	public Event(WTGEdge e) {
		this.type = e.getEventType().name();
		this.handlers = e.getEventHandlers().stream().map(SootMethod::getSignature).collect(Collectors.toSet());
		NObjectNode guiWidget = e.getGUIWidget();
		if(guiWidget != null) {
			this.widgetId = guiWidget.id;
			this.widgetClass = guiWidget.getClassType().getName();
			if(guiWidget.idNode != null) {
				this.widgetName = guiWidget.idNode.getIdName();
			}
		}
	}

	public String getType() {
		return type;
	}

	public Set<String> getHandlers() {
		return handlers;
	}

	public int getWidgetId() {
		return widgetId;
	}

	public String getWidgetClass() {
		return widgetClass;
	}

	public String getWidgetName() {
		return widgetName;
	}

	@Override
	public int hashCode() {
		return Objects.hash(handlers, type, widgetClass, widgetId, widgetName);
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj)
			return true;
		if ((obj == null) || (getClass() != obj.getClass()))
			return false;
		Event other = (Event) obj;
		return Objects.equals(handlers, other.handlers) && Objects.equals(type, other.type) && Objects.equals(widgetClass, other.widgetClass) && widgetId == other.widgetId && Objects.equals(widgetName, other.widgetName);
	}

	@Override
	public String toString() {
		return String.format("Event [type=%s, handlers=%s, widgetId=%s, widgetClass=%s, widgetName=%s]", type, handlers, widgetId, widgetClass, widgetName);
	}

}
