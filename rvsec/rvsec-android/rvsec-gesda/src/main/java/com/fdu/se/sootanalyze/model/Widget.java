package com.fdu.se.sootanalyze.model;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import soot.SootField;
import soot.Unit;

public abstract class Widget {
	private long id;

//	@Deprecated
//	private String widgetType;
	private String widgetId;

//	@Deprecated
//	private String event;
	@Deprecated//TODO nome da atividade (caminho completo)
	private String listenerName;
//	@Deprecated
//	private String eventMethod;
//	@Deprecated
//	private boolean eventRegisteredInLayoutFile = false;// whether the event of the widget is registered in the layout file, 1 yes, 0 no

	// ???????????
	private List<Widget> dWidgets = new ArrayList<>();// the dependency of this widget

//	private String text;
//	private String textId;
	private WidgetType type; // TODO
	private String name;

	private Set<Listener> listeners = new HashSet<>();// TODO

	private SootField field;// sootfield
//	@Deprecated
//	private SootMethod callbackMethod;

	private Unit declaration; /// ?????


	protected Widget(BaseWidgetBuilderNovo builder) {
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
	public boolean isEventRegisteredInLayoutFile() {
		return listeners.stream().anyMatch(Listener::isEventRegisteredInLayoutFile);
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
