package com.fdu.se.sootanalyze.model;

public enum ListenerType {
	OnClickListener("setOnClickListener", "onClick", Event.CLICK),
	OnLongClickListener("setOnLongClickListener", "onLongClick", Event.LONG_CLICK),
	OnItemClickListener("setOnItemClickListener", "onItemClick", Event.CLICK),
	OnItemLongClickListener("setOnItemLongClickListener", "onItemLongClick", Event.LONG_CLICK),
	OnMenuItemClickListener("setOnMenuItemClickListener", "onMenuItemClick", Event.CLICK),
	OnScrollListener("setOnScrollListener", "onScroll", Event.SCROLL),
	OnDragListener("setOnDragListener", "onDrag", Event.DRAG),
	OnHoverListener("setOnHoverListener", "onHover", Event.HOVER),
	OnTouchListener("setOnTouchListener", "onTouch", Event.TOUCH),
	OnKeyListener("setOnKeyListener", "onKey", Event.KEY),
	OnItemSelectedListener("setOnItemSelectedListener", "onItemSelected", Event.SELECTION),
	OnCheckedChangeListener("setOnCheckedChangeListener", "onCheckedChanged", Event.CLICK),
	OnFocusChangeListener("setOnFocusChangeListener", "onFocusChange", Event.FOCUS);

//	 //TODO
//	TextWatcher
//	OnGestureListener
//	OnEditorActionListener
//	CompoundButton.OnCheckedChangeListener

	private String listenerMethod;
	private String eventCallback;
	private Event event;

	ListenerType(String listenerMethod, String eventCallback, Event event) {
		this.listenerMethod = listenerMethod;
		this.eventCallback = eventCallback;
		this.event = event;
	}

	public String getListenerMethod() {
		return listenerMethod;
	}

	public String getEventCallback() {
		return eventCallback;
	}

	public Event getEvent() {
		return event;
	}

}
