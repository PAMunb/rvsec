package br.unb.cic.rvsec.apk.model;

import java.util.Objects;

public class ActivityInfo {
	private String name, shortName, packageName;
	private boolean isMain = false;
	private String layoutFileName;

	public ActivityInfo(String name, boolean isMain) {
		setName(name);
		this.isMain = isMain;
	}

	public String getName() {
		return name;
	}

	private void setName(String name) {
		this.name = name;
		if(name.contains(".")) {
			this.packageName = name.substring(0, name.lastIndexOf('.'));
			this.shortName = name.substring(name.lastIndexOf('.') + 1);
		}else {
			this.packageName = "";
			this.shortName = name;
		}
			
		
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

	@Override
	public int hashCode() {
		return Objects.hash(isMain, layoutFileName, name, packageName, shortName);
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj)
			return true;
		if ((obj == null) || (getClass() != obj.getClass()))
			return false;
		ActivityInfo other = (ActivityInfo) obj;
		return isMain == other.isMain && Objects.equals(layoutFileName, other.layoutFileName) && Objects.equals(name, other.name) && Objects.equals(packageName, other.packageName) && Objects.equals(shortName, other.shortName);
	}

	@Override
	public String toString() {
		return String.format("ActivityInfo [name=%s, isMain=%s, layoutFileName=%s]", name, isMain, layoutFileName);
	}

}
