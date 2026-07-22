package com.fdu.se.sootanalyze.model.out;

import java.util.ArrayList;
import java.util.List;

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
	
	

	public WidgetInfoOut() {
	}

	public WidgetInfoOut(String widgetId, WidgetType type, String name, String field, List<ListenerInfoOut> listeners, String contentDescription, String tooltipText, String text, String hint, String inputType, List<String> entries, String prompt,
			Integer spinnerMode, List<WidgetInfoOut> items) {
		this.widgetId = widgetId;
		this.type = type;
		this.name = name;
		this.field = field;
		this.listeners = listeners;
		this.contentDescription = contentDescription;
		this.tooltipText = tooltipText;
		this.text = text;
		this.hint = hint;
		this.inputType = inputType;
		this.entries = entries;
		this.prompt = prompt;
		this.spinnerMode = spinnerMode;
		this.items = items;
	}

	public String getWidgetId() {
		return widgetId;
	}

	public void setWidgetId(String widgetId) {
		this.widgetId = widgetId;
	}

	public WidgetType getType() {
		return type;
	}

	public void setType(WidgetType type) {
		this.type = type;
	}

	public String getName() {
		return name;
	}

	public void setName(String name) {
		this.name = name;
	}

	public String getField() {
		return field;
	}

	public void setField(String field) {
		this.field = field;
	}

	public List<ListenerInfoOut> getListeners() {
		return listeners;
	}

	public void setListeners(List<ListenerInfoOut> listeners) {
		this.listeners = listeners;
	}

	public String getContentDescription() {
		return contentDescription;
	}

	public void setContentDescription(String contentDescription) {
		this.contentDescription = contentDescription;
	}

	public String getTooltipText() {
		return tooltipText;
	}

	public void setTooltipText(String tooltipText) {
		this.tooltipText = tooltipText;
	}

	public String getText() {
		return text;
	}

	public void setText(String text) {
		this.text = text;
	}

	public String getHint() {
		return hint;
	}

	public void setHint(String hint) {
		this.hint = hint;
	}

	public String getInputType() {
		return inputType;
	}

	public void setInputType(String inputType) {
		this.inputType = inputType;
	}

	public List<String> getEntries() {
		return entries;
	}

	public void setEntries(List<String> entries) {
		this.entries = entries;
	}

	public String getPrompt() {
		return prompt;
	}

	public void setPrompt(String prompt) {
		this.prompt = prompt;
	}

	public Integer getSpinnerMode() {
		return spinnerMode;
	}

	public void setSpinnerMode(Integer spinnerMode) {
		this.spinnerMode = spinnerMode;
	}

	public List<WidgetInfoOut> getItems() {
		return items;
	}

	public void setItems(List<WidgetInfoOut> items) {
		this.items = items;
	}

	@Override
	public String toString() {
		return String.format("WidgetInfoOut [widgetId=%s, type=%s, name=%s, field=%s, listeners=%s, contentDescription=%s, tooltipText=%s, text=%s, hint=%s, inputType=%s, entries=%s, prompt=%s, spinnerMode=%s, items=%s]", widgetId, type, name, field,
				listeners, contentDescription, tooltipText, text, hint, inputType, entries, prompt, spinnerMode, items);
	}

}
