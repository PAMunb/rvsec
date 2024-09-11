package com.fdu.se.sootanalyze.model.xml;

import java.util.Objects;

import com.fdu.se.sootanalyze.model.info.RVSecInfo;

public class MethodInfo {
	private String name;
	private String signature;
	private int modifiers;

	private RVSecInfo rvsecInfo;

	public MethodInfo(String name, String signature, int modifiers) {
		this(name, signature, modifiers, new RVSecInfo());
	}

	public MethodInfo(String name, String signature, int modifiers, RVSecInfo rvsecInfo) {
		this.name = name;
		this.signature = signature;
		this.modifiers = modifiers;
		this.rvsecInfo = rvsecInfo;
	}

	public String getName() {
		return name;
	}

	public String getSignature() {
		return signature;
	}

	public int getModifiers() {
		return modifiers;
	}

	public RVSecInfo getRvsecInfo() {
		return rvsecInfo;
	}

	@Override
	public int hashCode() {
		return Objects.hash(modifiers, name, rvsecInfo, signature);
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj)
			return true;
		if ((obj == null) || (getClass() != obj.getClass()))
			return false;
		MethodInfo other = (MethodInfo) obj;
		return modifiers == other.modifiers && Objects.equals(name, other.name) && Objects.equals(rvsecInfo, other.rvsecInfo) && Objects.equals(signature, other.signature);
	}

	@Override
	public String toString() {
		return String.format("MethodInfo [name=%s, signature=%s, modifiers=%s, rvsecInfo=%s]", name, signature, modifiers, rvsecInfo);
	}

}
