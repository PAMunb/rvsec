package com.fdu.se.sootanalyze.model.out;

import soot.SootMethod;

public class MethodInfoOut {
	private String name;
	private String className;
	private String signature;
	private int modifiers;

	public MethodInfoOut(SootMethod method) {
		if (method != null) {
			this.name = method.getName();
			this.className = method.getDeclaringClass().getName();
			this.signature = method.getSignature();
			this.modifiers = method.getModifiers();
		}
	}

	public String getName() {
		return name;
	}

	public String getClassName() {
		return className;
	}

	public String getSignature() {
		return signature;
	}

	public int getModifiers() {
		return modifiers;
	}

	@Override
	public String toString() {
		return String.format("MethodInfoOut [name=%s, className=%s, signature=%s, modifiers=%s]", name, className, signature, modifiers);
	}

}
