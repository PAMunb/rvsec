package br.unb.cic.rvsec.reach.gesda;

public enum WidgetType {
	BUTTON("android.widget.Button", "Button"),
	MENU_ITEM("android.view.MenuItem", ""), // TODO
	SUB_MENU("android.view.SubMenu", ""), // TODO
	EDIT_TEXT("android.widget.EditText", "EditText"),
	SPINNER("android.widget.Spinner", "Spinner"),
	TEXT_VIEW("android.widget.TextView", "TextView"),
	CHECKED_TEXT_VIEW("android.widget.CheckedTextView", "CheckedTextView"),
	CHECKBOX("android.widget.CheckBox", "CheckBox"),
	TOGGLE_BUTTON("android.widget.ToggleButton", "ToggleButton"),
	RADIO_BUTTON("android.widget.RadioButton", "RadioButton"),
	IMAGE_BUTTON("android.widget.ImageButton", "ImageButton"),
	IMAGE_VIEW("android.widget.ImageView", "ImageView");

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
		if (clazz == null) {
			return null;
		}
		for (WidgetType type : values()) {
			if (type.getWidgetClass().equals(clazz)) {
				return type;
			}
		}
		return null;
	}

}
