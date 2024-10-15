package com.fdu.se.sootanalyze.model;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import com.fdu.se.sootanalyze.utils.NumberIncrementer;

import soot.SootField;

public class Widget {

	private final Long id;
	private final String widgetId;
	private final WidgetType type;
	private final String name;
	private final Set<Listener> listeners;
	private SootField field;

	private List<Widget> dWidgets = new ArrayList<>();// the dependency of this widget

	// view
	private final String contentDescription;
	private final String tooltipText;

	// textView (button, editText, ...)
	private final String text;
	private final String hint;
	private final String inputType;

	// spinner
	private final List<String> entries;
	private final String prompt;
	private final Integer spinnerMode;

	// subMenu
	private final List<Widget> items = new ArrayList<>();

	protected Widget(WidgetBuilder WidgetBuilder) {
		this.id = WidgetBuilder.id;
		this.type = WidgetBuilder.type;
		this.widgetId = WidgetBuilder.widgetId;
		this.name = WidgetBuilder.name;
		this.listeners = WidgetBuilder.listeners;
		this.field = WidgetBuilder.field;
		this.contentDescription = WidgetBuilder.contentDescription;
		this.tooltipText = WidgetBuilder.tooltipText;
		this.text = WidgetBuilder.text;
		this.hint = WidgetBuilder.hint;
		this.inputType = WidgetBuilder.inputType;
		this.entries = WidgetBuilder.entries;
		this.prompt = WidgetBuilder.prompt;
		this.spinnerMode = WidgetBuilder.spinnerMode;
	}

	public Long getId() {
		return id;
	}

	public String getWidgetId() {
		return widgetId;
	}

	public WidgetType getType() {
		return type;
	}

	public String getName() {
		return name;
	}

	public Set<Listener> getListeners() {
		return listeners;
	}

	public SootField getField() {
		return field;
	}

	public List<Widget> getdWidgets() {
		return dWidgets;
	}

	public String getContentDescription() {
		return contentDescription;
	}

	public String getTooltipText() {
		return tooltipText;
	}

	public String getText() {
		return text;
	}

	public String getHint() {
		return hint;
	}

	public String getInputType() {
		return inputType;
	}

	public List<String> getEntries() {
		return entries;
	}

	public String getPrompt() {
		return prompt;
	}

	public Integer getSpinnerMode() {
		return spinnerMode;
	}

	public List<Widget> getItems() {
		return items;
	}

	public void addListener(Listener listener) {
		if (listener != null) {
			listeners.add(listener);
		}
	}

	public void setField(SootField field) {
		this.field = field;
	}

	public void setdWidgets(List<Widget> dWidgets) {
		this.dWidgets = dWidgets;
	}

	public static WidgetBuilder builder(WidgetType widgetType) {
		return new WidgetBuilder(widgetType);
	}

	public static class WidgetBuilder {
		private static final NumberIncrementer currentId = new NumberIncrementer();// the current id of Widget

		private final Long id;
		private final WidgetType type;
		private String widgetId;
		private String name;
		private final Set<Listener> listeners = new HashSet<>();
		private SootField field;
		private String contentDescription;
		private String tooltipText;
		private String text;
		private String hint;
		private String inputType;
		private final List<String> entries = new ArrayList<>();
		private String prompt;
		private Integer spinnerMode;
		private List<Widget> items = new ArrayList<>();

		protected WidgetBuilder(WidgetType widgetType) {
			this.id = currentId.next();
			this.type = widgetType;
		}

		public WidgetBuilder widgetId(String widgetId) {
			this.widgetId = widgetId;
			return WidgetBuilder.this;
		}

		public WidgetBuilder name(String name) {
			this.name = name;
			return WidgetBuilder.this;
		}

		public WidgetBuilder addListener(Listener listener) {
			if (listener != null) {
				listeners.add(listener);
			}
			return WidgetBuilder.this;
		}

		public WidgetBuilder addMenuItem(Widget item) {
			if (item != null) {
				items.add(item);
			}
			return WidgetBuilder.this;
		}

		public void setMenuItems(List<Widget> items) {
			if (items != null) {
				this.items = items;
			}
		}

		public WidgetBuilder field(SootField field) {
			this.field = field;
			return WidgetBuilder.this;
		}

		public WidgetBuilder contentDescription(String contentDescription) {
			this.contentDescription = contentDescription;
			return WidgetBuilder.this;
		}

		public WidgetBuilder tooltipText(String tooltipText) {
			this.tooltipText = tooltipText;
			return WidgetBuilder.this;
		}

		public WidgetBuilder text(String text) {
			this.text = text;
			return WidgetBuilder.this;
		}

		public WidgetBuilder hint(String hint) {
			this.hint = hint;
			return WidgetBuilder.this;
		}

		public WidgetBuilder inputType(String inputType) {
			this.inputType = inputType;
			return WidgetBuilder.this;
		}

		public WidgetBuilder addEntry(String entry) {
			if (entry != null) {
				this.entries.add(entry);
			}
			return WidgetBuilder.this;
		}

		public WidgetBuilder prompt(String prompt) {
			this.prompt = prompt;
			return WidgetBuilder.this;
		}

		public WidgetBuilder spinnerMode(Integer spinnerMode) {
			this.spinnerMode = spinnerMode;
			return WidgetBuilder.this;
		}

		public Widget build() {
			if (this.type == null) {
				throw new NullPointerException("The property \"type\" is null.");
			}
			if (this.widgetId == null) {
				this.widgetId = "";//UUID.randomUUID().toString();
			}

			return new Widget(this);
		}

	}

	@Override
	public String toString() {
		return String.format("Widget [id=%s, widgetId=%s, type=%s, name=%s, listeners=%s, field=%s, dWidgets=%s, contentDescription=%s, tooltipText=%s, text=%s, hint=%s, inputType=%s, entries=%s, prompt=%s, spinnerMode=%s, items=%s]", id, widgetId,
				type, name, listeners, field, dWidgets, contentDescription, tooltipText, text, hint, inputType, entries, prompt, spinnerMode, items);
	}

}
