package com.fdu.se.sootanalyze.model;

public class TextViewWidget extends Widget {

	private String text;
	private String hint;
	private String inputMethod;
	private String inputType;

	TextViewWidget(TextViewWidgetBuilderNovo textViewWidgetBuilderNovo) {
		super(textViewWidgetBuilderNovo);
		this.text = textViewWidgetBuilderNovo.getText();
		this.hint = textViewWidgetBuilderNovo.getHint();
		this.inputMethod = textViewWidgetBuilderNovo.getInputMethod();
		this.inputType = textViewWidgetBuilderNovo.getInputType();
	}

	public String getText() {
		return text;
	}

	public String getHint() {
		return hint;
	}

	public String getInputMethod() {
		return inputMethod;
	}

	public String getInputType() {
		return inputType;
	}


	@Override
	public String toString() {
		return String.format("TextViewWidget [id=%s, widgetId=%s, listenerName=%s"
				+ ", type=%s, name=%s, listeners=%s"
				+ ", field=%s, declaration=%s"
				+ ", text=%s, hint=%s, inputMethod=%s, inputType=%s]",
				getId(), getWidgetId(), getListenerName(),
				getType(), getName(), getListeners(),
				getField(), getDeclaration(),
				text, hint, inputMethod, inputType);
	}


}
