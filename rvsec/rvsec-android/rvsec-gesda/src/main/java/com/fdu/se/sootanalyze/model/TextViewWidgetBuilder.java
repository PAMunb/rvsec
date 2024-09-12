package com.fdu.se.sootanalyze.model;

import soot.SootField;

public class TextViewWidgetBuilder extends BaseWidgetBuilder {
	private String text;
	private String hint;
	private String inputMethod;
	private String inputType;

	public TextViewWidgetBuilder(WidgetType widgetType) {
		super(widgetType);
	}

	public TextViewWidgetBuilder text(String text) {
		this.text = text;
		return this;
	}

	public TextViewWidgetBuilder hint(String hint) {
		this.hint = hint;
		return this;
	}

	public TextViewWidgetBuilder inputMethod(String inputMethod) {
		this.inputMethod = inputMethod;
		return this;
	}

	public TextViewWidgetBuilder inputType(String inputType) {
		this.inputType = inputType;
		return this;
	}

	public TextViewWidgetBuilder widgetId(String widgetId) {
		setWidgetId(widgetId);
		return this;
	}

	public TextViewWidgetBuilder name(String name) {
		setName(name);
		return this;
	}

	public TextViewWidgetBuilder withListener(Listener listener) {
		addListener(listener);
		return this;
	}

	public TextViewWidgetBuilder field(SootField field) {
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
