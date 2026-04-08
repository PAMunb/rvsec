package presto.android.gui.clients.wtg.model;

import java.util.Collection;
import java.util.Objects;
import java.util.Set;
import java.util.stream.Collectors;

import presto.android.gui.wtg.EventHandler;
import presto.android.gui.wtg.ds.WTGEdge;

/**
 * Represents a directed edge in the Window Transition Graph (WTG),
 * connecting a source {@link Window} to a target {@link Window}.
 *
 * <p>Each Transition carries two sets of {@link Event} objects:
 * <ul>
 *   <li><b>events</b> -- the UI events (e.g., click, menu-select) that
 *       trigger the transition;</li>
 *   <li><b>callbacks</b> -- lifecycle or framework callbacks invoked
 *       during the transition (e.g., {@code onResume}).</li>
 * </ul>
 *
 * <p>Source and target windows are referenced by their numeric IDs to keep
 * the serialized JSON compact. Equality considers all four fields.</p>
 */
public class Transition {
	private int sourceId;
	private int targetId;
	private Set<Event> events;
	private Set<Event> callbacks;

	/**
	 * Constructs a Transition from a GATOR {@link WTGEdge}.
	 *
	 * <p>Extracts source/target window IDs and converts the edge's handlers
	 * and callbacks into {@link Event} sets.</p>
	 *
	 * @param e the GATOR WTG edge to convert
	 */
	public Transition(WTGEdge e) {
		this.sourceId = e.getSourceNode().getWindow().id;
		this.targetId = e.getTargetNode().getWindow().id;
		this.events = toEvents(e.getWTGHandlers());
		this.callbacks = toEvents(e.getCallbacks());
	}

	/**
	 * Converts a collection of GATOR {@link EventHandler}s into a set of
	 * {@link Event} model objects.
	 */
	private Set<Event> toEvents(Collection<EventHandler> handlers) {
		return handlers.stream().map(Event::new).collect(Collectors.toSet());
	}

	public int getSourceId() {
		return sourceId;
	}

	public int getTargetId() {
		return targetId;
	}

	public Set<Event> getEvents() {
		return events;
	}

	public Set<Event> getCallbacks() {
		return callbacks;
	}

	@Override
	public int hashCode() {
		return Objects.hash(callbacks, events, targetId, sourceId);
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj)
			return true;
		if ((obj == null) || (getClass() != obj.getClass()))
			return false;
		Transition other = (Transition) obj;
		return Objects.equals(callbacks, other.callbacks) && Objects.equals(events, other.events) && targetId == other.targetId && sourceId == other.sourceId;
	}

	@Override
	public String toString() {
		return String.format("Transition [sourceId=%s, getTargetId=%s, events=%s, callbacks=%s]", sourceId, targetId, events, callbacks);
	}

}
