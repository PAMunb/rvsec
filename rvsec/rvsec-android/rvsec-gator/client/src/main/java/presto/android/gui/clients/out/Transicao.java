package presto.android.gui.clients.out;

import java.util.Objects;

public class Transicao {
	private int sourceId;
	private int getTargetId;
	private Evento event;

	public Transicao(int sourceId, int getTargetId, Evento event) {
		this.sourceId = sourceId;
		this.getTargetId = getTargetId;
		this.event = event;
	}

	public int getSourceId() {
		return sourceId;
	}

	public int getGetTargetId() {
		return getTargetId;
	}

	public Evento getEvent() {
		return event;
	}

	@Override
	public int hashCode() {
		return Objects.hash(event, getTargetId, sourceId);
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj)
			return true;
		if ((obj == null) || (getClass() != obj.getClass()))
			return false;
		Transicao other = (Transicao) obj;
		return Objects.equals(event, other.event) && getTargetId == other.getTargetId && sourceId == other.sourceId;
	}

	@Override
	public String toString() {
		return String.format("Transition [sourceId=%s, getTargetId=%s, event=%s]", sourceId, getTargetId, event);
	}

}
