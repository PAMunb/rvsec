package br.unb.cic.rvsec.reach.writer.json;

import java.util.HashSet;
import java.util.Set;
import java.util.stream.Collectors;

import br.unb.cic.rvsec.reach.model.RvsecClass;

public class RvsecClassJson {
	private String className;
	private boolean isActivity;
	private boolean isMainActivity;
	private Set<RvsecMethodJson> methods = new HashSet<>();

	public RvsecClassJson(RvsecClass clazz) {
		this.className = clazz.getClassName();
		this.isActivity = clazz.isActivity();
		this.isMainActivity = clazz.isMainActivity();

		if (clazz.getMethods() != null) {
			methods = clazz.getMethods().stream().map(RvsecMethodJson::new).collect(Collectors.toSet());
		}
	}

	public String getClassName() {
		return className;
	}

	public void setClassName(String className) {
		this.className = className;
	}

	public boolean isActivity() {
		return isActivity;
	}

	public void setActivity(boolean isActivity) {
		this.isActivity = isActivity;
	}

	public boolean isMainActivity() {
		return isMainActivity;
	}

	public void setMainActivity(boolean isMainActivity) {
		this.isMainActivity = isMainActivity;
	}

	public Set<RvsecMethodJson> getMethods() {
		return methods;
	}

	public void setMethods(Set<RvsecMethodJson> methods) {
		this.methods = methods;
	}

}
