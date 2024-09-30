package com.fdu.se.sootanalyze.model;

import java.util.HashSet;
import java.util.Objects;
import java.util.Set;

import soot.SootMethod;

public class Listener {
	private ListenerType type;
	private String listernerClass;
	private SootMethod callbackMethod;
	private boolean eventRegisteredInLayoutFile = false;// whether the event of the widget is registered in the layout file

	private String callbackMethodName;
	private Set<String> targets = new HashSet<>();

	public Listener(ListenerType listenerType) {
		Objects.requireNonNull(listenerType);
		this.type = listenerType;
	}

	public Listener(ListenerType listenerEnum, boolean eventRegisteredInLayoutFile) {
		this(listenerEnum);
		this.eventRegisteredInLayoutFile = eventRegisteredInLayoutFile;
	}

	public Listener(ListenerType listenerEnum, String callbackMethodName, boolean eventRegisteredInLayoutFile) {
		this(listenerEnum, eventRegisteredInLayoutFile);
		this.callbackMethodName = callbackMethodName;
	}

	public ListenerType getType() {
		return type;
	}

	public String getListernerMethod() {
		return type.getListernerMethod();
	}

	public Event getEvent() {
		return type.getEvent();
	}

	public String getEventCallback() {
		return type.getEventCallback();
	}

	public String getListernerClass() {
		return listernerClass;
	}

	public void setListernerClass(String listernerClass) {
		this.listernerClass = listernerClass;
	}

	public SootMethod getCallbackMethod() {
		return callbackMethod;
	}

	public void setCallbackMethod(SootMethod callbackMethod) {
		this.callbackMethod = callbackMethod;
	}

	public boolean isEventRegisteredInLayoutFile() {
		return eventRegisteredInLayoutFile;
	}

	public String getCallbackMethodName() {
		return callbackMethodName;
	}

	public void setCallbackMethodName(String callbackMethodName) {
		this.callbackMethodName = callbackMethodName;
	}
	
	public void addTarget(String targetClass) {
		if (targetClass != null) {
			targets.add(targetClass);
		}
	}

	public Set<String> getTargets() {
		return targets;
	}

	@Override
	public String toString() {
		return String.format("Listener [listenerEnum=%s, listernerClass=%s, callbackMethod=%s, eventRegisteredInLayoutFile=%s, targets=%s]", type, listernerClass, callbackMethod, eventRegisteredInLayoutFile, targets);
	}

}
