package com.fdu.se.sootanalyze.model.out;

import com.fdu.se.sootanalyze.model.ListenerType;

public class ListenerInfoOut {
	private ListenerType type;
//	private String listernerClass;
	private MethodInfoOut callbackMethod;
	private boolean registeredInFile;

	public ListenerInfoOut() {
	}

//	public ListenerInfoOut(ListenerType type, String listernerClass, MethodInfoOut callbackMethod, boolean registeredInFile) {
//		this.type = type;
//		this.listernerClass = listernerClass;
//		this.callbackMethod = callbackMethod;
//		this.registeredInFile = registeredInFile;
//	}

	public ListenerType getType() {
		return type;
	}

	public void setType(ListenerType type) {
		this.type = type;
	}

	public MethodInfoOut getCallbackMethod() {
		return callbackMethod;
	}

	public void setCallbackMethod(MethodInfoOut callbackMethod) {
		this.callbackMethod = callbackMethod;
	}

	public boolean isRegisteredInFile() {
		return registeredInFile;
	}

	public void setRegisteredInFile(boolean registeredInFile) {
		this.registeredInFile = registeredInFile;
	}

	@Override
	public String toString() {
		return String.format("ListenerInfoOut [type=%s, callbackMethod=%s, registeredInFile=%s]", type, callbackMethod, registeredInFile);
	}

}
