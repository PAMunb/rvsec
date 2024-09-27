package br.unb.cic.rvsec.reach.gesda;

public class MethodInfoOut {
	private String name;
	private String className;
	private String signature;
	private int modifiers;

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
