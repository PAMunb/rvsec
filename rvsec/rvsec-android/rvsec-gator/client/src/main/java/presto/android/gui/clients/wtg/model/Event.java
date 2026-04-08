package presto.android.gui.clients.wtg.model;

import java.util.Objects;

import presto.android.gui.graph.NObjectNode;
import presto.android.gui.wtg.EventHandler;

/**
 * Represents a UI event within the Window Transition Graph (WTG).
 *
 * <p>An Event captures the type of user interaction (e.g., click, long-click),
 * the handler method that processes the event, and the target widget's identity
 * (resource ID, class, and name). Events are extracted from GATOR's
 * {@link EventHandler} during static analysis and serialized to JSON as part
 * of the WTG output consumed by the RV-Android testing tools.</p>
 *
 * <p>Equality is based on all fields, so two events are considered identical
 * only when they share the same type, handler, widget ID, class, and name.</p>
 */
public class Event {

	private String type;
	private String handler;
	private int widgetId;
	private String widgetClass;
	private String widgetName;

	/**
	 * Constructs an Event from a GATOR {@link EventHandler}.
	 *
	 * <p>Extracts the event type, handler signature, and widget metadata.
	 * If the widget has an associated {@code idNode}, the resource name and
	 * numeric ID are taken from it (overriding the raw object node ID).</p>
	 *
	 * @param e the GATOR event handler to convert
	 */
	public Event(EventHandler e) {
		this.type = e.getEvent().toString();
		this.handler = (e.getEventHandler() == null) ? "" : e.getEventHandler().getSignature();
		if (e.getWidget() != null) {
			NObjectNode guiWidget = e.getWidget();
			this.widgetId = guiWidget.id;
			this.widgetClass = guiWidget.getClassType().getName();
			if (guiWidget.idNode != null) {
				this.widgetName = guiWidget.idNode.getIdName();
				this.widgetId = guiWidget.idNode.getIdValue();
			}
		}
	}

	public String getType() {
		return type;
	}

	public String getHandler() {
		return handler;
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
		return Objects.hash(handler, type, widgetClass, widgetId, widgetName);
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj)
			return true;
		if ((obj == null) || (getClass() != obj.getClass()))
			return false;
		Event other = (Event) obj;
		return Objects.equals(handler, other.handler) && Objects.equals(type, other.type) && Objects.equals(widgetClass, other.widgetClass) && widgetId == other.widgetId && Objects.equals(widgetName, other.widgetName);
	}

	@Override
	public String toString() {
		return String.format("Event [type=%s, handler=%s, widgetId=%s, widgetClass=%s, widgetName=%s]", type, handler, widgetId, widgetClass, widgetName);
	}

}
