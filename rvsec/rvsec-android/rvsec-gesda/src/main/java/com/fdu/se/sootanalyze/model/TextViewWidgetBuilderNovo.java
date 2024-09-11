package com.fdu.se.sootanalyze.model;

import soot.SootField;

public class TextViewWidgetBuilderNovo extends BaseWidgetBuilderNovo {
	private String text;
	private String hint;
	private String inputMethod;
	private String inputType;

	public TextViewWidgetBuilderNovo(WidgetType widgetType) {
		super(widgetType);
	}

	public TextViewWidgetBuilderNovo text(String text) {
		this.text = text;
		return this;
	}

	public TextViewWidgetBuilderNovo hint(String hint) {
		this.hint = hint;
		return this;
	}

	public TextViewWidgetBuilderNovo inputMethod(String inputMethod) {
		this.inputMethod = inputMethod;
		return this;
	}

	public TextViewWidgetBuilderNovo inputType(String inputType) {
		this.inputType = inputType;
		return this;
	}

	public TextViewWidgetBuilderNovo widgetId(String widgetId) {
		setWidgetId(widgetId);
		return this;
	}

	public TextViewWidgetBuilderNovo name(String name) {
		setName(name);
		return this;
	}

	public TextViewWidgetBuilderNovo withListener(Listener listener) {
		addListener(listener);
		return this;
	}

	public TextViewWidgetBuilderNovo field(SootField field) {
		setField(field);
		return this;
	}

	protected String getText() {
		return text;
	}

	protected String getHint() {
		return hint;
	}

	protected String getInputMethod() {
		return inputMethod;
	}

	protected String getInputType() {
		return inputType;
	}

	public TextViewWidget build() {
		validate();
		return new TextViewWidget(this);
	}
}
