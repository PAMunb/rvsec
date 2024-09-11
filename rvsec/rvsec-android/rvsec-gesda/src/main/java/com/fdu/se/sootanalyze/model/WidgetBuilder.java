package com.fdu.se.sootanalyze.model;

public class WidgetBuilder {


	public static TextViewWidgetBuilderNovo newWidget(WidgetType widgetType) {
		return new TextViewWidgetBuilderNovo(widgetType);
	}

	public static TextViewWidgetBuilderNovo newButton() {
		return newWidget(WidgetType.BUTTON);
	}

	public static TextViewWidgetBuilderNovo newMenuItem() {
		return newWidget(WidgetType.MENU_ITEM);
	}

	public static TextViewWidgetBuilderNovo newSubMenu() {
		return newWidget(WidgetType.SUB_MENU);
	}

	public static SpinnerWidgetBuilderNovo newSpinner() {
		return new SpinnerWidgetBuilderNovo(WidgetType.SPINNER);
	}


//	class BaseWidgetBuilder {
//		long id;
//		WidgetType type;
//		String widgetId;
//		String name;
//		Set<Listener> listeners = new HashSet<>();
//		SootField field;
//
//		protected BaseWidgetBuilder(WidgetType widgetType) {
//			this.id = currentId.next();
//			this.type = widgetType;
//		}
//
//		protected String getWidgetId() {
//			return widgetId;
//		}
//
//		protected void setWidgetId(String widgetId) {
//			this.widgetId = widgetId;
//		}
//
//		protected String getName() {
//			return name;
//		}
//
//		protected void setName(String name) {
//			this.name = name;
//		}
//
//		protected Set<Listener> getListeners() {
//			return listeners;
//		}
//
//		protected void setListeners(Set<Listener> listeners) {
//			this.listeners = listeners;
//		}
//
//		protected SootField getField() {
//			return field;
//		}
//
//		protected void setField(SootField field) {
//			this.field = field;
//		}
//
//	}
//
//	public class TextViewWidgetBuilder extends BaseWidgetBuilder {
//		String text;
//		String hint;
//		String inputMethod;
//		String inputType;
//
//		TextViewWidgetBuilder(WidgetType widgetType) {
//			super(widgetType);
//		}
//
//		public TextViewWidgetBuilder text(String text) {
//			this.text = text;
//			return this;
//		}
//
//		public TextViewWidgetBuilder hint(String text) {
//			this.text = text;
//			return this;
//		}
//
//		public TextViewWidgetBuilder inputMethod(String inputMethod) {
//			this.inputMethod = inputMethod;
//			return this;
//		}
//
//		public TextViewWidgetBuilder inputType(String inputType) {
//			this.inputType = inputType;
//			return this;
//		}
//
//		public TextViewWidgetBuilder widgetId(String widgetId) {
//			this.widgetId = widgetId;
//			return this;
//		}
//
//		public TextViewWidgetBuilder name(String name) {
//			this.name = name;
//			return this;
//		}
//
//		public TextViewWidgetBuilder withListener(Listener listener) {
//			listeners.add(listener);
//			return this;
//		}
//
//		public TextViewWidgetBuilder field(SootField field) {
//			this.field = field;
//			return this;
//		}
//
//		public TextViewWidget build() {
//			return new TextViewWidget(this);
//		}
//	}
//
//	public class SpinnerWidgetBuilder extends BaseWidgetBuilder {
//		List<String> values;
//
//		SpinnerWidgetBuilder(WidgetType widgetType) {
//			super(widgetType);
//		}
//
//
//
//		public SpinnerWidgetBuilder values(List<String> values) {
//			this.values = values;
//			return this;
//		}
//
//		public SpinnerWidgetBuilder widgetId(String widgetId) {
//			this.widgetId = widgetId;
//			return this;
//		}
//
//		public SpinnerWidgetBuilder name(String name) {
//			this.name = name;
//			return this;
//		}
//
//		public SpinnerWidgetBuilder withListener(Listener listener) {
//			listeners.add(listener);
//			return this;
//		}
//
//		public SpinnerWidgetBuilder field(SootField field) {
//			this.field = field;
//			return this;
//		}
//
//		public SpinnerWidget build() {
//			return new SpinnerWidget(id, widgetType, widgetId, event, listenerName, eventMethod, false, listenerName, values);
//		}
//	}

}
