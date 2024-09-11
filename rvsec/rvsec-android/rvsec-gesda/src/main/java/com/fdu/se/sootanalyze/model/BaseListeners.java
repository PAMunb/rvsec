package com.fdu.se.sootanalyze.model;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

public class BaseListeners {
	private static final Map<String, ListenerType> mapByListenerMethod = new HashMap<>();
	private static final Map<String, ListenerType> mapByEventCallback = new HashMap<>();
	private static final Map<Event, Set<ListenerType>> mapByEvent = new HashMap<>();

	static {
		for (ListenerType l : ListenerType.values()) {

			if(!mapByEvent.containsKey(l.getEvent())) {
				mapByEvent.put(l.getEvent(), new HashSet<>());
			}
			mapByEvent.get(l.getEvent()).add(l);

			mapByEventCallback.put(l.getEventCallback(), l);
			mapByListenerMethod.put(l.getListernerMethod(), l);
		}
	}

	public Set<ListenerType> getListenersByEvent(Event event) {
		return mapByEvent.get(event);
//		if(set == null) {
//			set = new HashSet<>();
//		}
//		return set;
	}

	public static ListenerType getByListenerMethod(String listenerMethod) {
		return mapByListenerMethod.get(listenerMethod);
	}

	public static ListenerType getByEventCallback(String eventCallback) {
		return mapByEventCallback.get(eventCallback);
	}

	public static Event getEvent(String listenerMethod) {
		ListenerType listenerEnum2 = mapByListenerMethod.get(listenerMethod);
		if(listenerEnum2 != null) {
			return listenerEnum2.getEvent();
		}
		return null;
	}

	public static String getEventCallBack(String listenerMethod) {
		ListenerType listener = mapByListenerMethod.get(listenerMethod);
		String callBack = null;
		if (listener != null) {
			callBack = listener.getEventCallback();
		}
		return callBack;
	}

}
