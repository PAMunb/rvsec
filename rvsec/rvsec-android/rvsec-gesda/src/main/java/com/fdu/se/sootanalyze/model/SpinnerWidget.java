package com.fdu.se.sootanalyze.model;

import java.util.List;

public class SpinnerWidget extends Widget {
	private List<String> values;

	SpinnerWidget(SpinnerWidgetBuilderNovo spinnerWidgetBuilderNovo) {
		super(spinnerWidgetBuilderNovo);
		this.values = spinnerWidgetBuilderNovo.values;
	}

	public List<String> getValues() {
		return values;
	}

}
