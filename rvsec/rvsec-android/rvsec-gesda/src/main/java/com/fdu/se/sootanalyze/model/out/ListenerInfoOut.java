package com.fdu.se.sootanalyze.model.out;

import com.fdu.se.sootanalyze.model.Listener;
import com.fdu.se.sootanalyze.model.ListenerType;

public class ListenerInfoOut {
	private ListenerType type;
	private String listernerClass;
	private MethodInfoOut callbackMethod;
	private boolean registeredInFile;

	public ListenerInfoOut(Listener listener) {
		this.type = listener.getType();
		this.listernerClass = listener.getListernerClass();
		this.callbackMethod = new MethodInfoOut(listener.getCallbackMethod());
		this.registeredInFile = listener.isEventRegisteredInLayoutFile();
	}

	public ListenerType getType() {
		return type;
	}

	public String getListernerClass() {
		return listernerClass;
	}

	public MethodInfoOut getCallbackMethod() {
		return callbackMethod;
	}

	public boolean isRegisteredInFile() {
		return registeredInFile;
	}

	@Override
	public String toString() {
		return String.format("ListenerInfoOut [type=%s, listernerClass=%s, callbackMethod=%s, registeredInFile=%s]", type, listernerClass, callbackMethod, registeredInFile);
	}

}
