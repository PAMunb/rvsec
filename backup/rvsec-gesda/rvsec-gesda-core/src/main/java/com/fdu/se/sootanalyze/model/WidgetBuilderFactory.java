package com.fdu.se.sootanalyze.model;

import com.fdu.se.sootanalyze.model.Widget.WidgetBuilder;

public class WidgetBuilderFactory {

	public static WidgetBuilder newWidget(WidgetType widgetType) {
		return new Widget.WidgetBuilder(widgetType);
	}

	public static WidgetBuilder newButton() {
		return newWidget(WidgetType.BUTTON);
	}

	public static WidgetBuilder newMenuItem() {
		return newWidget(WidgetType.MENU_ITEM);
	}

	public static WidgetBuilder newSubMenu() {
		return newWidget(WidgetType.SUB_MENU);
	}

	public static WidgetBuilder newSpinner() {
		return newWidget(WidgetType.SPINNER);
	}

}
