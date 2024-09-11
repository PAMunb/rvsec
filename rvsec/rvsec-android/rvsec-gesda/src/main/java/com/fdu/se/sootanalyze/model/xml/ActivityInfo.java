package com.fdu.se.sootanalyze.model.xml;

import java.util.HashSet;
import java.util.Objects;
import java.util.Set;

public class ActivityInfo {
	private String name, shortName, packageName;
	private boolean isMain = false;
	private String layoutFileName;
	private Set<MethodInfo> methods = new HashSet<>();
	

	public ActivityInfo(String name, boolean isMain) {
		setName(name);
		this.isMain = isMain;
	}

	
	public String getName() {
		return name;
	}

	private void setName(String name) {
		this.name = name;
		this.packageName = name.substring(0, name.lastIndexOf('.'));
		this.shortName = name.substring(name.lastIndexOf('.') + 1);
	}

	public String getShortName() {
		return shortName;
	}

	public String getPackageName() {
		return packageName;
	}

	public boolean isMain() {
		return isMain;
	}

	public String getLayoutFileName() {
		return layoutFileName;
	}

	public void setLayoutFileName(String layoutFileName) {
		this.layoutFileName = layoutFileName;
	}

	public Set<MethodInfo> getMethods() {
		return methods;
	}

	public boolean addMethod(MethodInfo methodInfo) {
		return methods.add(methodInfo);
	}

	@Override
	public int hashCode() {
		return Objects.hash(isMain, layoutFileName, methods, name, packageName, shortName);
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj)
			return true;
		if ((obj == null) || (getClass() != obj.getClass()))
			return false;
		ActivityInfo other = (ActivityInfo) obj;
		return isMain == other.isMain && Objects.equals(layoutFileName, other.layoutFileName) && Objects.equals(methods, other.methods) && Objects.equals(name, other.name) && Objects.equals(packageName, other.packageName)
				&& Objects.equals(shortName, other.shortName);
	}

	@Override
	public String toString() {
		return String.format("ActivityInfo [name=%s, isMain=%s, layoutFileName=%s, methods=%s]", name, isMain, layoutFileName, methods);
	}

}
