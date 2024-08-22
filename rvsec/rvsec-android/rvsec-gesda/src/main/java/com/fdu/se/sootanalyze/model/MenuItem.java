package com.fdu.se.sootanalyze.model;

public class MenuItem extends Widget {
//    private String text;
    private int itemId;

    public MenuItem() {
        this.setEvent("click");
        this.setWidgetType("android.view.MenuItem");
    }

//    public String getText() {
//        return text;
//    }
//
//    public void setText(String text) {
//        this.text = text;
//    }

    public int getItemId() {
        return itemId;
    }

    public void setItemId(int itemId) {
        this.itemId = itemId;
    }

	@Override
	public String toString() {
		return String.format(
				"MenuItem [itemId=%s, getField()=%s, getCallbackMethod()=%s, getText()=%s, getTextId()=%s, getName()=%s, getWidgetType()=%s, getWidgetId()=%s, getEvent()=%s, getId()=%s, getEventMethod()=%s, isEventRegisteredInLayoutFile()=%s, getListenerName()=%s]",
				itemId, getField(), getCallbackMethod(), getText(), getTextId(), getName(), getWidgetType(), getWidgetId(), getEvent(), getId(), getEventMethod(), isEventRegisteredInLayoutFile(), getListenerName());
	}
    
    
}
