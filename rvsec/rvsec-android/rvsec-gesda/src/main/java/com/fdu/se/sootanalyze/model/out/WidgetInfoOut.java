package com.fdu.se.sootanalyze.model.out;

import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

import com.fdu.se.sootanalyze.model.Widget;
import com.fdu.se.sootanalyze.model.WidgetType;

public class WidgetInfoOut {
	private String widgetId;
	private WidgetType type;
	private String name;
	private String field;
	private List<ListenerInfoOut> listeners = new ArrayList<>();

	private String contentDescription;
	private String tooltipText;

	// textView (button, editText, ...)
	private String text;
	private String hint;
	private String inputType;

	// spinner
	private List<String> entries = new ArrayList<>();
	private String prompt;
	private Integer spinnerMode;

	// subMenu
	private List<WidgetInfoOut> items = new ArrayList<>();

	public WidgetInfoOut(Widget widget) {
		if (widget != null) {
			this.widgetId = widget.getWidgetId();
			this.type = widget.getType();
			this.name = widget.getName();
			this.field = getField(widget);
			this.listeners = getListeners(widget);
			this.contentDescription = widget.getContentDescription();
			this.tooltipText = widget.getTooltipText();
			this.text = widget.getText();
			this.hint = widget.getHint();
			this.inputType = widget.getInputType();
			this.entries = widget.getEntries();
			this.prompt = widget.getPrompt();
			this.spinnerMode = widget.getSpinnerMode();
			this.items = widget.getItems().stream().map(WidgetInfoOut::new).collect(Collectors.toList());
		}
	}

	private List<ListenerInfoOut> getListeners(Widget widget) {
		return widget.getListeners().stream().map(ListenerInfoOut::new).collect(Collectors.toList());
	}

	private String getField(Widget widget) {
		if (widget.getField() != null) {
			return widget.getField().getSignature();
		}
		return null;
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

	public String getField() {
		return field;
	}

	public List<ListenerInfoOut> getListeners() {
		return listeners;
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

	public List<WidgetInfoOut> getItems() {
		return items;
	}

	@Override
	public String toString() {
		return String.format("WidgetInfoOut [widgetId=%s, type=%s, name=%s, field=%s, listeners=%s, contentDescription=%s, tooltipText=%s, text=%s, hint=%s, inputType=%s, entries=%s, prompt=%s, spinnerMode=%s, items=%s]", widgetId, type, name, field,
				listeners, contentDescription, tooltipText, text, hint, inputType, entries, prompt, spinnerMode, items);
	}

}
