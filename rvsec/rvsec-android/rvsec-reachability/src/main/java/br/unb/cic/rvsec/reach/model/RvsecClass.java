package br.unb.cic.rvsec.reach.model;

import java.util.HashSet;
import java.util.Set;

import soot.SootClass;

public class RvsecClass {
	private final String className;
	private final boolean isActivity;
	private final boolean isMainActivity;

	private Set<RvsecMethod> methods = new HashSet<>();

	public RvsecClass(SootClass clazz, boolean isActivity, boolean isMainActivity) {
		this.className = clazz.getName();
		this.isActivity = isActivity;
		this.isMainActivity = isMainActivity;
	}

	public void addMethod(RvsecMethod method) {
		if (method != null) {
			methods.add(method);
		}
	}

	public void removeMethod(RvsecMethod method) {
		methods.remove(method);
	}

	public Set<RvsecMethod> getMethods() {
		return methods;
	}

	public String getClassName() {
		return className;
	}

	public boolean isActivity() {
		return isActivity;
	}

	public boolean isMainActivity() {
		return isMainActivity;
	}

}
