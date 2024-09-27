package br.unb.cic.rvsec.reach.gesda;

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
//	CompoundButton.OnCheckedChangeListener: Acionado quando o estado de um CompoundButton (como um CheckBox ou RadioButton) é alterado.

	private String listernerMethod;
	private String eventCallback;
	private Event event;

	ListenerType(String listernerMethod, String eventCallback, Event event) {
		this.listernerMethod = listernerMethod;
		this.eventCallback = eventCallback;
		this.event = event;
	}

	public String getListernerMethod() {
		return listernerMethod;
	}

	public String getEventCallback() {
		return eventCallback;
	}

	public Event getEvent() {
		return event;
	}

}
