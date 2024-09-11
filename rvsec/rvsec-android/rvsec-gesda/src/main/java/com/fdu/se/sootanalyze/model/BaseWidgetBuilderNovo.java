package com.fdu.se.sootanalyze.model;

import java.util.HashSet;
import java.util.Set;

import com.fdu.se.sootanalyze.utils.NumberIncrementer;

import soot.SootField;

public class BaseWidgetBuilderNovo {
	private static NumberIncrementer currentId = new NumberIncrementer();// the current id of Widget

	private long id;
	private WidgetType type;
	private String widgetId;
	private String name;
	private Set<Listener> listeners = new HashSet<>();
	private SootField field;

	protected BaseWidgetBuilderNovo(WidgetType widgetType) {
		this.id = currentId.next();
		this.type = widgetType;
	}

	protected long getId() {
		return id;
	}

	protected WidgetType getType() {
		return type;
	}

	protected String getWidgetId() {
		return widgetId;
	}

	protected void setWidgetId(String widgetId) {
		this.widgetId = widgetId;
	}

	protected String getName() {
		return name;
	}

	protected void setName(String name) {
		this.name = name;
	}

	protected Set<Listener> getListeners() {
		return listeners;
	}

	protected void addListener(Listener listener) {
		if (listener != null) {
			listeners.add(listener);
		}
	}

	protected SootField getField() {
		return field;
	}

	protected void setField(SootField field) {
		this.field = field;
	}

	public void validate() {
		// TODO
	}

}
