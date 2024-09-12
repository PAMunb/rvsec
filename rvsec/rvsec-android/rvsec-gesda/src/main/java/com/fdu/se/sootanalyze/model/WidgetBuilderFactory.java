package com.fdu.se.sootanalyze.model;

public class WidgetBuilderFactory {

	public static TextViewWidgetBuilder newWidget(WidgetType widgetType) {
		return new TextViewWidgetBuilder(widgetType);
	}

	public static TextViewWidgetBuilder newButton() {
		return newWidget(WidgetType.BUTTON);
	}

	public static TextViewWidgetBuilder newMenuItem() {
		return newWidget(WidgetType.MENU_ITEM);
	}

	public static TextViewWidgetBuilder newSubMenu() {
		return newWidget(WidgetType.SUB_MENU);
	}

	public static SpinnerWidgetBuilder newSpinner() {
		return new SpinnerWidgetBuilder(WidgetType.SPINNER);
	}

}
