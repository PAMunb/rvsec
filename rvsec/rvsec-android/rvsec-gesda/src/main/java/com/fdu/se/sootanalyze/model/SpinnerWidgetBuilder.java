package com.fdu.se.sootanalyze.model;

import java.util.List;

import soot.SootField;

public class SpinnerWidgetBuilder extends BaseWidgetBuilder {
	List<String> values;

	SpinnerWidgetBuilder(WidgetType widgetType) {
		super(widgetType);
	}

	public SpinnerWidgetBuilder values(List<String> values) {
		this.values = values;
		return this;
	}

	public SpinnerWidgetBuilder widgetId(String widgetId) {
		setWidgetId(widgetId);
		return this;
	}

	public SpinnerWidgetBuilder name(String name) {
		setName(name);
		return this;
	}

	public SpinnerWidgetBuilder withListener(Listener listener) {
		addListener(listener);
		return this;
	}

	public SpinnerWidgetBuilder field(SootField field) {
		setField(field);
		return this;
	}

	public SpinnerWidget build() {
		return new SpinnerWidget(this);
	}
}
