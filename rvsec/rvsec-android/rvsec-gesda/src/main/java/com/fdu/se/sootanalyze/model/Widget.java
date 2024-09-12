package com.fdu.se.sootanalyze.model;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import soot.SootField;
import soot.Unit;

public abstract class Widget {
	private long id;
	private String widgetId;
	private WidgetType type; 
	private String name;
	private Set<Listener> listeners = new HashSet<>();
	private SootField field;
	
	private String contentDescription;

	private Unit declaration; /// ?????
	
	@Deprecated//TODO nome da atividade (caminho completo)
	private String listenerName;

	// ???????????
	private List<Widget> dWidgets = new ArrayList<>();// the dependency of this widget


	protected Widget(BaseWidgetBuilder builder) {
		this.id = builder.getId();
		this.widgetId = builder.getWidgetId();
		this.type = builder.getType();
		this.name = builder.getName();
		this.listeners = builder.getListeners();
		this.field = builder.getField();
	}

	public long getId() {
		return id;
	}

	public String getWidgetId() {
		return widgetId;
	}

	public WidgetType getType() {
		return type;
	}

	public String getName() {
		return name;
	}

	public Set<Listener> getListeners() {
		return listeners;
	}

	public List<Widget> getdWidgets() {
		return dWidgets;
	}

	public void setdWidgets(List<Widget> dWidgets) {
		this.dWidgets = dWidgets;
	}

	public SootField getField() {
		return field;
	}

	public void setField(SootField field) {
		this.field = field;
	}

	public Unit getDeclaration() {
		return declaration;
	}

	public void setDeclaration(Unit declaration) {
		this.declaration = declaration;
	}

	@Deprecated
	public String getListenerName() {
		return listenerName;
	}

	@Deprecated
	public void setListenerName(String listenerName) {
		this.listenerName = listenerName;
	}

	public void addListener(Listener listener) {
		listeners.add(listener);
	}

	@Override
	public String toString() {
		return String.format("Widget [id=%s, widgetId=%s, listenerName=%s, type=%s, name=%s, listeners=%s, field=%s, declaration=%s]", id, widgetId, listenerName, type, name,
				listeners, field, declaration);
	}

}
