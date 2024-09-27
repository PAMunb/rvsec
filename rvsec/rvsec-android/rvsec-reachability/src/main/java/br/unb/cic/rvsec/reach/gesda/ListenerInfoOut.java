package br.unb.cic.rvsec.reach.gesda;

public class ListenerInfoOut {
	private ListenerType type;
	private String listernerClass;
	private MethodInfoOut callbackMethod;
	private boolean registeredInFile;

	public ListenerType getType() {
		return type;
	}

	public void setType(ListenerType type) {
		this.type = type;
	}

	public String getListernerClass() {
		return listernerClass;
	}

	public void setListernerClass(String listernerClass) {
		this.listernerClass = listernerClass;
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
		return String.format("ListenerInfoOut [type=%s, listernerClass=%s, callbackMethod=%s, registeredInFile=%s]", type, listernerClass, callbackMethod, registeredInFile);
	}

}
