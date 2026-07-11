package com.fdu.se.sootanalyze.model.out;

public class MethodInfoOut {
	private String name;
	private String className;
	private String signature;
	private int modifiers;
	
	public MethodInfoOut() {
	}

	public MethodInfoOut(String name, String className, String signature, int modifiers) {
		this.name = name;
		this.className = className;
		this.signature = signature;
		this.modifiers = modifiers;
	}

	public String getName() {
		return name;
	}

	public void setName(String name) {
		this.name = name;
	}

	public String getClassName() {
		return className;
	}

	public void setClassName(String className) {
		this.className = className;
	}

	public String getSignature() {
		return signature;
	}

	public void setSignature(String signature) {
		this.signature = signature;
	}

	public int getModifiers() {
		return modifiers;
	}

	public void setModifiers(int modifiers) {
		this.modifiers = modifiers;
	}

	@Override
	public String toString() {
		return String.format("MethodInfoOut [name=%s, className=%s, signature=%s, modifiers=%s]", name, className, signature, modifiers);
	}

}
