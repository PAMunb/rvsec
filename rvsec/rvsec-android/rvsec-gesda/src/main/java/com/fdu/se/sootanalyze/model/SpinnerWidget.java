package com.fdu.se.sootanalyze.model;

import java.util.List;

public class SpinnerWidget extends Widget {
	private List<String> values;
	private String prompt;
	private int spinnerMode;

	SpinnerWidget(SpinnerWidgetBuilder spinnerWidgetBuilder) {
		super(spinnerWidgetBuilder);
		this.values = spinnerWidgetBuilder.values;
	}

	public List<String> getValues() {
		return values;
	}

}
