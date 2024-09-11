package com.fdu.se.sootanalyze.model;

public enum WidgetType {
	BUTTON("android.widget.Button", "Button"),
	MENU_ITEM("android.view.MenuItem", ""), // TODO
	SUB_MENU("android.view.SubMenu", ""), // TODO
	EDIT_TEXT("android.widget.EditText", "EditText"),
	SPINNER("android.widget.Spinner", "Spinner"),
	TEXT_VIEW("android.widget.EditText", "TextView");

	private String widgetClass;
	private String xmlTag;

	WidgetType(String widgetClass, String xmlTag) {
		this.widgetClass = widgetClass;
		this.xmlTag = xmlTag;
	}

	public String getWidgetClass() {
		return widgetClass;
	}

	public String getXmlTag() {
		return xmlTag;
	}

	public static WidgetType getByWidgetClass(String clazz) {
		for (WidgetType type : values()) {
			if (type.getWidgetClass().equals(clazz)) {
				return type;
			}
		}
		return null;
	}

}
