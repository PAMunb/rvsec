package com.fdu.se.sootanalyze.model;

import java.util.List;

import soot.SootField;

public class SpinnerWidgetBuilderNovo extends BaseWidgetBuilderNovo {
	List<String> values;

	SpinnerWidgetBuilderNovo(WidgetType widgetType) {
		super(widgetType);
	}

	public SpinnerWidgetBuilderNovo values(List<String> values) {
		this.values = values;
		return this;
	}

	public SpinnerWidgetBuilderNovo widgetId(String widgetId) {
		setWidgetId(widgetId);
		return this;
	}

	public SpinnerWidgetBuilderNovo name(String name) {
		setName(name);
		return this;
	}

	public SpinnerWidgetBuilderNovo withListener(Listener listener) {
		addListener(listener);
		return this;
	}

	public SpinnerWidgetBuilderNovo field(SootField field) {
		setField(field);
		return this;
	}

	public SpinnerWidget build() {
		return new SpinnerWidget(this);
	}
}
