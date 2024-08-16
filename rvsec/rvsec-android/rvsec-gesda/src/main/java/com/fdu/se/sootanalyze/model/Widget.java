package com.fdu.se.sootanalyze.model;

import java.util.ArrayList;
import java.util.List;

import soot.SootField;
import soot.SootMethod;

public class Widget {
	private long id;
	
    private String widgetType;
    private String widgetId;
    
    private String event;
    private String listenerName; 
    private String eventMethod; 
    @Deprecated
    private boolean layoutRegister = false;//whether the event of the widget is registered in the layout file, 1 yes, 0 no
    
    private List<Widget> dWidgets = new ArrayList<>();//the dependency of this widget
    
    private String text;
    private String textId;
    private String name;
    
    private SootField field;// sootfield
	private SootMethod callbackMethod;
    

    public Widget() {
    }

    public SootField getField() {
		return field;
	}

	public void setField(SootField field) {
		this.field = field;
	}

	public SootMethod getCallbackMethod() {
		return callbackMethod;
	}

	public void setCallbackMethod(SootMethod callbackMethod) {
		this.callbackMethod = callbackMethod;
	}

	public String getText() {
		return text;
	}

	public void setText(String text) {
		this.text = text;
	}

	public String getTextId() {
		return textId;
	}

	public void setTextId(String textId) {
		this.textId = textId;
	}

	public String getName() {
		return name;
	}

	public void setName(String tmp) {
		this.name = tmp;
	}

	public String getWidgetType() {
        return widgetType;
    }

    public void setWidgetType(String widgetType) {
        this.widgetType = widgetType;
    }

    public String getWidgetId() {
        return widgetId;
    }

    public void setWidgetId(String widgetId) {
        this.widgetId = widgetId;
    }

    public String getEvent() {
        return event;
    }

    public void setEvent(String event) {
        this.event = event;
    }

    public long getId() {
        return id;
    }

    public void setId(long id) {
        this.id = id;
    }

    public String getEventMethod() {
        return eventMethod;
    }

    public void setEventMethod(String eventMethod) {
        this.eventMethod = eventMethod;
    }

    public boolean isLayoutRegister() {
        return layoutRegister;
    }

    public void setLayoutRegister(boolean layoutRegister) {
        this.layoutRegister = layoutRegister;
    }

    public String getListenerName() {
        return listenerName;
    }

    public void setListenerName(String listenerName) {
        this.listenerName = listenerName;
    }

    public List<Widget> getdWidgets() {
        return dWidgets;
    }

    public void setdWidgets(List<Widget> dWidgets) {
        this.dWidgets = dWidgets;
    }

	@Override
	public String toString() {
		return String.format("Widget [id=%s, widgetType=%s, widgetId=%s, event=%s, listenerName=%s, eventMethod=%s, layoutRegister=%s, text=%s, textId=%s, name=%s, field=%s, callbackMethod=%s]", id, widgetType, widgetId, event, listenerName,
				eventMethod, layoutRegister, text, textId, name, field, callbackMethod);
	}



    
}
